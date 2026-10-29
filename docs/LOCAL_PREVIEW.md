# Review Principia-Legacy 1.5 locally

**Accepted preview: reader 1.5.0rc4 · atlas 1.5.0-review5.** Accepted on 29 October 2026; the same scientific records are published as `1.5.0-exploratory` with reader 1.5.0. [Public deployment](DEPLOYMENT-1.5.md). The preview remains separate for future development.

Open **[http://127.0.0.1:8767/](http://127.0.0.1:8767/)**. The lightweight preview uses bundled assets and the private server's read-only database through SSH. The header identifies **Private cloud · SSH**. Network access and the configured `principia-hk` SSH host are required; no database, model or corpus is downloaded. Settings → About this installation identifies software and scientific snapshot separately. Reload an older tab. Old `?preview=...` parameters never selected a different application build.

This Mac starts the preview automatically at login. After this software update, reload an already-open tab once to load its reconnection support.

For a manual installation, double-click `start-cloud.command` in the **Principia-Legacy Preview** folder next to the development folder, or run this from either folder:

```sh
python3 start-cloud.py
```

Python 3.12+ and SSH are sufficient; Node.js and an API key are unnecessary. The cloud package is approximately **3.2 MB**. Existing personal maps remain available at the same browser origin. A disconnected tunnel reconnects automatically, and pending atlas reads resume in the same page. A temporary connection notice preserves your query and current view. The supplied Mac now starts this preview at login and restarts it if the local process exits. You can open the URL directly without starting a terminal. Internet access and a reachable server remain necessary.

Offline review remains available through the previously verified **review3** reader archive, launched with `python3 start.py` (default port 8765). It does not contain review5's new explanations or the server-only semantic index. Keep explicitly downloaded snapshots separate from authoritative server data.

## Search and topic browsing

**Browse the atlas** prioritizes exact terms, curated aliases and spelling corrections. If these return no matches, the private server ranks related entries using a small, locally cached sentence encoder. Suggestions are labelled **Related by meaning**; similarity is not evidence, scientific equivalence, or complete coverage. No provider key or external inference service is involved. Single names and nonsense queries do not automatically acquire neighbours.

Try **neuronal group communication**, **neuronal state space**, and **brain activity as trajectories in a low dimensional space**. Two neuroscience topics now contain checked explanations from three full-text papers. The communication topic has 11 insights and eight warranted relationships, including a separately labelled teaching prerequisite. Its ancestry remains incomplete. Open **What is available in this atlas?** to distinguish explained works and topics from reading-list entries.

Multiword method names receive phrase priority; spelling variants, known singular forms and questions containing an example are handled without a provider call. Semantic suggestions remain approximate. A match is a place to continue reading, not an answer verified against every premise in a question.

Under **Browse all topics**, **Refine by area** is optional. It shows at most eight choices; typing narrows them. Subject, area, coverage and page remain in navigation history and survive reload.

## A short reading journey

1. Choose **Physics**. Discovery suggestions and topic cards now follow that subject.
2. Set **Coverage → Ideas available**, or select **Reading route checked by AI** for the stricter explanatory-route subset. This means machine editorial review, not expert human approval.
3. Open a topic, switch between **Map** and **List**, and select an insight. The inspector starts with its claim and reasoning; related works, other topics, attribution and evidence follow.
4. Select an arrow to inspect its precise meaning and warrant. History, reasoning, evidence, analogy and learning prerequisites remain distinct.
5. Follow a work or scientist, then use the contextual **Back** control. Subject, filters, pagination, display mode, scroll and focus return with you.
6. Search for an idea or a person—for example, a spelling variant of Alan Turing. Results include **topics, works, ideas and people**. Reading-list cards disclose the absence of checked insights before opening. They also link to the original work. Use the inspector’s **Back to results** control to return directly to a search, including on a phone.

Topic lists have their own pages, so every admitted insight remains reachable while graphs keep the 200-node safety bound. Work and person collections also paginate. Try keyboard navigation, the list alternative and a narrow window; inline mathematics uses bundled KaTeX.

## Trace a discovery

Choose **Trace a discovery** in the same input area. Enter a paper, technique or scientific result. In the top-right **Settings**, add your SiliconFlow key and exact model ID. **Load my available models** checks account availability without silently substituting a model. The default is `deepseek-ai/DeepSeek-V4.1-Flash`; a saved selection is respected. Saving a key on this device is optional.

The progress view shows sources, new insights, checks completed and elapsed time. Remaining-time ranges are estimates. **Inspect draft now** opens the emerging map. Pausing preserves the current tab's checkpoint; an unfinished evidence review can be resumed explicitly. A missing link is shown as a gap, not invented to connect the drawing.

Use **Save on this device** or **Download map** to retain a result. The saved-map library reads compact metadata instead of parsing every full map. Unsaved tab checkpoints do not survive reload; a downloaded map preserves its content, not the running session.

The final six-query Flash test completed all six maps in 142–193 seconds. Four met the structural-route check; GPU/CUDA and ChatGPT remained incomplete. Only one met both the first-insight and completion-time targets. Earlier provider failures remain recorded. These are experimental drafts, not a guaranteed reconstruction of scientific ancestry or a human-reviewed account. [Actual acceptance evidence](../reports/acceptance-1.5.md).

## Privacy and reproducibility

Personal exploration ranks public, snapshot-pinned atlas shards in a browser worker. It fetches only bounded record matches; the atlas server does not receive the private research prompt, API key or generated map. The provider and scholarly search services receive the requests sent directly to them. Ordinary **Browse the atlas** queries use the atlas search API.

Maps and optional credentials stay in this browser's local storage. Local ports and the public site have separate storage. Historical topic links remain snapshot-pinned; **What changed** compares public snapshots. Internal development and correction snapshots remain reproducible from the source archive.

[Coverage and remaining work](../BUILD_STATUS.md) · [Personal exploration](PERSONAL_EXPLORATION.md) · [Private staging and restoration](STAGING.md)

## Current completion audit

[28 October coverage and verification report](../reports/coverage-review5-20261028.md): 5,700 insights, 4,211 relationships, 593 explained works out of 1,233 listed, and 49 topics meeting the strict reading-route criteria. The collection remains exploratory; qualified human review is zero. Catalogue size is not completeness. The cloud stores the authoritative corpus, evidence, model, index and receipts; the Mac runs only the thin reader.
