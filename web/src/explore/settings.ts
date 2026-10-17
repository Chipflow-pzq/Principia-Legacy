import { DEFAULT_MODEL } from "./provider";

export type ProviderSettings = {
  key: string;
  model: string;
  rememberKey: boolean;
};
export const SETTINGS_KEY = "principia-provider-settings/v1";
export function loadSettings(): ProviderSettings {
  const fallback = { key: "", model: DEFAULT_MODEL, rememberKey: false };
  try {
    const stored = JSON.parse(localStorage.getItem(SETTINGS_KEY) || "null");
    if (!stored || stored.provider !== "siliconflow") return fallback;
    return {
      key:
        stored.rememberKey === true && typeof stored.key === "string"
          ? stored.key.slice(0, 512)
          : "",
      model:
        typeof stored.model === "string" && stored.model.trim()
          ? stored.model.trim().slice(0, 160)
          : DEFAULT_MODEL,
      rememberKey: stored.rememberKey === true,
    };
  } catch {
    return fallback;
  }
}
/** Persistence is an explicit settings action. Maps and exports never contain this object. */
export function persistSettings(settings: ProviderSettings): void {
  localStorage.setItem(
    SETTINGS_KEY,
    JSON.stringify({
      provider: "siliconflow",
      model: settings.model.trim(),
      rememberKey: settings.rememberKey,
      ...(settings.rememberKey ? { key: settings.key.trim() } : {}),
    }),
  );
}
