# Local review workspace

**Reader 1.4.1 · atlas 1.4.1-exploratory · 17 October 2026.** The local version has passed owner acceptance. It includes the corrected and expanded scientific collection as well as the reader and personal-exploration workflow.

## Open it

Use **[the ordinary local address](http://127.0.0.1:8767/)**, then choose **Trace a discovery**. The direct link is **[the same exploration workspace](http://127.0.0.1:8767/#page=explore)**. Old `?preview=...` links normalize automatically. A preview parameter never selected a different application build. **Settings → About this installation** identifies the reader version and the separate atlas snapshot. Topic and insight links retain their snapshot for reproducibility; personal exploration does not need a snapshot in its navigation URL. Open a fresh tab if an older tab retains earlier JavaScript. An existing reader on port 8765 is separate.

To restart from the repository root:

```sh
python3 start.py serve --offline --port 8767
```

Python 3.12+ is sufficient for the prebuilt reader. Reading the atlas or opening a saved map needs no network or API key. Creating a personal exploration is explicitly online and uses the key entered in the browser; the server process does not make provider requests.

## Explore from one place

The same input card offers **Browse the atlas** and **Trace a discovery**. The second button reveals the research input. Switching modes preserves an unfinished question, and returning to Browse restores the earlier search or topic. A public search can also prefill a research question.

Enter your own SiliconFlow key and exact model ID once in the global top-right **Settings**. **Load my available models** discovers your account's model IDs without silently changing the selection. The model is stored locally. Select **Remember API key on this device** only if you want the key retained after a reload; otherwise it stays in tab memory. **Clear API key** removes it from both places.

Enter a paper, technique or scientific advance and select **Build research map**. Source counts, new insights, stage activity and elapsed time appear as work progresses. **Inspect draft now** opens the emerging map. The final evidence check shows the number of insights and connections assessed, together with a **60-second maximum wait**, shared by formatting repair and any compatibility handling. Earlier stages show approximate remaining-time ranges.

If generation ends early, whole source-linked insights can still proceed to evidence review. If the review is incomplete, the map remains available with an unfinished-review label; it is never presented as having passed the check. **Resume evidence check** repeats only that unfinished step. Pausing preserves the draft and session checkpoint. A background run stays reachable from the header while browsing elsewhere.

Use **Save on this device** for browser storage or **Download map** for a portable file. **Open a map file** restores it offline without a key. After resuming a saved partial map, **Save updated map** explicitly replaces that local copy. **Undo removal** restores a map removed during the session. Closing or reloading the tab discards unsaved work and recovery checkpoints; a downloaded partial map preserves its content, not the ability to resume that session.

## Catalogue changes in 1.4

Discovery suggestions follow the selected subject. Search returns topics, works,
ideas and selected individual contributors; spelling corrections and related
concepts are explained inline. Open a work to see its people, containing topics,
checked insights and source versions. Search context survives reading and Back.
Metadata-only works clearly show that extraction is pending. See the [1.4 notes](RELEASE-1.4.md).

## Personal exploration inherited from 1.3

The explorer now looks for a governing principle, intermediate mechanisms and the requested result. It retrieves additional intermediate route concepts within the same eight-reference budget and preserves the main passage when multiple queries return one article. It reads bounded explanatory passages alongside research abstracts and the public atlas. Insights and connections are drafted separately. A bridge can use its own source rather than being restricted to sources already cited by both endpoints.

The application preserves complete singleton result objects as well as arrays, assigns node IDs, validates evidence anchors and independently checks each arrow's direction, scope and warrant. Generative requests use JSON-object mode after live comparisons exposed failures in nested strict decoding. Planning uses a small explicit reasoning allowance because some models ignored the non-thinking flag. Small verdict requests retain structured contracts. A completed empty drafting object, copied template or unmistakable input echo can receive one bounded replacement; no timed-out generation is automatically replayed. Four focused literature searches complement direct foundation and mechanism lookups. Node checks use batches of two and compare earlier ideas to avoid duplicate moves; a missing route can receive one bounded refinement that preserves already-checked records.

The map distinguishes **Foundation**, **Enabling idea**, **Requested result** and **Boundary or tradeoff**. Its reading route is navigation through individually labelled relationships, never a claim that a mixed path is a proof or documented historical influence. A mainly pedagogical route is labelled **guided reading path**. Missing links remain visible.

A known source conflict is excluded by exact reference revision. Older saved maps using it show an inspectable warning without rewriting their content.

Actual provider runs, unfavorable developmental results, test counts, timings and usage are recorded in [BUILD_STATUS](../BUILD_STATUS.md), the [1.3 live evaluation](../reports/product-readiness-1.3.md), and the [earlier six-query report](../reports/local-preview-1.3-six-query.md). Completion of a model check does not establish scientific correctness. No qualified human audit has been performed.

## Reader details to inspect

- **Mathematics:** inspect scaled dot-product attention in the Transformer topic. Inline formulas use bundled KaTeX; display equations scroll independently when necessary.
- **Navigation:** switch insights and connection types. Existing graph positions stay stable; returning from an inspector preserves search results. A streaming personal graph fits new nodes until you take control of the viewport.
- **Connections:** a new map starts with all connection types visible and shows how many are displayed. History is amber, reasoning blue, evidence green with long dashes, similar ideas purple with short dashes, and learning prerequisites pink and dotted. Legends and arrows share the same styles.
- **Sidebar:** the release dropdown is removed. Historical links and Changes remain available for reproducibility.
- **Accessibility:** use the list view, keyboard navigation and Escape to close Settings or an inspector without losing context. Check a narrow browser width as well as the desktop layout.

## Evidence and privacy

The agent searches Crossref, Europe PMC, revision-pinned Wikipedia reference passages and the public atlas index, with bounded follow-up retrieval. It does not browse the entire web or establish scientific priority. Sparse abstracts, paywalls, inaccessible sources and missing ancestry stay visible as gaps.

All generated maps remain **Personal draft · not verified**. Exact quotations, source identifiers, chronology, scope, relationship direction and a separate model check constrain admission, but can still miss errors. Cross-paper connections require a specific bridge or explicit, scoped synthesis; a citation or shared topic alone is insufficient. No map enters the published corpus automatically; no human scientific audit has been performed.

The key goes directly to SiliconFlow. Research questions go directly to the provider and scholarly search services, whose policies apply. The atlas server receives no private research question, key or generated map. Ordinary **Browse the atlas** searches use the server's read-only search API; transferring an earlier public search into Research does not undo that earlier request. Maps are saved only by explicit choice, to this browser's IndexedDB or a downloaded JSON file. Local preview ports and the public site have separate browser storage.

See [Personal exploration](PERSONAL_EXPLORATION.md) for data flow and operational bounds, [build status](../BUILD_STATUS.md) for readiness and spending receipts, and [verification](../reports/product-readiness-1.3.md) for actual results. See the [deployment record](DEPLOYMENT-1.4.1.md) for the separately verified public installation.
