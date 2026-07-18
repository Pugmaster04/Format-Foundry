const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
const source = fs.readFileSync(path.join(root, "docs", "site.js"), "utf8");
const marker = /\s+init\(\);\s*\}\)\(\);\s*$/;
assert.match(source, marker, "site.js bootstrap marker changed");
const instrumented = source.replace(
  marker,
  "\n  globalThis.__formatFoundrySiteTest = { buildSiteConfig };\n})();\n",
);
const context = { console };
vm.createContext(context);
vm.runInContext(instrumented, context, { filename: "site.js" });
const { buildSiteConfig } = context.__formatFoundrySiteTest;

const releaseBase = "https://github.com/Pugmaster04/Format-Foundry/releases/download/v1.8.18";
const assets = [
  "FormatFoundry_Setup_0.5.0-beta.exe",
  "FormatFoundry_0.5.0-beta.exe",
  "FormatFoundry_Updater_0.5.0-beta.exe",
  "format-foundry_0.5.0-beta_amd64.deb",
  "FormatFoundry_linux_0.5.0-beta_x86_64.AppImage",
  "FormatFoundry_linux_0.5.0-beta_x86_64.tar.gz",
].map((name) => ({ name, browser_download_url: `${releaseBase}/${name}` }));

const beta = buildSiteConfig("v1.8.18", assets, "Format Foundry Beta 0.5");
assert.equal(beta.version, "0.5.0-beta");
assert.equal(beta.displayVersion, "Beta 0.5");
assert.equal(beta.links.windowsInstaller, `${releaseBase}/FormatFoundry_Setup_0.5.0-beta.exe`);
assert.equal(beta.links.linuxDeb, `${releaseBase}/format-foundry_0.5.0-beta_amd64.deb`);

const missingInstaller = buildSiteConfig("v1.8.18", assets.slice(1), "Format Foundry Beta 0.5");
assert.equal(
  missingInstaller.links.windowsInstaller,
  "https://github.com/Pugmaster04/Format-Foundry/releases/tag/v1.8.18",
  "missing assets must fall back to the release page instead of a fabricated 404 URL",
);

const offlineFallback = buildSiteConfig();
assert.equal(offlineFallback.releasePage, "https://github.com/Pugmaster04/Format-Foundry/releases/latest");

const alphaAssets = [
  {
    name: "FormatFoundry_Setup_1.8.17.exe",
    browser_download_url:
      "https://github.com/Pugmaster04/Format-Foundry/releases/download/v1.8.17/FormatFoundry_Setup_1.8.17.exe",
  },
];
const alpha = buildSiteConfig("v1.8.17", alphaAssets, "Format Foundry v1.8.17");
assert.equal(alpha.version, "1.8.17");
assert.equal(alpha.displayVersion, "Alpha 1.8.17");

const releaseCandidate = buildSiteConfig("v1.8.19", assets, "Format Foundry Release Candidate 0.6");
assert.equal(releaseCandidate.displayVersion, "Release Candidate 0.6");

console.log("Website release contract passed.");
