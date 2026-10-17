# 1.4 local acceptance report

**Reader 1.4.0-rc.1 · 1.4.1-exploratory · 17 October 2026.** The local reader
and catalogue upgrade are ready for user acceptance. This is an exploratory
scientific collection, with no qualified human audit and no remote deployment.

| Area | Actual result |
|---|---|
| Reader behavior | Subject-aware discoveries; topics, works, insights and individuals in search; exact work/topic/insight links; source and revision inspectors |
| Backend | 117 Python/hosting tests passed |
| Full browser regression | 297 passed, 3 deliberate skips; desktop and mobile. Every populated topic and one empty catalogue page per subject traversed |
| Final changes | 32 work/search/navigation checks passed on the corrected snapshot, including a newly installed release absent from an open tab's cached list and recovery from an invalid link |
| Hosted mount | 2 browser tests passed under /web/legacy/, including work/profile reloads; local test only |
| Integrity | Exported schemas, record/source pins, all 781 topic/work references, joint premises, snapshot changes and cross-subject source closure passed |
| Corrections | Five real flagship records exercised in a disposable copy; stale work memberships and source changes covered by dedicated tests |
| Offline | Standard-library Python with external connections blocked; no background external requests from the reader |
| Mathematics | 8,658 formulas checked; zero current failures. Superseded immutable warnings remain recorded |
| Clean install | Offline distribution checksum/startup and source distribution's automatic offline rebuild passed; isolated hosted-reader imports passed |

The full browser run began with 1.4.0. The final source wording correction is
pinned in 1.4.1, and the final confirmation run covers its navigation and the last
UI changes. Regression fixtures do not constitute new live-provider experiments.
Initial assertion mismatches and an intentionally stopped development run are
preserved in `catalog-1.4-initial-browser-check.json`.

## Performance on this machine

Measured on macOS 26.3.1, x86_64, Python 3.12.7 and automated Chrome:

- First view: **1.12 seconds**, with five discovery controls visible.
- Thirty warm HTTP samples: search p95 **150 ms**; graph neighborhood p95 **109 ms**; full topic catalogue p95 **329 ms**.
- Combined browser and reader RSS: **952 MB**, including **264 MB** for the reader after historical browsing. Browser JavaScript heap: **15.7 MB**. RSS sums can count shared pages more than once.
- The earlier measurement was 1,245 MB. Removing retained large JSON cache keys and bounding the cache to two decoded snapshots reduced the measured working set. Both measurements are retained.
- Clean prebuilt startup: **0.73 seconds**. The source-only archive automatically rebuilt its index and started in **17.65 seconds**, without Node, installed Python packages or outbound networking.

These are local measurements, not public-server load tests. Two hosted-mount
browser profiles were checked locally; Linux and Windows were not executed.

## Coverage and evidence quality

There are **882 catalogue works and 899 selected individuals**. Of 781 registered
topics, **184** have admitted insights; **262 works** have extracted insights and
**620** await extraction. The corpus contains **2,905 insights and 1,941 separately
checked relationships**. The catalogue includes 107 explanatory source sections;
its work count is not a count of original discoveries.

All current scientist pages identify individuals. An original byline may still
appear in evidence attribution, but it cannot become a scientist profile. Metadata
provenance establishes documented relevance, not scientific support. Work links
pin exact revisions and scope; they never infer influence from shared membership.

The computing-origin source pass added 25 net insights and 21 relationships. Direct
agent inspection corrected mistaken reduction directions and the distinction
between countability and effective enumeration, and withheld four implementation
inventories. A positive sphere-packing check contained an incorrect normalization;
it was corrected and independently rechecked. This is evidence of the need for
review, not evidence that model checks are infallible. **No qualified human audit
has occurred.**

Selection draws on Nobel data, IMU/Abel records, computing histories, institutional
biographies and a historical supplement. Prize and institutional sources are a
biased starting point. The suggested 200–500 selections and deeper scientific
coverage targets are not met in every subject. See `catalog-1.4.json` for exact
shortfalls and `catalog-1.4-acquisition.json` for source failures and receipts.

## Usage and release boundary

Cumulative authoring ledger: **1,828 provider attempts**,
1,739 successful; **53
unknown-charge attempts** and up to **4
additional interrupted in-flight requests**. Reported usage totals
31,966,593 input and 3,809,024
output tokens. These totals include earlier development. The dated-rate subtotal
excludes 666 requests on unpriced models and unreported usage; it is not a bill.
The US$300-equivalent allowance remains owner-managed. Keys and source caches are
excluded from the archives.

The 120-case research pilot and 1.3 live Trace evaluation are preserved, not rerun.
The live evaluation still has scientific-scope and route-quality limitations.
This update does not certify unattended public research or stronger alignment.

Both local archives include checksums. `package-verification-1.4.json` records the
clean preflight; final delivery checks additionally compare every tested source,
asset and catalogue file against the packaged bytes. The final archive hashes and
sizes are recorded beside the archives in `dist/delivery-1.4.json`.
