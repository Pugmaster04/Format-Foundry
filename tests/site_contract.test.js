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
  "\n  globalThis.__formatFoundrySiteTest = { buildSiteConfig, applyStoreConfig };\n})();\n",
);
const context = { console };
vm.createContext(context);
vm.runInContext(instrumented, context, { filename: "site.js" });
const { buildSiteConfig, applyStoreConfig } = context.__formatFoundrySiteTest;

const releaseBase = "https://github.com/Pugmaster04/Format-Foundry/releases/download/v1.8.18";
const assets = [
  "FormatFoundry_Setup_0.7.1-beta.exe",
  "FormatFoundry_0.7.1-beta.exe",
  "FormatFoundry_Updater_0.7.1-beta.exe",
  "FormatFoundry_Portable_0.7.1-beta_windows_x86_64.zip",
  "format-foundry_0.7.1-beta_amd64.deb",
  "FormatFoundry_linux_0.7.1-beta_x86_64.AppImage",
  "FormatFoundry_linux_0.7.1-beta_x86_64.tar.gz",
].map((name) => ({ name, browser_download_url: `${releaseBase}/${name}` }));

const beta = buildSiteConfig("v1.8.18", assets, "Format Foundry Beta 0.7.1");
assert.equal(beta.version, "0.7.1-beta");
assert.equal(beta.displayVersion, "Beta 0.7.1");
assert.equal(beta.links.windowsInstaller, `${releaseBase}/FormatFoundry_Setup_0.7.1-beta.exe`);
assert.equal(
  beta.links.windowsPortableFolder,
  `${releaseBase}/FormatFoundry_Portable_0.7.1-beta_windows_x86_64.zip`,
);
assert.equal(beta.links.linuxDeb, `${releaseBase}/format-foundry_0.7.1-beta_amd64.deb`);

const missingInstaller = buildSiteConfig("v1.8.18", assets.slice(1), "Format Foundry Beta 0.7.1");
assert.equal(
  missingInstaller.links.windowsInstaller,
  "https://github.com/Pugmaster04/Format-Foundry/releases/tag/v1.8.18",
  "missing assets must fall back to the release page instead of a fabricated 404 URL",
);

const offlineFallback = buildSiteConfig();
assert.equal(offlineFallback.releasePage, "https://github.com/Pugmaster04/Format-Foundry/releases/latest");
assert.equal(offlineFallback.displayVersion, "View current release", "Offline pages must not claim an unpublished or stale version is current");
const unsafeAsset = buildSiteConfig("v1.8.18", [{ name: "FormatFoundry_Setup_0.7.1-beta.exe", browser_download_url: "javascript:alert(1)" }]);
assert.equal(unsafeAsset.links.windowsInstaller, "https://github.com/Pugmaster04/Format-Foundry/releases/latest");
for (const name of ["index.html", "downloads.html", "license.html"]) {
  const html = fs.readFileSync(path.join(root, "docs", name), "utf8");
  assert.doesNotMatch(html, /data-link="[^"]+" href="#"/, `${name} needs working no-JavaScript links`);
}

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

for (const metadata of [null, { published: false, productId: "9TEST1234567" }, { published: true, productId: "javascript:alert(1)" }]) {
  assert.equal(applyStoreConfig(alpha, metadata).links.windowsInstaller, alpha.links.windowsInstaller);
}
assert.equal(
  applyStoreConfig(alpha, { published: true, productId: "9TEST1234567" }).links.windowsInstaller,
  "https://apps.microsoft.com/detail/9TEST1234567",
);

const releaseCandidate = buildSiteConfig("v1.8.19", assets, "Format Foundry Release Candidate 0.6");
assert.equal(releaseCandidate.displayVersion, "Release Candidate 0.6");

console.log("Website release contract passed.");
