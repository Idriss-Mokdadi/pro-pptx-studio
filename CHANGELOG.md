# Changelog

## v6 (October 2026)
- **Rule checker** (`scripts/tplcheck.py`): text size, title at the top, bullets instead of paragraphs, at most 5 bullets, sample text, text off the slide or over the central picture, slide numbers, speaker notes, the same template slide twice in a row, one background family.
- **Talk time**: estimated from the speaker notes (120 words per minute by default, `"talk": {"minutes", "wpm"}`), with a timing plan per slide; when it runs over, the notes are shortened, slides are never merged unless asked.
- **Preview**: each cover is shown next to the template's plan slide and best content slide, with the number of content slides whose title is at the top.
- **Code windows**: colors from Pygments for any language (C, C++, Arduino, Java, Kotlin, YAML, JSON, Terraform, Dockerfile, SQL, MATLAB, bash…), plus `terminal` for commands with a `$` prompt.
- **Morph**: the title, slide number and logos get `!!` names so they glide between slides.
- **French mode** (`"lang": "fr"`): French spacing before `? ! ; :` and inside `« »`; French house titles.
- **Word groups** ("Sprint 1", "10 Aug", "5 GHz", "Q3 2026") kept on one line automatically.
- **Backup slides** after the closing (`"backup": true`), numbered A1, A2…
- **QR code** kit (`qr`), only when the user gives a link.
- **Feedback log**: after a correction the skill asks "only this presentation or all future ones"; the second answer is saved in `references/feedback-log.md`.
- **Library**: found by its folder name `pro-pptx-studio-skill` (no fixed path); `library.py status` lists new templates; `--index-only` indexes in place on the user's computer; no fixed template count anywhere.
- **Storyline**: simple topic titles only (full-sentence titles removed), slide count set by the content within about one slide per 45–90 s.
- **Smoke test** (`tests/smoke.py`) for changes to the skill.
- Shorter SKILL.md (the polish reference moved to `references/polish.md`); personal details removed from the examples.

## v5 (October 2026)
Automatic slide numbering starting at the table of contents (`polish.numbers`, on by default, moves above logo chips); library kept in one folder; banners are always wide (`polish.canvas` crops a template slide to 3:1 or 2:1); reuses a template's own page numbers (restyled to start at the table of contents) instead of adding a second set.

## v4 (October 2026)
House rules from real feedback, a default jury-defense outline, the polish pass, fact-checking of AI-made summaries, and a speech plus jury Q&A at delivery.

## v3
Template mode, cover preview, slide mixing, depth covers.

## v2
Generator with 59 styles, banners.
