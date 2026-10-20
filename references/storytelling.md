# Storyline rules

A deck is an argument. The audience should be able to follow it from the slide titles alone, and every slide should earn its place by moving that argument one step.

## Action titles
- Write each title as a complete sentence that states what the audience should conclude: "Edge inference cuts radio-on time by 99%", not "Results".
- 6–14 words, at most two lines, no final period.
- Topic labels ("Context", "Architecture", "Résultats") belong in the small kicker above the title, which deckkit fills from the current section automatically (some styles hide it).
- **Ghost-deck test:** list the titles in order. If someone reading only that list understands the story and the conclusion, the structure works. If not, fix the titles before designing anything.

## Story spine
Most technical decks follow **Situation → Complication → Resolution**:
1. Situation: the context the audience already accepts.
2. Complication: what is broken, costly or missing — quantified when possible.
3. Resolution: your solution, how it works, the proof it works, what comes next.

Put the main message early (cover subtitle or the first statement slide). Juries and judges decide in the first two minutes whether to follow closely.

## Sizing
- Live talk: about 1 slide per minute, never more than 1.5 slides per minute. A 10-minute defense → 10–12 slides including cover and closing.
- Pitch of 3–5 minutes → 7–10 slides, mostly visual.
- Leave the last 10–15% of the time for the conclusion; it is what the jury remembers.

## Archetypes (suggested slide sequence → component)

### Jury defense — PFA, internship, thesis (10–20 min)
1. `cover` — project title as a promise, names, supervisor, institution logos, date
2. `agenda` — only if the talk is ≥ 10 min
3. Context — `statement` or `image`
4. Problem, quantified — `stats` or `chart`
5. Objectives / specifications — `cards` (3–4) or `bento`
6. Existing solutions vs. ours — `compare` or `table`
7. Proposed architecture — `architecture` (groups or layers)
8. How it works — `process`; one `code` slide if code is the point
9. Implementation — `mockup` (dashboard, app), `image` (hardware photos)
10. Results — `chart` (highlight your bar), `kpi`
11. Demo — `statement` "Live demo" or `mockup`
12. Limits and perspectives — `compare` or `roadmap`
13. Conclusion: three things to remember — `cards` or `bento`
14. `closing`

**Internship defense** adds after the cover: the company in one slide (`stats` or `bento`: founded, people, sector), the team and your role (`team`), missions as a `timeline` or `roadmap`, and skills gained (`cards`) before the closing.

### Competition / hackathon pitch (3–7 min)
Hook (`statement`, one striking fact) → Problem (`stats`) → Solution in one sentence (`statement` with `highlight`) → Product (`bento` or `mockup`) → How it works (`process` or `architecture`) → Impact (`kpi` or `chart`) → Cost / feasibility (`table`) → Roadmap (`roadmap`) → Team (`team`) → Ask (`closing`).

### Technical talk / workshop
`cover` → `agenda` → for each part: `section`, the concept (`statement` or `architecture`), the mechanism (`process`), an example (`code` or `mockup`), a pitfall (`compare`) → recap (`cards`) → resources (`closing` with links). An optional `about` slide after the cover introduces the speaker.

### Progress review / weekly meeting
Status in one sentence (`statement`) → done vs. planned (`roadmap` with `current`) → key numbers (`kpi`) → risks and decisions (`compare` or `table`) → next steps (`points`).

## Text budget
- Content slide: ≤ 40 words outside the title. Cards: head 2–5 words, text ≤ 20 words. Process steps: text ≤ 12 words.
- One idea per card, row or step. If you need "and" twice, split.
- Write the detail the presenter will say into `notes:` instead of onto the slide.

## Numbers and facts
- Never invent a number, result, quote, name or source. Missing value → `[value]` on the slide and a line in your reply.
- Each number has a unit and a comparison point ("4 min vs. 30 days").
- External data gets a `source:` (author/organization, year).
- Round for the slide (42.7% → 43%) and keep the precise figure in the notes.

## Language notes
- French: kicker labels come from `lang: "fr"`. Use a non-breaking space before `: ; ? !` (e.g. `"Questions ?"`). Titles in sentence case, not Title Case.
- English: sentence case titles.
- Arabic (RTL) is not supported by the deckkit layouts; build Arabic slides with `custom()` and `rtlMode: true` on text, and check every slide visually.
