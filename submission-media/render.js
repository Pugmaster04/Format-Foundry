const assets = {
  cover: `
    <section class="cover-layout">
      <div class="cover-copy">
        <p class="eyebrow">OpenAI Build Week · Work & Productivity</p>
        <h1>Format<br>Foundry</h1>
        <p class="lede">One desktop workspace for the file jobs that usually get split across six utilities.</p>
        <div class="badge-row">
          <span class="badge accent">Windows + Linux</span>
          <span class="badge">Batch-ready</span>
          <span class="badge">Backend-aware</span>
        </div>
      </div>
      <div class="device-wrap">
        <div class="device-glow"></div>
        <div class="device">
          <div class="device-bar"><i class="device-dot"></i><i class="device-dot"></i><i class="device-dot"></i></div>
          <img src="screenshots/format-foundry-main-windows.png" alt="Format Foundry conversion workspace">
        </div>
      </div>
    </section>
    ${footer("Devpost gallery cover · Beta 0.5")}
  `,
  workflow: `
    <section class="gallery-layout">
      <div class="gallery-copy">
        ${brand()}
        <p class="eyebrow">01 · One workspace</p>
        <h2>Convert. Compress. Extract. Ship.</h2>
        <p class="lede">A workflow-first surface for documents, images, audio, video, archives, metadata, and repeatable queues.</p>
        <span class="proof">Fewer handoffs · clearer status · safer output</span>
      </div>
      ${device("screenshots/format-foundry-main-windows.png", "Format Foundry conversion workspace")}
    </section>
    ${footer("Authentic Windows Beta 0.5 capture")}
  `,
  backend: `
    <section class="gallery-layout reverse">
      <div class="gallery-copy">
        ${brand()}
        <p class="eyebrow">02 · Consumer-ready setup</p>
        <h2>Optional tools, clearly explained.</h2>
        <p class="lede">The updater detects every backend, explains which features it enables, and routes installation through trusted package managers and official links.</p>
        <div class="metric-row">
          <div class="metric"><strong>7 / 7</strong><span>Backends detected</span></div>
          <div class="metric"><strong>2</strong><span>Desktop platforms</span></div>
        </div>
      </div>
      ${device("screenshots/format-foundry-backend-center-windows.png", "Format Foundry Backend Center")}
    </section>
    ${footer("Backend Center · package-manager aware")}
  `,
  aria2: `
    <section class="gallery-layout">
      <div class="gallery-copy">
        ${brand()}
        <p class="eyebrow">03 · Download workspace</p>
        <h2>Downloads without hiding the risk.</h2>
        <p class="lede">HTTP, FTP, SFTP, BitTorrent, magnet, and Metalink intake with queue controls, explicit warnings, and visible pause, stop, and progress states.</p>
        <span class="proof">Aria2-powered · no hidden speed-limit flags</span>
      </div>
      ${device("screenshots/format-foundry-aria2-windows.png", "Format Foundry Aria2 workspace")}
    </section>
    ${footer("Aria2 workspace · explicit safety guidance")}
  `,
  idea: `
    <section class="gallery-layout reverse">
      <div class="gallery-copy">
        ${brand()}
        <p class="eyebrow">05 · Optional add-on</p>
        <h2>Capture the next useful idea without leaving the workspace.</h2>
        <p class="lede">Idea Bank is disabled by default, stores data locally, and adds searchable status, tags, notes, archive controls, and CSV export only when enabled.</p>
        <span class="proof">Opt-in · local-only · no network access</span>
      </div>
      ${device("screenshots/format-foundry-idea-bank-windows.png", "Format Foundry optional Idea Bank workspace")}
    </section>
    ${footer("Idea Bank · optional local workspace")}
  `,
  health: `
    <section class="gallery-layout">
      <div class="gallery-copy">
        ${brand()}
        <p class="eyebrow">06 · Optional add-on</p>
        <h2>Understand the device without changing it.</h2>
        <p class="lede">PC Health Snapshot is disabled by default and presents a private, read-only overview of the operating system, memory, disk space, and security-provider status.</p>
        <span class="proof">Opt-in · no network access · not antivirus</span>
      </div>
      ${device("screenshots/format-foundry-pc-health-windows.png", "Format Foundry optional PC Health Snapshot workspace")}
    </section>
    ${footer("PC Health Snapshot · private and read-only")}
  `,
  release: `
    <section class="release-layout">
      ${brand()}
      <p class="eyebrow">04 · Cross-platform delivery</p>
      <h2>Built like a consumer product, not a source-folder demo.</h2>
      <p class="lede">Versioned installers, launchers, uninstall paths, checksums, and coordinated release automation for normal Windows and Linux machines.</p>
      <div class="platform-row">
        <article class="platform-card"><span class="micro-label">Windows</span><strong>EXE Installer</strong><p>Start-menu integration, updater routing, upgrade detection, and a clear uninstall path.</p></article>
        <article class="platform-card"><span class="micro-label">Ubuntu / Debian</span><strong>.deb Package</strong><p>Desktop launcher, AppStream metadata, icon wiring, and no dependency on the source tree.</p></article>
        <article class="platform-card"><span class="micro-label">Portable Linux</span><strong>AppImage</strong><p>A self-contained fallback distributed beside the package-first install path.</p></article>
      </div>
      <div class="flow-line"><span>Clean clone</span><i></i><span>Cross-platform CI</span><i></i><span>Versioned release assets</span><i></i><span>Verified downloads</span></div>
    </section>
    ${footer("Release contract · Windows + Linux")}
  `,
  demo: `
    <section class="demo-layout">
      <div class="gallery-copy">
        ${brand()}
        <p class="eyebrow">OpenAI Build Week</p>
        <h1>From scattered tools to one dependable workflow.</h1>
        <div class="demo-label">3-minute product demo</div>
      </div>
      ${device("screenshots/format-foundry-main-windows.png", "Format Foundry desktop app")}
    </section>
    ${footer("Built with Codex · Format Foundry Beta 0.5")}
  `,
};

function brand() {
  return `
    <div class="brand-row">
      <img class="brand-icon" src="../assets/universal_file_utility_suite_preview.png" alt="">
      <span class="brand-wordmark">Format Foundry</span>
    </div>
  `;
}

function device(source, alt) {
  return `
    <div class="device-wrap">
      <div class="device-glow"></div>
      <div class="device">
        <div class="device-bar"><i class="device-dot"></i><i class="device-dot"></i><i class="device-dot"></i></div>
        <img src="${source}" alt="${alt}">
      </div>
    </div>
  `;
}

function footer(label) {
  return `
    <footer class="footer-row">
      <span>${label}</span>
      <span>© 2026 Pugmaster04 · FF/BW26</span>
    </footer>
  `;
}

const requested = new URLSearchParams(window.location.search).get("asset") || "cover";
document.body.dataset.asset = requested;
document.querySelector("#asset").innerHTML = assets[requested] || assets.cover;
