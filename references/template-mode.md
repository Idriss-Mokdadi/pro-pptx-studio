# Template mode (default)

Decks are built on real templates from the library: their backgrounds, photos, 3D art, decorations
and embedded fonts stay; the content is replaced and fitted; missing slide types are drawn with the
kit in the template's own fonts and colors; parts from other templates can be mixed in and
recolored; Morph and step reveals are added.

## 1. The library

On the user's computer, one parent folder named `pro-pptx-studio-skill` holds everything:
- `templates/` (or `Templates/`): the template files themselves, the only place where the user drops new ones.
- `template-library/`: the index (generated, never edited by hand): `index.json`, one folder per template
  (`meta.json`, `fonts/`, `slides/sNN.jpg`, `sheet.jpg`) and `_fonts/` (extra fonts for previews).
  It does not copy the .pptx files: a template is read from `<lib>/<id>/template.pptx` if present,
  otherwise from `meta.source_file` in `PPS_TEMPLATES` or the `templates`/`Templates` folder next to the library.
- `pro-pptx-studio/`: the user's copy of this skill (the GitHub repository), with `references/feedback-log.md`.

Find the folder by name among the folders connected to the session (it may be the connected folder
itself or a folder inside it); never assume a drive letter. Not found: ask the user to connect it.

In a cloud session linked to the computer:
1. Check for new templates (names only, fast): `library.py status --lib <parent>/template-library`.
2. New templates? Index them (see below), then pick with `library.py find` on the index.
3. Stage the chosen templates' library folders (`meta.json`, `fonts/*`, `sheet.jpg`, `slides/*`) plus
   `_fonts/*` if a template needs them, and their .pptx files from `templates`, keeping the layout:
   `./library/<id>/...` and `./templates/<file>.pptx`. Then `export PPS_LIB=$PWD/library`.
4. Not linked: ask the user to attach the template files, index them into a fresh `./library`.

Pass the folder with `"lib"` in specs or set `PPS_LIB` (render.py also uses it for fonts).

### Adding templates (automatic)
Only new files are indexed (by content hash), so point the command at the whole templates folder.
- **On the user's computer (preferred, nothing to copy back):** when a shell on the user's computer is
  available and has `python3`, `soffice` and `pdftoppm`, and the user's copy `<parent>/pro-pptx-studio`
  has the same version as this skill (first line of its SKILL.md title), run there:
  ```bash
  python3 <parent>/pro-pptx-studio/scripts/library.py index <parent>/templates --lib <parent>/template-library --index-only
  ```
  The index is written in place. `--index-only` reads each template where it is (no copy).
- **Otherwise, in the cloud:** stage the new .pptx files and the current `index.json`, index into the
  staged library (`library.py index ./templates --lib ./library`), then, in the same step, write the
  new `<id>/` folders (without `template.pptx`) and the updated `index.json` back to
  `<parent>/template-library` on the user's computer. Never end the step without writing them back.

A file that fails with "not a zip file" is an interrupted download: ask the user to download it again
(`scripts/recover_pptx.py` can salvage the readable parts, but missing pictures stay missing). Fonts
the template uses but cannot be extracted (Google Slides exports compress them) go to `LIB/_fonts` from
github.com/google/fonts, then `library.py rerender <ids|all>`. After indexing, look at each new
`sheet.jpg` and correct the guessed roles and tags, because they drive the choices:
```bash
python3 library.py set <id> --lib LIB --roles "3=stats,5=timeline,8=chart" --tags "cyber,security,hud" --rating yes|some|no --notes "what is special"
```
Roles: cover, agenda, section, statement, quote, text, two-col, list, cards, bento, stats,
big-number, kpi, steps, process, timeline, chart, table, infographic, image-text, about, team,
gallery, mockup, architecture, image, video, closing, assets (a slide of reusable objects),
credits (SlidesCarnival credit slide: never used as content), other (instructions, never used).

Other commands: `find "<topic>" [--mode dark]`, `show <id>` (text slots per slide: kind, shape
name, font, size, lines), `sheet <id>`, `covers [--ids a,b]`, `assets <id> [--slide n] --out DIR`
(extracts the cut-out PNG objects with a numbered sheet, for depth covers), `rerender <ids|all>`.
The library grows over time: never rely on a fixed list of templates, always ask `find` and read the
notes in `meta.json` for what makes each one special.

## 2. Preview (required unless the user named a template)
```bash
cat > brief.json <<'JSON'
{"title": "Project Title", "subtitle": "One-line promise of the project",
 "meta": ["Presenter name", "School · 2026"], "topic": "network ai security",
 "theme": "cyber", "n": 4, "lib": "LIB"}
JSON
python3 SKILL_DIR/scripts/tplpreview.py brief.json preview
```
`covers.jpg` shows each matching template's cover with the user's title, as designed and with the
theme fonts, and next to it the template's plan slide and best content slide (title on top, calm
background) with the count of content slides whose title is at the top. Send it and ask which letter
(AskUserQuestion); a template with few content-ready slides needs more canvas slides. `"templates": [ids]` forces the set,
`"color": "#00FF88"` adds a recolored variant.

## 3. Plan the deck
For every storyline slide choose, in this order:
1. A template slide whose role and slot count match (`library.py show <id>`): same template first,
   then a slide from another template that goes with it (it will be harmonized to the deck's hue).
2. A canvas: a template slide that keeps its background, title and decorations, with the other
   content removed, plus kit components or shapes copied from another template.
Vary layouts; never use the same slide twice in a row.

Text fitting:
- Headlines (sample text at least 3.5% of the slide width in pt, or `"fit": "title"`) are re-flowed
  to fill their slot: 1 to 4 balanced lines with explicit breaks, the size set by the box width and
  the slot height (never above the template size), fewer lines preferred when sizes are close, and
  stacked lines get tight leading. A top-anchored title may grow into free space below its slot
  (up to 1.8x); it stops before texts and pictures below it, narrows before content on its right
  (the box is narrowed too, so centred titles stay centred where possible), ignores backgrounds
  and art behind it, and runs after the font swap so the final font is measured.
- Small stickers placed over the sample title are reported (`overlaps`); the cover preview removes
  them, in a deck decide: keep, move or `remove`.
- A title split over two template shapes ("Digital / Media"): give each part its own shape, or put
  the whole title in the first with `{"text": "...", "merge": ["<second shape>"]}` (one headline over
  both slots). Split lines of one template size end up the same size.
- Below 45% of the template size the report warns: shorten the title if it looks small.
- Other texts keep the template's sample line count (`max_lines` to change it) and shrink if needed.

## 4. The spec
```json
{
 "lib": "LIB", "base": "<template id>", "out": "deck.pptx",
 "fonts": {"theme": "cyber:1"},          // or {"display": "Orbitron", "body": "Share Tech Mono"}, or omit to keep the template fonts
 "recolor": "#00E5FF",                   // optional: rotate the deck's accent hue to the topic color
 "harmonize": true,                      // default: slides from other templates take the base hue
 "motion": "auto",                       // auto | click | none
 "lang": "fr",                           // en (default) | fr: French spacing before ? ! ; : and « »
 "talk": {"minutes": 10, "wpm": 120},    // for tplcheck.py: estimated talk time from the notes
 "replace": {"Cloudlet Systems": "Organization Name", "November 2035": "2026"},   // exact sample texts, every slide
 "slides": [
  {"use": "#11", "canvas": {"keep": ["TextBox 7", "TextBox 10"]},   // keep background, decorations and these shapes only
   "text": {"TextBox 10": "THIRD PARTIES DOUBLED"}, "add": [{"kit": "chart", "box": [0.16, 0.36, 0.68, 0.5], "...": "..."}]},
  {"use": "#1",                                        // base slide 1, or "<other id>#n"
   "text": {"TextBox 9": "CYBER SECURITY", "TextBox 19": "How attacks happen", "TextBox 18": ["para 1", "para 2"]},
   "remove": ["TextBox 20", "Group 7"],                 // shapes to delete (after copies)
   "images": {"Freeform 5": "photos/team.jpg"},         // replace a picture, cropped to fill its frame
   "copy": [{"from": "colorful-and-white-modern-timeline#3", "region": [0, 0.14, 1, 0.72],
             "box": [0.02, 0.42, 0.96, 0.52], "prefix": "t:", "adapt_text": "dark"},
            {"from": "artificial-intelligence-to-enhance-language-skil#12", "shape": "Freeform 7", "box": [0.7, 0.3, 0.2, 0.4]}],
   "recolor": {"to": "#2D8CFF", "mode": "mono"},       // per slide: mono = every color takes this hue (good for rainbow kits)
   "add": [{"kit": "chart", "box": [0.2, 0.43, 0.6, 0.47], "kind": "column", "categories": ["2024", "2025"],
            "series": [{"name": "Third-party breaches", "values": [0.15, 0.30]}], "highlight": 1, "number_format": "0%"}],
   "animate": "auto",                                   // or [{"shapes": ["Group 2", "TextBox 26"], "effect": "pop"}, ...] or "none"
   "notes": "What the presenter says."},
  {"use": "#13", "backup": true, "canvas": {"keep": ["TextBox 11"]}, "text": {"TextBox 11": "Why Not Kubernetes?"},
   "notes": "Answer to a likely jury question."}          // backup slides go after the closing: numbered A1, A2...
 ]
}
```
Optional per slide: `"title_shapes": ["TextBox 9"]` names the title when the builder guesses wrong (the
title gets the Morph name and the title-at-top check), `"role": "section"` overrides the template role,
`"backup": true` marks a backup slide. Run `python3 SKILL_DIR/scripts/tplbuild.py spec.json`. Boxes are fractions of the slide
`[x, y, w, h]`. Copied shapes are renamed with their prefix (`t:TextBox 74`), so fill them with
`text` in the same slide. Leftover sample text (lorem ipsum, reallygreatsite, "Your sample…") is
removed automatically. The report lists every text fit, refits after a font change, recolors,
copies and warnings: fix every warning (shorten text first), then rebuild.

## 5. Kit components (`"add"`)
All take `box` and use the template's fonts and colors (`theme` in the report; override with a
top-level `"theme": {"accent": "00FF88"}`).
- `chart`: kind column|bar|line|area|donut|pie|stacked, categories, series [{name, values}],
  highlight (index of the bar that proves the point), number_format ("0%", "0.0", "#,##0"), unit, legend, title.
- `kpi`: items [{value, label, note, highlight}] as glass tiles.
- `table`: rows [[...]], header, col_widths, highlight_row.
- `code`: src, lang (any language Pygments knows: python, c, cpp, arduino, java, kotlin, javascript,
  yaml, json, terraform, docker, sql, matlab, bash...; `terminal` for commands with a `$` prompt and their
  output; `auto` to guess), filename (default from the language), highlight [line numbers].
- `qr`: url, label: a scannable QR code on a light chip. Only when the user gives a link or asks for one
  (closing slide: repository, demo video, contact).
- `bullets`: items [str | {head, text}], numbered, size.
- `text`: paras, role title|display|body|label|mono, align, size, color.
- `timeline`: items [{date, head, text, highlight}] (prefer copying a timeline from the kits).
- `image`: path, rounded, glow (soft accent glow behind: the effect the user loves), fit cover|contain.
- `mockup`: screenshot, device laptop|phone|browser, glow.
- `depth`: cutout (PNG with transparency), glow, shadow. Added last, so it sits in front of the
  title: place the box so the object overlaps the lower part of the title letters.
- `credit`: added automatically on the last slide when a SlidesCarnival template is used (CC BY 4.0).

## 6. Recipes
- **Depth cover**: base cover, then `{"kit": "depth", "cutout": "obj.png", "box": [0.42, 0.18, 0.4, 0.75]}`.
  Cut-outs: `assets` slides in the library (robots, 3D shapes, glass ribbons), PNG objects in
  templates (`library.py show` marks pictures with `png`), the user's photos (remove the background
  with the Canva connector `remove-background` when available), or Canva `generate-image` when the
  user approves it.
- **Glow photo**: `{"kit": "image", "path": "watch.jpg", "glow": true, "rounded": 0.08}`.
- **Timeline / roadmap**: copy a region from `colorful-and-white-modern-timeline` or
  `colorful-modern-infographic-timeline`, `adapt_text: "dark"` on dark decks, per-slide
  `recolor` mono to the deck accent, then fill `prefix:TextBox n` names (`library.py show` lists
  them; order milestones by x position) and remove the extra milestone shapes.
- **Chart or code slide**: canvas = a template slide with a title and empty space; remove its
  other content; add the kit component under the title.
- **Topic color**: `"recolor": "#hex"` rotates the accent hue in shapes, text, gradients, theme,
  backgrounds and decorative images; framed photos stay natural.

## 7. QA
```bash
python3 SKILL_DIR/scripts/render.py deck.pptx render --dpi 60 --cols 4
python3 SKILL_DIR/scripts/tplcheck.py spec.json --render render
```
The renderer uses the fonts embedded in the deck plus the skill fonts. Check every slide: text
inside its frame, no sample text left, numbers correct, nothing hidden behind art, the mix of
templates looks like one deck. Morph and animations only play in PowerPoint.

## Licenses
Canva templates: the user's own designs for their own decks; never share the template files.
SlidesCarnival: CC BY 4.0, keep the credit line; do not redistribute the files as they are.
The library therefore stays private (on the user's computer), outside the shareable skill zip.
