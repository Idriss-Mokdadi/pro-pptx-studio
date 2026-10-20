# Banners

```js
const { Banner, SIZES } = require(SKILL_DIR + "/scripts/banner.js");
await new Banner({
  style: "nebula", size: "linkedin-post", layout: "event",
  kicker: "IEEE IES/PES ENET'Com SBJC", title: "ElectroSpark 2.0", subtitle: "Talks and a 6-hour hackathon",
  details: [{ icon: "calendar", text: "12 Nov 2026" }, { icon: "map", text: "ENET'Com, Sfax" }],
  cta: "Register now", logos: ["ieee.png"], obj: "high-voltage", handle: "@ieee.enetcom",
}).save("out/electrospark-linkedin");   // → .pptx (editable), .png (exact pixels), .pdf
```

## Sizes (`size:`)
Pixel sizes follow Metricool's 2026 guide; platforms change them, so check before an important post.
- LinkedIn: `linkedin-banner` 1584×396 (profile), `linkedin-company` 1128×376, `linkedin-post` 1200×627, `linkedin-square` 1080×1080
- Facebook: `facebook-cover` 1702×630 (2× of 851×315), `facebook-event` 1920×1005, `facebook-post` 1200×1200
- Instagram: `instagram-square` 1080×1080, `instagram-portrait` 1080×1350, `story` 1080×1920
- X: `x-header` 1500×500, `x-post` 1200×675 · YouTube: `youtube-thumbnail` 1280×720, `youtube-banner` 2048×1152
- `webinar` / `slide` 1920×1080
- Print (mm, exported at 150 dpi + PDF): `a4`, `a4-landscape`, `a3`, `a2`, `rollup` (850×2000)
- Custom: `size: { px: [w, h] }` or `{ mm: [w, h] }`

## Layouts (`layout:`)
- `event` — kicker, title, subtitle, detail rows with icons, CTA pill, logos
- `webinar` — speaker `photo` in a ring, `speaker: { name, role }`, date/time details, CTA
- `announcement` — big statement + subtitle
- `achievement` — trophy (or `obj`), e.g. "1st place in Tunisia", event and team
- `quote` — `title` is the quote text
- `countdown` — `count: 3`, `unit: "days left"`
- `profile` — LinkedIn profile banner: text starts at 30 % width to leave room for the profile photo

The text stack is measured and scaled to fit; art goes right on landscape sizes and on top on portrait sizes.

## Workflow
1. Collect the real facts (event name, date, time, place, link, logos). Never invent them; use `[date]` placeholders and list them.
2. Show 3–4 styles: `node scripts/banner_preview.js brief.json outdir` (same fields as the Banner options, plus optional `styles: [...]`). Send the sheet; let the user pick.
3. Build every size they need from the same content, check each PNG by looking at it, deliver PNG (to post) + PPTX (to edit) + PDF (to print).
