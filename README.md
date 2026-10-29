<p align="center">
  <img src="docs/assets/banner.svg" alt="Principia-Legacy — A living atlas of human understanding" width="100%">
</p>

<p align="center">
  <a href="https://atlas.chipflow.net/web/legacy/"><strong>Explore the atlas ↗</strong></a>
  &nbsp; · &nbsp;
  <a href="#run-locally">Run locally</a>
  &nbsp; · &nbsp;
  <a href="docs/README.md">Documentation</a>
  &nbsp; · &nbsp;
  <a href="CONTRIBUTING.md">Contribute</a>
</p>

Every scientific breakthrough has an intellectual history: a way of seeing, a decisive experiment, an approximation that works, an assumption that fails.

**Principia-Legacy makes that history navigable.** Follow a discovery into its foundations, see an idea travel between disciplines, and inspect the reasons connecting one contribution to another.

### Understanding, with its reasons intact

The atlas connects **subjects → topics → works → insights** across mathematics, physics, computer science, economics, and biology & medicine. A work can belong to several topics; an insight can matter to several works. Individually sourced contributor profiles preserve who made those intellectual moves.

| Explore | Understand |
| :--- | :--- |
| **A work and its insights** | What problem was addressed, what changed, and under which assumptions. |
| **A connection** | Why it belongs: historical influence, reasoning, evidence, analogy, or a learning prerequisite. |
| **The evidence** | Source versions, inspectable passages, limitations, and the scope of each review. |
| **A correction** | What changed and what needs rechecking, while earlier snapshots remain reproducible. |

An arrow is a claim with a warrant. Shared topics alone do not establish influence, and an attractive graph does not justify an unsupported connection.

[![Explore the Transformer through its insights and evidenced connections](docs/screenshots/reader-map.png)](https://atlas.chipflow.net/web/legacy/#dossier=C01)

### Two ways to explore

**Browse the atlas.** Search topics, works, ideas, and people together—including spelling variants and related concepts—or choose a discovery in your subject. Open an insight, follow its connections, and examine its sources.

Start with [sphere packing](https://atlas.chipflow.net/web/legacy/#dossier=M06), [quantum memory](https://atlas.chipflow.net/web/legacy/#dossier=P01), [the Transformer](https://atlas.chipflow.net/web/legacy/#dossier=C01), [causal estimation](https://atlas.chipflow.net/web/legacy/#dossier=E01), or [AlphaFold 3](https://atlas.chipflow.net/web/legacy/#dossier=B01).

**Trace a discovery.** Bring a research question of your own. Add your SiliconFlow key and model in **Settings**, then build a personal graph from web passages and atlas insights. Progress and evidence gaps stay visible. These maps are experimental drafts, separate from the published collection.

Your browser contacts the research services directly. Keys can optionally be remembered on your device; generated maps are saved locally only when you choose to save them, or downloaded as JSON. The atlas server receives neither your provider key nor generated maps. [Workflow and privacy →](docs/PERSONAL_EXPLORATION.md)

### Run locally

Clone this repository and run with **Python 3.12+**:

```sh
python3 start.py
```

Open **http://127.0.0.1:8765**. On Windows, use `py -3 start.py`.

The source checkout includes the prebuilt 1.5 interface and the **1.4.1 reference corpus**; it rebuilds a local database on first launch and then works offline. The expanded **1.5 atlas is served from the cloud**, keeping the large database and private authoring evidence out of Git. **No Node.js, API key, GPU, or online installation is needed to browse the bundled corpus.** [Reading guide](docs/USAGE.md) · [Development](docs/DEVELOPMENT.md) · [Hosting](hosting/README.md)

To use the complete published collection, [open the public atlas](https://atlas.chipflow.net/web/legacy/). Operators with authorized SSH access can also run **`python3 start-cloud.py`** for a roughly **3.2 MB** local preview backed by the private staging database. [Preview and data editions →](docs/LOCAL_PREVIEW.md)

### An open, growing inheritance

**1.5 · exploratory release.** This edition deepens existing works, adds foundational explanations, and makes large collections easier to navigate. Indexed pagination and compact browser search keep evidence close without loading every full record. Private remote authoring preserves one canonical dataset; checksummed snapshots make offline review reproducible. The public edition contains **5,700 insights and 4,211 warranted relationships**. Snapshot-pinned semantic retrieval adds related concepts without a paid search service.

Coverage is measured in supported explanations, not catalogue entries. Registered topics, topics with content, and complete reading routes are reported separately. Content is exploratory and machine-screened; **qualified human auditing has not been performed**. [Actual coverage and checks →](BUILD_STATUS.md) · [Remote authoring →](docs/STAGING.md)

Preserving knowledge also means preserving how it became credible—and where it remains unsettled. This project offers a shared, inspectable record for learning, research, and correction. Its longer-term relevance to AI alignment is a research ambition, not an established result.

**Help shape the atlas:** contribute a sourced insight, challenge a connection, or make an explanation clearer. [Join the project →](CONTRIBUTING.md) Watch this repository to follow its development.

---

[MIT](LICENSE) for code · [CC BY 4.0](DATA_LICENSE.md) for original explanations · [Third-party rights](THIRD_PARTY_NOTICES.md) remain separate.
