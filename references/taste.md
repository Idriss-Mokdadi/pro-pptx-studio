# The user's taste (read before every deck or banner)

Built from the user's ratings of style directions, templates, slide types and theme fonts, and from their
feedback on real decks. "Same feel" means these traits.

## The rule that matters most
Decks must look like the user's designer templates: **designer art, not generated art**. Build on real
templates from the library (`references/template-mode.md`). The user firmly rejected decks built on
code-drawn backgrounds and on emoji-style or obviously AI-generated 3D objects, and wants every deck to look
as finished as the .pptx templates they collect. So:
- Backgrounds, photos, 3D renders and decorations come from library templates, the user's own files, or
  Canva (Canva-generated images are approved). Never procedural backgrounds or emoji 3D in template mode.
- Generated parts are limited to what looks right when drawn natively: charts, KPI tiles, tables, code
  windows, timelines, device mockups around real screenshots, QR codes, icons from Lucide or Phosphor.
- Mixing is welcome: icons from one template, background from another, a timeline from an infographic kit,
  recolored to the topic. The result must look like one designer made it.

## Fonts follow the topic
- Cyber / hacker: VT323 + Share Tech Mono, Orbitron + Share Tech Mono, Black Ops One + Rajdhani.
- AI / futuristic: Exo 2 (italic display) + Exo 2, Orbitron + Exo 2, Audiowide + Inter.
- Telecom / network: Saira + Inter, Rajdhani + Inter, Sora + Inter, Titillium Web.
- Energy / industrial: Barlow Condensed + Barlow, Teko + Barlow, Big Shoulders Display + Barlow.
- Defense / academic: Bebas Neue + Montserrat, Big Shoulders Display + Inter, Montserrat + Inter.
- Event / hackathon: Bungee, Monoton, Bowlby One or Rubik Mono One + Montserrat/Inter.
A template's own fonts are also fine when they already fit the topic. Offer both in the preview.

## Effects they love (use whenever possible)
- **Object in front of the title**: a cut-out object overlapping the big title letters (the `depth` kit,
  or a template that already does it).
- **Glow behind a product photo**: a soft colored glow behind a rounded photo or device.
- Hexagon badges, pill labels, HUD frames, glass panels, Morph transitions, step-by-step reveals.
- Numbered hexagon plan cards, real architectures redrawn as clean tiles with official icons, gradient
  charts with a glow on the key value, logos on a light chip.

## Templates
Each template's rating (yes / some / no) and notes live in the library index (`index.json`, `meta.json`)
and drive `library.py find`; templates rated "no" are never proposed. Read the notes of the chosen
templates instead of relying on a list here: the library grows over time.

## Slide types they approved
Glass, dark aurora, abstract 3D, cyber neon, HUD, duotone photos, isometric, device mockups, about-me, KPI
dashboards, roadmaps, code windows, bento grids (with their icons and fonts).

## What they rejected
- Code-drawn backgrounds, emoji-style or obviously AI-made 3D objects, generic fonts on a themed talk.
- Plain white minimal / Swiss layouts, consulting-style white slides, light pastel aurora, editorial
  magazine looks for technical content (editorial bold type only for an about-me part), neo-brutalism,
  blueprint paper, thin-grid SaaS dark.
- "Vibe-coded" signs: a giant circle on the cover, numbered lists as the only design, accent bars under
  titles, alternating white and dark slides, generic blue, lorem-like filler.
- Charts that only repeat what a screenshot already proves, comparisons nobody asked for, titles at the
  bottom of a slide.

## Defaults when the user says nothing
- Template mode first. Show the preview (cover, plan and content slide per template, with theme fonts) and
  let them choose; never pick silently when they are present.
- Motion: Morph between slides plus step reveals (`auto`); `click` when they want to reveal each point.
- Language follows the content and the audience; ask when it is unclear.
- About-me or team slide only when asked or when the deck is a pitch or a competition entry.
