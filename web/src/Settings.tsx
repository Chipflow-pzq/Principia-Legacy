import { useEffect, useRef, useState } from "react";
import { modelCatalog } from "./explore/provider";
import { version } from "../package.json";
import { persistSettings, type ProviderSettings } from "./explore/settings";

export function Settings({
  value,
  running,
  atlasRelease,
  onApply,
  onClose,
}: {
  value: ProviderSettings;
  running: boolean;
  atlasRelease?: string;
  onApply: (value: ProviderSettings) => void;
  onClose: () => void;
}) {
  const [draft, setDraft] = useState(value),
    [models, setModels] = useState<string[]>([]);
  const [busy, setBusy] = useState(false),
    [message, setMessage] = useState(""),
    [error, setError] = useState("");
  const dialog = useRef<HTMLDialogElement>(null),
    controller = useRef<AbortController | null>(null);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    dialog.current?.showModal();
    return () => {
      controller.current?.abort();
      previous?.focus({ preventScroll: true });
    };
  }, []);
  async function discover() {
    controller.current?.abort();
    const abort = new AbortController();
    controller.current = abort;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const available = await modelCatalog(draft.key, abort.signal);
      setModels(available);
      setMessage(
        `${available.length} models available to your account. Your selected model has not been changed.`,
      );
    } catch {
      if (!abort.signal.aborted)
        setError(
          "Could not load models. Check your key and connection, or enter the exact model ID.",
        );
    } finally {
      setBusy(false);
    }
  }
  function apply(event: React.FormEvent) {
    event.preventDefault();
    const next = { ...draft, key: draft.key.trim(), model: draft.model.trim() };
    onApply(next);
    try {
      persistSettings(next);
      onClose();
    } catch {
      setError(
        "Settings are applied for this tab, but browser storage is unavailable. They will be lost when the tab closes.",
      );
    }
  }
  function clear() {
    const next = { ...draft, key: "", rememberKey: false };
    setDraft(next);
    setModels([]);
    controller.current?.abort();
    onApply(next);
    try {
      persistSettings(next);
      setError("");
      setMessage("API key cleared from this tab and saved settings.");
    } catch {
      setError(
        "The key was cleared from this tab, but browser storage could not be changed. Clear this site's stored data to remove an earlier saved key.",
      );
    }
  }
  return (
    <dialog
      ref={dialog}
      className="settings-dialog"
      aria-labelledby="settings-title"
      onCancel={onClose}
      onClose={onClose}
    >
      <form onSubmit={apply}>
        <div className="settings-heading">
          <div>
            <span className="eyebrow">YOUR DEVICE · YOUR ACCOUNT</span>
            <h2 id="settings-title">Settings</h2>
          </div>
          <button type="button" onClick={onClose} aria-label="Close settings">
            ×
          </button>
        </div>
        <p>Set up SiliconFlow once for all your explorations.</p>
        <details className="settings-version">
          <summary>About this installation · Reader {version}</summary>
          <p>
            Reader {version} is the installed application. Atlas content{" "}
            {atlasRelease || "is loading"} is a separate, reproducible
            collection of published insights. Saved atlas links may pin that
            content edition. Personal discoveries are local drafts.
          </p>
        </details>
        {running && (
          <p className="local-notice">
            A discovery is being traced. Pause it before changing provider
            settings.
          </p>
        )}
        <div className="settings-grid">
          <label>
            SiliconFlow API key
            <input
              type="password"
              autoComplete="off"
              spellCheck={false}
              maxLength={512}
              value={draft.key}
              disabled={running}
              onChange={(e) => {
                controller.current?.abort();
                setModels([]);
                setDraft({ ...draft, key: e.target.value });
              }}
              placeholder="Your personal API key"
            />
          </label>
          <label>
            Model ID
            <input
              list="exploration-models"
              autoComplete="off"
              required
              maxLength={160}
              value={draft.model}
              disabled={running}
              onChange={(e) => setDraft({ ...draft, model: e.target.value })}
            />
          </label>
          <datalist id="exploration-models">
            {models.map((m) => (
              <option key={m} value={m} />
            ))}
          </datalist>
        </div>
        <div className="explore-actions">
          <button
            type="button"
            onClick={discover}
            disabled={!draft.key.trim() || running || busy}
          >
            {busy ? "Loading models…" : "Load my available models"}
          </button>
          <button
            type="button"
            onClick={clear}
            disabled={running || (!draft.key && !value.key)}
          >
            Clear API key
          </button>
        </div>
        <label className="remember-key">
          <input
            type="checkbox"
            checked={draft.rememberKey}
            disabled={running}
            onChange={(e) =>
              setDraft({ ...draft, rememberKey: e.target.checked })
            }
          />
          <span>
            Remember API key on this device
            <small>
              Keep it in this browser profile between visits. You can clear it
              here at any time.
            </small>
          </span>
        </label>
        <p className="privacy-note">
          Your key goes directly to SiliconFlow. It is never sent to the atlas
          server or included in map files. Your model choice is saved locally;
          remembering the key is optional.
        </p>
        {message && (
          <p className="local-notice" role="status">
            {message}
          </p>
        )}
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        <div className="settings-footer">
          <button type="button" onClick={onClose}>
            Close
          </button>
          <button
            className="primary"
            type="submit"
            disabled={running || !draft.model.trim()}
          >
            Save settings
          </button>
        </div>
      </form>
    </dialog>
  );
}
