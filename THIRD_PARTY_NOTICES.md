# Bundled software

The browser bundle includes React, React DOM, Scheduler, Cytoscape.js, and KaTeX. Their license texts are preserved in docs/licenses/; the Commander license is also retained for KaTeX's optional command-line dependency. KaTeX font assets are bundled locally so mathematical notation renders offline. Build-only tools are not required by the reader. Versions are pinned in web/pnpm-lock.yaml.

Source materials cited by the atlas retain source-specific rights; see DATA_LICENSE.md and individual Source records.

Optional public hosting uses Gunicorn 26.2.0, distributed under the MIT license. Gunicorn is installed separately from the pinned requirement in `hosting/requirements.txt`; it is not bundled with the offline reader.

The expanded foundations collection cites OpenStax books. Acquired publisher metadata identifies CC BY-NC-SA 4.0 for these source versions; the atlas does not relabel those books as CC BY 4.0. Other references include author-hosted papers and university course materials whose rights are recorded individually. Distribution includes independently written explanations, bibliographic metadata, passage locators and hashes, not the downloaded books, papers, illustrations or source caches. Any third-party quotation or adaptation remains subject to its source rights; the project's content license applies only to original project material.
