import { CONNECTIONS, LAYERS, words } from "./types";

export function ConnectionLine({ layer }: { layer: string }) {
  const value = CONNECTIONS[layer];
  return (
    <span
      aria-hidden="true"
      className="legend-line"
      style={{
        borderColor: value.ink,
        borderTopStyle: value.style,
        borderTopWidth: 3,
      }}
    />
  );
}
export function ConnectionLegend() {
  return (
    <div className="layer-legend">
      {LAYERS.map((layer) => (
        <div key={layer}>
          <ConnectionLine layer={layer} />
          {words(layer)}
        </div>
      ))}
    </div>
  );
}
export function ConnectionFilter({
  value,
  onChange,
}: {
  value: string[];
  onChange: (next: string[]) => void;
}) {
  return (
    <details className="layer-menu">
      <summary>Connection types · {value.length}</summary>
      <div>
        {LAYERS.map((layer) => (
          <label key={layer}>
            <input
              type="checkbox"
              checked={value.includes(layer)}
              onChange={() =>
                onChange(
                  value.includes(layer)
                    ? value.filter((l) => l !== layer)
                    : [...value, layer],
                )
              }
            />
            <ConnectionLine layer={layer} />
            {words(layer)}
          </label>
        ))}
      </div>
    </details>
  );
}
