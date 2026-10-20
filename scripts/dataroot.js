// Where the skill's data files live (MIT License). Fonts, 3D objects and styles ship as
// assets/bundle.tar.xz; the first use unpacks it into PPS_CACHE or ~/.cache/pro-pptx-studio.
const fs = require("fs");
const os = require("os");
const path = require("path");
const { execFileSync } = require("child_process");

const SKILL = path.join(__dirname, "..");
let cached = null;

function dataRoot() {
  if (cached) return cached;
  if (fs.existsSync(path.join(SKILL, "assets", "fonts"))) return (cached = SKILL);
  const bundle = path.join(SKILL, "assets", "bundle.tar.xz");
  if (!fs.existsSync(bundle)) return (cached = SKILL);
  const cache = process.env.PPS_CACHE || path.join(os.homedir(), ".cache", "pro-pptx-studio");
  const stamp = path.join(cache, ".unpacked-" + fs.statSync(bundle).size);
  if (!fs.existsSync(stamp)) {
    fs.mkdirSync(cache, { recursive: true });
    try {
      execFileSync("python3", ["-m", "tarfile", "-e", bundle, cache]);
    } catch (e) {
      execFileSync("tar", ["-xJf", bundle, "-C", cache]);   // no python3 on PATH
    }
    fs.writeFileSync(stamp, "ok");
  }
  return (cached = cache);
}

module.exports = { dataRoot, SKILL };
