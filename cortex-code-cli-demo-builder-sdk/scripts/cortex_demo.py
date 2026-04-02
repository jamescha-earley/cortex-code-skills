#!/usr/bin/env python3
"""
Cortex Code Demo Launcher
=========================
Manages tmux sessions, Terminal.app windows, ffmpeg screen recording,
and orchestrates the full demo flow using the Cortex Code Agent SDK
for reliable completion detection.

Subcommands:
    launch      Start tmux + cortex, optionally open Terminal + ffmpeg
    stop        Stop ffmpeg recording and clean up tmux session
    capture     Print the current tmux pane content (stripped of ANSI)
    type        Type text into the tmux pane with human-like speed
    send        Send raw tmux keys (e.g., "Enter", "Space", "1")
    status      Check if tmux session is alive and cortex is connected
    prompts     Load and print prompts from a YAML file
    preflight   Run prompts through SDK headlessly to validate and build manifest
    drive       Orchestrate the full demo: type prompts, detect completion, handle interactions

Usage:
    python3 cortex_demo.py launch [--no-record] [--prompts file.yaml]
    python3 cortex_demo.py preflight --prompts file.yaml [--connection devrel]
    python3 cortex_demo.py drive --prompts file.yaml [--manifest manifest.json]
    python3 cortex_demo.py stop

Requirements:
    - tmux (brew install tmux)
    - cortex CLI installed
    - ffmpeg (brew install ffmpeg) -- for recording
    - Screen Recording permission granted to Terminal.app
    - pyyaml (pip3 install pyyaml)
    - cortex-code-agent-sdk (pip3 install cortex-code-agent-sdk)
"""

import asyncio
import time
import random
import subprocess
import sys
import os
import re
import signal
import json
import unicodedata
from enum import Enum

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


# ─── Pane State Machine ──────────────────────────────────────────────────────


class PaneState(Enum):
    """Observable states of the cortex CLI pane."""
    PROCESSING = "processing"    # Agent is working (esc to interrupt visible)
    INTERACTIVE = "interactive"  # A permission/question prompt is waiting
    DONE = "done"                # Input bar visible, agent idle
    UNKNOWN = "unknown"          # Can't determine state


# Regex patterns for interactive UI elements
_RE_RADIO = re.compile(r'[❯›]\s*[○●]')
_RE_NUMBERED = re.compile(r'^\s*\d+\.\s+\S', re.MULTILINE)
_RE_CHECKBOX = re.compile(r'[◻◼☐☑]')


def classify_pane(content):
    """Classify the tmux pane content into a PaneState.

    Returns (PaneState, detail_string).
    """
    if not content or not content.strip():
        return PaneState.UNKNOWN, "empty pane"

    # Check for processing indicator first — it's the strongest signal
    if "esc to interrupt" in content:
        return PaneState.PROCESSING, "esc to interrupt visible"

    # Check for input bar — signals done
    has_input_bar = (
        "Type your message" in content
        or "auto-accept" in content
    )

    # Check for interactive prompts
    has_radio = bool(_RE_RADIO.search(content))
    has_numbered = bool(_RE_NUMBERED.search(content))
    has_checkbox = bool(_RE_CHECKBOX.search(content))

    # Free-text questions often end with "?" on a line near bottom
    lines = content.strip().split('\n')
    bottom_lines = lines[-8:] if len(lines) > 8 else lines
    bottom_text = '\n'.join(bottom_lines)
    has_question = '?' in bottom_text and not has_input_bar

    if has_radio:
        return PaneState.INTERACTIVE, "radio_buttons"
    if has_checkbox:
        return PaneState.INTERACTIVE, "checkbox"
    if has_numbered and not has_input_bar:
        # Numbered options near bottom (not just numbered list in output)
        # Only treat as interactive if the numbered items are in the last few lines
        last_lines = '\n'.join(lines[-5:]) if len(lines) > 5 else content
        if _RE_NUMBERED.search(last_lines):
            return PaneState.INTERACTIVE, "numbered_options"

    if has_input_bar:
        return PaneState.DONE, "input bar visible"

    if has_question:
        return PaneState.INTERACTIVE, "free_text_question"

    return PaneState.UNKNOWN, "no clear signals"


def handle_interactive_prompt(detail, manifest_entry=None):
    """Respond to an interactive prompt in the tmux pane.

    Args:
        detail: The detail string from classify_pane (e.g., "radio_buttons").
        manifest_entry: Optional dict from the preflight manifest with
                        expected interactions for this prompt.

    Returns the action taken as a string for logging.
    """
    if detail == "radio_buttons":
        send_keys("Enter")
        return "accepted default radio option"
    elif detail == "checkbox":
        send_keys("Space")
        time.sleep(0.5)
        send_keys("Enter")
        return "toggled checkbox and confirmed"
    elif detail == "numbered_options":
        send_keys("-l", "1")
        time.sleep(0.3)
        send_keys("Enter")
        return "selected option 1"
    elif detail == "free_text_question":
        # Use manifest hint if available, otherwise type a generic answer
        answer = "yes"
        if manifest_entry and manifest_entry.get("interactions"):
            for interaction in manifest_entry["interactions"]:
                if interaction.get("type") == "free_text":
                    answer = interaction.get("answer", "yes")
                    break
        type_text(answer)
        return f"typed free text: {answer}"
    else:
        # Unknown interactive type, try Enter
        send_keys("Enter")
        return f"sent Enter for unknown interactive: {detail}"


# ─── Prompts loading helper ──────────────────────────────────────────────────


def _load_prompts_list(path):
    """Load prompts from a YAML file and return a list of strings."""
    import yaml

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
        log(f"WARNING: No prompts found in {path}")
        sys.exit(1)

    return prompts


# ─── SDK Preflight ────────────────────────────────────────────────────────────


async def _run_preflight(prompts, connection):
    """Run prompts through the SDK headlessly and build a manifest.

    Returns a list of dicts, one per prompt:
        {
            "prompt": str,
            "index": int,
            "success": bool,
            "duration_ms": int,
            "interactions": [{"type": str, "tool": str, "answer": str}, ...],
            "error": str | None,
        }
    """
    from cortex_code_agent_sdk import CortexCodeSDKClient
    from cortex_code_agent_sdk.types import (
        AssistantMessage,
        CortexCodeAgentOptions,
        PermissionResultAllow,
        ResultMessage,
        TextBlock,
        ToolUseBlock,
    )

    manifest = []
    interactions_for_current = []

    async def auto_accept_tool(tool_name, tool_input, context):
        """Auto-accept all tool permission requests and record interactions."""
        if tool_name == "ask_user_question":
            # Build answers dict: pick the first option for each question
            questions = tool_input.get("questions", [])
            answers = {}
            for i, q in enumerate(questions):
                options = q.get("options", [])
                if options:
                    answers[f"q{i}"] = options[0].get("label", "Yes")
                else:
                    answers[f"q{i}"] = "Yes"
            interactions_for_current.append({
                "type": "ask_user_question",
                "tool": "ask_user_question",
                "questions": [q.get("question", "") for q in questions],
                "answer": json.dumps(answers),
            })
            return PermissionResultAllow(updated_input={"answers": answers})

        if tool_name == "exit_plan_mode":
            interactions_for_current.append({
                "type": "exit_plan_mode",
                "tool": "exit_plan_mode",
                "answer": "accepted",
            })
            return PermissionResultAllow()

        # Auto-accept everything else
        return PermissionResultAllow()

    options = CortexCodeAgentOptions(
        allowed_tools=ALLOWED_TOOLS,
        disallowed_tools=DISALLOWED_TOOLS,
        connection=connection,
        can_use_tool=auto_accept_tool,
        max_turns=50,
    )

    client = CortexCodeSDKClient(options=options)

    try:
        # Connect with streaming mode (required for can_use_tool)
        async def _empty_stream():
            if False:
                yield {}

        await client.connect(prompt=_empty_stream())

        for idx, prompt_text in enumerate(prompts):
            log(f"Preflight [{idx+1}/{len(prompts)}]: {prompt_text[:60]}...")
            interactions_for_current.clear()
            start_ms = time.time() * 1000
            error_msg = None
            is_error = False

            try:
                await client.query(prompt_text)
                async for msg in client.receive_response():
                    if isinstance(msg, ResultMessage):
                        is_error = msg.is_error
                        if is_error:
                            error_msg = msg.result or "unknown error"
                        break
            except Exception as e:
                is_error = True
                error_msg = str(e)

            elapsed_ms = int(time.time() * 1000 - start_ms)

            entry = {
                "prompt": prompt_text,
                "index": idx,
                "success": not is_error,
                "duration_ms": elapsed_ms,
                "interactions": list(interactions_for_current),
                "error": error_msg,
            }
            manifest.append(entry)
            status = "OK" if not is_error else f"FAILED: {error_msg}"
            log(f"  [{elapsed_ms}ms] {status}")

    finally:
        await client.disconnect()

    return manifest


def cmd_preflight(args):
    """Run SDK preflight: execute all prompts headlessly, produce manifest JSON."""
    prompts_path = PROMPTS_FILE
    connection = CONNECTION

    # Parse args
    i = 0
    while i < len(args):
        if args[i] == "--prompts" and i + 1 < len(args):
            prompts_path = os.path.abspath(args[i + 1])
            i += 2
        elif args[i] == "--connection" and i + 1 < len(args):
            connection = args[i + 1]
            i += 2
        else:
            i += 1

    prompts = _load_prompts_list(prompts_path)
    log(f"Starting preflight with {len(prompts)} prompts (connection={connection})...")

    manifest = asyncio.run(_run_preflight(prompts, connection))

    # Derive manifest path from prompts path
    base = os.path.splitext(prompts_path)[0]
    manifest_path = base + "_manifest.json"

    with open(manifest_path, "w") as f:
        json.dump({"prompts": manifest, "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S")}, f, indent=2)

    # Summary
    succeeded = sum(1 for m in manifest if m["success"])
    failed = len(manifest) - succeeded
    total_ms = sum(m["duration_ms"] for m in manifest)

    log(f"Preflight complete: {succeeded} OK, {failed} failed, {total_ms}ms total")
    print(json.dumps({
        "status": "complete",
        "manifest_path": manifest_path,
        "total_prompts": len(manifest),
        "succeeded": succeeded,
        "failed": failed,
        "total_duration_ms": total_ms,
    }))


# ─── Drive Loop ───────────────────────────────────────────────────────────────


def cmd_drive(args):
    """Drive the demo: type prompts, detect completion via state machine, handle interactions."""
    prompts_path = PROMPTS_FILE
    manifest_path = None
    pause_between = 5  # seconds between prompts

    # Parse args
    i = 0
    while i < len(args):
        if args[i] == "--prompts" and i + 1 < len(args):
            prompts_path = os.path.abspath(args[i + 1])
            i += 2
        elif args[i] == "--manifest" and i + 1 < len(args):
            manifest_path = os.path.abspath(args[i + 1])
            i += 2
        elif args[i] == "--pause" and i + 1 < len(args):
            pause_between = int(args[i + 1])
            i += 2
        else:
            i += 1

    if not tmux_session_exists():
        log("ERROR: tmux session not found. Run 'launch' first.")
        sys.exit(1)

    prompts = _load_prompts_list(prompts_path)

    # Load manifest if provided
    manifest_entries = {}
    if manifest_path and os.path.exists(manifest_path):
        with open(manifest_path, "r") as f:
            mdata = json.load(f)
        for entry in mdata.get("prompts", []):
            manifest_entries[entry["index"]] = entry
        log(f"Loaded manifest with {len(manifest_entries)} entries")

    results = []

    for idx, prompt_text in enumerate(prompts):
        log(f"Drive [{idx+1}/{len(prompts)}]: {prompt_text[:60]}...")
        mentry = manifest_entries.get(idx)

        # Check if preflight flagged this as failed
        if mentry and not mentry.get("success"):
            log(f"  WARNING: preflight flagged this prompt as failed: {mentry.get('error')}")
            # Still attempt it — the real session might behave differently

        # Type the prompt
        type_text(prompt_text)
        prompt_start = time.time()

        # Wait initial period before polling
        time.sleep(5)

        # Polling loop
        stable_count = 0
        prev_content = None
        max_wait = 300  # 5 minutes max per prompt
        poll_interval = 3

        # Use manifest duration as guidance for timeout
        if mentry and mentry.get("duration_ms"):
            # Allow 2x the preflight duration, minimum 60s
            guided_max = max(60, (mentry["duration_ms"] / 1000) * 2)
            max_wait = min(max_wait, int(guided_max))
            log(f"  Manifest guidance: preflight took {mentry['duration_ms']}ms, timeout={max_wait}s")

        while time.time() - prompt_start < max_wait:
            content = capture_pane()
            state, detail = classify_pane(content)

            if state == PaneState.PROCESSING:
                # Still working, reset stability counter
                stable_count = 0
                prev_content = content
                time.sleep(poll_interval)
                continue

            if state == PaneState.INTERACTIVE:
                log(f"  Interactive prompt detected: {detail}")
                action = handle_interactive_prompt(detail, mentry)
                log(f"  Action: {action}")
                # After interacting, wait a bit and reset
                time.sleep(2)
                stable_count = 0
                prev_content = None
                continue

            if state == PaneState.DONE:
                # Check stability — need 2 consecutive identical captures
                if content == prev_content:
                    stable_count += 1
                else:
                    stable_count = 1
                prev_content = content

                if stable_count >= 2 and (time.time() - prompt_start) >= 10:
                    elapsed = time.time() - prompt_start
                    log(f"  Done after {elapsed:.1f}s")
                    break

                time.sleep(poll_interval)
                continue

            # UNKNOWN state — keep polling
            if content == prev_content:
                stable_count += 1
            else:
                stable_count = 0
            prev_content = content

            # If stable and enough time has passed, assume done
            if stable_count >= 4 and (time.time() - prompt_start) >= 15:
                elapsed = time.time() - prompt_start
                log(f"  Assumed done (stable UNKNOWN) after {elapsed:.1f}s")
                break

            time.sleep(poll_interval)
        else:
            elapsed = time.time() - prompt_start
            log(f"  TIMEOUT after {elapsed:.1f}s")

        results.append({
            "index": idx,
            "prompt": prompt_text,
            "elapsed_s": round(time.time() - prompt_start, 1),
            "timed_out": (time.time() - prompt_start) >= max_wait,
        })

        # Pause between prompts for viewer readability
        if idx < len(prompts) - 1:
            log(f"  Pausing {pause_between}s before next prompt...")
            time.sleep(pause_between)

    # Print results summary
    print(json.dumps({
        "status": "drive_complete",
        "prompts_driven": len(results),
        "results": results,
    }))


# ─── Original Subcommands ────────────────────────────────────────────────────


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
    path = args[0] if args else PROMPTS_FILE
    prompts = _load_prompts_list(path)
    print(json.dumps({"prompts": prompts, "file": os.path.abspath(path)}))


# ─── Main ────────────────────────────────────────────────────────────────────


COMMANDS = {
    "launch": cmd_launch,
    "stop": cmd_stop,
    "capture": cmd_capture,
    "type": cmd_type,
    "send": cmd_send,
    "status": cmd_status,
    "prompts": cmd_prompts,
    "preflight": cmd_preflight,
    "drive": cmd_drive,
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
