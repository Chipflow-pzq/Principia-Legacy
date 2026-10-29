# Publishing the source on GitHub

This folder is the repository root: upload its **contents**, with `README.md` at the top level. Use Git or GitHub Desktop for the complete tree; a browser-only upload is less convenient for the canonical corpus and generated manifests. The intended repository is [Chipflow-pzq/Principia-Legacy](https://github.com/Chipflow-pzq/Principia-Legacy). Preparing a local candidate does not publish it.

Repository name: **Principia-Legacy**

Suggested description:

> A living atlas of human understanding: explore ideas, their evidenced connections, and the reasons behind scientific progress.

Suggested website: **https://atlas.chipflow.net/web/legacy/**

Suggested topics: `knowledge-graph`, `history-of-science`, `open-science`, `scientific-reasoning`, `digital-humanities`, `local-first`.

## Before a release push

- Use the supplied source archive or this reviewed folder. Keep `.gitignore` and `.gitattributes`; do not add `build/`, `.work/`, `dist/`, environments, keys or `hosting.json`.
- Check `git status` and inspect the staged file list. The publication report documents the package and credential-exclusion checks performed for this edition.
- Verify the existing remote and intended branch. Publish a dedicated `codex/` branch and open a pull request against `main`; leave merging to the maintainer.
- Enable private vulnerability reporting before announcing the project. The provided contribution, correction-issue and security guides then have a clear home.
- Keep original content attribution and third-party notices alongside MIT code licensing.

## Reproduce a source archive

The release pipeline provides separate reader and source packages. Use the accepted frozen snapshot ID; never reuse an older ID for changed data.

```sh
python3 start.py release --id RELEASE_ID --kind reader
python3 start.py release --id RELEASE_ID --kind source
```

The **reader** archive contains prebuilt assets, the compiled database, canonical record versions and all public release manifests. Internal `before-*` correction checkpoints and unselected numbered `-qaN`/`-reviewN` development snapshots remain in the **source** archive and authoritative server data home. The selected review snapshot is always included in the reader. Other internal snapshots can be explicitly rebuilt from the source archive; they are not silently discarded. The source archive includes these checkpoints, tests and authoring code, and omits the rebuildable database. This separation keeps routine installations smaller without deleting historical evidence.

Neither package includes credentials, personal maps or private authoring caches. Verify a clean extraction with `scripts/verify_release.py`, then launch it offline. Record compressed and installed sizes, the archive SHA-256, tested platforms and any failed checks in the dated acceptance report.

**1.5 was accepted for public deployment and a GitHub PR on 29 October 2026.** The maintainer will merge the PR manually. The publication branch starts from GitHub `main` and carries the net software changes, preserving the accepted development branch and its unpublished data separately. It retains the 1.4.1 reference corpus; the full 1.5 canonical dataset, derived database/model and private evidence stay on the server. See [deployment provenance](DEPLOYMENT-1.5.md).

## GitHub releases and repository presentation

Use the README as the landing page and `docs/` for detailed guides. Preserve historical evidence in `reports/`; generated records and assets are marked in `.gitattributes` so repository language statistics better reflect the implementation.

When creating a GitHub release, describe software changes, admitted coverage, machine screening and human review separately. Attach the verified source/offline archives and their SHA-256 files, and link the current limitations. A source cleanup or successful build does not establish broader scientific coverage or completed human review.

Earlier 1.5 review archives are dated artifacts, not the public release source. Their checksums continue to describe those exact files. Build full scientific archives from the authoritative server data home; a Git checkout alone intentionally contains only the smaller reference corpus. Never relabel an old review archive as the current public snapshot.
