(() => {
  const fallbackPackageVersion = "0.5.0-beta";
  const fallbackReleaseTag = "v1.8.18";
  const repoOwner = "Pugmaster04";
  const repoName = "Format-Foundry";
  const repoUrl = `https://github.com/${repoOwner}/${repoName}`;
  const githubLatestReleaseApi = `https://api.github.com/repos/${repoOwner}/${repoName}/releases/latest`;

  function detectPackageVersion(assets) {
    const patterns = [
      /^FormatFoundry_Setup_(.+)\.exe$/i,
      /^FormatFoundry_Updater_(.+)\.exe$/i,
      /^format-foundry_(.+)_(?:amd64|arm64)\.deb$/i,
      /^FormatFoundry_linux_(.+)_(?:x86_64|aarch64)\.AppImage$/i,
    ];
    for (const asset of Array.isArray(assets) ? assets : []) {
      const name = String(asset?.name || "");
      for (const pattern of patterns) {
        const match = name.match(pattern);
        if (match?.[1]) return match[1];
      }
    }
    return fallbackPackageVersion;
  }

  function formatDisplayVersion(packageVersion, releaseName) {
    const explicit = String(releaseName || "").match(
      /\b(Release Candidate|RC|Beta|Alpha|Stable)\s+v?([0-9]+(?:\.[0-9]+)*)\b/i,
    );
    if (explicit) {
      const phase = /^(?:release candidate|rc)$/i.test(explicit[1])
        ? "Release Candidate"
        : explicit[1][0].toUpperCase() + explicit[1].slice(1).toLowerCase();
      return `${phase} ${explicit[2]}`;
    }
    if (/beta/i.test(packageVersion)) {
      return `Beta ${packageVersion.replace(/^v/i, "").replace(/-?beta/i, "").replace(/\.0$/, "")}`;
    }
    return `Alpha ${packageVersion.replace(/^v/i, "")}`;
  }

  function buildSiteConfig(tagName, assets = [], releaseName = "") {
    const rawTag = String(tagName || fallbackReleaseTag).trim() || fallbackReleaseTag;
    const releaseTag = rawTag.startsWith("v") ? rawTag : `v${rawTag}`;
    const packageVersion = detectPackageVersion(assets);
    const assetUrlByName = new Map(
      (Array.isArray(assets) ? assets : [])
        .map((asset) => [String(asset?.name || ""), String(asset?.browser_download_url || "")])
        .filter(([name, url]) => name && url),
    );
    const taggedReleasePage = `${repoUrl}/releases/tag/${releaseTag}`;
    const releasePage = assetUrlByName.size ? taggedReleasePage : `${repoUrl}/releases/latest`;
    const resolveAssetUrl = (name) => assetUrlByName.get(name) || releasePage;

    return {
      version: packageVersion,
      displayVersion: formatDisplayVersion(packageVersion, releaseName),
      repo: repoUrl,
      releasePage,
      links: {
        windowsInstaller: resolveAssetUrl(`FormatFoundry_Setup_${packageVersion}.exe`),
        windowsPortable: resolveAssetUrl(`FormatFoundry_${packageVersion}.exe`),
        windowsUpdater: resolveAssetUrl(`FormatFoundry_Updater_${packageVersion}.exe`),
        linuxDeb: resolveAssetUrl(`format-foundry_${packageVersion}_amd64.deb`),
        linuxAppImage: resolveAssetUrl(`FormatFoundry_linux_${packageVersion}_x86_64.AppImage`),
        linuxTarball: resolveAssetUrl(`FormatFoundry_linux_${packageVersion}_x86_64.tar.gz`),
      },
    };
  }

  function buildListContent(site) {
    return {
      windowsAlt: [
        {
          href: site.links.windowsPortable,
          title: "Portable Windows app",
          description: "Single-file executable when you do not want the installer path.",
          action: "Download EXE",
        },
        {
          href: site.links.windowsUpdater,
          title: "Standalone updater",
          description: "Separate updater binary for manual update workflows.",
          action: "Download updater",
        },
      ],
      linuxAlt: [
        {
          href: site.links.linuxAppImage,
          title: "Linux AppImage",
          description: "Portable self-contained build when you do not want a system package install.",
          action: "Download AppImage",
        },
        {
          href: site.links.linuxTarball,
          title: "Linux tarball",
          description: "Raw packaged bundle for manual extraction or archive workflows.",
          action: "Download tarball",
        },
      ],
    };
  }

  async function fetchLatestSiteConfig() {
    try {
      const response = await fetch(githubLatestReleaseApi, {
        headers: { Accept: "application/vnd.github+json" },
      });
      if (!response.ok) {
        throw new Error(`GitHub release request failed with status ${response.status}.`);
      }
      const payload = await response.json();
      const tagName = String(payload?.tag_name || "").trim();
      if (!tagName) {
        throw new Error("GitHub release payload did not include a usable tag.");
      }
      return buildSiteConfig(tagName, payload?.assets || [], payload?.name || "");
    } catch (error) {
      console.warn("Format Foundry site falling back to embedded release metadata.", error);
      return buildSiteConfig(fallbackReleaseTag);
    }
  }

  function applyVersion(site) {
    document.querySelectorAll("[data-version]").forEach((node) => {
      node.textContent = site.displayVersion;
    });
  }

  function applyLinks(site) {
    document.querySelectorAll("[data-link]").forEach((node) => {
      const key = node.getAttribute("data-link");
      let href = "";
      if (key === "repo" || key === "releasePage") {
        href = site[key];
      } else if (key && Object.prototype.hasOwnProperty.call(site.links, key)) {
        href = site.links[key];
      } else {
        console.warn(`Unknown data-link key: ${key || "(empty)"}`);
      }
      if (href) {
        node.href = href;
      }
    });
  }

  function renderList(node, items) {
    node.replaceChildren();
    items.forEach((item) => {
      const link = document.createElement("a");
      link.className = "asset-link";
      link.href = item.href;

      const textWrap = document.createElement("span");
      const title = document.createElement("strong");
      title.textContent = item.title;
      const description = document.createElement("span");
      description.textContent = item.description;
      textWrap.append(title, description);

      const action = document.createElement("em");
      action.textContent = item.action;

      link.append(textWrap, action);
      node.append(link);
    });
  }

  function applyLists(site) {
    const lists = buildListContent(site);
    document.querySelectorAll("[data-render-list]").forEach((node) => {
      const listKey = node.getAttribute("data-render-list");
      const items = lists[listKey] || [];
      if (!lists[listKey]) {
        console.warn(`Unknown data-render-list key: ${listKey || "(empty)"}`);
      }
      renderList(node, items);
    });
  }

  function setupRevealAnimations() {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      document.querySelectorAll(".reveal").forEach((node) => node.classList.add("is-visible"));
      return;
    }

    if (!("IntersectionObserver" in window)) {
      document.querySelectorAll(".reveal").forEach((node) => node.classList.add("is-visible"));
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.18, rootMargin: "0px 0px -8% 0px" },
    );

    document.querySelectorAll(".reveal").forEach((node) => observer.observe(node));
  }

  async function init() {
    const site = await fetchLatestSiteConfig();
    applyVersion(site);
    applyLinks(site);
    applyLists(site);
    setupRevealAnimations();
  }

  init();
})();
