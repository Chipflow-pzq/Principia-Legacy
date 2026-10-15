# Trust boundaries

The reader is a local, read-only application bound to 127.0.0.1. It makes no outbound requests. Explicit source links open separately and need an Internet connection. The service rejects write verbs, unrecognized Host headers, arbitrary file paths, and unsupported API routes. It is not an Internet-facing hosting server.

Documents, imported patches, and model outputs are untrusted data. Acquisition uses an explicit HTTPS hostname allowlist, checks resolved addresses and redirects, and caps downloads and cache size. Source-supplied code is never executed. Normal scientific discussion is retained; operational harmful instructions and patient-level information are outside the corpus scope.

Credentials are loaded only by explicit authoring commands, never by the browser or reader. Do not store secrets in corpus records, patches, prompts, or the repository. API receipts contain model/request identities, hashes, usage, and redacted failure categories. Timeouts can incur charges. Spending oversight remains with the owner.

An evidence brief is not an authorization token. It always declares read_only. Policy profiles must be human supplied; no scientific finding grants permission to spend, contact others, change credentials, approve records, or perform real-world actions.

Report security issues privately to the repository maintainer once a public repository has been designated. Do not include credentials in reports.
