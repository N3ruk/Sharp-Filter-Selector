const manifest = { name: "Sharp Filter Selector", author: "N3ruk", flags: [], api_version: 1 };
const internal = window.__DECKY_SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED_deckyLoaderAPIInit;
if (!internal) throw new Error("Decky API unavailable");
let api;
try { api = internal.connect(2, manifest.name); } catch (_) { api = internal.connect(1, manifest.name); }
const setNisEnabled = api.callable("set_nis_enabled");
const setNisSharpness = api.callable("set_nis_sharpness");
const getStatus = api.callable("get_status");
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

function Panel() {
  const [nisEnabled, setNisEnabledState] = React.useState(storedEnabled);
  const [sharpness, setSharpnessState] = React.useState(storedSharpness);
  const [status, setStatus] = React.useState("Checking Gamescope…");

  function describe(enabled, level, displays) {
    const targets = displays?.length ? ` (${displays.join(", ")})` : "";
    return enabled
      ? `NIS active · sharpness ${level}/5${targets}`
      : `NIS disabled · FSR active${targets}`;
  }

  async function applyEnabled(enabled) {
    setStatus("Applying…");
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
      setStatus(describe(enabled, sharpness, displays));
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
      setStatus(describe(true, level, result.displays));
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
        setStatus(describe(desiredEnabled, desiredSharpness, displays));
      } catch (error) {
        if (!mounted) return;
        try {
          const result = await getStatus();
          if (!mounted) return;
          if (result.success) {
            setNisEnabledState(result.enabled);
            if (Number.isInteger(result.level)) setSharpnessState(result.level);
            setStatus(describe(result.enabled, result.level ?? desiredSharpness, result.displays));
          } else {
            setStatus(result.error || "Available in a Gamescope session");
          }
        } catch (_) {
          setStatus(`Error: ${String(error)}`);
        }
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
          ? "NVIDIA Image Scaling is the active Gamescope scaling filter."
          : "AMD FidelityFX Super Resolution is the active Gamescope scaling filter.",
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
        style: { fontSize: "12px", opacity: 0.75, padding: "4px 0 8px" }
      }, status)
    )
  );
}

var index = DFL.definePlugin(() => ({
  name: "Sharp Filter Selector",
  title: React.createElement("div", { className: DFL.staticClasses.Title }, "Sharp Filter Selector"),
  content: React.createElement(Panel),
  icon: React.createElement("span", null, "✦"),
  onDismount() {}
}));

export { index as default };
