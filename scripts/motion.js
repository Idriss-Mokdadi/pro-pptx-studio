// motion.js — post-processor for decks written by pptxgenjs (MIT License, see ../LICENSE).
//
// Adds what pptxgenjs cannot write: native PowerPoint slide transitions (Morph, Fade, Push)
// and entrance animations (fade, rise, pop, wipe), plus the deck palette in the theme part so
// PowerPoint's color picker offers the deck colors.
//
// Library use (deckkit.js calls this for you):
//   const { finalize } = require("./motion.js");
//   await finalize("deck.pptx", plan, palette);
//
// CLI use, on any pptxgenjs deck:
//   node motion.js deck.pptx plan.json [out.pptx]
//
// plan = { slides: [ { transition: "morph"|"fade"|"push"|"none", speed: "fast"|"med"|"slow",
//                      mode: "auto"|"click"|"none",
//                      steps: [ { names: ["shapeName", ...], effect: "fade"|"rise"|"pop"|"wipe" } ] } ] }
// plan.slides[i] applies to the i-th slide in presentation order. Shapes are matched by the
// name pptxgenjs writes from `objectName`. Unknown names are reported, never guessed.

const fs = require("fs");
const path = require("path");

function loadJSZip() {
  const tries = [
    () => require("jszip"),
    () => require(require.resolve("jszip", { paths: [path.dirname(require.resolve("pptxgenjs"))] })),
  ];
  for (const t of tries) { try { return t(); } catch (_) { /* next */ } }
  throw new Error("jszip not found. It ships with pptxgenjs: install pptxgenjs (npm i pptxgenjs) or set NODE_PATH to the node_modules folder that holds it.");
}

const DUR = { fade: 450, rise: 550, pop: 450, wipe: 600 };
const PRESET = { fade: [10, 0], rise: [42, 0], pop: [53, 16], wipe: [22, 8] };

function esc(s) { return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }

class Ids { constructor() { this.n = 0; } next() { return ++this.n; } }

function tgt(spid) { return `<p:tgtEl><p:spTgt spid="${spid}"/></p:tgtEl>`; }

function anim(ids, spid, attr, from, to, dur) {
  return `<p:anim calcmode="lin" valueType="num"><p:cBhvr><p:cTn id="${ids.next()}" dur="${dur}" fill="hold"/>${tgt(spid)}` +
    `<p:attrNameLst><p:attrName>${attr}</p:attrName></p:attrNameLst></p:cBhvr><p:tavLst>` +
    `<p:tav tm="0"><p:val><p:strVal val="${from}"/></p:val></p:tav>` +
    `<p:tav tm="100000"><p:val><p:strVal val="${to}"/></p:val></p:tav></p:tavLst></p:anim>`;
}

function effectXml(ids, spid, effect, delay, nodeType) {
  const [presetID, presetSubtype] = PRESET[effect] || PRESET.fade;
  const dur = DUR[effect] || DUR.fade;
  let body = `<p:set><p:cBhvr><p:cTn id="${ids.next()}" dur="1" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst></p:cTn>${tgt(spid)}` +
    `<p:attrNameLst><p:attrName>style.visibility</p:attrName></p:attrNameLst></p:cBhvr><p:to><p:strVal val="visible"/></p:to></p:set>`;
  if (effect === "wipe") {
    body += `<p:animEffect transition="in" filter="wipe(left)"><p:cBhvr><p:cTn id="${ids.next()}" dur="${dur}"/>${tgt(spid)}</p:cBhvr></p:animEffect>`;
  } else {
    body += `<p:animEffect transition="in" filter="fade"><p:cBhvr><p:cTn id="${ids.next()}" dur="${dur}"/>${tgt(spid)}</p:cBhvr></p:animEffect>`;
  }
  if (effect === "rise") {
    body += anim(ids, spid, "ppt_x", "#ppt_x", "#ppt_x", dur);
    body += anim(ids, spid, "ppt_y", "#ppt_y+.05", "#ppt_y", dur);
  } else if (effect === "pop") {
    body += anim(ids, spid, "ppt_w", "#ppt_w*0.70", "#ppt_w", dur);
    body += anim(ids, spid, "ppt_h", "#ppt_h*0.70", "#ppt_h", dur);
  }
  return `<p:par><p:cTn id="${ids.next()}" presetID="${presetID}" presetClass="entr" presetSubtype="${presetSubtype}" fill="hold" grpId="0" nodeType="${nodeType}">` +
    `<p:stCondLst><p:cond delay="${delay}"/></p:stCondLst><p:childTnLst>${body}</p:childTnLst></p:cTn></p:par>`;
}

// steps: [{ spids: [..], effect }]
function timingXml(steps, mode, kinds, stagger) {
  const ids = new Ids();
  const rootId = ids.next(); // 1
  const seqId = ids.next();  // 2
  let groups = "";
  if (mode === "click") {
    for (const st of steps) {
      const outer = ids.next(), inner = ids.next();
      let fx = "";
      st.spids.forEach((spid, i) => { fx += effectXml(ids, spid, st.effect, i * 60, i === 0 ? "clickEffect" : "withEffect"); });
      groups += `<p:par><p:cTn id="${outer}" fill="hold"><p:stCondLst><p:cond delay="indefinite"/></p:stCondLst><p:childTnLst>` +
        `<p:par><p:cTn id="${inner}" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>${fx}</p:childTnLst></p:cTn></p:par>` +
        `</p:childTnLst></p:cTn></p:par>`;
    }
  } else {
    const outer = ids.next(), inner = ids.next();
    let fx = "";
    steps.forEach((st, si) => {
      st.spids.forEach((spid, i) => { fx += effectXml(ids, spid, st.effect, si * stagger + i * 40, "withEffect"); });
    });
    groups = `<p:par><p:cTn id="${outer}" fill="hold"><p:stCondLst><p:cond delay="indefinite"/><p:cond evt="onBegin" delay="0"><p:tn val="${seqId}"/></p:cond></p:stCondLst><p:childTnLst>` +
      `<p:par><p:cTn id="${inner}" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>${fx}</p:childTnLst></p:cTn></p:par>` +
      `</p:childTnLst></p:cTn></p:par>`;
  }
  const all = [...new Set(steps.flatMap((s) => s.spids))];
  let bld = "";
  for (const spid of all) {
    if (kinds[spid] === "nvSpPr") bld += `<p:bldP spid="${spid}" grpId="0" animBg="1"/>`;
    else if (kinds[spid] === "nvGraphicFramePr") bld += `<p:bldGraphic spid="${spid}" grpId="0"><p:bldAsOne/></p:bldGraphic>`;
  }
  return `<p:timing><p:tnLst><p:par><p:cTn id="${rootId}" dur="indefinite" restart="never" nodeType="tmRoot"><p:childTnLst>` +
    `<p:seq concurrent="1" nextAc="seek"><p:cTn id="${seqId}" dur="indefinite" nodeType="mainSeq"><p:childTnLst>${groups}</p:childTnLst></p:cTn>` +
    `<p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst>` +
    `<p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst></p:seq>` +
    `</p:childTnLst></p:cTn></p:par></p:tnLst>${bld ? `<p:bldLst>${bld}</p:bldLst>` : ""}</p:timing>`;
}

function transitionXml(kind, speed) {
  const spd = ["fast", "med", "slow"].includes(speed) ? speed : "med";
  if (kind === "fade") return `<p:transition spd="${spd}"><p:fade/></p:transition>`;
  if (kind === "push") return `<p:transition spd="${spd}"><p:push dir="u"/></p:transition>`;
  if (kind === "morph") {
    // Morph needs PowerPoint 2019 / Microsoft 365. Older viewers and LibreOffice use the Fade fallback.
    return `<mc:AlternateContent xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006">` +
      `<mc:Choice xmlns:p159="http://schemas.microsoft.com/office/powerpoint/2015/09/main" Requires="p159">` +
      `<p:transition spd="${spd}"><p159:morph option="byObject"/></p:transition></mc:Choice>` +
      `<mc:Fallback><p:transition spd="${spd}"><p:fade/></p:transition></mc:Fallback></mc:AlternateContent>`;
  }
  return "";
}

function stripMotion(xml) {
  return xml
    .replace(/<mc:AlternateContent\b[^>]*>(?:(?!<\/mc:AlternateContent>)[\s\S])*?<p:transition[\s\S]*?<\/mc:AlternateContent>/g, "")
    .replace(/<p:transition\b[^>]*\/>/g, "")
    .replace(/<p:transition\b[\s\S]*?<\/p:transition>/g, "")
    .replace(/<p:timing\b[\s\S]*?<\/p:timing>/g, "");
}

function insertMotion(xml, motionXml) {
  if (!motionXml) return xml;
  // CT_Slide order: cSld, clrMapOvr?, transition?, timing?, extLst?
  let at;
  const clr = xml.indexOf("</p:clrMapOvr>");
  if (clr >= 0) at = clr + "</p:clrMapOvr>".length;
  else {
    const c = xml.indexOf("</p:cSld>");
    if (c < 0) throw new Error("slide has no </p:cSld>");
    at = c + "</p:cSld>".length;
  }
  return xml.slice(0, at) + motionXml + xml.slice(at);
}

function shapeIndex(xml) {
  const byName = {}, kinds = {};
  const re = /<p:(nvSpPr|nvPicPr|nvGraphicFramePr|nvCxnSpPr|nvGrpSpPr)>\s*<p:cNvPr\b[^>]*?\bid="(\d+)"[^>]*?\bname="([^"]*)"/g;
  const re2 = /<p:(nvSpPr|nvPicPr|nvGraphicFramePr|nvCxnSpPr|nvGrpSpPr)>\s*<p:cNvPr\b[^>]*?\bname="([^"]*)"[^>]*?\bid="(\d+)"/g;
  let m;
  while ((m = re.exec(xml))) { (byName[unesc(m[3])] ||= []).push(m[2]); kinds[m[2]] = m[1]; }
  while ((m = re2.exec(xml))) { if (!kinds[m[3]]) { (byName[unesc(m[2])] ||= []).push(m[3]); kinds[m[3]] = m[1]; } }
  return { byName, kinds };
}
function unesc(s) { return s.replace(/&quot;/g, '"').replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&amp;/g, "&"); }

async function slideParts(zip) {
  const pres = await zip.file("ppt/presentation.xml").async("string");
  const rels = await zip.file("ppt/_rels/presentation.xml.rels").async("string");
  const relMap = {};
  for (const m of rels.matchAll(/<Relationship\b[^>]*?Id="([^"]+)"[^>]*?Target="([^"]+)"/g)) relMap[m[1]] = m[2];
  for (const m of rels.matchAll(/<Relationship\b[^>]*?Target="([^"]+)"[^>]*?Id="([^"]+)"/g)) relMap[m[2]] ||= m[1];
  const lst = (pres.match(/<p:sldIdLst>([\s\S]*?)<\/p:sldIdLst>/) || [, ""])[1];
  return [...lst.matchAll(/r:id="([^"]+)"/g)].map((m) => "ppt/" + relMap[m[1]].replace(/^\/?ppt\//, "").replace(/^\.\//, ""));
}

function themeScheme(xml, pal) {
  const slots = ["dk1", "lt1", "dk2", "lt2", "accent1", "accent2", "accent3", "accent4", "accent5", "accent6", "hlink", "folHlink"];
  for (const k of slots) if (!/^[0-9A-Fa-f]{6}$/.test(pal.colors[k] || "")) throw new Error(`palette color ${k} must be 6 hex digits`);
  const name = esc(pal.name || "Deck");
  const scheme = `<a:clrScheme name="${name}">` + slots.map((k) => `<a:${k}><a:srgbClr val="${pal.colors[k].toUpperCase()}"/></a:${k}>`).join("") + `</a:clrScheme>`;
  return xml.replace(/<a:clrScheme\b[\s\S]*?<\/a:clrScheme>/, () => scheme).replace(/(<a:theme\b[^>]*?\bname=")[^"]*"/, (_, h) => `${h}${name}"`);
}

async function finalize(deckPath, plan, palette, outPath = deckPath) {
  const JSZip = loadJSZip();
  const zip = await JSZip.loadAsync(fs.readFileSync(deckPath));
  const report = { animated: 0, transitions: 0, missing: [] };
  if (palette) {
    const tp = "ppt/theme/theme1.xml";
    if (zip.file(tp)) zip.file(tp, themeScheme(await zip.file(tp).async("string"), palette));
  }
  if (plan && Array.isArray(plan.slides)) {
    const parts = await slideParts(zip);
    for (let i = 0; i < parts.length && i < plan.slides.length; i++) {
      const sp = plan.slides[i] || {};
      const f = zip.file(parts[i]);
      if (!f) continue;
      let xml = stripMotion(await f.async("string"));
      const { byName, kinds } = shapeIndex(xml);
      let motionXml = "";
      if (sp.transition && sp.transition !== "none") { motionXml += transitionXml(sp.transition, sp.speed); report.transitions++; }
      const steps = [];
      if (sp.mode && sp.mode !== "none" && Array.isArray(sp.steps)) {
        for (const st of sp.steps) {
          const spids = [];
          for (const n of st.names || []) {
            if (byName[n]) spids.push(...byName[n]); else report.missing.push(`slide ${i + 1}: ${n}`);
          }
          if (spids.length) steps.push({ spids, effect: st.effect || "fade" });
        }
      }
      if (steps.length) { motionXml += timingXml(steps, sp.mode, kinds, sp.stagger || 140); report.animated++; }
      zip.file(parts[i], insertMotion(xml, motionXml));
    }
  }
  const buf = await zip.generateAsync({ type: "nodebuffer", compression: "DEFLATE", mimeType: "application/vnd.openxmlformats-officedocument.presentationml.presentation" });
  fs.writeFileSync(outPath, buf);
  return report;
}

module.exports = { finalize, transitionXml, timingXml };

if (require.main === module) {
  const [deck, planFile, out] = process.argv.slice(2);
  if (!deck || !planFile) { console.error("usage: node motion.js deck.pptx plan.json [out.pptx]"); process.exit(2); }
  const plan = JSON.parse(fs.readFileSync(planFile, "utf8"));
  finalize(deck, plan, plan.palette || null, out || deck)
    .then((r) => { console.log(JSON.stringify(r)); if (r.missing.length) process.exitCode = 1; })
    .catch((e) => { console.error(e.message); process.exit(1); });
}
