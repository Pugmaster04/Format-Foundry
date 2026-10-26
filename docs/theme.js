(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.FormatFoundryTheme = api;
  if (typeof document !== "undefined") {
    const source = document.currentScript?.src;
    if (!source || document.documentElement.dataset.appearanceEditor === "true") return;
    let previewReceived = false;
    if (new URLSearchParams(location.search).get("theme-preview") === "1" && window.parent !== window) {
      const previewPages = new Set(["index.html", "downloads.html", "license.html", "404.html"]);
      document.addEventListener("click", (event) => {
        const link = event.target.closest?.("a[href]");
        if (!link) return;
        const target = new URL(link.href);
        if (target.origin !== location.origin || !previewPages.has(target.pathname.split("/").pop())) return;
        target.searchParams.set("theme-preview", "1");
        event.preventDefault(); location.assign(target.href);
      });
      window.addEventListener("message", (event) => {
        if (event.source !== window.parent || event.origin !== location.origin || event.data?.channel !== "format-foundry-theme") return;
        try { api.apply(event.data.theme, document); previewReceived = true; } catch { /* Invalid preview data is ignored. */ }
      });
    }
    const url = new URL("theme.json", source);
    url.searchParams.set("v", String(Date.now()));
    fetch(url, { cache: "no-store" }).then((response) => {
      if (!response.ok) throw new Error("Appearance file unavailable");
      return response.json();
    }).then((theme) => { if (!previewReceived) api.apply(theme, document); })
      .catch(() => { /* The checked-in theme.css remains available offline and without JavaScript. */ });
  }
})(globalThis, function () {
  "use strict";
  const defaults = Object.freeze({
    schemaVersion: 1, background: "#07131a", panel: "#0b1b23", text: "#eff5f2", muted: "#a7b9b2",
    accent: "#1fa58e", highlight: "#f6efe6", border: "#add8e6", bodyFont: "plex", headingFont: "grotesk",
    textSize: 16, contentWidth: 1180, sectionSpacing: 48, cornerRadius: 32, buttonShape: "pill", showGrid: true, backgroundGlow: true,
  });
  const colors = ["background", "panel", "text", "muted", "accent", "highlight", "border"];
  const bounds = { textSize: [14, 20], contentWidth: [960, 1600], sectionSpacing: [24, 104], cornerRadius: [0, 48] };
  const bodyFonts = { plex: '"IBM Plex Sans", "Segoe UI", sans-serif', system: '"Segoe UI", system-ui, sans-serif' };
  const headingFonts = { grotesk: '"Space Grotesk", "IBM Plex Sans", sans-serif', system: '"Segoe UI", system-ui, sans-serif', serif: 'Georgia, "Times New Roman", serif' };
  const radii = { pill: 999, soft: 12, square: 3 };
  function validate(value) {
    if (!value || typeof value !== "object" || Array.isArray(value)
      || Object.keys(value).sort().join("|") !== Object.keys(defaults).sort().join("|")) throw new Error("Appearance settings must contain exactly the supported theme fields.");
    if (value.schemaVersion !== 1) throw new Error("This appearance file has an unsupported version.");
    const result = Object.fromEntries(Object.keys(defaults).map((key) => [key, value[key]]));
    for (const key of colors) {
      if (typeof value[key] !== "string" || !/^#[0-9a-f]{6}$/i.test(value[key])) throw new Error(`${key} must be a six-digit hex color.`);
      result[key] = value[key].toLowerCase();
    }
    for (const [key, [low, high]] of Object.entries(bounds)) {
      if (!Number.isInteger(value[key]) || value[key] < low || value[key] > high) throw new Error(`${key} must be a whole number from ${low} to ${high}.`);
    }
    for (const [key, options] of [["bodyFont", bodyFonts], ["headingFont", headingFonts], ["buttonShape", radii]]) {
      if (typeof value[key] !== "string" || !Object.hasOwn(options, value[key])) throw new Error(`Choose a supported ${key}.`);
    }
    for (const key of ["showGrid", "backgroundGlow"]) if (typeof value[key] !== "boolean") throw new Error(`${key} must be true or false.`);
    return result;
  }
  function rgb(color) { return [1, 3, 5].map((index) => parseInt(color.slice(index, index + 2), 16)); }
  function shift(color, offsets) { return "#" + rgb(color).map((channel, index) => Math.max(0, Math.min(255, channel + offsets[index])).toString(16).padStart(2, "0")).join(""); }
  function channels(color) { return rgb(color).join(", "); }
  function luminance(color) {
    return rgb(color).map((channel) => channel / 255).map((channel) => channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4)
      .reduce((total, channel, index) => total + channel * [0.2126, 0.7152, 0.0722][index], 0);
  }
  function contrast(first, second) { const [light, dark] = [luminance(first), luminance(second)].sort((a, b) => b - a); return (light + 0.05) / (dark + 0.05); }
  function readable(color, background) {
    if (contrast(color, background) >= 4.5) return color;
    const target = contrast("#000000", background) >= contrast("#ffffff", background) ? "#000000" : "#ffffff";
    for (let step = 1; step <= 20; step++) {
      const blended = "#" + rgb(color).map((channel, index) => Math.floor((channel * (20 - step) + rgb(target)[index] * step + 10) / 20).toString(16).padStart(2, "0")).join("");
      if (contrast(blended, background) >= 4.5) return blended;
    }
    return target;
  }
  function css(value) {
    const theme = validate(value), panel = theme.panel;
    const strong = shift(theme.accent, [19, 31, 28]), pale = shift(theme.accent, [188, 90, 106]);
    const palette = [theme.highlight, strong, pale];
    const score = (color) => Math.min(...palette.map((background) => contrast(color, background)));
    const ink = score("#072019") >= score("#ffffff") ? "#072019" : "#ffffff";
    const values = {
      bg: theme.background, "bg-alt": panel, surface: `rgba(${channels(panel)}, 0.7)`,
      "surface-strong": `rgba(${channels(shift(panel, [2, 4, 5]))}, 0.92)`,
      line: `rgba(${channels(theme.border)}, 0.12)`, "line-strong": `rgba(${channels(theme.border)}, 0.2)`,
      text: theme.text, muted: theme.muted, accent: theme.accent, "accent-strong": strong, sand: theme.highlight,
      "accent-text": readable(strong, theme.background), "highlight-text": readable(theme.highlight, theme.background),
      "accent-rgb": channels(theme.accent), "accent-strong-rgb": channels(strong), "sand-rgb": channels(theme.highlight),
      "sand-glow-rgb": channels(shift(theme.highlight, [-13, -25, -42])), "bg-rgb": channels(theme.background),
      "stage-rgb": channels(shift(panel, [-1, 1, 3])), "card-start-rgb": channels(shift(panel, [-2, -4, -5])), "card-end-rgb": channels(shift(panel, [-2, -5, -7])),
      "bg-mid": shift(theme.background, [1, 4, 5]), "bg-end": shift(theme.background, [5, 6, 7]), "frame-bg": shift(theme.background, [-3, -2, -3]),
      "accent-pale": pale, "button-ink": ink, "badge-ink": ink === "#072019" ? "#05211c" : ink,
      "sparkle-rgb": luminance(theme.background) > 0.5 ? "0, 0, 0" : "255, 255, 255",
      "font-body": bodyFonts[theme.bodyFont], "font-heading": headingFonts[theme.headingFont],
      "base-text-size": `${theme.textSize}px`, "content-width": `${theme.contentWidth}px`, "section-space": `${theme.sectionSpacing}px`,
      "radius-xl": `${theme.cornerRadius}px`, "radius-lg": `${Math.max(0, theme.cornerRadius - 10)}px`, "button-radius": `${radii[theme.buttonShape]}px`,
      "grid-opacity": theme.showGrid ? "0.55" : "0", "background-glow": theme.backgroundGlow ? "1" : "0",
    };
    return "/* Generated by the Format Foundry appearance editor. */\n:root {\n" + Object.entries(values).map(([key, item]) => `  --${key}: ${item};\n`).join("") + "}\n";
  }
  function apply(theme, document) {
    let style = document.getElementById("foundry-theme-preview");
    if (!style) { style = document.createElement("style"); style.id = "foundry-theme-preview"; document.head.append(style); }
    style.textContent = css(theme);
  }
  const presets = Object.freeze({
    original: { label: "Foundry teal", description: "The current website design.", theme: { ...defaults } },
    midnight: { label: "Midnight blue", description: "Cool blue accents and deep navy panels.", theme: { ...defaults, background: "#101522", panel: "#151e32", text: "#f1f4fc", muted: "#acb8d0", accent: "#7a9cfa", highlight: "#d8e4ff", border: "#abbde8", buttonShape: "soft" } },
    daylight: { label: "Daylight", description: "A bright canvas with green accents.", theme: { ...defaults, background: "#f0f5f1", panel: "#ffffff", text: "#142d29", muted: "#50655e", accent: "#27a88a", highlight: "#e5d5a8", border: "#49665b", cornerRadius: 20, showGrid: false, backgroundGlow: false } },
    amber: { label: "Warm amber", description: "Warm neutrals and serif headings.", theme: { ...defaults, background: "#17130f", panel: "#241d16", text: "#fbf1df", muted: "#c4b49b", accent: "#d78b36", highlight: "#ffe2ad", border: "#d4b995", headingFont: "serif", cornerRadius: 24, buttonShape: "soft" } },
  });
  return { defaults, colors, bounds, bodyFonts, headingFonts, validate, css, apply, contrast, presets };
});
