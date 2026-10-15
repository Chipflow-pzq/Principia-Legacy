# Evaluation and audit

The 120-case synthetic pilot has six families: source grounding, scope transfer, counterevidence, correction, facts-to-values transitions, and authorization. Thirty development and ninety held-out cases use disjoint contribution subjects. Their files, hashes, construction method, and evaluator prompt hash are frozen before execution. Do not tune the prompt against held-out outcomes.

Conditions are unstructured evidence, flat contribution cards, an untyped graph, the typed atlas, and a boundary-removal ablation. All derive from the same selected contribution/source neighborhood. Context ceilings are matched by characters; actual token receipts are retained, so exact token equality is not claimed. Missing responses are counted, not silently discarded. The runner is resumable.

The unstructured condition uses project-authored paraphrases and source locators, not raw source passages. Visible fields differ across conditions. This is an implementation pilot; the proposal's stricter matched-evidence and input-token-controlled comparative study remains outstanding. The summary's `unsupported_assertions_per_case` denominator is all attempted cases, including misses, rather than only trap cases. This naming clarifies the existing calculation without changing model responses or rerunning held-out cases.

```sh
python3 start.py evaluate --split all
python3 start.py evaluate --split all --allow-network --env-file /path/to/private.env
```

The first command is a zero-network feasibility check. The second incurs provider usage. Results contain per-case answers, condition, family, split, citation IDs, mock actions, and receipt identity. No real tools or consequential actions are available to the evaluated model.

Rule-based verdict agreement, citation-ID validity, reported conditions, correction-version uptake, and mock-action refusal are instrumentation measures. They do not independently assess subtle scientific correctness or semantic citation fidelity. Synthetic templates and model screening are not expert-authored gold judgments. No result establishes superalignment.

The separate stratified 100-contribution/150-relation audit sample is a review queue, not a completed human audit. It records frozen IDs, hashes, source references, and empty adjudication fields. Qualified reviewers must assess claim fidelity and arrow correctness separately. Report actual judgments and uncertainty intervals only after real adjudication; do not relabel automated output as independent human review.
