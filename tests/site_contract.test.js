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
  "FormatFoundry_Setup_7.1.5-beta.exe",
  "FormatFoundry_7.1.5-beta.exe",
  "FormatFoundry_Updater_7.1.5-beta.exe",
  "FormatFoundry_Portable_7.1.5-beta_windows_x86_64.zip",
  "format-foundry_7.1.5-beta_amd64.deb",
  "FormatFoundry_linux_7.1.5-beta_x86_64.AppImage",
  "FormatFoundry_linux_7.1.5-beta_x86_64.tar.gz",
].map((name) => ({ name, browser_download_url: `${releaseBase}/${name}` }));

const beta = buildSiteConfig("v1.8.18", assets, "Format Foundry Beta 7.1.5 Security Update");
assert.equal(beta.compatible, true);
assert.equal(beta.version, "7.1.5-beta");
assert.equal(beta.displayVersion, "Beta 7.1.5 Security Update");
assert.equal(beta.links.windowsInstaller, `${releaseBase}/FormatFoundry_Setup_7.1.5-beta.exe`);
assert.equal(
  beta.links.windowsPortableFolder,
  `${releaseBase}/FormatFoundry_Portable_7.1.5-beta_windows_x86_64.zip`,
);
assert.equal(beta.links.linuxDeb, `${releaseBase}/format-foundry_7.1.5-beta_amd64.deb`);

const missingInstaller = buildSiteConfig("v1.8.18", assets.slice(1), "Format Foundry Beta 7.1.5 Security Update");
assert.equal(
  missingInstaller.links.windowsInstaller,
  "https://github.com/Pugmaster04/Format-Foundry/releases/tag/v1.8.18",
  "missing assets must fall back to the release page instead of a fabricated 404 URL",
);

const offlineFallback = buildSiteConfig();
assert.equal(offlineFallback.releasePage, "downloads.html#security-update-required");
assert.equal(offlineFallback.displayVersion, "Beta 7.1.5 Security Update required");
assert.equal(offlineFallback.compatible, false);
const unsafeAsset = buildSiteConfig("v1.8.18", [{ name: "FormatFoundry_Setup_7.1.5-beta.exe", browser_download_url: "javascript:alert(1)" }]);
assert.equal(unsafeAsset.links.windowsInstaller, "downloads.html#security-update-required");
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
assert.equal(alpha.displayVersion, "Alpha 1.8.17 (Incompatible)");
assert.equal(alpha.compatible, false);
assert.equal(alpha.links.windowsInstaller, "downloads.html#security-update-required");

for (const metadata of [null, { published: false, productId: "9TEST1234567" }, { published: true, productId: "javascript:alert(1)" }]) {
  assert.equal(applyStoreConfig(alpha, metadata).links.windowsInstaller, alpha.links.windowsInstaller);
}
assert.equal(
  applyStoreConfig(alpha, { published: true, productId: "9TEST1234567", packageVersion: "0.7.1-beta" }).links.windowsInstaller,
  "downloads.html#security-update-required",
);
assert.equal(
  applyStoreConfig(alpha, { published: true, productId: "9TEST1234567", packageVersion: "7.1.5-beta", releaseLabel: "Beta 7.1.5 Security Update" }).links.windowsInstaller,
  "https://apps.microsoft.com/detail/9TEST1234567",
);

const releaseCandidate = buildSiteConfig("v1.8.19", assets, "Format Foundry Release Candidate 0.6");
assert.equal(releaseCandidate.displayVersion, "Release Candidate 0.6 (Incompatible)");
assert.equal(releaseCandidate.compatible, false);

for (const version of ["0.5.0-beta", "0.7.1-beta", "7.1.4-beta", "7.1.5-alpha", "99.0.0-alpha"]) {
  const oldAssets = assets.map((asset) => ({
    name: asset.name.replaceAll("7.1.5-beta", version),
    browser_download_url: asset.browser_download_url.replaceAll("7.1.5-beta", version),
  }));
  const old = buildSiteConfig("v1.8.18", oldAssets);
  assert.equal(old.compatible, false, `${version} must remain incompatible`);
  for (const url of Object.values(old.links)) assert.equal(url, "downloads.html#security-update-required");
}
const policy = JSON.parse(fs.readFileSync(path.join(root, "docs", "release-security.json"), "utf8"));
assert.equal(policy.minimumCompatibleVersion, beta.version);
assert.equal(policy.minimumCompatibleLabel, beta.displayVersion);
assert.ok(policy.incompatibleReleases.every((release) => release.compatible === false && release.downloadsEnabled === false));
const downloads = fs.readFileSync(path.join(root, "docs", "downloads.html"), "utf8");
assert.match(downloads, /id="security-update-required"/);
assert.doesNotMatch(downloads, /href="https:\/\/github\.com\/Pugmaster04\/Format-Foundry\/releases\/(?:latest|download\/)/);

console.log("Website release contract passed.");
