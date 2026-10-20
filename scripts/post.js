// post.js — post-processing for decks written by pptxgenjs. MIT License.
//  charts(file, specs): vivid native charts — gradient bars and areas, glowing lines, one highlighted point.
//  embedFonts(file, fontsDir): runs embed_fonts.py so the deck carries its fonts.
const fs = require("fs");
const path = require("path");
const { spawnSync } = require("child_process");

function loadJSZip() {
  for (const t of [() => require("jszip"), () => require(require.resolve("jszip", { paths: [path.dirname(require.resolve("pptxgenjs"))] }))]) { try { return t(); } catch (_) {} }
  throw new Error("jszip not found (ships with pptxgenjs)");
}
const clr = (c, alpha) => `<a:srgbClr val="${c}">${alpha !== undefined ? `<a:alpha val="${alpha}"/>` : ""}</a:srgbClr>`;
const grad = (c, ang, a1 = 100000, a2 = 35000) => `<a:gradFill rotWithShape="1"><a:gsLst><a:gs pos="0">${clr(c, a1)}</a:gs><a:gs pos="100000">${clr(c, a2)}</a:gs></a:gsLst><a:lin ang="${ang}" scaled="0"/></a:gradFill>`;
const glow = (c, rad = 76200, a = 45000) => `<a:effectLst><a:glow rad="${rad}">${clr(c, a)}</a:glow></a:effectLst>`;

function styleChart(xml, spec) {
  let i = 0; const cols = spec.colors || [];
  const isBar = /<c:barChart>/.test(xml), isLine = /<c:lineChart>/.test(xml), isArea = /<c:areaChart>/.test(xml);
  if (!isBar && !isLine && !isArea) return xml;
  return xml.replace(/<c:ser>([\s\S]*?)<\/c:ser>/g, (whole, inner) => {
    const c = (cols[i] || cols[0] || "4472C4").toUpperCase(); i++;
    let sp;
    if (isBar) sp = `<c:spPr>${spec.gradient === false ? `<a:solidFill>${clr(c)}</a:solidFill>` : grad(c, spec.horizontal ? 0 : 5400000, 100000, 40000)}<a:ln><a:noFill/></a:ln>${spec.glow ? glow(c, 63500, 30000) : ""}</c:spPr>`;
    else if (isArea) sp = `<c:spPr>${grad(c, 5400000, 70000, 0)}<a:ln w="28575" cap="rnd"><a:solidFill>${clr(c)}</a:solidFill><a:round/></a:ln></c:spPr>`;
    else sp = `<c:spPr><a:ln w="38100" cap="rnd"><a:solidFill>${clr(c)}</a:solidFill><a:round/></a:ln>${spec.glow ? glow(c, 101600, 40000) : ""}</c:spPr>`;
    let out = inner.replace(/<c:spPr>[\s\S]*?<\/c:spPr>/, sp);
    if (!/<c:spPr>/.test(inner)) out = out.replace(/(<c:tx>[\s\S]*?<\/c:tx>)/, `$1${sp}`);
    if (isBar && spec.highlight !== undefined && i === 1) {
      const hc = (spec.accent || c).toUpperCase();
      const dpt = `<c:dPt><c:idx val="${spec.highlight}"/><c:invertIfNegative val="0"/><c:bubble3D val="0"/><c:spPr>${grad(hc, spec.horizontal ? 0 : 5400000, 100000, 70000)}<a:ln><a:noFill/></a:ln>${glow(hc, 127000, 55000)}</c:spPr></c:dPt>`;
      out = out.replace(/<c:dPt>[\s\S]*?<\/c:dPt>/g, "");
      if (/<c:dLbls>/.test(out)) out = out.replace(/<c:dLbls>/, dpt + "<c:dLbls>"); else out = out.replace(/<c:cat>/, dpt + "<c:cat>");
    }
    if (isLine) out = out.replace(/<c:marker>[\s\S]*?<\/c:marker>/, `<c:marker><c:symbol val="circle"/><c:size val="8"/><c:spPr><a:solidFill>${clr(c)}</a:solidFill><a:ln w="19050"><a:solidFill>${clr("FFFFFF")}</a:solidFill></a:ln></c:spPr></c:marker>`);
    return `<c:ser>${out}</c:ser>`;
  });
}

async function charts(file, specs) {
  if (!specs || !specs.length) return { styled: 0 };
  const JSZip = loadJSZip(); const zip = await JSZip.loadAsync(fs.readFileSync(file));
  const parts = Object.keys(zip.files).filter((n) => /^ppt\/charts\/chart\d+\.xml$/.test(n)).sort((a, b) => +a.match(/(\d+)\.xml/)[1] - +b.match(/(\d+)\.xml/)[1]);
  let n = 0;
  for (let k = 0; k < parts.length && k < specs.length; k++) { const x = await zip.file(parts[k]).async("string"); const y = styleChart(x, specs[k]); if (y !== x) { zip.file(parts[k], y); n++; } }
  fs.writeFileSync(file, await zip.generateAsync({ type: "nodebuffer", compression: "DEFLATE", mimeType: "application/vnd.openxmlformats-officedocument.presentationml.presentation" }));
  return { styled: n };
}

function embedFonts(file, fontsDir) {
  const py = process.env.PYTHON || "python3";
  const r = spawnSync(py, [path.join(__dirname, "embed_fonts.py"), file, fontsDir], { encoding: "utf8" });
  if (r.error || r.status !== 0) return { error: (r.stderr || String(r.error)).trim().split("\n").slice(-2).join(" ") || "python3 or fontTools missing (pip install fonttools)" };
  try { return JSON.parse(r.stdout.trim().split("\n").pop()); } catch (_) { return { output: r.stdout.trim() }; }
}

module.exports = { charts, embedFonts, styleChart };
