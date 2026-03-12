#!/usr/bin/env python3
"""
Cortex Code Automated Demo Script
==================================
Spawns a real cortex interactive session in tmux, types demo prompts
with human-like speed, waits for responses, and records the terminal
window as a real MP4 video using ffmpeg screen capture (AVFoundation).

The script:
  1. Launches cortex in a detached tmux session
  2. Opens a visible Terminal.app window attached to tmux
  3. Positions/sizes the window to a known screen region
  4. Starts ffmpeg screen capture (cropped to the terminal window)
  5. Types prompts with human-like speed, auto-accepts permissions
  6. Stops recording when all prompts are complete

Usage:
    python3 cortex_demo.py                          # Record MP4
    python3 cortex_demo.py --no-record              # Run without recording
    python3 cortex_demo.py --prompts my_prompts.yaml  # Use custom prompts file

Requirements:
    - tmux (brew install tmux)
    - cortex CLI installed
    - ffmpeg (brew install ffmpeg) -- for recording
    - Screen Recording permission granted to Terminal.app
"""

import time
import random
import subprocess
import sys
import os
import re
import signal
import yaml

# ─── Configuration ────────────────────────────────────────────────────────────

# Typing speed: (min, max) seconds per character
TYPING_SPEED = (0.03, 0.08)

# Seconds to pause between prompts (so viewer can read the response)
PAUSE_BETWEEN_PROMPTS = 5

# Max seconds to wait for a single response (0 = no limit)
RESPONSE_TIMEOUT = 0

# How many seconds of no pane content change before we consider the response done
IDLE_THRESHOLD = 10

# Terminal dimensions (cols x rows) for the tmux session
TERMINAL_COLS = 140
TERMINAL_ROWS = 50

# Cortex connection to use
CONNECTION = "devrel"

# Session name for easy identification
SESSION_NAME = "Cortex Code Demo"

# tmux session name (internal)
TMUX_SESSION = "cortex_demo"

# Recording output (relative to current working directory)
MP4_FILE = os.path.join(os.getcwd(), "cortex_demo.mp4")

# Default prompts file (relative to current working directory)
PROMPTS_FILE = os.path.join(os.getcwd(), "cortex_demo_prompts.yaml")

# ─── ffmpeg screen capture settings ──────────────────────────────────────────

# AVFoundation device index for screen capture (run: ffmpeg -f avfoundation -list_devices true -i "")
SCREEN_DEVICE_INDEX = "3"

# Terminal window position and size (in screen pixels).
# These define where Terminal.app will be placed and the ffmpeg crop region.
# Adjust if your screen layout is different.
WINDOW_X = 100       # pixels from left edge
WINDOW_Y = 30        # pixels from top edge (below menu bar)
WINDOW_WIDTH = 1600  # window width in pixels
WINDOW_HEIGHT = 950  # window height (fits above Dock)

# ffmpeg recording settings
FFMPEG_FPS = 30
FFMPEG_CRF = 20  # quality: lower = better, 18-23 is good range

# ─── Tool allowlists ─────────────────────────────────────────────────────────

# Tools to pre-approve via --allowed-tools (no permission prompt).
# IMPORTANT: --allowed-tools acts as a whitelist -- any tool NOT listed
# here will be completely blocked (not just prompted).
ALLOWED_TOOLS = [
    # Read-only tools (completely safe)
    "Read", "Glob", "Grep",
    "web_search", "web_fetch",
    "data_diff", "fdbt",
    "enter_plan_mode", "exit_plan_mode", "ask_user_question",
    # Snowflake SQL execution
    "sql",
    # Bash -- allow most commands, block destructive ones via DISALLOWED_TOOLS
    "Bash",
    # Sub-agents (they have their own permission checks)
    "skill", "task",
    # Notebook operations (read/execute cells)
    "notebook_actions",
    # File write/edit (needed for most demos)
    "Edit", "Write",
]

# Tools that are completely blocked -- cannot be used at all.
DISALLOWED_TOOLS = [
    "Bash(rm -rf *)",
    "Bash(sudo *)",
    "Bash(git push *)", "Bash(git reset --hard *)", "Bash(git rebase *)",
]

# ─── Demo Prompts ─────────────────────────────────────────────────────────────


def load_prompts(path):
    """Load prompts from a YAML file. Returns a list of strings."""
    with open(path, "r") as f:
        data = yaml.safe_load(f)

    raw = data.get("prompts", [])
    prompts = []
    for item in raw:
        # Collapse multiline YAML into a single line
        text = " ".join(str(item).split()).strip()
        if text:
            prompts.append(text)

    if not prompts:
        log(f"WARNING: No prompts found in {path}")
        sys.exit(1)

    return prompts

# ─── Helpers ──────────────────────────────────────────────────────────────────

ANSI_RE = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]|\x1b\[\?[0-9]+[a-z]')


def strip_ansi(text):
    """Remove ANSI escape codes from text."""
    return ANSI_RE.sub('', text)


def log(msg):
    """Print a timestamped log message to stderr."""
    timestamp = time.strftime("%H:%M:%S")
    print(f"\033[90m[{timestamp}] {msg}\033[0m", file=sys.stderr)


def tmux(*args):
    """Run a tmux command and return its output."""
    cmd = ["tmux"] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout


def tmux_session_exists():
    """Check if the tmux session is still alive."""
    result = subprocess.run(
        ["tmux", "has-session", "-t", TMUX_SESSION],
        capture_output=True,
    )
    return result.returncode == 0


def capture_pane():
    """Capture the current tmux pane content, stripped of ANSI codes."""
    raw = tmux("capture-pane", "-t", TMUX_SESSION, "-p")
    return strip_ansi(raw)


def send_keys(*keys):
    """Send keystrokes to the tmux session."""
    tmux("send-keys", "-t", TMUX_SESSION, *keys)


def type_prompt(text):
    """
    Type text character-by-character into the cortex TUI with human-like delays,
    then press Enter to submit.
    """
    send_keys("Escape")
    time.sleep(0.5)

    for char in text:
        if char == " ":
            send_keys("Space")
        else:
            send_keys("-l", char)

        delay = random.uniform(*TYPING_SPEED)
        if char in ".,!?;:":
            delay += random.uniform(0.05, 0.12)
        time.sleep(delay)

    time.sleep(random.uniform(0.3, 0.6))
    send_keys("Enter")


def _is_yes_no_prompt(content):
    """Check if the screen shows a compact yes/no numbered prompt.
    
    Looks at the last few non-empty lines for patterns like:
      1. Yes
      2. No
    This avoids matching numbered lists in regular output.
    """
    lines = [l.strip() for l in content.strip().splitlines() if l.strip()]
    tail = lines[-6:] if len(lines) >= 6 else lines
    tail_text = "\n".join(tail)
    # Must have both "1." and "2." in the tail, with Yes/No nearby
    if "1." not in tail_text or "2." not in tail_text:
        return False
    # Check for yes/no style options (case-insensitive)
    lower = tail_text.lower()
    return ("yes" in lower and "no" in lower)


def _detect_interactive_prompt(content):
    """Detect if the screen is showing an interactive prompt and return the type.

    Returns one of:
        "numbered"  -- numbered options (1. / 2.) -- send "1"
        "radio"     -- radio buttons with cursor (❯ or >) -- send Enter
        "checkbox"  -- checkbox selection (◻/◼/☐/☑/[ ]/[x]) -- send Space then Enter
        None        -- not an interactive prompt
    """
    # Radio buttons: cursor indicator with circle options
    if "❯" in content or "›" in content:
        if "○" in content or "●" in content or "◯" in content:
            return "radio"

    # Checkbox: square markers
    if any(marker in content for marker in ["◻", "◼", "☐", "☑", "[ ]", "[x]", "◯", "●"]):
        # Checkboxes often have a submit/confirm at the bottom
        if "❯" in content or "›" in content:
            return "checkbox"

    # Numbered options: 1. and 2. present
    if "1." in content and "2." in content:
        return "numbered"

    return None


def wait_for_response(timeout=RESPONSE_TIMEOUT):
    """
    Smart wait: polls the tmux pane to detect when cortex finishes responding.

    Detection strategy:
    1. Wait for the input prompt ("Type your message") to DISAPPEAR
    2. Watch for activity (pane content changes, "esc to interrupt")
    3. Done when "Type your message" reappears or content is idle
    4. Auto-send "1" for permission prompts
    """
    MIN_WAIT = 10
    start = time.time()
    last_activity = time.time()
    saw_working = False
    prompt_disappeared = False
    last_content = ""
    interactions_sent = 0
    stable_prompt_count = 0  # how many consecutive polls the screen has been stable in interactive state

    while timeout == 0 or (time.time() - start < timeout):
        time.sleep(1)

        if not tmux_session_exists():
            log("ERROR: tmux session died")
            return False

        content = capture_pane()

        # Phase 1: Wait for the input prompt to disappear
        if not prompt_disappeared:
            if "Type your message" not in content:
                prompt_disappeared = True
                saw_working = True
                last_activity = time.time()
                log("  Cortex is processing...")
            continue

        # Phase 2: Monitor for completion
        if content != last_content:
            last_activity = time.time()
            saw_working = True
        last_content = content

        if "esc to interrupt" in content:
            saw_working = True
            last_activity = time.time()

        # Done: input prompt reappears
        if "Type your message" in content:
            elapsed = time.time() - start
            if elapsed >= MIN_WAIT:
                log(f"  Response complete ({elapsed:.0f}s)")
                return True

        # Auto-accept interactive prompts (permissions, plan mode, confirmations, etc.)
        # Strategy: detect that cortex is in an interactive state (no output indicators)
        # and the screen has been stable for 2+ polls, then respond generically.
        if interactions_sent < 50:
            is_outputting = (
                "Type your message" in content
                or "esc to interrupt" in content
            )

            if not is_outputting:
                prompt_type = _detect_interactive_prompt(content)

                if prompt_type and content == last_content:
                    stable_prompt_count += 1
                else:
                    stable_prompt_count = 0

                # Wait for screen to stabilize (2+ consecutive polls unchanged)
                # before sending input, to avoid reacting to partial renders
                if prompt_type and stable_prompt_count >= 2:
                    if prompt_type == "radio":
                        log("  Interactive prompt (radio) -- sending Enter")
                        time.sleep(0.3)
                        send_keys("Enter")
                    elif prompt_type == "checkbox":
                        log("  Interactive prompt (checkbox) -- selecting first + submit")
                        time.sleep(0.3)
                        send_keys("Space")
                        time.sleep(0.5)
                        send_keys("Enter")
                    elif prompt_type == "numbered":
                        log("  Interactive prompt (numbered) -- sending '1'")
                        time.sleep(0.3)
                        send_keys("1")

                    interactions_sent += 1
                    last_activity = time.time()
                    saw_working = True
                    stable_prompt_count = 0
            else:
                stable_prompt_count = 0

        # Idle check
        elapsed = time.time() - start
        idle_time = time.time() - last_activity
        if saw_working and idle_time > IDLE_THRESHOLD and elapsed >= MIN_WAIT:
            log(f"  Response appears complete (idle {idle_time:.0f}s, total {elapsed:.0f}s)")
            return True

    log("WARNING: timed out waiting for response")
    return False


def wait_for_connection():
    """Wait for cortex to fully connect to Snowflake."""
    log("Waiting for cortex to connect...")
    start = time.time()
    while time.time() - start < 45:
        time.sleep(2)
        if not tmux_session_exists():
            log("ERROR: tmux session died during startup")
            return False
        content = capture_pane()
        if CONNECTION in content and "Connecting" not in content:
            if time.time() - start >= 8:
                log("Connected.")
                return True
    log("Connection may still be in progress, continuing anyway...")
    return True


def run_demo_prompts_only(prompts):
    """Type prompts and wait for responses. Assumes cortex is already connected."""
    log("Starting demo prompts.\n")

    for i, prompt in enumerate(prompts, 1):
        log(f"--- Prompt {i}/{len(prompts)} ---")
        log(f"Typing: {prompt[:80]}{'...' if len(prompt) > 80 else ''}")

        type_prompt(prompt)
        log("Submitted. Waiting for response...")

        success = wait_for_response()
        if success:
            log(f"Prompt {i} complete.")
        else:
            log(f"Prompt {i} may not have completed fully. Continuing anyway.")

        if i < len(prompts):
            log(f"Pausing {PAUSE_BETWEEN_PROMPTS}s before next prompt...")
            time.sleep(PAUSE_BETWEEN_PROMPTS)

    log("\nAll prompts complete. Pausing 5s so viewer can read the output...")
    time.sleep(5)
    return True


# ─── Terminal window management ──────────────────────────────────────────────


def open_terminal_with_tmux():
    """
    Open a Terminal.app window attached to the tmux session,
    positioned and sized for consistent screen capture.
    Uses the Basic (default) profile which has SF Mono font.
    Returns True if successful.
    """
    applescript = f'''
    tell application "Terminal"
        activate
        set newTab to do script "tmux attach -t {TMUX_SESSION}"
        delay 1
        set bounds of front window to {{{WINDOW_X}, {WINDOW_Y}, {WINDOW_X + WINDOW_WIDTH}, {WINDOW_Y + WINDOW_HEIGHT}}}
        -- Use Basic (default) profile -- has SF Mono which renders all Unicode correctly
        set current settings of front window to first settings set whose name is "Basic"
    end tell
    '''
    try:
        subprocess.run(["osascript", "-e", applescript],
                       capture_output=True, text=True, timeout=10)
        log(f"Terminal.app window opened at ({WINDOW_X}, {WINDOW_Y}) size {WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        return True
    except Exception as e:
        log(f"WARNING: AppleScript failed: {e}")
        log("Falling back -- please manually attach: tmux attach -t cortex_demo")
        return False


def get_retina_scale():
    """
    Detect Retina scaling factor by comparing physical resolution
    to the "UI Looks like" resolution from system_profiler.
    Returns 2 for Retina, 1 for standard/external monitors.
    """
    try:
        result = subprocess.run(
            ["system_profiler", "SPDisplaysDataType"],
            capture_output=True, text=True, timeout=10,
        )
        output = result.stdout
        # Find physical resolution and "UI Looks like" resolution
        res_match = re.search(r'Resolution:\s*(\d+)\s*x\s*(\d+)', output)
        ui_match = re.search(r'UI Looks like:\s*(\d+)\s*x\s*(\d+)', output)
        if res_match and ui_match:
            phys_w = int(res_match.group(1))
            ui_w = int(ui_match.group(1))
            scale = max(1, phys_w // ui_w)
            log(f"  Display: {phys_w}x{int(res_match.group(2))} physical, "
                f"UI={ui_w}x{int(ui_match.group(2))}, scale={scale}x")
            return scale
        # Fallback: if "Retina" appears anywhere, assume 2x
        if "Retina" in output:
            return 2
        return 1
    except Exception:
        return 1  # Safe default: no scaling


def _kill_stale_ffmpeg():
    """Kill any leftover ffmpeg screen-capture processes from previous runs."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "ffmpeg.*avfoundation"],
            capture_output=True, text=True,
        )
        pids = result.stdout.strip().split()
        if pids and pids[0]:
            log(f"Killing {len(pids)} stale ffmpeg process(es): {', '.join(pids)}")
            for pid in pids:
                try:
                    os.kill(int(pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass
            time.sleep(1)
    except Exception:
        pass


def start_ffmpeg_recording(output_path):
    """
    Start ffmpeg screen capture in the background.
    Records the full screen and crops to the terminal window region.
    Returns the ffmpeg subprocess (Popen object).
    """
    # Kill any stale ffmpeg processes that might be hogging the AVFoundation device
    _kill_stale_ffmpeg()

    scale = get_retina_scale()

    # ffmpeg avfoundation captures at physical (Retina) resolution,
    # but window coordinates from AppleScript are in logical (point) coordinates.
    # So we multiply by the scale factor for the crop filter.
    crop_w = WINDOW_WIDTH * scale
    crop_h = WINDOW_HEIGHT * scale
    crop_x = WINDOW_X * scale
    crop_y = WINDOW_Y * scale

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-f", "avfoundation",
        "-capture_cursor", "1",        # include cursor in recording
        "-framerate", str(FFMPEG_FPS),
        "-pixel_format", "uyvy422",
        "-i", f"{SCREEN_DEVICE_INDEX}:none",
        "-vf", f"crop={crop_w}:{crop_h}:{crop_x}:{crop_y},format=yuv420p",
        "-c:v", "libx264",
        "-preset", "veryfast",          # fast encoding to keep up in realtime
        "-crf", str(FFMPEG_CRF),
        "-movflags", "frag_keyframe+empty_moov",  # write moov upfront so file is playable even if ffmpeg dies
        "-y",                           # overwrite output
        output_path,
    ]

    log(f"Starting ffmpeg recording -> {output_path}")
    log(f"  Crop: {crop_w}x{crop_h} at ({crop_x},{crop_y}) [scale={scale}x]")
    log(f"  FPS: {FFMPEG_FPS}, CRF: {FFMPEG_CRF}")

    # Write ffmpeg stderr to a log file instead of PIPE to avoid
    # buffer deadlock on long recordings (ffmpeg writes a LOT of progress)
    ffmpeg_log_path = output_path + ".log"
    ffmpeg_log = open(ffmpeg_log_path, "w")

    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,       # keep stdin open so we can send 'q' to quit
        stdout=subprocess.DEVNULL,
        stderr=ffmpeg_log,
        # Put ffmpeg in its own process group so Python's signal handlers
        # don't accidentally kill it before it can finalize the file
        preexec_fn=os.setpgrp,
    )

    # Give ffmpeg a moment to initialize
    time.sleep(2)

    if proc.poll() is not None:
        ffmpeg_log.close()
        with open(ffmpeg_log_path, "r") as f:
            err = f.read()
        log(f"ERROR: ffmpeg exited immediately: {err[-500:]}")
        return None

    log("ffmpeg is recording.")
    return proc, ffmpeg_log, ffmpeg_log_path


def stop_ffmpeg_recording(ffmpeg_info):
    """Gracefully stop ffmpeg using multiple strategies."""
    proc, ffmpeg_log, ffmpeg_log_path = ffmpeg_info

    if proc is None or proc.poll() is not None:
        ffmpeg_log.close()
        return

    log("Stopping ffmpeg recording...")

    # Strategy 1: Send 'q' to stdin (ffmpeg's native quit command)
    try:
        log("  Sending 'q' to ffmpeg stdin...")
        proc.stdin.write(b"q")
        proc.stdin.flush()
        proc.stdin.close()
        proc.wait(timeout=15)
        log("  ffmpeg stopped cleanly via 'q' command.")
    except subprocess.TimeoutExpired:
        # Strategy 2: Send SIGINT directly to the process
        log("  'q' didn't work, sending SIGINT...")
        try:
            proc.send_signal(signal.SIGINT)
            proc.wait(timeout=10)
            log("  ffmpeg stopped via SIGINT.")
        except subprocess.TimeoutExpired:
            # Strategy 3: Force kill (SIGKILL -- AVFoundation-hung ffmpeg ignores SIGTERM)
            log("  SIGINT didn't work, force killing (SIGKILL)...")
            proc.kill()
            proc.wait(timeout=5)
    except Exception as e:
        log(f"  Error stopping ffmpeg: {e}")
        try:
            proc.kill()
            proc.wait(timeout=5)
        except Exception:
            pass

    ffmpeg_log.close()

    # Print summary from ffmpeg log
    try:
        with open(ffmpeg_log_path, "r") as f:
            log_content = f.read()
        for line in log_content.split("\n"):
            if "frame=" in line and "time=" in line:
                log(f"  {line.strip()}")
        # Clean up log file
        os.remove(ffmpeg_log_path)
    except Exception:
        pass


# ─── Main ─────────────────────────────────────────────────────────────────────


def main():
    record = "--no-record" not in sys.argv

    # Parse --prompts <file> argument
    prompts_file = PROMPTS_FILE
    if "--prompts" in sys.argv:
        idx = sys.argv.index("--prompts")
        if idx + 1 < len(sys.argv):
            prompts_file = os.path.abspath(sys.argv[idx + 1])

    # Load prompts from file
    log(f"Loading prompts from {prompts_file}")
    prompts = load_prompts(prompts_file)

    log("Starting Cortex Code demo...")
    log(f"Connection: {CONNECTION}")
    log(f"Prompts: {len(prompts)}")
    log(f"Recording: {'ffmpeg screen capture' if record else 'disabled'}")
    print(file=sys.stderr)

    # Kill any existing demo session
    subprocess.run(["tmux", "kill-session", "-t", TMUX_SESSION],
                   capture_output=True)

    # Build the cortex command
    allowed_tools_str = " ".join(f'"{t}"' for t in ALLOWED_TOOLS)
    disallowed_tools_str = " ".join(f'"{t}"' for t in DISALLOWED_TOOLS)
    cortex_cmd = (
        f"cortex "
        f"--connection {CONNECTION} "
        f"--no-auto-update "
        f'--session-name "{SESSION_NAME}" '
        f"--allowed-tools {allowed_tools_str} "
        f"--disallowed-tools {disallowed_tools_str}"
    )

    # Start cortex in a detached tmux session
    log("Launching cortex in tmux...")
    subprocess.run([
        "tmux", "new-session", "-d",
        "-s", TMUX_SESSION,
        "-x", str(TERMINAL_COLS),
        "-y", str(TERMINAL_ROWS),
        cortex_cmd,
    ])
    tmux("set-option", "-t", TMUX_SESSION, "status", "off")

    # Wait for cortex to connect before doing anything else
    wait_for_connection()
    time.sleep(2)

    ffmpeg_info = None

    try:
        if record:
            # ── ffmpeg recording mode ──

            # Open a visible Terminal.app window attached to the tmux session
            log("Opening Terminal window for screen capture...")
            open_terminal_with_tmux()
            time.sleep(3)  # let window settle

            # Start ffmpeg screen capture (crops to terminal window)
            ffmpeg_info = start_ffmpeg_recording(MP4_FILE)
            if ffmpeg_info is None:
                log("ERROR: ffmpeg failed to start. Running without recording.")
                record = False
            else:
                time.sleep(1)  # brief pause so recording captures the ready state

        # Run the demo prompts (same whether recording or not)
        run_demo_prompts_only(prompts)

    except KeyboardInterrupt:
        log("\nInterrupted by user (Ctrl+C).")
    finally:
        # Always stop ffmpeg cleanly so the MP4 is finalized
        if record and ffmpeg_info:
            stop_ffmpeg_recording(ffmpeg_info)

            # Check output file
            if os.path.exists(MP4_FILE):
                size_mb = os.path.getsize(MP4_FILE) / (1024 * 1024)
                log(f"Recording saved: {MP4_FILE} ({size_mb:.1f} MB)")
                log(f"  Play:  open {MP4_FILE}")
            else:
                log("WARNING: MP4 file was not created")

        # Clean up
        log("Cleaning up...")

        # Close the Terminal.app window we opened
        try:
            subprocess.run(
                ["osascript", "-e", '''
                tell application "Terminal"
                    close front window
                end tell
                '''],
                capture_output=True, timeout=5,
            )
        except Exception:
            pass

        # Exit cortex and kill tmux
        send_keys("C-c")
        time.sleep(2)
        subprocess.run(["tmux", "kill-session", "-t", TMUX_SESSION],
                       capture_output=True)

        print(file=sys.stderr)
        log("Demo complete!")

        if record:
            log("")
            log(f"  MP4: {MP4_FILE}")
            log(f"  Play: open {MP4_FILE}")


if __name__ == "__main__":
    main()
