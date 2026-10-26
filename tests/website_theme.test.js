const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const theme = require("../docs/theme.js");
const docs = path.join(__dirname, "..", "docs");

test("published CSS matches the canonical appearance file", () => {
  const config = JSON.parse(fs.readFileSync(path.join(docs, "theme.json"), "utf8"));
  assert.equal(theme.css(config), fs.readFileSync(path.join(docs, "theme.css"), "utf8"));
});

test("untrusted appearance files cannot inject CSS, scripts, font URLs, or extra fields", () => {
  for (const overrides of [
    { accent: "#000000;}</style><script>alert(1)</script>" }, { bodyFont: "url(https://invalid.test/)" },
    { headingFont: "__proto__" }, { textSize: true }, { textSize: NaN }, { contentWidth: 100000 },
    { showGrid: "false" }, { schemaVersion: 2 }, { unknown: "property" },
  ]) assert.throws(() => theme.css({ ...theme.defaults, ...overrides }));
  assert.throws(() => theme.validate([]));
  assert.throws(() => theme.validate({}));
});

test("imports normalize color case and field order for stable undo and save detection", () => {
  const reordered = Object.fromEntries(Object.entries({ ...theme.defaults, accent: "#1FA58E" }).reverse());
  assert.equal(JSON.stringify(theme.validate(reordered)), JSON.stringify(theme.defaults));
});

test("every preset has readable text and supported settings", () => {
  for (const preset of Object.values(theme.presets)) {
    assert.doesNotThrow(() => theme.validate(preset.theme));
    assert.ok(theme.contrast(preset.theme.text, preset.theme.background) >= 4.5, preset.label);
    assert.ok(theme.contrast(preset.theme.muted, preset.theme.background) >= 4.5, preset.label);
    for (const token of ["accent-text", "highlight-text"]) {
      const color = theme.css(preset.theme).match(new RegExp(`--${token}: (#[0-9a-f]{6});`))[1];
      assert.ok(theme.contrast(color, preset.theme.background) >= 4.5, `${preset.label} ${token}`);
    }
  }
});

test("every public page loads the theme and keeps the download security policy", () => {
  for (const name of ["index.html", "downloads.html", "license.html", "404.html"]) {
    const html = fs.readFileSync(path.join(docs, name), "utf8");
    assert.match(html, /href="theme\.css"/);
    assert.match(html, /defer src="theme\.js"/);
  }
  const html = fs.readFileSync(path.join(docs, "downloads.html"), "utf8");
  assert.match(html, /id="security-update-required"/);
  assert.match(html, /Beta 7\.1\.5 Security Update/);
  assert.match(fs.readFileSync(path.join(docs, "appearance.html"), "utf8"), /id="publish-dialog"/);
});
