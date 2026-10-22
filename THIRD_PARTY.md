# Third-party material

Fonts, 3D objects and generator styles are packed in `assets/bundle.tar.xz` (to stay under the skill upload limit of 200 files); paths below are inside that archive, which the scripts unpack on first use to `~/.cache/pro-pptx-studio` (or `PPS_CACHE`).

- **Fonts** (`assets/fonts/*`): Google Fonts families under the SIL Open Font License 1.1. Each folder contains the family's OFL.txt. Most files were instanced to static weights, subset to Latin, and renamed for PowerPoint (allowed by the OFL as modified versions). Families with Reserved Font Names (Alfa Slab One, Audiowide, Bowlby One, Press Start 2P, Russo One, Share Tech Mono, Monoton) and Black Ops One, Bungee, Rubik Mono One are shipped unmodified. Teko was instanced from the variable font (no reserved name). Fonts embedded into decks are subsets, which the OFL allows for documents.
- **3D objects** (`assets/3d/*.png`): Microsoft Fluent Emoji, MIT License, Copyright (c) Microsoft Corporation. See `assets/3d/LICENSE-MIT-Microsoft-Fluent-Emoji.txt`. Generator fallback only.
- **Icons**: rendered at build time from react-icons (MIT), which packages Lucide (ISC) and Phosphor (MIT).
- **Python libraries** (installed with `pip install -r requirements.txt`, not bundled): python-pptx (MIT), lxml (BSD-3-Clause), fonttools (MIT), Pillow (MIT-CMU), numpy (BSD-3-Clause), Pygments (BSD-2-Clause, code window colors), qrcode (BSD, QR codes).
- **Ported design systems** (`styles/*` with group "system"): palettes and font pairings from beautiful-html-templates by zarazhangrui, MIT License. No template code or assets are included.
- **Template library**: not part of this package. It lives privately on the user's computer and holds the user's own Canva designs (Canva Content License: for the owner's own use) and SlidesCarnival templates (CC BY 4.0: credit SlidesCarnival, do not redistribute the files as they are). Decks built on SlidesCarnival templates get a credit line automatically.
