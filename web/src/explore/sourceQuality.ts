/** Revision-specific findings from development source comparisons, not human certification.
 * Excluding one known conflicting revision must not become a blanket publisher ban.
 */
export const sourceQualityFindings = [
  {
    sourceId: "reference_43320329_1375542196",
    title: "Single instruction, multiple threads",
    checkedAt: "2026-10-17",
    finding:
      "This reference revision describes SIMT as lacking per-thread program counters and branch divergence. NVIDIA documents per-thread execution state and independent scheduling for Volta and later GPUs. The reference is unsuitable for a general account of current CUDA execution.",
    comparisonUrl:
      "https://docs.nvidia.com/cuda/cuda-programming-guide/03-advanced/advanced-kernel-programming.html",
    comparisonTitle:
      "NVIDIA CUDA Programming Guide: independent thread scheduling",
  },
];

export function sourceCautions(sources: { id: string }[]) {
  const ids = new Set(sources.map((s) => s.id));
  return sourceQualityFindings.filter((f) => ids.has(f.sourceId));
}
