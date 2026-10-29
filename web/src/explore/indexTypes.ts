import type { Contribution } from "../types";
export type Entry = Pick<
  Contribution,
  | "id"
  | "revision"
  | "content_hash"
  | "title"
  | "pillar"
  | "kind"
  | "claim"
  | "explanation"
  | "assumptions"
  | "limits"
  | "attribution"
  | "date"
> & { neighbors?: string[]; compact?: boolean };
export type Index = {
  entries: Entry[];
  total: number;
  snapshot_hash: string;
  release_id: string;
  worker?: Worker;
};
