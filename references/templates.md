# Learning from templates the user likes

The goal is the same *feel* (palette, type, surfaces, background mood, density), not a copy. Every new style lands in `styles/` of the data folder (the skill folder, or the unpacked bundle cache `~/.cache/pro-pptx-studio`) and is offered in future previews. Styles added to the cache are lost if the cache is cleared: keep a copy of the JSON.

## 1. A .pptx file (Canva download, Slidesgo, SlidesCarnival, an old deck)
```bash
python3 scripts/style_from_template.py template.pptx --id cloud-blue --name "Cloud Blue" --tags security,cloud
```
It reads the theme and slide colors, the fonts (mapped to the bundled open fonts), renders the slides to measure brightness and the dominant palette, and writes `styles/cloud-blue.json` plus `assets/templates/cloud-blue/reference.jpg`. Then:
1. Look at `reference.jpg` next to a preview of the new style (`node scripts/preview.js` with `styles: ["cloud-blue"]`).
2. Edit the JSON by hand where the automatic guess is off: `background.recipe` (aurora, glassblobs, meshlight, network, waves, binary, hex, circuit, gridfloor, sweep, shards, ribbon, orbs, paper, graph, dots, solid), `card.kind` (glass, tile, hud, hex, outline, soft, solid, block, brutal), `hero.kind` (3d, orbs, iso, none), `chrome` (kicker dot/bracket/slash/hex/none, nav, footer text/logos/none), fonts, and `weight` (how much the user likes it).
3. Re-run the preview until it feels like the template.

`--keep-background` copies the template's own full-slide background image and uses it as-is (recipe `image`). Use it only for files the user may reuse and keep that skill private: Canva's license forbids redistributing its content, and SlidesCarnival forbids redistributing its files. Without the flag the style gets a generated background in the same colors, which is safe to share.

## 2. A Canva link (Canva connector)
1. If it is a short `canva.link/…` URL, resolve it (`resolve-shortlink`).
2. `read-design` with `thumbnails` for the pages: look at them to judge the palette, type and layout.
3. `get-export-formats`, then `export-design` as `pptx` and download the file; run method 1 on it.
4. If the export link cannot be downloaded from this environment, ask the user to download it in Canva (Share → Download → PowerPoint) and attach it. Canva drops its animations on export and Pro elements need replacing.

A template only works with the connector once the user has opened it in Canva (that makes a design in their account).

## 3. Screenshots (Behance, Dribbble, Pinterest, a talk)
Look at the images, then write a style JSON by hand starting from the closest existing style (`node scripts/styles.js find "<words>"`): copy it, change the colors to the screenshot's, pick fonts from `assets/fonts`, choose the background recipe and card kind. Preview, compare, adjust.

## 4. Filling a template exactly
When a school or company template is mandatory, do not restyle it: use the pptx skill's template workflow (unzip, duplicate layouts, replace text) and apply only `references/storytelling.md` to the content.

## Fonts in templates
Canva exports embed subsets of their fonts. `style_from_template.py` maps them to the closest bundled open font (TT Hoves → Plus Jakarta Sans, Gotham → Montserrat, HK Modular → Orbitron, Pattanakarn → Saira, Alpha/Extenda → Big Shoulders Display, Canva Sans → DM Sans, …). Commercial fonts are never copied into the skill.
