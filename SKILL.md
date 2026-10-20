---
name: pro-pptx-studio
description: Make PowerPoint (.pptx) presentations and banners that look designer-made, built on the user's real templates (Canva and other designer decks in a private library) - keeping their backgrounds, photos and fonts, mixing parts across templates, re-fonting for the topic, adding alive charts, KPIs, code windows, timelines, real-architecture diagrams, logos and Morph. Always previews the cover on several templates first. Use for any new deck (defenses, internships, PFA, pitches, technical talks, IEEE events) and for banners.
license: MIT (see LICENSE); fonts SIL OFL 1.1 (inside assets/bundle.tar.xz, unpacked on first use to ~/.cache/pro-pptx-studio or PPS_CACHE); template files keep their own licenses (see references/template-mode.md)
---

# Pro PPTX Studio v5

`SKILL_DIR` = the folder containing this file. Needs Python 3 with `python-pptx`, `lxml`, `fonttools`, `Pillow`, `numpy`; LibreOffice and Poppler for previews; Node.js 18+ only for the generator fallback and banners (`npm install` in `SKILL_DIR`).

Read `references/taste.md` first, then the **House rules** below: they come from the user's feedback on their internship defense deck and override older guidance (including "action titles" in `references/storytelling.md`). The core rule stays: decks look like the user's own Canva files, built **on real templates**, never on code-drawn backgrounds or emoji-style 3D objects.

## House rules (the user's corrections, apply to every deck)

**Readability**
- Never put text over the central picture of a background (cover art, globe, device). Place titles beside it (`polish.title_lines` with a box clear of the art); move presenter pills and labels off it too.
- Titles sit at the **top** of every content slide. Template slides whose title slot is at the bottom or in the middle (e.g. a "stats" slide with the title low) are not used for content, or their title is moved up with `polish.move`.
- Text-heavy slides (code, tables, lists, diagrams) use a **calm background**: a canvas of the template's plainest slide, never a busy photo background. Keep the busy art for the cover, section and closing slides.
- Every slide keeps the same background family (no white/dark mixing).
- **Every deck is numbered.** The cover has no number; numbering starts at the table of contents (Presentation Plan = 1) and runs to the closing slide, which is numbered too. `tplpolish.py` adds the numbers by default (bottom-right, display font, bold, 18 pt, white or the template's text color) and lifts them above a logo chip or card sitting in the corner. If the plan is not slide 2, set `polish.numbers.start_slide` to its slide number.

**Text**
- Simple topic titles: "Presentation Plan", "Host Company: X", "Problem Statement", "Project Objectives", "Work Plan", "Technical Choices", "Network Architecture", "Tests and Validation", "Cost Analysis", "Conclusion and Perspectives". One line when it fits.
- Bullets or short phrases only, never paragraphs (≤ 5 bullets, ≤ 8 words each when possible). Put the explanation in `notes`.
- No jargon labels the audience may not know (say "Terraform", not "HCL").
- Keep word groups on one line with non-breaking spaces: `Sprint\u00a01`, `1–10\u00a0Aug`, `MIM-15`.
- Text inside any container (pill, hexagon, tile, card) is centered horizontally and vertically on the container's full bounds (`polish.center`; measure the visible shape, not only the inner freeform).
- Labels are readable: nothing important under 16 pt on a 1440 pt-wide canvas; closing line ("Questions and discussion are welcome") ≥ 32 pt.

**Content**
- Verify every fact against the user's primary files (report, journal, code, screenshots). AI-written summaries the user brings (e.g. from Gemini) are leads, not sources: check dates, file names and claims, and list contradictions to the user before building (wrong dates, files that don't exist, diagrams that don't match the deployment).
- Official dates come from the signed log/journal, not a provisional plan.
- Add logos the user provides (school, host company) on a light rounded chip (`polish.logos`): cover and closing get both, the company slide gets the company logo.
- Show the **real** deployment when there is one: portal screenshots, Resource-visualizer exports redrawn as clean tiles with the official icons cropped from the user's export (`--icons`, then `polish.diagram` tiles), plus the logical architecture drawn as panels.
- Charts only where real numbers tell the story (costs, hours, measurements). No chart where a screenshot or KPI tiles already prove the point (tests slide). No competitor comparison (e.g. Azure vs AWS) unless the user asks. Never invent values; when a chart mixes sources, say so in the notes.
- Code slides explain **why** the tool and **which commands** were used (e.g. `terraform init / plan / apply / destroy` with one comment each), not a random excerpt.

**Design**
- Not too simple, not boring: plan slides use numbered hexagon cards (`polish.cards`), KPI rows use one value size and centered text, charts get gradients and a glow on the point that proves the argument (`polish.charts`).
- Mix template parts freely when they harmonize; recolor to the topic.

## Decks

### 1. Brief
Get the real content: audience, length, language, presentation time of day (for the greeting in the speech), deck type, and the user's assets (logos, screenshots, photos, data, report, code). Never invent facts, numbers, names or results: write `[value]` and list what the user must fill. Ask one short question only if something essential is missing (duration, language, official dates).

### 2. Storyline
Follow `references/storytelling.md` for structure, but with the house titles. Default outline for a **jury defense (internship, PFA, thesis)**, ~1 slide per 40–60 s:
1. Cover (title, presenter pill, supervisor, both logos) · 2. Presentation Plan (6 hexagon cards) · 3. Host Company (pills + short bullets + logo) · 4. Problem Statement (risks as bullets + the problem as one question) · 5. Project Objectives · 6. Work Plan (sprints on a step/timeline slide) · 7. Technical Choices (KPI tiles + "not chosen" line) · 8. Architecture (logical, panels) · 9. Deployed in X (real resources, tiles) · 10. Implementation (why + commands) · 11. Policy / rules (KPI tiles) · 12. Troubleshooting (table: problem, root cause, fix) · 13. Tests and Validation (real screenshots + result tiles) · 14. Cost Analysis (donut + bar chart) · 15. Conclusion and Perspectives · 16. Thank you + "Questions and discussion are welcome".
For 12+ slides show the outline and wait for a yes.

### 3. Library
Everything lives in one folder, `E:\claude-skills\pro-pptx-studio-skill`: the templates in `Templates\` (the only folder where the user adds presentations, any time) and their index in `template-library\` (74 templates rated, tagged and mapped slide by slide). Stage the index, pick templates with `library.py find`, stage only those (`references/template-mode.md`, section 1). Any .pptx in `Templates` that is not in the index yet is new: index it with `scripts/library.py index`, check its roles on `sheet.jpg`, and copy the new index folders back.

### 4. Preview (required unless the user already named a template)
`python3 SKILL_DIR/scripts/tplpreview.py brief.json preview` renders the user's title on the covers of the best-matching templates, as designed and with the topic's fonts. Send `covers.jpg`, ask which letter. They may combine ("B's template with D's fonts", "this one but green").

### 5. Plan and build
Map every storyline slide to a template slide (`library.py show <id>` for slots and positions), respecting the house rules: content slides use template slides with the title on top; text-heavy slides use a canvas of the plainest slide; never the same slide twice in a row. Then:
```bash
python3 SKILL_DIR/scripts/tplbuild.py spec.json
```
- Fonts follow the topic (`"fonts": {"theme": "telecom:0"}`; pairs in `taste.md`), unless the template's own fonts fit and the user picked them.
- Template body slots accept a list of short phrases: `"TextBox 21": ["• Point one", "• Point two"]`.
- Kit components (`references/template-mode.md`, section 5): `kpi` for value tiles, `table` for problem/cause/fix, `code` for a terminal window, `bullets` with `{head, text}`, `chart` (give it a `name` such as `chart-cost` so polish can style it), `image` for screenshots (`fit: contain`).
- Canvas slides remove everything not in `keep`; small decorations survive unless they overlap an `add` box, so list leftovers in `remove` (warnings about shapes already gone are harmless).
- Every slide gets `notes` (the speech, 2–5 sentences). Fix every warning in the report (shorten text first), rebuild.

### 6. Polish and slide numbers
Add a `"polish"` section to the same spec and run `scripts/tplpolish.py` after every build:
```bash
python3 SKILL_DIR/scripts/tplbuild.py spec.json && python3 SKILL_DIR/scripts/tplpolish.py spec.json
```
`polish` operations (slide numbers are 1-based, boxes are fractions `[x, y, w, h]`, colors hex without `#`, `font` is `display|body|mono` or a family name):
- `title_lines`: `[{slide, shape, lines: [..], size, box?}]` rewrite a title as explicit lines (keeps its gradient/style), e.g. a 4-line cover title left of the art.
- `move`: `[{slide, shape, box: [x, y, w?, h?]}]` move or stretch a shape or group (stretching a pill group widens it to fit a long name).
- `center`: `[{slide, shape, box, size?}]` put a text shape exactly over its container and center it.
- `align`: `[{slide, shape, align: l|c|r}]`.
- `logos`: `[{slide, box, files: [..]}]` light chip with logos side by side (aspect kept).
- `text`: `[{slide, box, paras, size, font, color, bold, align, anchor}]` free text, e.g. the large closing line.
- `cards`: `[{slide, box, cols, items: [[num, head, sub], ..]}]` numbered hexagon cards in a gradient (plan slide).
- `diagram`: `[{slide, nodes, links, labels}]`; node `type: tile` = light card with `icon`, `name`, `kind`, `accent` (resource-visualizer look); `type: panel` = translucent box with `lines: [{t, size, color, bold, font}]`, `border`, `fill`, `alpha`, `radius` (0.5 = pill). Links: `from`/`to` as `"id.l|r|t|b"` or `[x, y]`, `via: [[x, y]]` for elbows, `arrows: both|end|start|none`, `dash`, `color`, `width`. Draw outer panels before inner ones.
- `charts`: `[{slide, name, highlight?, center?: [big, small], clean_axes?: true}]` gradient bars/slices, glow on the highlighted point, white labels, hidden value axis, donut center label.
- `remove`: `[{slide, shapes: [..]}]`; `kpi: true` (default) centers KPI tile text and gives a row one value size.
- `numbers` (always on, no need to write it): slide numbers named `slide-number`, re-created on every run. Options: `start_slide` (slide that shows the first number, default 2 = the plan), `start_at` (default 1), `skip` (slide numbers to leave blank, e.g. a full-bleed photo), `box` (default `[0.925, 0.925, 0.055, 0.045]`, bottom-right), `format` (`"{n}"`, or `"{n} / {total}"`), `size` (18), `color` (`text`), `font` (`display`), `bold` (true). `"numbers": false` turns them off, only when the user asks.
- Icons from a screenshot: `python3 SKILL_DIR/scripts/tplpolish.py --icons export.png '{"vm": [x, y, r], "fw": [x, y, r]}' icons/` crops each icon around pixel center (x, y) with half-size r and makes the white background transparent; place them on light tiles.

### 7. QA (required)
```bash
python3 SKILL_DIR/scripts/render.py deck.pptx render --dpi 60 --cols 4
```
Look at the sheet, then every doubtful slide full size, against this checklist: title on top and readable; no text over the central art; text centered in its containers; no paragraph; no word group split; nothing hidden or overlapping; no leftover sample text; slide numbers present (cover blank, plan = 1, closing numbered), readable and not over a logo or content; numbers match the sources; charts only where they add something; the deck reads as one design. If the pptx skill is available, also run its `scripts/office/validate.py`. Glow effects only show in PowerPoint, not in the rendered PDF.

### 8. Deliver
Send the .pptx (and a PDF). In a few lines: template, fonts, motion, what changed, `[value]` items to fill, and any contradiction found in the sources. Then offer, for defenses: a short, memorizable speech (one key word per slide, greeting matched to the time of day), and a jury Q&A list with easy answers grouped by theme (including the trick questions the sources expose). Fonts are embedded (PowerPoint 2019/365); Morph needs PowerPoint 2019+.

## When no template fits
Use the generator (v2): `scripts/deckkit.js` with the 59 styles (`references/components.md`, `references/styles.md`, `node scripts/preview.js`). Even then: house rules (slide numbers included: cover blank, plan = 1, closing numbered), thematic fonts, real images, no emoji-style 3D unless the user asks.

## Banners
See `references/banners.md` (`scripts/banner.js`, 25 sizes). Prefer a library template of the right shape (webinar banner, Instagram post, poster) through `tplbuild.py` when one fits; logos on a light chip; text off the central art.

## Non-negotiables
- Slide numbers on every slide from the table of contents onward.
- Titles at the top, simple, ≤ 2 lines; bullets not paragraphs; never below 12 pt (16 pt for anything the jury must read).
- Never leave template sample text, fake names, fake websites or lorem ipsum.
- Never invent numbers; verify AI-made summaries against the primary files.
- Keep template licenses: Canva templates stay private; SlidesCarnival decks keep the credit line.
- Motion follows speech: titles never animate; one idea per step; diagrams appear whole.
