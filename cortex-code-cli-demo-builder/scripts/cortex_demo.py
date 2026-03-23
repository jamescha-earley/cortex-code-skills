#!/usr/bin/env python3
"""
Cortex Code Demo Launcher
=========================
Thin helper for managing tmux sessions, Terminal.app windows, and ffmpeg
screen recording. The actual demo driving (typing prompts, reading screen
state, deciding when to proceed) is done by Cortex Code itself.

Subcommands:
    launch    Start tmux + cortex, optionally open Terminal + ffmpeg
    stop      Stop ffmpeg recording and clean up tmux session
    capture   Print the current tmux pane content (stripped of ANSI)
    type      Type text into the tmux pane with human-like speed
    send      Send raw tmux keys (e.g., "Enter", "Space", "1")
    status    Check if tmux session is alive and cortex is connected
    prompts   Load and print prompts from a YAML file

Usage:
    python3 cortex_demo.py launch [--no-record]
    python3 cortex_demo.py stop
    python3 cortex_demo.py capture
    python3 cortex_demo.py type "What tables do we have?"
    python3 cortex_demo.py send Enter
    python3 cortex_demo.py send 1
    python3 cortex_demo.py status
    python3 cortex_demo.py prompts [path/to/prompts.yaml]

Requirements:
    - tmux (brew install tmux)
    - cortex CLI installed
    - ffmpeg (brew install ffmpeg) -- for recording
    - Screen Recording permission granted to Terminal.app
    - pyyaml (pip3 install pyyaml)
"""

import time
import random
import subprocess
import sys
import os
import re
import signal
import json
import unicodedata

# ─── Configuration ────────────────────────────────────────────────────────────

# Typing speed: (min, max) seconds per character
TYPING_SPEED = (0.03, 0.08)

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

SCREEN_DEVICE_INDEX = "3"
WINDOW_X = 100
WINDOW_Y = 30
WINDOW_WIDTH = 1600
WINDOW_HEIGHT = 950
FFMPEG_FPS = 30
FFMPEG_CRF = 20

# ─── Tool allowlists ─────────────────────────────────────────────────────────

ALLOWED_TOOLS = [
    "Read", "Glob", "Grep",
    "web_search", "web_fetch",
    "data_diff", "fdbt",
    "enter_plan_mode", "exit_plan_mode", "ask_user_question",
    "sql",
    "Bash",
    "skill", "task",
    "notebook_actions",
    "Edit", "Write",
]

DISALLOWED_TOOLS = [
    "Bash(rm -rf *)",
    "Bash(sudo *)",
    "Bash(git push *)", "Bash(git reset --hard *)", "Bash(git rebase *)",
]

# ─── State file for ffmpeg process info ──────────────────────────────────────

STATE_FILE = os.path.join(os.getcwd(), ".cortex_demo_state.json")


def _save_state(data):
    with open(STATE_FILE, "w") as f:
        json.dump(data, f)


def _load_state():
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _clear_state():
    try:
        os.remove(STATE_FILE)
    except FileNotFoundError:
        pass


# ─── Helpers ──────────────────────────────────────────────────────────────────

ANSI_RE = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]|\x1b\[\?[0-9]+[a-z]')


def mp4_name_from_prompts_file(prompts_path):
    """Derive a descriptive MP4 filename from the first comment line in a prompts YAML.

    Reads the file looking for a line like:
        # Cortex AI Functions: Document Intelligence Demo
    and turns it into:
        cortex_ai_functions_document_intelligence_demo.mp4

    Falls back to the default MP4_FILE if nothing usable is found.
    """
    try:
        with open(prompts_path, "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("#") and len(line) > 2:
                    # Strip leading '#' and whitespace
                    title = line.lstrip("#").strip()
                    if not title:
                        continue
                    # Normalise unicode, lowercase, replace non-alphanum with underscore
                    title = unicodedata.normalize("NFKD", title)
                    slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
                    if slug:
                        return os.path.join(os.getcwd(), f"{slug}.mp4")
    except (FileNotFoundError, PermissionError):
        pass
    return MP4_FILE


def strip_ansi(text):
    return ANSI_RE.sub('', text)


def log(msg):
    timestamp = time.strftime("%H:%M:%S")
    print(f"\033[90m[{timestamp}] {msg}\033[0m", file=sys.stderr)


def tmux(*args):
    cmd = ["tmux"] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout


def tmux_session_exists():
    result = subprocess.run(
        ["tmux", "has-session", "-t", TMUX_SESSION],
        capture_output=True,
    )
    return result.returncode == 0


def capture_pane():
    raw = tmux("capture-pane", "-t", TMUX_SESSION, "-p")
    return strip_ansi(raw)


def send_keys(*keys):
    tmux("send-keys", "-t", TMUX_SESSION, *keys)


def type_text(text):
    """Type text character-by-character with human-like delays, then press Enter."""
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


# ─── Terminal window management ──────────────────────────────────────────────


def open_terminal_with_tmux():
    applescript = f'''
    tell application "Terminal"
        activate
        set newTab to do script "tmux attach -t {TMUX_SESSION}"
        delay 1
        set bounds of front window to {{{WINDOW_X}, {WINDOW_Y}, {WINDOW_X + WINDOW_WIDTH}, {WINDOW_Y + WINDOW_HEIGHT}}}
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
        return False


def get_retina_scale():
    try:
        result = subprocess.run(
            ["system_profiler", "SPDisplaysDataType"],
            capture_output=True, text=True, timeout=10,
        )
        output = result.stdout
        res_match = re.search(r'Resolution:\s*(\d+)\s*x\s*(\d+)', output)
        ui_match = re.search(r'UI Looks like:\s*(\d+)\s*x\s*(\d+)', output)
        if res_match and ui_match:
            phys_w = int(res_match.group(1))
            ui_w = int(ui_match.group(1))
            scale = max(1, phys_w // ui_w)
            log(f"  Display: {phys_w}x{int(res_match.group(2))} physical, "
                f"UI={ui_w}x{int(ui_match.group(2))}, scale={scale}x")
            return scale
        if "Retina" in output:
            return 2
        return 1
    except Exception:
        return 1


# ─── ffmpeg management ───────────────────────────────────────────────────────


def _kill_stale_ffmpeg():
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
    _kill_stale_ffmpeg()
    scale = get_retina_scale()
    crop_w = WINDOW_WIDTH * scale
    crop_h = WINDOW_HEIGHT * scale
    crop_x = WINDOW_X * scale
    crop_y = WINDOW_Y * scale

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-f", "avfoundation",
        "-capture_cursor", "1",
        "-framerate", str(FFMPEG_FPS),
        "-pixel_format", "uyvy422",
        "-i", f"{SCREEN_DEVICE_INDEX}:none",
        "-vf", f"crop={crop_w}:{crop_h}:{crop_x}:{crop_y},format=yuv420p",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", str(FFMPEG_CRF),
        "-movflags", "frag_keyframe+empty_moov",
        "-y",
        output_path,
    ]

    log(f"Starting ffmpeg recording -> {output_path}")
    log(f"  Crop: {crop_w}x{crop_h} at ({crop_x},{crop_y}) [scale={scale}x]")

    ffmpeg_log_path = output_path + ".log"
    ffmpeg_log = open(ffmpeg_log_path, "w")

    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=ffmpeg_log,
        preexec_fn=os.setpgrp,
    )

    time.sleep(2)

    if proc.poll() is not None:
        ffmpeg_log.close()
        with open(ffmpeg_log_path, "r") as f:
            err = f.read()
        log(f"ERROR: ffmpeg exited immediately: {err[-500:]}")
        return None

    log("ffmpeg is recording.")
    # Save PID so stop command can find it later
    _save_state({
        "ffmpeg_pid": proc.pid,
        "ffmpeg_log_path": ffmpeg_log_path,
        "mp4_path": output_path,
    })
    ffmpeg_log.close()  # close our handle; ffmpeg keeps writing via its own fd
    return proc.pid


def stop_ffmpeg_recording():
    state = _load_state()
    pid = state.get("ffmpeg_pid")
    ffmpeg_log_path = state.get("ffmpeg_log_path")
    mp4_path = state.get("mp4_path", MP4_FILE)

    if pid is None:
        log("No ffmpeg process found in state file.")
        return

    log(f"Stopping ffmpeg (PID {pid})...")

    # Strategy 1: SIGINT (like Ctrl-C, ffmpeg finalizes the file)
    try:
        os.kill(pid, signal.SIGINT)
        # Wait for it to exit
        for _ in range(15):
            time.sleep(1)
            try:
                os.kill(pid, 0)  # check if alive
            except ProcessLookupError:
                log("  ffmpeg stopped cleanly via SIGINT.")
                break
        else:
            # Strategy 2: SIGKILL
            log("  SIGINT didn't work, force killing...")
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    except ProcessLookupError:
        log("  ffmpeg already exited.")

    # Report on the recording
    if os.path.exists(mp4_path):
        size_mb = os.path.getsize(mp4_path) / (1024 * 1024)
        log(f"Recording saved: {mp4_path} ({size_mb:.1f} MB)")
    else:
        log("WARNING: MP4 file was not created")

    # Clean up log file
    if ffmpeg_log_path:
        try:
            os.remove(ffmpeg_log_path)
        except FileNotFoundError:
            pass

    _clear_state()


# ─── Subcommands ─────────────────────────────────────────────────────────────


def cmd_launch(args):
    """Launch tmux session with cortex, optionally open Terminal + start recording."""
    record = "--no-record" not in args

    # Determine MP4 filename from --prompts flag if provided
    mp4_path = MP4_FILE
    if "--prompts" in args:
        idx = args.index("--prompts")
        if idx + 1 < len(args):
            prompts_path = os.path.abspath(args[idx + 1])
            mp4_path = mp4_name_from_prompts_file(prompts_path)

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
        f"--disallowed-tools {disallowed_tools_str} "
        f"--auto-accept-plans"
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

    # Wait for cortex to connect
    log("Waiting for cortex to connect...")
    start = time.time()
    connected = False
    while time.time() - start < 45:
        time.sleep(2)
        if not tmux_session_exists():
            log("ERROR: tmux session died during startup")
            sys.exit(1)
        content = capture_pane()
        if CONNECTION in content and "Connecting" not in content:
            if time.time() - start >= 8:
                log("Connected.")
                connected = True
                break
    if not connected:
        log("Connection may still be in progress, continuing anyway...")

    time.sleep(2)

    if record:
        log("Opening Terminal window for screen capture...")
        open_terminal_with_tmux()
        time.sleep(3)

        ffmpeg_pid = start_ffmpeg_recording(mp4_path)
        if ffmpeg_pid is None:
            log("ERROR: ffmpeg failed to start.")
            sys.exit(1)
        time.sleep(1)

    # Print status as JSON for Cortex Code to parse
    print(json.dumps({
        "status": "ready",
        "session": TMUX_SESSION,
        "recording": record,
        "mp4_path": mp4_path if record else None,
    }))


def cmd_stop(args):
    """Stop recording and clean up."""
    state = _load_state()

    # Stop ffmpeg if recording
    if state.get("ffmpeg_pid"):
        stop_ffmpeg_recording()

    # Close Terminal.app window
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
    if tmux_session_exists():
        send_keys("C-c")
        time.sleep(2)
        subprocess.run(["tmux", "kill-session", "-t", TMUX_SESSION],
                       capture_output=True)

    mp4_path = state.get("mp4_path", MP4_FILE)
    if os.path.exists(mp4_path):
        size_mb = os.path.getsize(mp4_path) / (1024 * 1024)
        print(json.dumps({
            "status": "stopped",
            "mp4_path": mp4_path,
            "mp4_size_mb": round(size_mb, 1),
        }))
    else:
        print(json.dumps({"status": "stopped", "mp4_path": None}))

    log("Demo session cleaned up.")


def cmd_capture(args):
    """Capture and print the current tmux pane content."""
    if not tmux_session_exists():
        print("ERROR: tmux session not found", file=sys.stderr)
        sys.exit(1)
    print(capture_pane())


def cmd_type(args):
    """Type text into the tmux pane with human-like speed and press Enter."""
    if not args:
        print("Usage: cortex_demo.py type \"text to type\"", file=sys.stderr)
        sys.exit(1)
    text = " ".join(args)
    if not tmux_session_exists():
        print("ERROR: tmux session not found", file=sys.stderr)
        sys.exit(1)
    type_text(text)
    log(f"Typed: {text[:80]}{'...' if len(text) > 80 else ''}")


def cmd_send(args):
    """Send raw tmux keys (e.g., Enter, Space, 1, C-c)."""
    if not args:
        print("Usage: cortex_demo.py send <key> [key...]", file=sys.stderr)
        sys.exit(1)
    if not tmux_session_exists():
        print("ERROR: tmux session not found", file=sys.stderr)
        sys.exit(1)
    send_keys(*args)
    log(f"Sent keys: {' '.join(args)}")


def cmd_status(args):
    """Print session status as JSON."""
    alive = tmux_session_exists()
    content = capture_pane() if alive else ""
    state = _load_state()

    print(json.dumps({
        "session_alive": alive,
        "recording": bool(state.get("ffmpeg_pid")),
        "mp4_path": state.get("mp4_path"),
    }))


def cmd_prompts(args):
    """Load and print prompts from a YAML file."""
    import yaml

    path = args[0] if args else PROMPTS_FILE
    path = os.path.abspath(path)

    with open(path, "r") as f:
        data = yaml.safe_load(f)

    raw = data.get("prompts", [])
    prompts = []
    for item in raw:
        text = " ".join(str(item).split()).strip()
        if text:
            prompts.append(text)

    if not prompts:
        print(f"WARNING: No prompts found in {path}", file=sys.stderr)
        sys.exit(1)

    # Print as JSON for easy parsing
    print(json.dumps({"prompts": prompts, "file": path}))


# ─── Main ────────────────────────────────────────────────────────────────────


COMMANDS = {
    "launch": cmd_launch,
    "stop": cmd_stop,
    "capture": cmd_capture,
    "type": cmd_type,
    "send": cmd_send,
    "status": cmd_status,
    "prompts": cmd_prompts,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print("Usage: cortex_demo.py <command> [args...]", file=sys.stderr)
        print(f"Commands: {', '.join(COMMANDS.keys())}", file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]
    args = sys.argv[2:]
    COMMANDS[command](args)


if __name__ == "__main__":
    main()
