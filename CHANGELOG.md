# Nexen 2.1.0

- Plain `nexen start` now always selects connected mode, using the original NexChat interface and hosted services, even if the previous session was independent. Stop any running session before switching.
- `nexen start --no-contact` selects the original NexChat interface with the incomplete local compatibility backend. It does not yet implement chat, servers, DMs, uploads, calls, admin or settings. `--no-contact --basic-ui` selects the previous basic local chat instead.
- The local login-only setting and existing data remain saved; the mode must now be selected explicitly on each start.
- Version displays and `nexen version` now show 2.1.0. The existing six-digit installation ID remains unchanged.

This package is prepared for release; it is not published to GitHub until you push the files. Connected uploads still require the separately configured secure storage signer.
