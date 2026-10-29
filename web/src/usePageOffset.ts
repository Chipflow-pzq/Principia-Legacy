import { useEffect, useState } from "react";

/** Small, shareable collection positions; ownership prevents paging another entity. */
export function usePageOffset(
  parameter: string,
  owner: string,
  pageSize: number,
) {
  const read = () => {
    const value =
      new URLSearchParams(location.hash.slice(1)).get(parameter) || "";
    const split = value.lastIndexOf(":");
    const number = Number(value.slice(split + 1));
    return value.slice(0, split) === owner &&
      Number.isSafeInteger(number) &&
      number >= 0
      ? Math.min(10_000_000, Math.floor(number / pageSize) * pageSize)
      : 0;
  };
  const [offset, update] = useState(read);
  useEffect(() => {
    const restore = () => update(read());
    restore();
    window.addEventListener("popstate", restore);
    window.addEventListener("hashchange", restore);
    return () => {
      window.removeEventListener("popstate", restore);
      window.removeEventListener("hashchange", restore);
    };
  }, [parameter, owner, pageSize]);
  const setOffset = (value: number) => {
    const route = new URLSearchParams(location.hash.slice(1));
    route.set(parameter, `${owner}:${value}`);
    history.replaceState(history.state, "", "#" + route.toString());
    update(value);
  };
  return [offset, setOffset] as const;
}
