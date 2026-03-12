---
name: linkedin-post
description: "Draft LinkedIn posts matching a personal voice and style. Fetches source material, applies voice guide, and runs a deslopify pass. Use when: user wants to write a LinkedIn post, promote something on LinkedIn, draft social media content, or create a LinkedIn announcement. Triggers: linkedin post, write a linkedin post, social media post, promote on linkedin, draft linkedin."
---

# LinkedIn Post Writer

Draft LinkedIn posts that match the author's personal voice and pass a deslopify check.

## Workflow

### Step 1: Gather Source Material

Identify what the post is about. The user may provide:
- A URL to fetch (event page, blog post, product page)
- A file to read
- Inline text or bullet points describing what to promote
- A request to write about a topic from scratch

If a URL is provided, **Fetch** it. If a file path, **Read** it.
If the user has provided their LinkedIn profile URL, **Fetch** it to understand their recent posting activity and style.

### Step 2: Load the Voice Guide

**Read** `references/voice_guide.md` from this skill's directory. These are the style rules the post must follow.

### Step 3: Draft the Post

Write a LinkedIn post using the source material and voice guide. Follow these rules:

1. Open with a short hook — emoji optional, conversational tone required
2. Keep paragraphs to 1-3 sentences with line breaks between them
3. Weave technical details into prose rather than formal bullet lists
4. Include a personal take or opinion where possible
5. End with a question or call to action directed at the audience
6. Add 3-5 hashtags at the bottom
7. Aim for 80-150 words unless the topic demands more

### Step 4: Deslopify Pass

**Read** the deslopify style guide at `~/.snowflake/cortex/skills/deslopify/references/style_guide.md`.

Scan the draft against the deslopify trope list. If tropes are found:
1. List them briefly
2. Rewrite to remove them
3. Present the clean version

If no tropes are found, skip to Step 5.

### Step 5: Present the Draft

Show the final post to the user.

**Wait for feedback.** The user may want to:
- Adjust the tone
- Add or remove details
- Change the opening or closing
- Make it longer or shorter

Apply edits as requested. Re-run the deslopify check on any substantial rewrites.

## Stopping Points

- After Step 5: Present the draft and wait for user feedback before making further changes.

## Output

- A LinkedIn post matching the author's voice, free of AI writing tropes
