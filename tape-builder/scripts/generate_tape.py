#!/usr/bin/env python3
"""
Generate a VHS .tape file from a cortex_demo_prompts.yaml file.

Usage:
    python3 generate_tape.py prompts.yaml
    python3 generate_tape.py prompts.yaml --output demo.tape
    python3 generate_tape.py prompts.yaml --connection myconn --theme "Dracula"
    python3 generate_tape.py prompts.yaml --gif-only
    python3 generate_tape.py prompts.yaml --mp4-only
"""

import argparse
import os
import sys
import yaml


# --- Default Settings ---

DEFAULTS = {
    "connection": "devrel",
    "theme": "Catppuccin Mocha",
    "font_family": "SF Mono",
    "font_size": 14,
    "width": 1400,
    "height": 800,
    "typing_speed": "50ms",
    "padding": 20,
    "framerate": 30,
    "window_bar": "Colorful",
    "window_bar_size": 40,
    "wait_timeout": "30m",
    "pause_between_prompts": 3,
    "sleep_per_prompt": 240,
    "session_name": "Demo",
}


def load_prompts(path):
    """Load prompts from a YAML file. Returns list of strings."""
    with open(path, "r") as f:
        data = yaml.safe_load(f)

    raw = data.get("prompts", [])
    prompts = []
    for item in raw:
        text = " ".join(str(item).split()).strip()
        if text:
            prompts.append(text)

    if not prompts:
        print(f"ERROR: No prompts found in {path}", file=sys.stderr)
        sys.exit(1)

    return prompts, data


def escape_tape_string(text):
    """Escape a string for use in a VHS Type command."""
    return text.replace("\\", "\\\\").replace('"', '\\"')


def generate_tape(prompts, args, raw_data):
    """Generate VHS tape content from prompts and settings."""
    lines = []

    # Header comments (preserve from YAML)
    for key, val in raw_data.items():
        if key == "prompts":
            continue

    # Extract comment lines from the original YAML for the header
    yaml_path = args.prompts_file
    try:
        with open(yaml_path, "r") as f:
            for line in f:
                line = line.rstrip()
                if line.startswith("#"):
                    lines.append(line)
                elif line.strip() == "":
                    continue
                else:
                    break
    except Exception:
        pass

    if lines:
        lines.append("#")

    lines.append(f"# VHS Tape — {len(prompts)} prompts")
    lines.append(f"# Run: vhs {args.output}")
    lines.append(f"# Validate: vhs validate {args.output}")
    lines.append("")

    # --- Output ---
    lines.append("# --- Output ---")
    if args.gif_only:
        lines.append(f"Output {args.output_prefix}.gif")
    elif args.mp4_only:
        lines.append(f"Output {args.output_prefix}.mp4")
    else:
        lines.append(f"Output {args.output_prefix}.gif")
        lines.append(f"Output {args.output_prefix}.mp4")
    lines.append("")

    # --- Settings ---
    lines.append("# --- Terminal Settings ---")
    lines.append("Require cortex")
    lines.append(f'Set Shell "bash"')
    lines.append(f"Set FontSize {args.font_size}")
    lines.append(f'Set FontFamily "{args.font_family}"')
    lines.append(f"Set Width {args.width}")
    lines.append(f"Set Height {args.height}")
    lines.append(f"Set TypingSpeed {args.typing_speed}")
    lines.append(f'Set Theme "{args.theme}"')
    lines.append(f"Set Padding {args.padding}")
    lines.append(f"Set Framerate {args.framerate}")
    lines.append(f"Set WindowBar {args.window_bar}")
    lines.append(f"Set WindowBarSize {args.window_bar_size}")
    lines.append(f"Set WaitTimeout {args.wait_timeout}")
    lines.append("")

    # --- Launch Cortex ---
    lines.append("# --- Launch Cortex ---")
    cortex_cmd = (
        f"cortex"
        f" --connection {args.connection}"
        f" --bypass"
        f" --auto-accept-plans"
        f' --disallowed-tools ask_user_question enter_plan_mode'
        f" --no-auto-update"
        f' --session-name \'{args.session_name}\''
    )
    lines.append(f'Type "{escape_tape_string(cortex_cmd)}"')
    lines.append("Enter")
    lines.append("Sleep 15s")
    lines.append(r"Wait+Screen /\? for help/")
    lines.append("Sleep 1s")
    lines.append("")

    # --- Prompts ---
    # NOTE: We use Sleep-based waits for prompt responses rather than
    # Wait+Screen because VHS's screen buffer polling can hang during
    # complex multi-tool Cortex responses with rapid TUI re-renders.
    # Wait+Screen /\? for help/ works for initial startup and simple
    # prompts but is unreliable for longer, tool-heavy responses.
    pause = args.pause_between_prompts
    sleep_per = args.sleep_per_prompt
    for i, prompt in enumerate(prompts, 1):
        lines.append(f"# --- Prompt {i}/{len(prompts)} ---")
        lines.append(f"Sleep {pause}s")
        lines.append(f'Type "{escape_tape_string(prompt)}"')
        lines.append("Enter")
        lines.append(f"Sleep {sleep_per}s")
        lines.append("")

    # --- Cleanup ---
    lines.append("# --- End ---")
    lines.append("Sleep 5s")

    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(
        description="Generate a VHS .tape file from a cortex demo prompts YAML."
    )
    parser.add_argument("prompts_file", help="Path to prompts YAML file")
    parser.add_argument(
        "--output", "-o",
        default="cortex_demo.tape",
        help="Output tape file path (default: cortex_demo.tape)",
    )
    parser.add_argument(
        "--output-prefix",
        default="cortex_demo",
        help="Prefix for output GIF/MP4 files (default: cortex_demo)",
    )
    parser.add_argument("--connection", default=DEFAULTS["connection"])
    parser.add_argument("--theme", default=DEFAULTS["theme"])
    parser.add_argument("--font-family", default=DEFAULTS["font_family"])
    parser.add_argument("--font-size", type=int, default=DEFAULTS["font_size"])
    parser.add_argument("--width", type=int, default=DEFAULTS["width"])
    parser.add_argument("--height", type=int, default=DEFAULTS["height"])
    parser.add_argument("--typing-speed", default=DEFAULTS["typing_speed"])
    parser.add_argument("--padding", type=int, default=DEFAULTS["padding"])
    parser.add_argument("--framerate", type=int, default=DEFAULTS["framerate"])
    parser.add_argument("--window-bar", default=DEFAULTS["window_bar"])
    parser.add_argument("--window-bar-size", type=int, default=DEFAULTS["window_bar_size"])
    parser.add_argument("--wait-timeout", default=DEFAULTS["wait_timeout"])
    parser.add_argument(
        "--pause-between-prompts",
        type=int,
        default=DEFAULTS["pause_between_prompts"],
    )
    parser.add_argument(
        "--sleep-per-prompt",
        type=int,
        default=DEFAULTS["sleep_per_prompt"],
        help="Seconds to sleep after each prompt for response (default: 240)",
    )
    parser.add_argument("--session-name", default=DEFAULTS["session_name"])
    parser.add_argument("--gif-only", action="store_true", help="Only output GIF")
    parser.add_argument("--mp4-only", action="store_true", help="Only output MP4")

    args = parser.parse_args()

    prompts_path = os.path.abspath(args.prompts_file)
    if not os.path.exists(prompts_path):
        print(f"ERROR: File not found: {prompts_path}", file=sys.stderr)
        sys.exit(1)

    prompts, raw_data = load_prompts(prompts_path)
    tape_content = generate_tape(prompts, args, raw_data)

    output_path = os.path.abspath(args.output)
    with open(output_path, "w") as f:
        f.write(tape_content)

    print(f"Generated {output_path}")
    print(f"  Prompts: {len(prompts)}")
    print(f"  Theme: {args.theme}")
    print(f"  Connection: {args.connection}")
    print(f"")
    print(f"  Validate: vhs validate {args.output}")
    print(f"  Record:   vhs {args.output}")


if __name__ == "__main__":
    main()
