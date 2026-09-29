import { callable, definePlugin } from "@decky/api";
import {
  PanelSection,
  PanelSectionRow,
  SliderField,
  ToggleField,
  staticClasses,
} from "@decky/ui";
import { useEffect, useState } from "react";
import { FaWandMagicSparkles } from "react-icons/fa6";

type Diagnostic = {
  display?: string;
  serverId?: number | null;
  legacyFilter?: number | null;
  newFilter?: number | null;
  fsrFeedback?: number | null;
};

type BackendResult = {
  success: boolean;
  error?: string;
  enabled?: boolean;
  requested?: boolean;
  fsrOverride?: boolean;
  enforcing?: boolean;
  engine?: string;
  selectedEngine?: string;
  level?: number | null;
  rawValue?: number | null;
  displays?: string[];
  diagnostics?: Diagnostic[];
};

type CapabilityResult = {
  success: boolean;
  gamescopePid?: number | null;
  gamescopeExecutable?: string | null;
  gamescopeVersion?: string | null;
  supportsSGSR?: boolean;
  sgsrEvidence?: string;
  hdrInput?: boolean;
  hdrInputKnown?: boolean;
  hdrOutputEnabled?: boolean;
  hdrSource?: string;
  nativeSharpEngine?: string;
  showFsrOverride?: boolean;
  steamos?: boolean;
  errors?: string[];
};

const setNisEnabled = callable<[enabled: boolean], BackendResult>("set_nis_enabled");
const setFsrOverride = callable<[enabled: boolean], BackendResult>("set_fsr_override");
const setNisSharpness = callable<[level: number], BackendResult>("set_nis_sharpness");
const getStatus = callable<[], BackendResult>("get_status");
const getCapabilities = callable<[], CapabilityResult>("get_capabilities");

const NIS_ENABLED_KEY = "sharp-filter-nis-enabled";
const NIS_SHARPNESS_KEY = "sharp-filter-nis-sharpness";
const FSR_OVERRIDE_KEY = "sharp-filter-fsr-override";

function storedNisEnabled(): boolean {
  return localStorage.getItem(NIS_ENABLED_KEY) === "true";
}

function storedFsrOverride(): boolean {
  return localStorage.getItem(FSR_OVERRIDE_KEY) === "true";
}

function storedSharpness(): number {
  const value = Number(localStorage.getItem(NIS_SHARPNESS_KEY));
  return Number.isInteger(value) && value >= 0 && value <= 5 ? value : 5;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function targetSummary(result: BackendResult): string {
  const diagnostics = Array.isArray(result.diagnostics) ? result.diagnostics : [];
  if (!diagnostics.length) return "";

  return diagnostics
    .map((d) => {
      const display = d.display ?? "?";
      const sid = Number.isInteger(d.serverId) ? `#${d.serverId}` : "";
      const legacy = d.legacyFilter ?? "?";
      const modern = d.newFilter ?? "?";
      const feedback = d.fsrFeedback === 1 ? " FSR" : "";
      return `${display}${sid}[${legacy}/${modern}]${feedback}`;
    })
    .join(" · ");
}

function nativeLabel(capabilities: CapabilityResult | null): string {
  if (!capabilities?.supportsSGSR) return "FSR";
  return capabilities.hdrInput ? "FSR (HDR fallback)" : "SGSR";
}

function Content() {
  const [nisEnabled, setNisEnabledState] = useState<boolean>(storedNisEnabled);
  const [fsrOverride, setFsrOverrideState] = useState<boolean>(storedFsrOverride);
  const [sharpness, setSharpnessState] = useState<number>(storedSharpness);
  const [capabilities, setCapabilities] = useState<CapabilityResult | null>(null);
  const [status, setStatus] = useState<string>("Checking Gamescope…");

  const clearHdrFeedback = () => setCapabilities((previous) => previous ? {
    ...previous,
    hdrInput: false,
    hdrInputKnown: false,
    hdrSource: "unknown",
    showFsrOverride: Boolean(previous.supportsSGSR),
  } : previous);

  const describe = (
    nis: boolean,
    fsr: boolean,
    level: number,
    displays?: string[],
    caps: CapabilityResult | null = capabilities,
  ) => {
    const targets = displays?.length ? ` (${displays.join(", ")})` : "";
    if (nis) return `NIS active · sharpness ${level}/5${targets}`;
    if (fsr) return `FSR override active · sharpness ${level}/5${targets}`;
    return `Sharp native · ${nativeLabel(caps)}${targets}`;
  };

  const refreshCapabilities = async (): Promise<CapabilityResult | null> => {
    try {
      const result = await getCapabilities();
      setCapabilities(result);
      return result;
    } catch {
      clearHdrFeedback();
      return null;
    }
  };

  const verifyNis = async (level: number, fallbackDisplays?: string[]) => {
    for (let attempt = 0; attempt < 5; attempt++) {
      await sleep(attempt === 0 ? 350 : 500);
      const result = await getStatus();
      if (result?.success && result.enabled) {
        const targets = targetSummary(result);
        setStatus(
          targets
            ? `NIS verified active · ${targets}`
            : `NIS verified active · sharpness ${level}/5`,
        );
        return true;
      }
    }

    try {
      const result = await getStatus();
      if (result?.success) {
        const targets = targetSummary(result);
        if (result.requested && result.enforcing) {
          setStatus(
            targets
              ? `NIS failed · targets ${targets}`
              : "NIS failed · Gamescope targets found but NIS is not active",
          );
        } else {
          setStatus(
            describe(
              Boolean(result.enabled),
              Boolean(result.fsrOverride),
              Number.isInteger(result.level) ? Number(result.level) : level,
              result.displays ?? fallbackDisplays,
            ),
          );
        }
      } else {
        setStatus(result?.error || "Could not verify the active Gamescope filter");
      }
    } catch {
      setStatus("NIS requested · verification unavailable");
    }
    return false;
  };

  const applyNis = async (enabled: boolean) => {
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
  };

  const applyFsr = async (enabled: boolean) => {
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
  };

  const applySharpness = async (value: number) => {
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
  };

  useEffect(() => {
    let mounted = true;
    let timer: ReturnType<typeof setInterval> | undefined;

    const initialize = async () => {
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
          setStatus(describe(false, false, desiredSharpness, undefined, caps));
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
          } catch {
            // Keep SGSR capability, but do not hide FSR using stale HDR feedback.
            if (mounted) clearHdrFeedback();
          }
        }, 1500);
      } catch (error) {
        if (!mounted) return;
        setStatus(`Error: ${String(error)}`);
      }
    };

    void initialize();
    return () => {
      mounted = false;
      if (timer !== undefined) clearInterval(timer);
    };
  }, []);

  const showFsrOverride = Boolean(capabilities?.showFsrOverride);
  const supportsSgsr = Boolean(capabilities?.supportsSGSR);

  return (
    <PanelSection title="Sharp Filter">
      <PanelSectionRow>
        <ToggleField
          label="Use NIS"
          description={
            nisEnabled
              ? "Override the native Sharp filter with NVIDIA Image Scaling."
              : `Native Sharp filter: ${nativeLabel(capabilities)}.`
          }
          checked={nisEnabled}
          onChange={applyNis}
        />
      </PanelSectionRow>

      {showFsrOverride && (
        <PanelSectionRow>
          <ToggleField
            label="Use FSR"
            description={
              fsrOverride
                ? "Override SGSR with AMD FidelityFX Super Resolution."
                : "Leave this off to use Gamescope's native SGSR Sharp filter."
            }
            checked={fsrOverride}
            onChange={applyFsr}
          />
        </PanelSectionRow>
      )}

      <PanelSectionRow>
        <SliderField
          label={`Sharpness (${sharpness}/5)`}
          description="Shared FSR/NIS sharpening: 0 minimum, 5 maximum. Disabled when using native Sharp/SGSR."
          value={sharpness}
          min={0}
          max={5}
          step={1}
          notchCount={6}
          disabled={!nisEnabled && !fsrOverride}
          onChange={applySharpness}
        />
      </PanelSectionRow>

      <PanelSectionRow>
        <div style={{ fontSize: "12px", opacity: 0.8, padding: "4px 0 8px" }}>
          {status}
          {supportsSgsr && capabilities?.gamescopeVersion
            ? ` · Gamescope ${capabilities.gamescopeVersion}`
            : ""}
        </div>
      </PanelSectionRow>
    </PanelSection>
  );
}

export default definePlugin(() => ({
  name: "Sharp Filter Selector",
  titleView: <div className={staticClasses.Title}>Sharp Filter Selector</div>,
  content: <Content />,
  icon: <FaWandMagicSparkles />,
  onDismount() {},
}));
