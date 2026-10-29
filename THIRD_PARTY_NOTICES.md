# Bundled software

The browser bundle includes React, React DOM, Scheduler, Cytoscape.js, and KaTeX. Their license texts are preserved in docs/licenses/; the Commander license is also retained for KaTeX's optional command-line dependency. KaTeX font assets are bundled locally so mathematical notation renders offline. Build-only tools are not required by the reader. Versions are pinned in web/pnpm-lock.yaml.

Source materials cited by the atlas retain source-specific rights; see DATA_LICENSE.md and individual Source records.

Optional public hosting uses Gunicorn 26.2.0, distributed under the MIT license. Gunicorn is installed separately from the pinned requirement in `hosting/requirements.txt`; it is not bundled with the offline reader.

The expanded foundations collection cites OpenStax books. Acquired publisher metadata identifies CC BY-NC-SA 4.0 for these source versions; the atlas does not relabel those books as CC BY 4.0. Other references include author-hosted papers and university course materials whose rights are recorded individually. Distribution includes independently written explanations, bibliographic metadata, passage locators and hashes, not the downloaded books, papers, illustrations or source caches. Any third-party quotation or adaptation remains subject to its source rights; the project's content license applies only to original project material.

## Optional personal explorations

A user-initiated exploration can retrieve short Wikipedia excerpts directly in
the browser. These excerpts remain attributed to Wikipedia contributors under
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/), with a source
revision link. Open-access article excerpts retain their separately recorded
licenses. Exporting a personal map preserves these credits and licenses; the
project's original-content license does not replace them. Retrieved source caches
and personal maps are not distributed as part of the published atlas.

## Representative work and contributor catalogue

The 1.4 catalogue uses bibliographic facts and short project-authored descriptions
with documentary links. Nobel API metadata is made available under CC0; see the
[Nobel data terms](https://www.nobelprize.org/about/terms-of-use-for-api-nobelprize-org-and-data-nobelprize-org/).
Official Nobel motivations retained in evidence notes are attributed to that data.
IMU, Abel Prize, Computer History Museum, MacTutor, university, museum and scholarly
biography pages retain their respective rights. Their full pages and acquisition
caches are not bundled. Links and hashes identify the consulted material; the
project's CC BY license does not relicense source prose or original publications.

## Optional private-server semantic search

FastEmbed (Apache-2.0) and ONNX Runtime (MIT), installed separately, run the
`sentence-transformers/all-MiniLM-L6-v2` encoder (Apache-2.0) from the
[Qdrant ONNX distribution](https://huggingface.co/Qdrant/all-MiniLM-L6-v2-onnx).
The private index records exact model file hashes and dependency version. Neither
these dependencies nor the encoder weights are bundled in the cloud preview or
standard offline reader. Their own licenses remain applicable to separate
installation and redistribution.
