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
const setFsrOverride = callable("set_fsr_override");
const setNisSharpness = callable("set_nis_sharpness");
const getStatus = callable("get_status");
const getCapabilities = callable("get_capabilities");

// @decky/rollup maps these public frontend imports to Decky's injected globals.
const React = window.SP_REACT;
const DFL = window.DFL;

const NIS_ENABLED_KEY = "sharp-filter-nis-enabled";
const NIS_SHARPNESS_KEY = "sharp-filter-nis-sharpness";
const FSR_OVERRIDE_KEY = "sharp-filter-fsr-override";

function storedNisEnabled() {
  return localStorage.getItem(NIS_ENABLED_KEY) === "true";
}

function storedFsrOverride() {
  return localStorage.getItem(FSR_OVERRIDE_KEY) === "true";
}

function storedSharpness() {
  const value = Number(localStorage.getItem(NIS_SHARPNESS_KEY));
  return Number.isInteger(value) && value >= 0 && value <= 5 ? value : 5;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function targetSummary(result) {
  const diagnostics = Array.isArray(result?.diagnostics) ? result.diagnostics : [];
  if (!diagnostics.length) return "";
  return diagnostics.map((d) => {
    const display = d.display ?? "?";
    const sid = Number.isInteger(d.serverId) ? `#${d.serverId}` : "";
    const legacy = d.legacyFilter ?? "?";
    const modern = d.newFilter ?? "?";
    const feedback = d.fsrFeedback === 1 ? " FSR" : "";
    return `${display}${sid}[${legacy}/${modern}]${feedback}`;
  }).join(" · ");
}

function nativeLabel(capabilities) {
  if (!capabilities?.supportsSGSR) return "FSR";
  return capabilities.hdrInput ? "FSR (HDR fallback)" : "SGSR";
}

function Content() {
  const [nisEnabled, setNisEnabledState] = React.useState(storedNisEnabled);
  const [fsrOverride, setFsrOverrideState] = React.useState(storedFsrOverride);
  const [sharpness, setSharpnessState] = React.useState(storedSharpness);
  const [capabilities, setCapabilities] = React.useState(null);
  const [status, setStatus] = React.useState("Checking Gamescope…");

  function describe(nis, fsr, level, displays, caps = capabilities) {
    const targets = displays?.length ? ` (${displays.join(", ")})` : "";
    if (nis) return `NIS active · sharpness ${level}/5${targets}`;
    if (fsr) return `FSR override active · sharpness ${level}/5${targets}`;
    return `Sharp native · ${nativeLabel(caps)}${targets}`;
  }

  async function refreshCapabilities() {
    try {
      const result = await getCapabilities();
      setCapabilities(result);
      return result;
    } catch (_) {
      return null;
    }
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
          setStatus(targets ? `NIS failed · targets ${targets}` : "NIS failed · Gamescope targets found but NIS is not active");
        } else {
          setStatus(describe(
            Boolean(result.enabled),
            Boolean(result.fsrOverride),
            Number.isInteger(result.level) ? Number(result.level) : level,
            result.displays ?? fallbackDisplays
          ));
        }
      } else {
        setStatus(result?.error || "Could not verify the active Gamescope filter");
      }
    } catch (_) {
      setStatus("NIS requested · verification unavailable");
    }
    return false;
  }

  async function applyNis(enabled) {
    setStatus(enabled ? "Applying NIS…" : "Restoring native Sharp filter…");
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
        localStorage.setItem(FSR_OVERRIDE_KEY, "false");
        setFsrOverrideState(false);
      }

      localStorage.setItem(NIS_ENABLED_KEY, String(enabled));
      setNisEnabledState(enabled);

      const caps = await refreshCapabilities();
      if (enabled) {
        setStatus("NIS requested · verifying…");
        await verifyNis(sharpness, displays);
      } else {
        setStatus(describe(false, false, sharpness, displays, caps ?? capabilities));
      }
    } catch (error) {
      setStatus(`Error: ${String(error)}`);
    }
  }

  async function applyFsr(enabled) {
    setStatus(enabled ? "Applying FSR override…" : "Restoring native SGSR…");
    try {
      const result = await setFsrOverride(enabled);
      if (!result.success) {
        setStatus(result.error || "Could not change the FSR override");
        return;
      }

      let displays = result.displays;
      if (enabled) {
        const sharpnessResult = await setNisSharpness(sharpness);
        if (!sharpnessResult.success) {
          setStatus(sharpnessResult.error || "Could not apply FSR sharpness");
          return;
        }
        displays = sharpnessResult.displays;
        localStorage.setItem(NIS_ENABLED_KEY, "false");
        setNisEnabledState(false);
      }

      localStorage.setItem(FSR_OVERRIDE_KEY, String(enabled));
      setFsrOverrideState(enabled);

      const caps = await refreshCapabilities();
      setStatus(describe(false, enabled, sharpness, displays, caps ?? capabilities));
    } catch (error) {
      setStatus(`Error: ${String(error)}`);
    }
  }

  async function applySharpness(value) {
    const level = Math.max(0, Math.min(5, Math.round(value)));
    setSharpnessState(level);
    localStorage.setItem(NIS_SHARPNESS_KEY, String(level));
    if (!nisEnabled && !fsrOverride) return;

    setStatus(nisEnabled ? "Applying NIS sharpness…" : "Applying FSR sharpness…");
    try {
      const result = await setNisSharpness(level);
      if (!result.success) {
        setStatus(result.error || "Could not apply filter sharpness");
        return;
      }
      if (nisEnabled) {
        setStatus(`NIS requested · sharpness ${level}/5 · verifying…`);
        await verifyNis(level, result.displays);
      } else {
        setStatus(describe(false, true, level, result.displays));
      }
    } catch (error) {
      setStatus(`Error: ${String(error)}`);
    }
  }

  React.useEffect(() => {
    let mounted = true;
    let timer;

    async function initialize() {
      try {
        const caps = await getCapabilities();
        if (!mounted) return;
        setCapabilities(caps);

        const desiredNis = storedNisEnabled();
        let desiredFsr = storedFsrOverride();
        const desiredSharpness = storedSharpness();

        if (caps.success && !caps.supportsSGSR && desiredFsr) {
          desiredFsr = false;
          localStorage.setItem(FSR_OVERRIDE_KEY, "false");
        }

        if (desiredNis) {
          const engineResult = await setNisEnabled(true);
          if (!mounted) return;
          if (!engineResult.success) {
            setStatus(engineResult.error || "Available in a Gamescope session");
            return;
          }

          const sharpnessResult = await setNisSharpness(desiredSharpness);
          if (!mounted) return;
          if (!sharpnessResult.success) {
            setStatus(sharpnessResult.error || "Could not apply NIS sharpness");
            return;
          }

          localStorage.setItem(FSR_OVERRIDE_KEY, "false");
          setFsrOverrideState(false);
          setNisEnabledState(true);
          setSharpnessState(desiredSharpness);
          setStatus("NIS requested · verifying…");
          await verifyNis(desiredSharpness, sharpnessResult.displays);
        } else if (desiredFsr && caps.supportsSGSR) {
          const result = await setFsrOverride(true);
          if (!mounted) return;
          if (!result.success) {
            setStatus(result.error || "Could not restore FSR override");
            return;
          }
          const sharpnessResult = await setNisSharpness(desiredSharpness);
          if (!mounted) return;
          if (!sharpnessResult.success) {
            setStatus(sharpnessResult.error || "Could not apply FSR sharpness");
            return;
          }
          setNisEnabledState(false);
          setFsrOverrideState(true);
          setSharpnessState(desiredSharpness);
          setStatus(describe(false, true, desiredSharpness, sharpnessResult.displays ?? result.displays, caps));
        } else if (caps.success) {
          // Passive initialization must never overwrite the filter or scaler
          // currently selected by Steam/QAM.
          setNisEnabledState(false);
          setFsrOverrideState(false);
          setSharpnessState(desiredSharpness);
          setStatus(describe(false, false, desiredSharpness, void 0, caps));
        } else {
          setNisEnabledState(false);
          setFsrOverrideState(false);
          setSharpnessState(desiredSharpness);
          setStatus("Gamescope capability detection unavailable");
        }

        timer = setInterval(async () => {
          try {
            const next = await getCapabilities();
            if (mounted) setCapabilities(next);
          } catch (_) {
            // Keep the last known capability state; never expose SGSR on uncertainty.
          }
        }, 1500);
      } catch (error) {
        if (!mounted) return;
        setStatus(`Error: ${String(error)}`);
      }
    }

    initialize();
    return () => {
      mounted = false;
      if (timer !== undefined) clearInterval(timer);
    };
  }, []);

  const showFsrOverride = Boolean(capabilities?.showFsrOverride);
  const supportsSgsr = Boolean(capabilities?.supportsSGSR);

  const rows = [
    React.createElement(DFL.PanelSectionRow, { key: "nis" },
      React.createElement(DFL.ToggleField, {
        label: "Use NIS",
        description: nisEnabled
          ? "Override the native Sharp filter with NVIDIA Image Scaling."
          : `Native Sharp filter: ${nativeLabel(capabilities)}.`,
        checked: nisEnabled,
        onChange: applyNis
      })
    )
  ];

  if (showFsrOverride) {
    rows.push(
      React.createElement(DFL.PanelSectionRow, { key: "fsr" },
        React.createElement(DFL.ToggleField, {
          label: "Use FSR",
          description: fsrOverride
            ? "Override SGSR with AMD FidelityFX Super Resolution."
            : "Leave this off to use Gamescope's native SGSR Sharp filter.",
          checked: fsrOverride,
          onChange: applyFsr
        })
      )
    );
  }

  rows.push(
    React.createElement(DFL.PanelSectionRow, { key: "sharpness" },
      React.createElement(DFL.SliderField, {
        label: `Sharpness (${sharpness}/5)`,
        description: "Shared FSR/NIS sharpening: 0 minimum, 5 maximum. Disabled when using native Sharp/SGSR.",
        value: sharpness,
        min: 0,
        max: 5,
        step: 1,
        notchCount: 6,
        disabled: !nisEnabled && !fsrOverride,
        onChange: applySharpness
      })
    )
  );

  rows.push(
    React.createElement(DFL.PanelSectionRow, { key: "status" },
      React.createElement("div", {
        style: { fontSize: "12px", opacity: 0.80, padding: "4px 0 8px" }
      }, status, supportsSgsr && capabilities?.gamescopeVersion ? ` · Gamescope ${capabilities.gamescopeVersion}` : "")
    )
  );

  return React.createElement(DFL.PanelSection, { title: "Sharp Filter" }, ...rows);
}

const index = definePlugin(() => ({
  name: "Sharp Filter Selector",
  titleView: React.createElement("div", { className: DFL.staticClasses.Title }, "Sharp Filter Selector"),
  content: React.createElement(Content),
  icon: React.createElement("span", null, "✦"),
  onDismount() {}
}));

export { index as default };
