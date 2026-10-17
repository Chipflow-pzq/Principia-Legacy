export const STAGES = [
  "Find sources",
  "Plan the search",
  "Follow earlier work",
  "Build the map",
  "Check the evidence",
];
export type Progress = {
  stage: number;
  detail: string;
  stageStarted: number;
  papers: number;
  passages: number;
  atlas: number;
  insights: number;
  connections: number;
  characters: number;
  activity: string[];
  titles: string[];
  foundations?: string[];
  state: "working" | "paused" | "complete";
  refinement?: boolean;
  deadline?: number;
  reviewedInsights?: number;
  reviewedConnections?: number;
};
const windows = [
  [4, 25],
  [4, 35],
  [6, 65],
  [15, 110],
  [8, 40],
];

/** A range, not a promise or a synthetic completion percentage. No personal data is saved. */
export function remainingEstimate(progress: Progress, now: number) {
  if (progress.state !== "working") return "";
  if (progress.stage === 4 && progress.deadline !== undefined) {
    const seconds = Math.max(0, Math.ceil((progress.deadline - now) / 1000));
    return seconds
      ? `Evidence check ends within ${seconds} sec`
      : "Finishing this check…";
  }
  const elapsed = Math.max(0, (now - progress.stageStarted) / 1000);
  const [low, high] = windows[progress.stage];
  if (elapsed > high + 45)
    return "Taking longer than usual · remaining time uncertain";
  const rest = windows.slice(progress.stage + 1);
  const lower = Math.max(5, low - elapsed) + rest.reduce((s, w) => s + w[0], 0);
  const upper =
    Math.max(15, high - elapsed) + rest.reduce((s, w) => s + w[1], 0);
  const label = (seconds: number) =>
    seconds < 60
      ? `${Math.ceil(seconds / 10) * 10} sec`
      : `${Math.ceil(seconds / 60)} min`;
  const a = label(lower),
    b = label(upper);
  return a === b ? `About ${b} remaining` : `About ${a}–${b} remaining`;
}
