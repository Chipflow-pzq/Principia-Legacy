# Security

The local reader binds to loopback and exposes read-only operations. Optional public hosting uses the separate adapter in `hosting/`; authoring is an explicit local CLI operation and must never be exposed as a web endpoint.

Do not put credentials, private source caches, production configurations or unpublished jobs in an issue or pull request. The reader does not need API credentials.

For a vulnerability, use this repository's **Security → Report a vulnerability** once private vulnerability reporting is enabled. If that option is unavailable, open a minimal issue requesting a private contact channel without exploit details or secrets. See [the publication checklist](docs/PUBLISHING.md) for enabling that channel before announcing a repository.
