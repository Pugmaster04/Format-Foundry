(() => {
  "use strict";
  const api = window.FormatFoundryTheme;
  const $ = (id) => document.getElementById(id);
  const initialHash = new URLSearchParams(location.hash.slice(1));
  const token = initialHash.get("editor") || "";
  if (token) history.replaceState(null, "", location.pathname + location.search);
  const local = location.hostname === "127.0.0.1" && /^[A-Za-z0-9_-]{40,64}$/.test(token);
  const colorLabels = { background: "Page background", panel: "Panels", text: "Main text", muted: "Secondary text", accent: "Accent", highlight: "Highlights", border: "Borders" };
  const state = { theme: { ...api.defaults }, saved: "", committed: "", history: [], connected: false, canPublish: false, busy: false, saving: false, closed: false, phone: false };
  document.querySelector(".controls-pane").inert = true;
  let publicationTimer;
  const canonical = (theme) => JSON.stringify(api.validate(theme));
  function status(message, error = false, url = "") {
    $("status-message").textContent = message;
    $("status-message").parentElement.classList.toggle("error", error);
    $("publication-link").hidden = !url;
    if (url) $("publication-link").href = url;
  }
  function buttons() {
    $("save-local").disabled = !state.connected || state.busy || state.saving || state.closed;
    $("publish").disabled = !state.connected || !state.canPublish || state.busy || state.saving || state.closed;
    $("close-editor").disabled = state.saving || state.busy || state.closed;
    $("undo").disabled = !state.history.length || state.busy;
    $("save-indicator").textContent = canonical(state.theme) === state.saved ? "Saved appearance" : "Unsaved changes";
    $("publish").textContent = state.busy ? "Publishing…" : "Publish to website";
  }
  function preview() {
    $("preview").contentWindow?.postMessage({ channel: "format-foundry-theme", theme: state.theme }, location.origin);
    const main = Math.min(api.contrast(state.theme.text, state.theme.background), api.contrast(state.theme.text, state.theme.panel));
    const muted = Math.min(api.contrast(state.theme.muted, state.theme.background), api.contrast(state.theme.muted, state.theme.panel));
    $("contrast-info").textContent = `Text contrast ${main.toFixed(1)}:1 · secondary ${muted.toFixed(1)}:1${Math.min(main, muted) < 4.5 ? " — consider stronger contrast" : " — good contrast"}`;
    $("contrast-info").classList.toggle("warning", Math.min(main, muted) < 4.5);
    for (const element of document.querySelectorAll("[data-preset]")) element.setAttribute("aria-pressed", String(canonical(api.presets[element.dataset.preset].theme) === canonical(state.theme)));
    for (const key of Object.keys(api.bounds)) $(key + "-value").textContent = `${state.theme[key]} px`;
    buttons();
  }
  function syncControls() {
    for (const element of document.querySelectorAll("[data-setting]")) {
      const value = state.theme[element.dataset.setting];
      if (element.type === "checkbox") element.checked = value;
      else element.value = value;
      element.setCustomValidity("");
      element.removeAttribute("aria-invalid");
    }
    preview();
  }
  function commit() {
    const current = canonical(state.theme);
    if (current !== state.committed) {
      state.history.push(state.committed);
      if (state.history.length > 50) state.history.shift();
      state.committed = current;
    }
    preview();
  }
  function choose(theme) { state.theme = api.validate(theme); commit(); syncControls(); }
  for (const [key, preset] of Object.entries(api.presets)) {
    const button = document.createElement("button");
    button.className = "preset"; button.dataset.preset = key; button.type = "button";
    button.title = preset.description; button.setAttribute("aria-pressed", "false");
    const swatches = document.createElement("span"); swatches.className = "swatches"; swatches.setAttribute("aria-hidden", "true");
    for (const value of [preset.theme.background, preset.theme.panel, preset.theme.accent, preset.theme.highlight]) {
      const swatch = document.createElement("span"); swatch.style.backgroundColor = value; swatches.append(swatch);
    }
    const title = document.createElement("strong"); title.textContent = preset.label;
    button.append(swatches, title); button.addEventListener("click", () => { choose(preset.theme); status(`${preset.label} applied to the preview.`); });
    $("presets").append(button);
  }
  for (const [key, label] of Object.entries(colorLabels)) {
    const row = document.createElement("div"); row.className = "color-setting";
    const name = document.createElement("label"); name.htmlFor = `${key}-picker`; name.textContent = label;
    const picker = document.createElement("input"); picker.type = "color"; picker.id = `${key}-picker`; picker.dataset.setting = key; picker.setAttribute("aria-label", label);
    const hex = document.createElement("input"); hex.type = "text"; hex.id = `${key}-hex`; hex.className = "hex-field";
    hex.dataset.setting = key; hex.maxLength = 7; hex.spellcheck = false; hex.setAttribute("aria-label", `${label} hex color`); hex.pattern = "#[0-9a-fA-F]{6}"; hex.required = true;
    picker.addEventListener("input", () => { hex.value = picker.value; hex.setCustomValidity(""); hex.removeAttribute("aria-invalid"); });
    hex.addEventListener("input", () => {
      const valid = /^#[0-9a-f]{6}$/i.test(hex.value);
      hex.setCustomValidity(valid ? "" : "Enter a six-digit hex color, for example #1fa58e.");
      hex.setAttribute("aria-invalid", String(!valid));
      if (valid) picker.value = hex.value;
    });
    row.append(name, picker, hex); $("color-controls").append(row);
  }
  for (const element of document.querySelectorAll("[data-setting]")) {
    element.addEventListener("input", () => {
      if (!element.checkValidity()) return;
      const value = element.type === "checkbox" ? element.checked : element.type === "range" ? Number(element.value) : element.value;
      try { state.theme = api.validate({ ...state.theme, [element.dataset.setting]: value }); preview(); } catch (error) { status(error.message, true); }
    });
    element.addEventListener("change", () => { if (element.checkValidity()) commit(); });
  }
  $("controls").addEventListener("submit", (event) => event.preventDefault());
  $("undo").addEventListener("click", () => {
    const previous = state.history.pop(); if (!previous) return;
    state.theme = JSON.parse(previous); state.committed = previous; syncControls(); status("Previous appearance restored.");
  });
  $("reset").addEventListener("click", () => { choose(api.defaults); status("Original website design restored in the preview."); });
  $("export").addEventListener("click", () => {
    if (!$("controls").reportValidity()) return;
    const url = URL.createObjectURL(new Blob([JSON.stringify(api.validate(state.theme), null, 2) + "\n"], { type: "application/json" }));
    const link = document.createElement("a"); link.href = url; link.download = "format-foundry-theme.json"; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000); status("Appearance settings exported.");
  });
  $("import").addEventListener("click", () => $("import-file").click());
  $("import-file").addEventListener("change", async () => {
    const file = $("import-file").files[0]; if (!file) return;
    try { if (file.size > 16384) throw new Error("That appearance file is too large."); choose(JSON.parse(await file.text())); status("Imported appearance applied to the preview."); }
    catch (error) { status(`Could not import: ${error.message}`, true); }
    $("import-file").value = "";
  });
  async function request(path, theme) {
    const options = { headers: { "X-FormatFoundry-Editor-Token": token }, cache: "no-store" };
    if (theme !== undefined) { options.method = "POST"; options.headers["Content-Type"] = "application/json"; options.body = JSON.stringify(theme); }
    const response = await fetch(path, options), result = await response.json();
    if (result.saved && theme?.theme) { state.saved = canonical(theme.theme); buttons(); }
    if (!response.ok) throw new Error(result.error || "The editor could not complete that action.");
    return result;
  }
  $("save-local").addEventListener("click", async () => {
    if (!$("controls").reportValidity()) return;
    state.saving = true; buttons();
    try { const result = await request("/api/save", { theme: state.theme }); status(result.backupCreated ? "Saved to your project. A recovery copy of the previous appearance was created." : "Saved to your project."); }
    catch (error) { status(error.message, true); }
    finally { state.saving = false; buttons(); }
  });
  $("publish").addEventListener("click", () => { if ($("controls").reportValidity()) $("publish-dialog").showModal(); });
  $("cancel-publish").addEventListener("click", () => $("publish-dialog").close());
  async function pollPublication(commit, started) {
    try {
      const result = await request(`/api/publication?commit=${encodeURIComponent(commit)}`);
      if (result.state !== "pending") { state.busy = false; buttons(); status(result.message, result.state === "failed", result.url); return; }
      if (Date.now() - started > 240000) throw new Error("Changes were sent to GitHub. Publication is still running; check the live website shortly.");
      status(result.message); publicationTimer = setTimeout(() => pollPublication(commit, started), 5000);
    } catch (error) { state.busy = false; buttons(); status(error.message, true); }
  }
  $("confirm-publish").addEventListener("click", async () => {
    $("publish-dialog").close(); state.busy = true; buttons(); status("Saving and sending your appearance to the website…");
    try {
      const result = await request("/api/publish", { theme: state.theme });
      if (result.unchanged) { state.busy = false; status("These appearance settings are already saved on GitHub.", false, result.url); buttons(); }
      else await pollPublication(result.commit, Date.now());
    } catch (error) { state.busy = false; buttons(); status(error.message, true); }
  });
  $("close-editor").addEventListener("click", async () => {
    if (canonical(state.theme) !== state.saved && !confirm("Close without saving your latest appearance changes?")) return;
    try { await request("/api/close", {}); clearTimeout(publicationTimer); state.closed = true; buttons(); status("Editor closed. Open Customize Website.cmd to start it again."); }
    catch (error) { status(error.message, true); }
  });
  function resizePreview() {
    const width = state.phone ? 390 : 1280;
    const available = Math.max(240, $("preview-host").clientWidth - (innerWidth < 780 ? 28 : 48));
    const scale = Math.min(1, available / width), height = state.phone ? 844 : Math.max(800, Math.floor(($("preview-host").clientHeight - 48) / scale));
    $("preview").style.width = `${width}px`; $("preview").style.height = `${height}px`; $("preview").style.transform = `scale(${scale})`;
    $("preview-viewport").style.width = `${width * scale}px`; $("preview-viewport").style.height = `${height * scale}px`;
    $("preview-dimensions").textContent = `${width} px`;
    $("desktop").setAttribute("aria-pressed", String(!state.phone)); $("mobile").setAttribute("aria-pressed", String(state.phone));
  }
  $("desktop").addEventListener("click", () => { state.phone = false; resizePreview(); });
  $("mobile").addEventListener("click", () => { state.phone = true; resizePreview(); });
  $("preview-page").addEventListener("change", () => { $("preview").src = `${$("preview-page").value}?theme-preview=1`; });
  $("preview").addEventListener("load", () => {
    const name = $("preview").contentWindow.location.pathname.split("/").pop();
    if ([...$("preview-page").options].some((option) => option.value === name)) $("preview-page").value = name;
    preview(); resizePreview();
  });
  new ResizeObserver(resizePreview).observe($("preview-host"));
  window.addEventListener("beforeunload", (event) => { if (!state.closed && canonical(state.theme) !== state.saved) { event.preventDefault(); event.returnValue = ""; } });
  async function start() {
    try {
      const response = await fetch("theme.json", { cache: "no-store" });
      if (response.ok) state.theme = api.validate(await response.json());
      if (local) {
        const result = await request("/api/state"); state.theme = api.validate(result.theme); state.connected = true; state.canPublish = result.canPublish;
        $("mode-badge").textContent = "Project connected"; $("mode-badge").classList.add("connected"); $("close-editor").hidden = false;
        $("connection-help").textContent = "Save to project keeps your appearance files and a recovery copy locally. Publish updates only the website appearance.";
        status(result.warning || "Project connected. Preview your changes, then save or publish.");
      } else status("Preview mode. Open Customize Website.cmd to save directly and publish.");
    } catch (error) { status(`Could not load saved settings: ${error.message}`, true); }
    state.saved = canonical(state.theme); state.committed = state.saved;
    syncControls(); document.querySelector(".controls-pane").inert = false; $("preview").src = "index.html?theme-preview=1";
  }
  start();
})();
