# Publishing the source on GitHub

This folder is the repository root: upload its **contents**, with `README.md` at the top level. Use Git or GitHub Desktop for the complete tree; a browser-only upload is less convenient for the canonical corpus and generated manifests. Repository ownership and its GitHub URL have intentionally not been guessed.

Suggested repository name: **principia-legacy**

Suggested description:

> A living atlas of human understanding: explore ideas, their evidenced connections, and the reasons behind scientific progress.

Suggested website: **https://atlas.chipflow.net/web/legacy/**

Suggested topics: `knowledge-graph`, `history-of-science`, `open-science`, `scientific-reasoning`, `digital-humanities`, `local-first`.

## Before the first push

- Use the supplied source archive or this reviewed folder. Keep `.gitignore` and `.gitattributes`; do not add `build/`, `.work/`, `dist/`, environments, keys or `hosting.json`.
- Check `git status` and inspect the staged file list. The publication report documents the package and credential-exclusion checks performed for this edition.
- Create the destination repository under the intended account. No remote was created by this preparation.
- Enable private vulnerability reporting before announcing the project. The provided contribution, correction-issue and security guides then have a clear home.
- Keep original content attribution and third-party notices alongside MIT code licensing.

## Reproduce a source archive

The existing release pipeline can package the unchanged frozen data with the current reader:

```sh
python3 start.py release --id 1.2.0-exploratory
python3 scripts/source_archive.py dist/principia-legacy-1.2.0-exploratory.zip
```

The `-source.zip` contains the complete source, canonical corpus, prebuilt offline interface, documentation, tests and per-file checksums. It omits the rebuildable database. The offline ZIP also includes that database. Neither includes credentials or authoring caches. Package verification is an explicit final step; `scripts/verify_release.py` checks an extracted distribution's `CHECKSUMS.json`.

A content correction requires a **new release identifier**; never reuse `1.2.0-exploratory` for changed canonical membership. This publication edition reorganizes source and documentation while preserving the frozen scientific snapshot. Historical manifests and record hashes remain unchanged.

## GitHub releases and repository presentation

Use the README as the landing page and `docs/` for detailed guides. Preserve historical evidence in `reports/`; generated records and assets are marked in `.gitattributes` so repository language statistics better reflect the implementation.

When creating a GitHub release, describe software changes, admitted coverage, machine screening and human review separately. Attach the verified source/offline archives and their SHA-256 files, and link the current limitations. A source cleanup or successful build does not establish broader scientific coverage or completed human review.
