# Six-query browser investigation

**17 October 2026 · local development.** The original timeout/oversized-response failures did not recur in the latest complete six-query block. All six DeepSeek V4.1 Flash explorations returned source-linked graphs in **65–105 seconds** on the final frozen build. Scientific acceptance remains uneven: rendering, model approval and graph connectivity do not certify correctness.

The exact user queries, including `resuable rocket`, were submitted through the real browser form with the authorized SiliconFlow account. Each paid exploration ran alone, using the application's four-request concurrency and normal limits. No model answer or retrieved source was mocked in these runs. Unpaid software fixtures are reported separately.

## Actual results

**Final frozen build: reader 1.3.0.dev12, DeepSeek V4.1 Flash.** Every question below was submitted through the browser on this build after the source-pipeline, navigation and reference-identity fixes. The original spelling was preserved.

| Exact query | First draft insight | Completed | Insights / connections | Directed-core diagnostic |
|---|---:|---:|---:|---|
| lithography machines for chip | 31.6 s | 69.0 s | 8 / 8 | Present |
| Plasma-enhanced chemical vapour decomposition | 32.4 s | 67.8 s | 7 / 10 | Present |
| resuable rocket | 32.4 s | 64.8 s | 6 / 7 | Present |
| GPU and cuda | 34.7 s | 69.1 s | 8 / 8 | Present |
| Alphafold | 34.0 s | 104.6 s | 10 / 10 | Present |
| large language models such as chatgpt | 31.6 s | 83.0 s | 7 / 7 | Present |

Earlier development comparisons remain below. The earlier main matrix used dev8. Dev9 adds a conservative operational-component inference gate; its two targeted tests are separate rows, not replacements for weaker earlier results. Dev10 also reserves a direct full-text study in retrieval and adds empirical/directional admission guards. Its AlphaFold retest is separate. Dev11 completed all six in 58–94 seconds but only four met the structural diagnostic. Its AlphaFold draft lost two proposed foundations because the model abbreviated source IDs. Dev12 recovers an omitted revision only for one uniquely retrieved reference page; all recovered claims still receive fresh checks. Deterministic re-screening of prior outputs is recorded separately and does not change these measured outputs or timings.

| Exact query | Selected model | Build | First draft insight | Completed | Insights / connections | Directed-core diagnostic |
|---|---|---|---:|---:|---:|---|
| lithography machines for chip | DeepSeek-V4.1-Flash | dev8 | 28.9 s | 79.5 s | 8 / 9 | Incomplete |
| Plasma-enhanced chemical vapour decomposition | DeepSeek-V4.1-Flash | dev8 | 36.2 s | 98.0 s | 9 / 8 | Present |
| resuable rocket | DeepSeek-V4.1-Flash | dev8 | 29.8 s | 63.1 s | 7 / 8 | Present |
| GPU and cuda | DeepSeek-V4.1-Flash | dev8 | 32.7 s | 72.2 s | 8 / 6 | Incomplete |
| Alphafold | DeepSeek-V4.1-Flash | dev8 | 35.5 s | 92.1 s | 7 / 6 | Incomplete |
| large language models such as chatgpt | DeepSeek-V4.1-Flash | dev8 | 28.1 s | 98.9 s | 10 / 10 | Present |
| Plasma-enhanced chemical vapour decomposition | GLM-5.3-Flash | dev8 | 36.9 s | 110.7 s | 8 / 8 | Present |
| GPU and cuda | GLM-5.3-Flash | dev8 | 43.8 s | 188.7 s | 10 / 9 | Incomplete |
| Plasma-enhanced chemical vapour decomposition | DeepSeek-V4.1-Flash | dev9 | 29.8 s | 70.2 s | 7 / 9 | Present |
| Alphafold | GLM-5.3-Flash | dev9 | 52.3 s | 140.4 s | 8 / 9 | Incomplete |
| Alphafold | DeepSeek-V4.1-Flash | dev10 | 31.3 s | 95.9 s | 9 / 6 | Incomplete |
| lithography machines for chip | DeepSeek-V4.1-Flash | dev11 | 29.9 s | 87.5 s | 9 / 8 | Incomplete |
| Plasma-enhanced chemical vapour decomposition | DeepSeek-V4.1-Flash | dev11 | 31.0 s | 70.4 s | 7 / 7 | Present |
| resuable rocket | DeepSeek-V4.1-Flash | dev11 | 37.5 s | 94.0 s | 8 / 9 | Present |
| GPU and cuda | DeepSeek-V4.1-Flash | dev11 | 32.6 s | 88.2 s | 10 / 13 | Present |
| Alphafold | DeepSeek-V4.1-Flash | dev11 | 29.7 s | 79.2 s | 7 / 9 | Incomplete |
| large language models such as chatgpt | DeepSeek-V4.1-Flash | dev11 | 27.7 s | 58.0 s | 7 / 6 | Present |

Targets: first draft insight within 60 seconds; completed check within 180 seconds. Draft insights are not yet checked. GLM's GPU run missed the completion target at 188.7 seconds and had scientific defects. Timings are observations on this Mac, not promises or a controlled model ranking. Network and model variability matter.

The directed-core diagnostic requires a designated foundation and requested result, a reachable explanatory core, at least two non-teaching connections in that core, and 80% of retained insights connected. A guided reading route can be useful without meeting that metric. Conversely, a graph can pass it and contain an invalid scientific arrow. The frozen metric was not relaxed to improve results.

## Final graph inspection

- **Case 1: Representative optical-lithography explanation with a foundational route.** Wave interference and ray optics lead into photoresist response, reticle projection, step-and-scan exposure, immersion and diffraction/depth-of-focus constraints. Eight insights and eight relationships; no duplicate projection additions. This is a generic projection/DUV process map, not a complete EUV machine architecture. Resist development belongs to the surrounding fabrication workflow, not necessarily the exposure machine itself. Named-machine control, precision metrology, priority and quantified process windows remain unestablished.
- **Case 2: Representative PECVD mechanism with connected general chemistry and plasma ideas.** Electric discharge and radical reactivity connect to electron acceleration, precursor dissociation, surface reaction, ion bombardment and film deposition. Seven insights and ten relationships; every retained insight participates in the graph. Several links are explicitly authored teaching aids. Radical reactivity is general; ion-bombardment evidence is specific to carbon/oxide films. No universal low-temperature limit, complete plasma kinetics, reactor recipe or historical priority is established.
- **Case 3: Representative reusable-stage route grounded in Newtonian mechanics.** Newton third law and conservation of momentum connect to reaction thrust, retrograde burns, soft landing and repeated use. Six insights and seven relationships; all insights connected. Two mismatched limiting arrows were correctly withheld. No detailed guidance/control architecture, thermal-protection chain, inspection or reflight certification is established. An orbital-launch first stage follows a suborbital recovery trajectory. Priority and the first operational reuse are not independently established.
- **Case 4: Connected GPU/CUDA execution explanation with a general parallelism foundation.** Independent work, throughput-oriented processors, kernels, block/grid organization, warps and memory management lead to CUDA execution. Eight insights and eight relationships. The known conflicting SIMT reference was withheld. Much evidence describes earlier CUDA/hardware generations. Many-core operation is an enabling architecture rather than a universal law. Current independent scheduling, unified memory and the programming model are incomplete. Host/device transfer is a visible side branch lacking a retained connection; no specific speedup is established.
- **Case 5: Representative AlphaFold2 architecture and evolutionary-data route, with a separate physical-folding gap.** Evolutionary covariation, structural/sequence databases, MSA and pair embeddings, Evoformer updates, coordinate output and local AMBER refinement form an inspectable route. The original AlphaFold2 paper is among the three retained sources. Ten insights and ten connections; nine insights participate. The hydrophobic-effect foundation remains disconnected from the learned algorithm: no arrow was invented to imply that AlphaFold simulates global folding. Thermodynamic scope and the sequence-determined-fold premise need qualification. Training losses, detailed coordinate generation, disordered proteins and later AlphaFold generations are not comprehensively established.
- **Case 6: Representative statistical-learning to conversational-language-model route.** Statistical estimation, conditional sequence prediction, attention, positional information, GPT pretraining and conversational fine-tuning form a seven-insight, seven-relationship map. All insights are connected. A component-as-deduction error was withheld; a separately checked teaching link supplies the foundation. The architectural explanation is about text language models and early documented ChatGPT fine-tuning. The endpoint mentions speech and images, whose separate implementations are not established by this route. Token prediction is often simplified as word prediction in the sources. Proprietary current model details, historical influence and comprehensive alignment mechanisms remain gaps.

These assessments remain fallible. The admission checks remove known error shapes, not all scientific mistakes.

## Earlier scientific failures and retained limitations

These are agent assessments of the actual exported records and excerpts, **not qualified human audits**:

- **Lithography:** wave optics, diffraction-limited resolution, mask exposure, resist response and scanner imaging give a useful guided reading route. Scanner operation remains distinct from downstream etching; this is not a full EUV engineering history.
- **PECVD:** the dev9 DeepSeek retest gives electric field and chemical bonding foundations, discharge, excitation control, inductive coupling, surface reaction and film deposition. GLM's dev8 run gives electrical breakdown → energetic electrons → precursor dissociation → deposition, with sheath and hydrogen-content branches. Material/temperature scope and primary attribution remain incomplete. An earlier DeepSeek arrow incorrectly made generic CVD a logical premise for PECVD; the new component gate addresses that shape.
- **Reusable rocket:** conserved momentum → thrust → retropropulsive landing → recovery and repeated use. Detailed guidance, throttling, thermal protection, inspection and reflight certification remain gaps. The typo was not changed in the user's query or export.
- **GPU/CUDA:** indexed kernels, thread hierarchy and memory use are inspectable, but the primary-source and generational scope is inadequate. A GLM result reversed a bound and incorrectly derived a measured speedup from broad architecture statements; it is a failed quality case despite a completed model check.
- **AlphaFold:** the six-query DeepSeek result has sequence/structure and coevolution foundations but mixes AlphaFold generations in a side branch and omits a clear AlphaFold 2 coordinate-generation mechanism. Its main route is incomplete. An independent read-only probe later retrieved the AlphaFold 2 open-access paper; that later evidence does not retroactively support the earlier map.
- **LLMs/ChatGPT:** probability, neural representations, next-token learning, attention and conversational generation provide a selective explanation. They do not establish proprietary current ChatGPT internals or a complete historical reconstruction.

The complete machine-readable report preserves every developmental attempt, including empty graphs, wrong endpoints, unsupported links, timeouts and slow runs. Earlier full blocks tested DeepSeek V4 Flash; bounded probes also tested V4 Pro and Qwen3.8-27B. No model was silently substituted. These six queries are development cases, not the separately frozen research suite.

## Engineering changes

- **Reference identity:** generated citations sometimes omitted a page revision suffix. A deterministic inspection found eight such citations with exact supplied anchors in the preserved dev11 AlphaFold draft. New generation can resolve only one uniquely retrieved version of that exact page. Ambiguous versions, explicit wrong revisions and invented anchors remain invalid; imports retain strict full identities. No extra model call is needed for this normalization.

- Complete singleton insights survive parsing; `Alphafold` is accepted; disjoint insight IDs prevent connection loss.
- The connection contract detects source IDs used as node IDs and unknown predicates before discarding records. Its one bounded format repair cannot invent a new relationship.
- Retrieval preserves specific techniques and qualified queries, rejects disambiguation pages, retains canonical explanatory passages across aliases, and searches intermediate mechanisms within the existing eight-reference budget.
- One additive refinement can supply two missing or corrected insights and four candidate arrows. Checked records remain immutable. Missing general foundations or exact endpoints can be restored under new identities and fresh checks.
- Review uses small node batches and independent arrow checks, with four concurrent requests and a shared 60-second deadline per pass. Only unresolved verdicts receive bounded follow-ups. A timeout, rate limit or authorization failure is not silently replayed.
- The stream limit distinguishes transport metadata from answer size. Planning bounds reasoning explicitly; literal templates and completed empty objects can use the single semantic recovery allowance. All attempts retain usage receipts.
- Navigation distinguishes teaching routes, scientific relationships and historical claims. Labels remain legible over crossing arrows. Every node and arrow has an accessible inspector and source quotations; saved maps open offline.
- **Full-text evidence:** one direct study retains a full-text slot beside reviews. Acquired explanations can displace abstracts in a full 60-source pool. The 24,000-character packet preserves the selected study; method paragraphs can match route concepts without repeating the product name. A live source-only diagnostic confirmed the AlphaFold 2 architecture passages reach the packet.
- **Navigation race:** topic links now resolve their snapshot even while the initial catalogue is loading; later navigation cancels the pending intent.
- A known incorrect SIMT reference revision is excluded. Older maps show a warning linked to [NVIDIA's independent-thread-scheduling documentation](https://docs.nvidia.com/cuda/cuda-programming-guide/03-advanced/advanced-kernel-programming.html), without silently rewriting their contents.

## Verification and limits

The final software suite passed **265 tests with three expected skips**, and both hosted-prefix tests passed. Deterministic replay of 11 earlier maps withheld the three identified invalid arrows, with no new model calls; the two changed copies reopened and inspected offline on desktop/mobile. Original maps and original metrics remain preserved.

See [BUILD_STATUS](../BUILD_STATUS.md) for final software checks, measured reader performance and the current preview link. Desktop and 390-pixel mobile import/inspection tests block external networking and check all exported nodes and arrows. Source/model requests happen only during explicitly online exploration. Maps and API keys are not uploaded to the atlas server; persistence is explicit and local.

The scientific snapshot is unchanged. These personal drafts do not add corpus coverage. Qualified human scientific audits: **zero**. Better primary-source retrieval and independent scientific review remain necessary before treating this as a reliably comprehensive research lineage system. No deployment, remote Git update, new corpus publication or distribution archive was made.

## Usage and reproduction

Preserved: **107 browser attempts**, including **102 with model calls**, plus **15 diagnostic calls**. This investigation reports **1,673 submitted requests**, **7,869,641 input / 1,091,442 output tokens**, and **0 requests with incomplete usage**.

Including prior documented preview QA: **2,481 requests**, **11,808,402 input / 1,853,438 output tokens**, **29 incomplete usage records**. Failed calls are included where receipts exist. Tokens are not a bill, missing usage is not zero cost, and the allowance remains manually managed. This is not a complete project billing total.

The opt-in [browser driver](../scripts/live_browser_qa.mjs) loads an external credential, discovers exact models and writes receipts/maps/screenshots to ignored `.work/`. It targets loopback previews, uses disposable contexts, and does not automatically save the key or upload maps. Ordinary tests make no paid requests. See [development instructions](../docs/DEVELOPMENT.md) and the [full receipt report](local-preview-1.3-six-query.json).
