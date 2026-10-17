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

Download the source, extract it, and run with **Python 3.12+**:

```sh
python3 start.py
```

Open **http://127.0.0.1:8765**. On Windows, use `py -3 start.py`.

Reading works offline: prebuilt assets are included, and the search database rebuilds on first launch. **No Node.js, API key, GPU, or online installation is needed to browse.** [Reading guide](docs/USAGE.md) · [Development](docs/DEVELOPMENT.md) · [Hosting](hosting/README.md)

### An open, growing inheritance

**1.4.1 · exploratory atlas:** 882 catalogued works · 899 selected contributors · 2,905 insights · 1,941 checked relationships. Of 781 registered topics, 184 have populated maps; 620 works still await insight extraction. Content is machine-screened, coverage is incomplete, and qualified human auditing remains outstanding. [Evidence and limitations →](docs/STATUS.md)

Preserving knowledge also means preserving how it became credible—and where it remains unsettled. This project offers a shared, inspectable record for learning, research, and correction. Its longer-term relevance to AI alignment is a research ambition, not an established result.

**Help shape the atlas:** contribute a sourced insight, challenge a connection, or make an explanation clearer. [Join the project →](CONTRIBUTING.md) Watch this repository to follow its development.

---

[MIT](LICENSE) for code · [CC BY 4.0](DATA_LICENSE.md) for original explanations · [Third-party rights](THIRD_PARTY_NOTICES.md) remain separate.
