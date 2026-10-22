// Starter for a new deck. Copy next to your assets, set SKILL_DIR, fill the content, run: node build.js
// Each title is an action title (a sentence stating the takeaway). Each slide has notes.
const path = require("path");
const SKILL_DIR = process.env.SKILL_DIR || "REPLACE_WITH_SKILL_DIR";
const { Deck } = require(path.join(SKILL_DIR, "scripts", "deckkit.js"));

const deck = new Deck({
  style: "nebula",          // the style the user picked in the preview
  motion: "subtle",         // none | subtle | lively | click
  lang: "en",               // en | fr
  title: "Project name",
  topic: "keywords for the 3D hero object",
  footer: "Project name · Event 2026",
  logos: [],                // e.g. ["logos/school.png", "logos/company.png"]
});

deck.cover({ kicker: "Event · 2026", title: "Project name", subtitle: "What it is and how it works, in one line", meta: ["Presented by …", "Supervised by …", "Month 2026"], notes: "Introduce the team and the problem in one sentence." });
deck.agenda({ items: ["Context", "Problem", "Solution", "Results", "Next steps"], notes: "…" });
deck.section({ number: "01", title: "Context", notes: "…" });
deck.stats({ title: "Action title that states what the numbers prove", items: [{ value: "[value]", label: "Metric", note: "Context" }, { value: "[value]", label: "Metric", note: "Context", highlight: true }, { value: "[value]", label: "Metric", note: "Context" }], source: "Organization, year", notes: "…" });
deck.closing({ subtitle: "Project name", contact: ["email@example.com"], notes: "Thank the jury and invite questions." });

deck.save("deck.pptx").catch((e) => { console.error(e); process.exit(1); });
