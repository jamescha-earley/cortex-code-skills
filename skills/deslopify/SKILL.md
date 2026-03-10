---
name: deslopify
description: "Rewrite text to remove AI slop, tropes, and cliches. Makes text more genuine, natural, and human-sounding. Use when: user asks to deslopify, naturalize, de-slop, remove AI tropes, make text sound human, clean up AI writing, or review text for AI patterns. Triggers: deslopify, naturalize, de-slop, AI slop, AI tropes, sound human, AI writing."
---

# Deslopify

Remove AI writing tropes and make text genuine, direct, and human.

Based on the [Deslopify](https://github.com/glaforge/deslopify) skill by [Guillaume Laforge](https://github.com/glaforge), grounded in the [AI Writing Tropes](https://tropes.fyi/) directory.

## Workflow

### Step 1: Get the Text

Identify the text to deslopify. The user may provide:
- Inline text or a draft pasted into the conversation
- A file path to read
- A URL to fetch
- A request to deslopify your own future output

If the user wants you to deslopify a file, **Read** the file. If a URL, **Fetch** it.

### Step 2: Load the Style Guide

**Read** `references/style_guide.md` from this skill's directory. This is the complete list of AI writing anti-patterns you must check against. Do not skip this step.

### Step 3: Analyze the Text

Scan the text for tropes listed in the style guide. Categorize findings by:

- **Word Choice** (magic adverbs, "delve" family, "tapestry"/"landscape", "serves as" dodge)
- **Sentence Structure** (negative parallelism, "Not X. Not Y. Just Z.", "The X? A Y.", anaphora abuse, tricolon abuse, filler transitions, superficial analyses, false ranges, gerund fragment litany)
- **Paragraph Structure** (short punchy fragments, listicle in a trench coat)
- **Tone** (false suspense, patronizing analogies, "imagine a world", false vulnerability, "the truth is simple", grandiose stakes inflation, "let's break this down", vague attributions, invented concept labels)
- **Formatting** (em-dash addiction, bold-first bullets, unicode decoration)
- **Composition** (fractal summaries, dead metaphors, historical analogy stacking, one-point dilution, content duplication, signposted conclusions, "despite its challenges")

Present a brief summary of what you found before rewriting. Example:

```
Found 7 tropes:
- 3x Negative parallelism ("It's not X -- it's Y")
- 2x Em-dash addiction
- 1x Grandiose stakes inflation
- 1x Bold-first bullets
```

### Step 4: Rewrite

Rewrite the text to eliminate the identified tropes while preserving the core meaning and intent. Follow these principles:

- **Be direct.** Say what you mean without rhetorical tricks.
- **Vary sentence structure.** Mix lengths and forms naturally.
- **Use simple words.** Prefer "is" over "serves as", "use" over "leverage".
- **Cut filler.** Remove "it's worth noting", "importantly", "interestingly".
- **Stay specific.** Replace vague claims with concrete ones or cut them.
- **Don't overformat.** Avoid bold-first bullets, excessive em dashes, unicode arrows.
- **Preserve voice.** If the original has personality, keep it. Just remove the slop.

Present the rewritten text to the user.

### Step 5: Show the Diff (Optional)

If the text is short-to-medium length, show a before/after comparison highlighting the key changes and which tropes were removed.

## Stopping Points

- After Step 3 (analysis): If the user only asked for a review/audit rather than a rewrite, stop here and present findings.
- After Step 4 (rewrite): Present the result and wait for feedback before making further edits.

## Output

- A trope analysis summary listing what was found
- A rewritten version of the text, free of AI slop
- Optionally, a before/after diff of key changes
