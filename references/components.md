# deckkit components (v2)

```js
const { Deck } = require(SKILL_DIR + "/scripts/deckkit.js");
const deck = new Deck({
  style: "nebula",            // a style id (node scripts/styles.js list) or a path to a style .json
  motion: "subtle",           // none | subtle | lively | click
  lang: "fr",                 // en | fr — default labels (Sommaire, Partie, Merci…)
  title: "Project Title",     // file metadata; also used to pick the 3D hero object
  topic: "network security ai",    // optional, helps pick the hero object
  footer: "Project Title · 2026",
  logos: ["school.png", "company.png"],   // cover logo row; footer row in styles whose chrome.footer is "logos"
  hero: "shield",             // optional 3D object for cover/section/closing (assets/3d/index.json)
  colors: { primary: "…" },   // optional brand override of any style color
  embedFonts: true,           // default: the deck carries its fonts (EOT, like Canva exports)
});
// … queue slides …
await deck.save("deck.pptx");   // prints a JSON report: slides, styled charts, embedded fonts, warnings
```

Options on every slide: `notes` (speaker notes), `motion` ("none" | "auto" | "click"), `kicker` (overrides the section label; `""` hides it).
Icons: a semantic name — shield, lock, ai, brain, chip, antenna, wifi, signal, cloud, server, database, network, code, terminal, bolt, battery, plug, sun, leaf, drop, gauge, chart, bars, pie, target, rocket, users, user, clock, calendar, check, alert, search, settings, tool, phone, laptop, eye, sparkles, star, trophy, book, school, money, globe, map, mail, link, layers, box, thermo, heart, flask, bell, message, play, filter, send, robot, camera, radar, factory, car, home, hospital, handshake, idea, puzzle, key, fingerprint, arrowUp, arrowDown, dollar, megaphone, flag, mic — or any react-icons name (`LuShieldCheck`, `PiRobotFill`).
3D objects (`obj:` on cards/bento/points, `hero:` on the deck): 172 Fluent 3D objects, e.g. robot, satellite-antenna, shield, locked, key, light-bulb, gear, brain, laptop, mobile-phone, high-voltage, battery, electric-plug, bar-chart, chart-increasing, trophy, 1st-place-medal, graduation-cap, books, microscope, microbe, rocket, cloud, globe-showing-europe-africa, factory, hospital, stethoscope, magnifying-glass-tilted-left, bell, calendar, megaphone, handshake, party-popper, joystick. Full list: `assets/3d/index.json`.

## Structure
- **cover** `{ kicker, title, subtitle, meta: [..], date, image?, layout?: "display" }` — hero art from the style (3D object, orbs, isometric) or `image`. Titles ≤ 6 words look best.
- **agenda** `{ title?, items: [..], current? }` — numbered tiles, one row up to 5 items. Reuse with `current` between parts.
- **section** `{ number, title, subtitle? }` — huge display word, hero object glides in with Morph.
- **statement** `{ kicker?, text, highlight?, support? }` — one sentence ≤ 20 words.
- **quote** `{ text, author, role? }` — real quotes only.
- **closing** `{ title?, subtitle?, contact: [..] }`.

## Content
- **cards** `{ title, items: [{ icon | obj, head, text, highlight? }] }` — 2–6 items; 4+ become a grid.
- **bento** `{ title?, items }` — 3–7 tiles (Ivan Volti layout). Tile types: `{type:"hero", kicker?, title, obj?}`, `{type:"stat", value, label, accent?}`, `{type:"feature", icon|obj, head, text}`, `{type:"chips", head, items:[..]}`, `{type:"people", value, label, photos:[..]}`, `{type:"image", path}`.
- **stats** `{ title, items: [{ value, label, note?, highlight? }], source? }` — 2–4 big numbers, glow on dark styles.
- **kpi** `{ title, ring: { value: 0–100, label, display? }, tiles: [{ label, value, delta?: "-12%", good?: true }], trend: { label, values: [..], color? } }` — dashboard slide.
- **chart** `{ title, type: column|bar|line|area|pie|doughnut, data: [{ name, labels, values }], highlight?: index, takeaway?: { value, label, text }, center?: { value, label } (doughnut), format?, source?, gradient?: true }` — native editable chart, restyled after saving: gradient bars and areas, glowing lines, the `highlight` bar in the accent color with a glow.
- **table** `{ title, headers, rows, highlightCol?, highlightRow?, colW? }` — ≤ 8 rows.
- **compare** `{ title, left: { tag?, head, items }, right: { … } }` — right side emphasized.
- **process** `{ title, steps: [{ icon | obj, head, text, highlight? }] }` — 3–5 steps with chevrons.
- **roadmap** `{ title, current, steps: [{ label, head, text?, icon? }] }` — curved path, done part in the accent color, current milestone glows.
- **timeline** `{ title, steps: [{ label, head, text? }] }` — colorful milestones, alternating labels.
- **architecture** `{ title, groups: [{ name, items: [str | { text, highlight }], highlight? }] }` (columns with arrows) or `{ layers: [...], build: "up" }` (stacked layers).
- **points** `{ title, items, obj? }` — numbered list; `obj` adds a 3D object on the right. Use sparingly.

## Product, people, code
- **mockup** `{ title, device: laptop | browser | phone | phones | tablet, screens: [paths], url?, items: [..] }` — real screenshots inside device frames; laptop + `screens[1]` adds a phone in front.
- **image** `{ title, path, items, caption?, fit?: "contain" }` — rounded photo or screenshot on the right.
- **about** `{ name, role, bio, photo?, label?, chips: [..], highlights: [{ value, label }] }` — speaker introduction.
- **team** `{ title, members: [{ name, role, photo? }] }` — initials when no photo.
- **code** `{ title, code, file?, highlight: [line numbers], note? }` — editor window with syntax colors.

## custom — anything else, inside the system
```js
deck.custom({ title: "…" }, async (k) => {
  // k.grid {W,H,M,CW,Y0,Y1,CH} in inches · k.colors · k.style
  const { names, inside } = k.card(0.7, 2.2, 5, 3, "box1", { emphasis: true });   // a surface in the style's own language
  k.text("Text", { x: 1, y: 2.5, w: 4.4, h: 1, fontSize: 18, color: inside.text, objectName: "t1" });
  k.slide.addImage({ path: k.object("robot"), x: 9, y: 2.4, w: 3, h: 3, objectName: "!!hero" });
  k.step([...names, "t1"]); k.step("!!hero", "emph");
});
```
Give every animated element an `objectName`. A name starting with `!!` on consecutive slides makes Morph glide that element between them.
