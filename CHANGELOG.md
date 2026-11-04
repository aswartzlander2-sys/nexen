# Nexen 3.0.1

- Restore Liquid Glass and loading saved uploaded backgrounds through the configured storage signer. Glass uses a built-in fallback when the signer is unavailable.
- Keep the exposed legacy client-side credentials removed; hosted storage still requires a secure signer or CloudGate proxy. The independent backend remains incomplete.

# Nexen 3.0.0

- Updated the interface to the NexChat 3 origin SPA, with Nexen version and local-only ID on the login and settings footers.
- Preserved local Owner setup, login-only behavior and release channels.
- Liquid Glass is disabled; a saved signed wallpaper is not loaded without a configured signer.
- Independent mode still has an incomplete backend; the version number is not a claim that local chat or server features work.
- Removed credential-bearing upstream storage defaults and the legacy signer. A secure CloudGate proxy is needed for new hosted uploads.

# Nexen 2.1.3

- Clarify that the local Owner credentials are kept until the user list is cleared.
- In independent login-only mode, the Sign in tab fills the entire segmented pill.

# Nexen 2.1.2

- Version updated to 2.1.2. The full release package includes the original NexChat CSS, JavaScript, and other UI assets.

# Nexen 2.1.1

- Show the six-digit ID only in independent mode; retain it across updates and make it available via `nexen id`.
- Use Classic appearance and remove the Liquid Glass choice, including for profiles that previously selected glass.
- Avoid attempting to load or repeatedly retry an uploaded wallpaper when no storage signer is configured. Existing wallpaper settings remain saved. A working signer and original bucket access are still needed for cloud wallpaper uploads and downloads.
- Fix catch-up without a message watermark to fetch the newest messages, preserve older-history navigation and avoid writing messages on open.
- Select stable GitHub Releases for normal updates and opt-in B preview Releases for `nexen update -B`; E development builds are not automatically installed. See `RELEASING.md`.
- Close local SQLite connections after requests.

The original-UI independent backend is still incomplete. Connected-mode file storage remains unavailable until a safe signer is deployed and configured. This package has not been published to GitHub.
