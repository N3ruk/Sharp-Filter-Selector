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
  enforcing?: boolean;
  level?: number | null;
  rawValue?: number | null;
  displays?: string[];
  diagnostics?: Diagnostic[];
};

const setNisEnabled = callable<[enabled: boolean], BackendResult>("set_nis_enabled");
const setNisSharpness = callable<[level: number], BackendResult>("set_nis_sharpness");
const getStatus = callable<[], BackendResult>("get_status");

const ENABLED_KEY = "sharp-filter-nis-enabled";
const SHARPNESS_KEY = "sharp-filter-nis-sharpness";

function storedEnabled(): boolean {
  return localStorage.getItem(ENABLED_KEY) === "true";
}

function storedSharpness(): number {
  const value = Number(localStorage.getItem(SHARPNESS_KEY));
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

function Content() {
  const [nisEnabled, setNisEnabledState] = useState<boolean>(storedEnabled);
  const [sharpness, setSharpnessState] = useState<number>(storedSharpness);
  const [status, setStatus] = useState<string>("Checking Gamescope…");

  const describe = (enabled: boolean, level: number, displays?: string[]) => {
    const targets = displays?.length ? ` (${displays.join(", ")})` : "";
    return enabled
      ? `NIS active · sharpness ${level}/5${targets}`
      : `NIS disabled · FSR active${targets}`;
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
              : "NIS failed · SteamOS targets found but NIS is not active",
          );
        } else {
          setStatus(
            describe(
              Boolean(result.enabled),
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

  const applyEnabled = async (enabled: boolean) => {
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
  };

  const applySharpness = async (value: number) => {
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
  };

  useEffect(() => {
    let mounted = true;
    const desiredEnabled = storedEnabled();
    const desiredSharpness = storedSharpness();

    const initialize = async () => {
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
    };

    void initialize();
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <PanelSection title="Sharp Filter">
      <PanelSectionRow>
        <ToggleField
          label="Use NIS"
          description={
            nisEnabled
              ? "SteamOS: target every Gamescope Xwayland and force a real NIS transition."
              : "AMD FidelityFX Super Resolution is the selected Gamescope filter."
          }
          checked={nisEnabled}
          onChange={applyEnabled}
        />
      </PanelSectionRow>

      <PanelSectionRow>
        <SliderField
          label={`NIS sharpness (${sharpness}/5)`}
          description="0 applies minimum sharpening; 5 applies maximum sharpening."
          value={sharpness}
          min={0}
          max={5}
          step={1}
          notchCount={6}
          disabled={!nisEnabled}
          onChange={applySharpness}
        />
      </PanelSectionRow>

      <PanelSectionRow>
        <div style={{ fontSize: "12px", opacity: 0.8, padding: "4px 0 8px" }}>
          {status}
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
