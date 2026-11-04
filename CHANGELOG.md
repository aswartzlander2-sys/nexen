# Nexen 3.1.7

- Added persistent Owner permission switches in isolated mode. The isolated admin backend remains incomplete; switches do not implement missing admin operations.

# Nexen 3.1.6

- Flush browser HTTP cache when the app version changes, prevent stale cached assets and reload open tabs after a newer server starts. Cookies, browser storage, local accounts and the Nexen ID are not cleared.
- Show loaded avatar pictures as backgrounds so an invisible image loader cannot draw a broken-image icon over the picture.

# Nexen 3.1.5

- Restore the Owner role to the oldest existing local user if a legacy database contains users but no Owner; retain existing Owners unchanged. `nexen owner` displays the saved local Owner.
- Allow `nexen remove anylist` and other local removal commands when stopped, regardless of the last selected mode. `anylist` warns that it deletes local users, chats, files, and policies.
- Keep `start-isolated` as the primary command; the old `--no-contact` spelling remains a hidden compatibility alias.

# Nexen 3.1.4

- Hide avatar decorations until their image successfully loads, and hide them after an error, avoiding broken-image icons on top of working photos.

# Nexen 3.1.3

- Show the isolated first Owner as Owner rather than Admin.
- Fix broken avatar decoration overlays and restore the available avatar frame assets.
- When a stable update is available, `nexen update` runs the operating-system installer to reinstall the application while preserving local data and ID.

# Nexen 3.1.2

- Show an initial instead of a broken image when a profile picture cannot load; available pictures still load normally. Old private iDrive photos require a working secure signer.
- Include a local installer for the downloaded full package to recover from older installed updaters.

# Nexen 3.1.1

- Add `nexen start-isolated` for independent mode; `nexen start` remains connected.
- Allow local account creation by default, even if a previous session used `-L`; `-L` disables signup for that session only. The old `start --no-contact` spelling remains compatible.
- Add `nexen repair` to reinstall the latest stable version without removing local data or the ID. Stop the server first.

# Next release (unpublished)

- Add `nexen repair` to reinstall the latest stable application without removing local data, settings, or the installation ID. Stop the server first.

# Nexen 3.1.0

- Make the NexChat Origin SPA the canonical root UI for the whole application, including settings and legacy page URLs.
- Preserve the Nexen footer, Glass, background loading, safe storage handling, Owner setup, and updater channels.
- Independent mode still uses an incomplete local backend.

# Nexen 3.0.3

- Old page URLs such as `/profile.html` now open the NexChat 3 SPA at their corresponding routes instead of returning 404.
- A previous install must be stopped and updated or reinstalled to replace its running old UI server.

# Nexen 3.0.2

- Serve the NexChat 3 Origin SPA at the launcher root; the repository root now opens that UI rather than the older sign-in page.
- Stable update checks both numeric versions on main and stable releases; opt-in `-B` checks B/E preview releases and the experimental branch. Branch archives are pinned to the checked commit and errors do not claim there is no update.
- Older installed updaters still require a published release, or a one-time reinstall using the updated installer. Independent mode remains incomplete.

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
