# Polish pass (tplpolish.py)

Open this file before writing the `"polish"` section of a spec. Run the polish after every build, on the
same spec:
```bash
python3 SKILL_DIR/scripts/tplbuild.py spec.json && python3 SKILL_DIR/scripts/tplpolish.py spec.json
```
Slide numbers are 1-based, boxes are fractions `[x, y, w, h]` of the slide, colors are hex without `#`,
`font` is `display|body|mono` or a family name. Shapes can be named by their name or by `#id`.

## Operations
- `title_lines`: `[{slide, shape, lines: [..], size, box?}]` rewrites a title as explicit lines (keeps its
  gradient and style), e.g. a 4-line cover title placed beside the central art.
- `move`: `[{slide, shape, box: [x, y, w?, h?]}]` moves or stretches a shape or group (stretching a pill
  group widens it to fit a long name).
- `center`: `[{slide, shape, box, size?}]` puts a text shape exactly over its container (pill, hexagon,
  tile, card: measure the visible shape, not only the inner freeform) and centers it both ways.
- `align`: `[{slide, shape, align: l|c|r}]`.
- `logos`: `[{slide, box, files: [..]}]` light rounded chip with logos side by side (aspect kept). Cover and
  closing get every logo the user gave (school, company, club); the company slide gets the company logo.
- `text`: `[{slide, box, paras, size, font, color, bold, align, anchor}]` free text, e.g. the large closing
  line ("Questions and discussion are welcome", at least 32 pt).
- `cards`: `[{slide, box, cols, items: [[num, head, sub], ..]}]` numbered hexagon cards in a gradient (plan
  slide).
- `diagram`: `[{slide, nodes, links, labels}]`.
  - Node `type: tile`: light card with `icon`, `name`, `kind`, `accent` (the look of a cloud provider's
    resource view).
  - Node `type: panel`: translucent box with `lines: [{t, size, color, bold, font}]`, `border`, `fill`,
    `alpha`, `radius` (0.5 = pill).
  - Links: `from`/`to` as `"id.l|r|t|b"` or `[x, y]`, `via: [[x, y]]` for elbows,
    `arrows: both|end|start|none`, `dash`, `color`, `width`. Draw outer panels before inner ones.
- `charts`: `[{slide, name, highlight?, center?: [big, small], clean_axes?: true}]` gradient bars or slices,
  a glow on the highlighted point, white labels, a hidden value axis and a donut center label.
- `canvas`: `{aspect, top?, left?}` crops the slide to a banner after everything else. The aspect must be
  above 1; `top` and `left` are fractions of the 16:9 slide where the kept band starts. Every shape is
  shifted, so place the content inside the band first.
- `remove`: `[{slide, shapes: [..]}]` (a missing shape is a warning, not an error).
- `kpi: true` (default): centers the text of KPI tiles and gives a row one value size.

## Slide numbers (always on)
`numbers` does not need to be written. Numbers are named `slide-number` and re-created on every run. The
cover has no number, numbering starts at the plan (= 1) and the closing slide is numbered. Backup slides
(`"backup": true` in the spec) are numbered `A1`, `A2`... and are not counted in `{total}`.

When the template already prints page numbers (a slide-number field or a small number near an edge such
as "01"), the polish reuses them in their own style and copies one to slides that lack it, so there is
never a second set. Numbers move up when a logo chip or a card sits in their corner.

Options:
- `start_slide`: the slide that shows the first number (default 2 = the plan).
- `start_at`: the first number (default 1).
- `skip`: slide numbers to leave blank, e.g. a full-bleed photo.
- `box`: position (default `[0.925, 0.925, 0.055, 0.045]`, bottom-right).
- `format`: `"{n}"` (default) or `"{n} / {total}"`.
- `backup_format`: default `"A{k}"`.
- `size` (18), `color` (`text`), `font` (`display`), `bold` (true).

Set `"numbers": false` only when the user asks for a deck without numbers.

## Morph names (automatic)
When the transition is Morph (the default), the polish names the title of every slide `!!title`, the slide
number `!!slide-number` and the logo chip `!!logos`. PowerPoint then glides these objects from one slide to
the next instead of fading them. Other shapes keep their template names, so templates designed with their
own Morph keep working. `"morph_names": false` turns this off. Morph plays only in PowerPoint 2019 and
later; older versions show a fade.

## French and word groups
The polish applies the same typography as the build, using the spec's `lang`: non-breaking spaces in word
groups such as "Sprint 1", "10 Aug", "5 GHz" and "Q3 2026", and the French spaces before `? ! ; :` and
inside `« »`.

## Icons from a screenshot
```bash
python3 SKILL_DIR/scripts/tplpolish.py --icons export.png '{"vm": [x, y, r], "fw": [x, y, r]}' icons/
```
This crops each icon around the pixel center (x, y) with half-size r and makes the white background
transparent. Place the icons on light tiles (`diagram` nodes of type `tile`).
