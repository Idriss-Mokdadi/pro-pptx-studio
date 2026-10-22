---
name: pro-pptx-studio
description: Make PowerPoint (.pptx) presentations and banners that look designer-made, built on the user's own templates (Canva and other designer decks in a private library) - keeping their backgrounds, photos and fonts, mixing parts across templates, re-fonting for the topic, adding alive charts, KPIs, code windows, timelines, architecture diagrams, logos, QR codes and Morph. Previews each candidate template (cover, plan and content slide) first and checks every rule automatically. Use for any new deck (defenses, end-of-year projects, internships, pitches, technical talks, events) and for banners.
license: MIT (see LICENSE); fonts SIL OFL 1.1 (inside assets/bundle.tar.xz, unpacked on first use to ~/.cache/pro-pptx-studio or PPS_CACHE); template files keep their own licenses (see references/template-mode.md)
---

# Pro PPTX Studio v6

`SKILL_DIR` = the folder containing this file. Needs Python 3.10+ with the packages of `requirements.txt`
(python-pptx, lxml, fonttools, Pillow, numpy, Pygments, qrcode; `pip install -r requirements.txt` adds the
missing ones), LibreOffice and Poppler for previews, and Node.js 18+ only for the generator fallback and
banners (`npm install` in `SKILL_DIR`).

Read `references/taste.md` first, then the **house rules** below. The house rules are the user's own
corrections: they override anything else in the references. The core rule: decks look like the user's
designer files, built **on real templates**, never on code-drawn backgrounds or emoji-style 3D objects.

## Where the library is
The user keeps one parent folder named **`pro-pptx-studio-skill`**:
```
pro-pptx-studio-skill/
├── pro-pptx-studio/     the user's copy of this skill (the GitHub repository)
├── templates/           their .pptx templates, added any time (a folder named Templates also works)
└── template-library/    the index the skill generates (never edited by hand)
```
Find it by name among the folders connected to the session (the connected folder itself or one level
inside); never assume a drive letter. Not found: ask the user to connect it. At the start of every deck:
1. Run `library.py status --lib <parent>/template-library` (file names only, fast) and index any new
   template: on the user's computer when its shell can (nothing to copy back), otherwise in the cloud and
   write the new index back in the same step (`references/template-mode.md`, section 1).
2. Read `<parent>/pro-pptx-studio/references/feedback-log.md`: corrections the user saved since this version
   was installed. They apply like house rules.

## House rules (apply to every deck)

**Readability**
- Never put text over the central picture of a background (cover art, globe, device). Titles go beside it;
  presenter pills and labels move off it too.
- Titles sit at the **top** of every content slide. Template slides whose title slot is low or in the middle
  are not used for content, or their title is moved up.
- Text-heavy slides (code, tables, lists, diagrams) use a **calm background**: a canvas of the template's
  plainest slide. Busy art is for the cover, section and closing slides.
- Every slide keeps the same background family (no white/dark mixing).
- **Every deck is numbered**: the cover has no number, numbering starts at the plan (= 1) and runs to the
  closing slide, which is numbered too; backup slides are A1, A2... The polish does it automatically.

**Text**
- Simple topic titles, one line when it fits: "Presentation Plan", "Problem Statement", "Project
  Objectives", "Work Plan", "Technical Choices", "Network Architecture", "Tests and Validation", "Cost
  Analysis", "Conclusion and Perspectives" (French equivalents in `references/storytelling.md`). Never
  full-sentence titles.
- Bullets or short phrases only, never paragraphs (at most 5 bullets, about 8 words each). The explanation
  goes in the notes.
- No jargon labels the audience may not know: name the tool they know, not its internal acronym or file
  format.
- Word groups stay on one line: the builder adds non-breaking spaces in "Sprint 1", "10 Aug", "5 GHz",
  "Q3 2026"; type ` ` yourself for other groups. French decks set `"lang": "fr"` for the French
  spaces before `? ! ; :`.
- Text inside any container (pill, hexagon, tile, card) is centered both ways on the container's full bounds.
- Readable sizes: nothing important under 16 pt on a 1440 pt-wide canvas (the checker scales this to the
  slide size); the closing line ("Questions and discussion are welcome") at least 32 pt.

**Content**
- Verify every fact against the user's primary files (report, journal, code, screenshots). Summaries made by
  any AI assistant are leads, not sources: check dates, file names and claims, and list contradictions to
  the user before building.
- Official dates come from the signed log or journal, not a provisional plan.
- Add the logos the user provides on a light rounded chip: cover and closing get all of them, a company
  slide gets the company logo.
- Show the **real** system when there is one: screenshots of the real tool or portal, the provider's
  resource view redrawn as clean tiles with the official icons cropped from the user's screenshot, and the
  logical architecture drawn as panels.
- Charts only where real numbers tell the story (costs, hours, measurements); none where a screenshot or KPI
  tiles already prove the point. No comparison between vendors or competitors unless the user asks. Never
  invent values; when a chart mixes sources, say so in the notes.
- Code slides show **why** the tool was chosen and **which commands** were used (the 3–5 commands of the
  workflow, one comment each), not a random excerpt.
- A QR code only when the user gives a link or asks for one.

**Design**
- Not too simple, not boring: plan slides use numbered hexagon cards, KPI rows use one value size and
  centered text, charts get gradients and a glow on the point that proves the argument.
- Mix template parts freely when they harmonize; recolor to the topic.

## Decks

### 1. Brief
Get the real content: audience, talk duration, language, time of day (for the greeting in the speech), deck
type, and the user's assets (logos, screenshots, photos, data, report, code). Never invent facts, numbers,
names or results: write `[value]` and list what the user must fill. Ask one short question only if
something essential is missing (duration, language, official dates).

### 2. Storyline
Follow `references/storytelling.md`. No fixed slide count: one main idea per slide, the number set by the
real content within about one slide per 45–90 seconds of talk (10 minutes ≈ 8–14 slides with cover and
closing). For defenses, plan 2–4 backup slides after the closing for the likely jury questions. Show the
outline as a list of titles and wait for a yes before building any deck of 8 slides or more.

### 3. Library
Pick templates with `library.py find "<topic>"` on the index, then stage only those
(`references/template-mode.md`, section 1).

### 4. Preview (required unless the user already named a template)
`python3 SKILL_DIR/scripts/tplpreview.py brief.json preview` renders the user's title on the covers of the
best-matching templates, as designed and with the topic's fonts, each next to the template's plan slide and
best content slide. Send `covers.jpg` and ask which letter. They may combine ("B's template with D's
fonts", "this one but green").

### 5. Plan and build
Map every storyline slide to a template slide (`library.py show <id>` for slots and positions), respecting
the house rules: content slides use template slides with the title on top; text-heavy slides use a canvas of
the plainest slide; never the same slide twice in a row. Write the spec (`references/template-mode.md`,
section 4: `lang`, `talk`, `backup`), then:
```bash
python3 SKILL_DIR/scripts/tplbuild.py spec.json
```
- Fonts follow the topic (`"fonts": {"theme": "telecom:0"}`; pairs in `taste.md`), unless the template's own
  fonts fit and the user picked them.
- Kit components (`template-mode.md`, section 5): `kpi`, `table`, `code` (any language, or `terminal`),
  `bullets`, `chart` (give it a `name` such as `chart-cost`), `image` (`fit: contain` for screenshots),
  `mockup`, `timeline`, `depth`, `qr`.
- Canvas slides remove everything not in `keep`; small decorations survive unless they overlap an `add` box,
  so list leftovers in `remove`.
- Every slide gets `notes` (the speech, 2–5 sentences). Fix every warning in the report (shorten text
  first), rebuild.

### 6. Polish
Open `references/polish.md`, add a `"polish"` section to the same spec, and run it after every build:
```bash
python3 SKILL_DIR/scripts/tplbuild.py spec.json && python3 SKILL_DIR/scripts/tplpolish.py spec.json
```
Slide numbers (backup slides A1, A2...) and Morph names (title, slide number, logos) are added automatically.

### 7. Check (required)
```bash
python3 SKILL_DIR/scripts/render.py deck.pptx render --dpi 60 --cols 4
python3 SKILL_DIR/scripts/tplcheck.py spec.json --render render
```
`tplcheck.py` lists every broken rule: correct every `fix`, look at every `check`, rebuild, and run it again
until no `fix` is left. It also estimates the talk time from the notes; when it runs over, shorten the
notes, and never merge, split or remove slides unless the user asks. Then look at the sheet and every
doubtful slide at full size for what a script cannot judge: the deck reads as one design, nothing hidden
behind art, numbers match the sources, charts add something. If the pptx skill is available, also run its
`scripts/office/validate.py`. Glow and Morph only show in PowerPoint, not in the rendered images.

### 8. Deliver
Send the .pptx. In a few lines: template, fonts, motion, estimated talk time, `[value]` items to fill, and
any contradiction found in the sources. Tell the user to export the PDF from PowerPoint (File → Export →
PDF): the LibreOffice PDF used for the previews loses the glow effects. For defenses, offer a short,
memorizable speech (one key word per slide, greeting matched to the time of day) and a jury Q&A list grouped
by theme, including the trick questions the sources expose. Fonts are embedded (PowerPoint 2019/365); Morph
needs PowerPoint 2019+.

## When the user corrects something
Apply the correction to the deck, then ask once (AskUserQuestion): **"Only this presentation"** or **"All
future presentations"**.
- Only this one: change the deck, save nothing.
- All future ones: add a dated line to `<parent>/pro-pptx-studio/references/feedback-log.md` on the user's
  computer (format in that file) and follow it for the rest of the session. If the computer is not
  reachable, give the user the line to add.
Don't ask again for a correction they already scoped.

## When no template fits
Use the generator: `scripts/deckkit.js` with its 59 styles (`references/components.md`,
`references/styles.md`, `node scripts/preview.js`). The house rules still apply (slide numbers included),
with thematic fonts, real images and no emoji-style 3D unless the user asks.

## Banners
A banner is **always wider than tall**: 3:1 by default (README or website header), 2:1 for a GitHub social
preview, or the platform's landscape size (LinkedIn, X, YouTube...). Portrait formats (story, poster,
roll-up) are posters, not banners. Build it in template mode on a library template (16:9), lay the content
out inside the band you will keep, then crop with `polish.canvas` (`{"aspect": 3, "top": 0.2}` keeps a 3:1
strip starting 20 % down the slide); render, check, and export the PNG at the exact pixel size. No credit
line on the banner itself (`"credit": false` in the spec); credit SlidesCarnival templates where the banner
is published (README, post text). The generator (`scripts/banner.js`, `references/banners.md`) is the
fallback when no template fits. Logos go on a light chip; text stays off the central art.

## Changing the skill itself
After any change to the scripts, run the smoke test before shipping the new version (about one minute, on
a template of the user's library):
```bash
python3 SKILL_DIR/tests/smoke.py --lib <parent>/template-library
```
Merge `references/feedback-log.md` into the house rules and empty it in each new version.

## Non-negotiables
- Slide numbers on every slide from the plan onward; backup slides A1, A2...
- Titles at the top, simple, at most 2 lines; bullets, not paragraphs; nothing the audience must read under
  16 pt (scaled to the slide size).
- Never leave template sample text, fake names, fake websites or lorem ipsum.
- Never invent numbers; verify AI-made summaries against the primary files.
- Keep template licenses: Canva templates stay private; SlidesCarnival decks keep the credit line.
- Motion follows speech: titles never animate; one idea per step; diagrams appear whole.
