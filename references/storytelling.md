# Storyline rules

A deck is an argument. Every slide moves it one step, and the audience can follow it from the titles
alone. These rules apply to every deck; the house rules in SKILL.md win if anything here disagrees.

## Titles
- Simple topic titles at the top of the slide, one line when it fits, never more than two lines
  (about 2–6 words): "Problem Statement", "Network Architecture", "Cost Analysis".
- No full-sentence titles. The conclusion of a slide goes in the speaker notes and, when it helps, in one
  short subtitle line under the title ("Third parties doubled in one year").
- English titles in Title Case; French titles in sentence case ("Plan de la présentation").
- Order test: read the titles in order. They should show the structure of the story (context → problem →
  solution → proof → next steps). If a title does not fit that line, the slide is in the wrong place or
  is not needed.

Common titles, English → French:
Presentation Plan → Plan de la présentation · Context → Contexte · Host Company: X → Entreprise d'accueil : X
· Problem Statement → Problématique · Project Objectives → Objectifs du projet · State of the Art → État de
l'art · Work Plan → Plan de travail · Technical Choices → Choix techniques · Network Architecture →
Architecture réseau · Implementation → Réalisation · Tests and Validation → Tests et validation · Results →
Résultats · Cost Analysis → Analyse des coûts · Conclusion and Perspectives → Conclusion et perspectives ·
"Questions and discussion are welcome" → « Place aux questions et à la discussion ».

## Story spine
Most technical decks follow **Situation → Complication → Resolution**:
1. Situation: the context the audience already accepts.
2. Complication: what is broken, costly or missing, quantified when possible.
3. Resolution: the solution, how it works, the proof that it works, what comes next.

Put the main message early (cover subtitle or the problem slide). Juries and judges decide in the first
two minutes whether to follow closely.

## How many slides
There is no fixed number. The content decides, within limits set by the talk time:
- One main idea per slide. Count the ideas the real content supports, then add the cover, the plan (talks
  of 8 minutes or more) and the closing.
- Limits: about one slide per 45–90 seconds of talk. A 10-minute talk gives roughly 8 to 14 slides, a
  3–5 minute pitch 6 to 10, a 20-minute defense 14 to 24.
- Above the limit: merge ideas or move details to the notes and to backup slides. Below it: the content is
  thin; ask the user for the missing material instead of padding.
- Leave the last 10–15 % of the time for the conclusion; it is what the jury remembers.
- Show the outline (the list of titles) and wait for a yes before building any deck of 8 slides or more.

## Building blocks
Pick only the blocks the content supports, in this order. Components in parentheses are the usual choice
(template slide roles in template mode, deckkit components in the generator).

### Jury defense: end-of-year project, internship, thesis
Cover (title, presenter, supervisor, every logo the user gave) → Presentation Plan (numbered hexagon
cards) → Context or Host Company (pills, short bullets, logo) → Problem Statement (risks as bullets, the
problem as one question) → Project Objectives (cards) → Work Plan (steps or timeline) → State of the Art or
Existing Solutions, only when the jury expects it (table) → Technical Choices (KPI tiles plus a "not chosen"
line) → Architecture (logical view as panels) → the real system: screenshots, deployed resources as tiles,
hardware photos → Implementation (why the tool, which commands; one code window) → Tests and Validation
(real screenshots plus result tiles) → Results or Cost Analysis (charts only with real numbers) →
Conclusion and Perspectives → Thank you + "Questions and discussion are welcome" → backup slides.
An internship defense adds the host company and the intern's missions; a thesis adds the state of the art.

### Competition or hackathon pitch (3–7 min)
Hook (one striking fact) → Problem (stats) → Solution in one sentence → Product (bento or mockup) → How it
works (process or architecture) → Impact (KPI or chart) → Cost and feasibility (table) → Roadmap → Team →
Ask (closing).

### Technical talk or workshop
Cover → Plan → for each part: section, the concept, the mechanism (process), an example (code or mockup),
a pitfall (compare) → recap (cards) → resources (closing with links; a QR code when the user gives a link).
An optional about slide after the cover introduces the speaker.

### Progress review or weekly meeting
Status in one sentence → done vs. planned (roadmap with the current step) → key numbers (KPI) → risks and
decisions (table) → next steps.

## Backup slides
For defenses, prepare 2–4 slides after the closing that answer the likely jury questions (choices that were
not made, limits, a detailed result, a cost detail). Mark them `"backup": true`: they are numbered A1, A2...,
not counted in the talk time, and shown only when a question comes.

## Text budget
- Content slide: at most 5 bullets of about 8 words; never a paragraph.
- Cards: head 2–5 words, text up to 20 words. Process steps: text up to 12 words.
- One idea per card, row or step. If a line needs "and" twice, split it.
- The detail the presenter will say goes into the notes.

## Notes and talk time
- Every slide gets notes: what the presenter says, 2–5 short sentences, written to be spoken.
- `tplcheck.py` estimates the talk time from the notes (spoken words ÷ 120 words per minute by default; set
  `"talk": {"minutes": 10, "wpm": 120}` in the spec). If the estimate runs over, shorten the notes. Never
  merge, split or remove slides to fit the time unless the user asks.

## Numbers and facts
- Never invent a number, result, quote, name or source. A missing value → `[value]` on the slide and a line
  in the reply.
- Each number has a unit and a comparison point ("4 min vs. 30 days").
- External data gets a source (author or organization, year).
- Round for the slide (42.7 % → 43 %) and keep the precise figure in the notes.

## Language notes
- French: set `"lang": "fr"` in the spec. The builder then adds the non-breaking space before `: ; ? !` and
  inside `« »`; write "Questions ?" with a normal space or none, it is fixed automatically.
- Word groups ("Sprint 1", "10 Aug", "5 GHz", "Q3 2026") are kept on one line automatically in every language.
- Arabic (RTL) is not supported by the generator layouts; build Arabic slides with `custom()` and
  `rtlMode: true` on text, and check every slide visually.
