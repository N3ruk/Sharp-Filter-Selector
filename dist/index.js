const manifest = { name: "Sharp Filter Selector", author: "N3ruk", flags: [], api_version: 1 };

// Runtime equivalent of @decky/api 1.1.3 as bundled by @decky/rollup.
// Plugin source imports the public API; the package itself performs this
// versioned loader connection internally.
const internalAPIConnection = window.__DECKY_SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED_deckyLoaderAPIInit;
if (!internalAPIConnection) {
  throw new Error("[@decky/api]: Failed to connect to the loader as the loader API was not initialized.");
}

const API_VERSION = 2;
let api;
try {
  api = internalAPIConnection.connect(API_VERSION, manifest.name);
} catch (_) {
  api = internalAPIConnection.connect(1, manifest.name);
  console.warn(`[@decky/api] Requested API version ${API_VERSION} but the running loader only supports version 1. Some features may not work.`);
}
if (api._version != null && api._version !== API_VERSION) {
  console.warn(`[@decky/api] Requested API version ${API_VERSION} but the running loader only supports version ${api._version}. Some features may not work.`);
}

const callable = api.callable;
const definePlugin = (fn) => (...args) => fn(...args);

const setNisEnabled = callable("set_nis_enabled");
const setNisSharpness = callable("set_nis_sharpness");
const getStatus = callable("get_status");

// @decky/rollup maps these public frontend imports to Decky's injected globals.
const React = window.SP_REACT;
const DFL = window.DFL;

const ENABLED_KEY = "sharp-filter-nis-enabled";
const SHARPNESS_KEY = "sharp-filter-nis-sharpness";

function storedEnabled() {
  return localStorage.getItem(ENABLED_KEY) === "true";
}

function storedSharpness() {
  const value = Number(localStorage.getItem(SHARPNESS_KEY));
  return Number.isInteger(value) && value >= 0 && value <= 5 ? value : 5;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function targetSummary(result) {
  const diagnostics = Array.isArray(result?.diagnostics) ? result.diagnostics : [];
  if (!diagnostics.length) return "";
  return diagnostics.map((d) => {
    const sid = Number.isInteger(d.serverId) ? `#${d.serverId}` : "";
    const legacy = d.legacyFilter ?? "?";
    const modern = d.newFilter ?? "?";
    const feedback = d.fsrFeedback === 1 ? " FSR" : "";
    return `${d.display ?? "?"}${sid}[${legacy}/${modern}]${feedback}`;
  }).join(" · ");
}

function Content() {
  const [nisEnabled, setNisEnabledState] = React.useState(storedEnabled);
  const [sharpness, setSharpnessState] = React.useState(storedSharpness);
  const [status, setStatus] = React.useState("Checking Gamescope…");

  function describe(enabled, level, displays) {
    const targets = displays?.length ? ` (${displays.join(", ")})` : "";
    return enabled
      ? `NIS active · sharpness ${level}/5${targets}`
      : `NIS disabled · FSR active${targets}`;
  }

  async function verifyNis(level, fallbackDisplays) {
    for (let attempt = 0; attempt < 5; attempt++) {
      await sleep(attempt === 0 ? 350 : 500);
      const result = await getStatus();
      if (result?.success && result.enabled) {
        const targets = targetSummary(result);
        setStatus(targets ? `NIS verified active · ${targets}` : `NIS verified active · sharpness ${level}/5`);
        return true;
      }
    }

    try {
      const result = await getStatus();
      if (result?.success) {
        const targets = targetSummary(result);
        if (result.requested && result.enforcing) {
          setStatus(targets ? `NIS failed · targets ${targets}` : "NIS failed · SteamOS targets found but NIS is not active");
        } else {
          setStatus(describe(result.enabled, Number.isInteger(result.level) ? result.level : level, result.displays ?? fallbackDisplays));
        }
      } else {
        setStatus(result?.error || "Could not verify the active Gamescope filter");
      }
    } catch (_) {
      setStatus("NIS requested · verification unavailable");
    }
    return false;
  }

  async function applyEnabled(enabled) {
    setStatus(enabled ? "Applying NIS to all Xwayland targets…" : "Restoring FSR…");
    try {
      const engineResult = await setNisEnabled(enabled);
      if (!engineResult.success) {
        setStatus(engineResult.error || "Gamescope is not available");
        return;
      }

      let displays = engineResult.displays;
      if (enabled) {
        const sharpnessResult = await setNisSharpness(sharpness);
        if (!sharpnessResult.success) {
          setStatus(sharpnessResult.error || "Could not apply NIS sharpness");
          return;
        }
        displays = sharpnessResult.displays;
      }

      localStorage.setItem(ENABLED_KEY, String(enabled));
      setNisEnabledState(enabled);

      if (enabled) {
        setStatus("NIS requested · verifying all Xwaylands…");
        await verifyNis(sharpness, displays);
      } else {
        setStatus(describe(false, sharpness, displays));
      }
    } catch (error) {
      setStatus(`Error: ${String(error)}`);
    }
  }

  async function applySharpness(value) {
    const level = Math.max(0, Math.min(5, Math.round(value)));
    setSharpnessState(level);
    localStorage.setItem(SHARPNESS_KEY, String(level));
    if (!nisEnabled) return;

    setStatus("Applying sharpness…");
    try {
      const result = await setNisSharpness(level);
      if (!result.success) {
        setStatus(result.error || "Could not apply NIS sharpness");
        return;
      }
      setStatus(`NIS requested · sharpness ${level}/5 · verifying…`);
      await verifyNis(level, result.displays);
    } catch (error) {
      setStatus(`Error: ${String(error)}`);
    }
  }

  React.useEffect(() => {
    let mounted = true;
    const desiredEnabled = storedEnabled();
    const desiredSharpness = storedSharpness();

    async function initialize() {
      try {
        const engineResult = await setNisEnabled(desiredEnabled);
        if (!mounted) return;
        if (!engineResult.success) {
          setStatus(engineResult.error || "Available in a Gamescope session");
          return;
        }

        let displays = engineResult.displays;
        if (desiredEnabled) {
          const sharpnessResult = await setNisSharpness(desiredSharpness);
          if (!mounted) return;
          if (!sharpnessResult.success) {
            setStatus(sharpnessResult.error || "Could not apply NIS sharpness");
            return;
          }
          displays = sharpnessResult.displays;
        }

        setNisEnabledState(desiredEnabled);
        setSharpnessState(desiredSharpness);

        if (desiredEnabled) {
          setStatus("NIS requested · verifying all Xwaylands…");
          await verifyNis(desiredSharpness, displays);
        } else {
          setStatus(describe(false, desiredSharpness, displays));
        }
      } catch (error) {
        if (!mounted) return;
        setStatus(`Error: ${String(error)}`);
      }
    }

    initialize();
    return () => { mounted = false; };
  }, []);

  return React.createElement(DFL.PanelSection, { title: "Sharp Filter" },
    React.createElement(DFL.PanelSectionRow, null,
      React.createElement(DFL.ToggleField, {
        label: "Use NIS",
        description: nisEnabled
          ? "SteamOS: target every Gamescope Xwayland and force a real NIS transition."
          : "AMD FidelityFX Super Resolution is the selected Gamescope filter.",
        checked: nisEnabled,
        onChange: applyEnabled
      })
    ),
    React.createElement(DFL.PanelSectionRow, null,
      React.createElement(DFL.SliderField, {
        label: `NIS sharpness (${sharpness}/5)`,
        description: "0 applies minimum sharpening; 5 applies maximum sharpening.",
        value: sharpness,
        min: 0,
        max: 5,
        step: 1,
        notchCount: 6,
        disabled: !nisEnabled,
        onChange: applySharpness
      })
    ),
    React.createElement(DFL.PanelSectionRow, null,
      React.createElement("div", {
        style: { fontSize: "12px", opacity: 0.80, padding: "4px 0 8px" }
      }, status)
    )
  );
}

const index = definePlugin(() => ({
  name: "Sharp Filter Selector",
  titleView: React.createElement("div", { className: DFL.staticClasses.Title }, "Sharp Filter Selector"),
  content: React.createElement(Content),
  icon: React.createElement("span", null, "✦"),
  onDismount() {}
}));

export { index as default };
