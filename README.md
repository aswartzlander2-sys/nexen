# Nexen 3.1.6

The NexChat Origin v3 SPA is the root interface, including the home, chat, server, and settings views. Legacy page links open the same SPA.

Nexen has two **separate** modes:

* **Connected (default):** serves the original NexChat frontend; it uses the hosted Supabase project and third-party services configured in that frontend. Existing accounts and chats remain on those services. This is not a self-hosted backend.
* **Independent (`start-isolated`):** serves the original UI using a local backend compatibility layer. This is **incomplete**: login and the home shell work, but servers, chats, DMs, uploads, calls and other features do not. Use `start-isolated --basic-ui` for the separate basic local chat. Neither independent interface uses the hosted database.

**Security:** This is an early implementation, not a security-audited production chat server. It serves HTTP, so passwords and messages are not protected against network observers. Use a trusted network or a correctly configured HTTPS reverse proxy, and restrict firewall access. HTTP on a LAN may also limit browser features. Do not expose this server directly to the public internet. A reverse proxy must preserve the original Host header. In the basic independent interface accounts share the same general chat and any signed-in account can download uploaded files. There is no login rate limiting.

## Install

For a downloaded full ZIP, extract it and run `python3 install-local.py` from its extracted directory after stopping Nexen. This replaces the installed app while preserving data and the ID; it does not require a GitHub release or the older updater.


Requires Python 3.9+ and curl (Windows also requires PowerShell). Push the complete package to `main`. The installer chooses the newest stable version from published releases or a numeric version on main, never a B or E build. Review scripts before running them; the bootstrap is downloaded from `main` and the application from the selected release tag or pinned main commit.

Linux:
```sh
curl -fsSL https://raw.githubusercontent.com/aswartzlander2-sys/nexen/main/install.sh -o install.sh && sh install.sh
```
Windows PowerShell:
```powershell
curl.exe -fsSL https://raw.githubusercontent.com/aswartzlander2-sys/nexen/main/install.ps1 -o install.ps1; if ($LASTEXITCODE -eq 0) { powershell -ExecutionPolicy Bypass -File .\install.ps1 }
```
Reopen the terminal if `nexen` is not found. On Linux add `~/.local/bin` to PATH if needed. Alternatively, run `python3 nexen.py ...` (Windows: `python nexen.py ...`) from a checkout.

## Run

The CLI prints brief progress messages for startup, shutdown, updates and removals, including the selected mode, data location, server address and log location. Passwords and session tokens are never printed.

```sh
nexen start                 # always connected mode, using the original NexChat interface
nexen start-isolated    # original interface + incomplete independent backend
nexen start-isolated -L # independent mode, block account creation
nexen stop
```
Open `http://localhost:63936` or `http://<host-LAN-IP>:63936`. The server binds `0.0.0.0`. Only one instance can bind the port. Stop the server before changing settings. A plain `nexen start` always selects connected mode, even after an independent session; to use independent mode again, specify `start-isolated`. Signups are enabled by default on each independent start, even if a previous session used `-L`. Independent data is kept when switching modes. `-L` is enforced by the independent server; it cannot be enforced against the hosted backend and is rejected in connected mode.

On the first `nexen start-isolated`, Nexen prompts for an Owner username and password. It stores the username and a salted password hash in the local database and identifies this account as Owner in the interface; the same Owner is reused on subsequent independent starts, so the prompt does not repeat. The CLI reports when an existing Owner is reused. Run `nexen owner` to see which local account is the Owner. If an older local database has users but no Owner, the earliest existing user is promoted on the next isolated start without changing passwords. To remove **all local users**, including the Owner, stop the server and run `nexen remove usr-list`; the next independent start prompts for a new Owner. This also signs out local users. It does not remove chats or files, and `nexen remove anylist` also clears users. Back up the data directory before removing anything.

When `-L` is active, account creation is refused by the local server, and Sign in fills the whole tab control. The setting applies only to that session; the next ordinary `nexen start-isolated` allows signup.

Independent accounts, chat and uploads live in `~/.nexen` (or the directory specified by `NEXEN_STATE_DIR`); backing up that directory while stopped preserves them. Connected-mode data stays on the original services. Settings and data are not migrated between modes. Linux sets the server process name to `NexChats Nexen`; other OSes may show Python instead.

## Version and installation ID

```sh
nexen version   # Nexen V.3.1.6
nexen id        # six-digit ID, including any leading zeros
```

The first `nexen id` or independent `nexen start-isolated` generates a random ID and stores it in `~/.nexen-identity`, separately from the program and `~/.nexen` data. It survives stopping, normal application removal/reinstallation, updates, and `nexen remove anylist`, provided this identity file is retained. Keep a backup if you need to preserve it through operating-system reinstall, profile deletion or disk replacement. If the file is deleted, a new ID is generated. The ID is not a secret; it is displayed in independent mode to anyone who can access that Nexen UI. Connected mode does not display it. `nexen id` remains available in either mode.

The identifier is per OS user account, not guaranteed to be shared by different users on the same computer. It is randomly chosen from one million possibilities, so two installations can occasionally get the same ID; six digits cannot guarantee global uniqueness. If `NEXEN_IDENTITY_FILE` is set, that path is used instead, and must also be retained.

## Independent NexChat 3 UI (incomplete)

Independent mode serves the requested NexChat 3 login and home pages using local fonts and a new local compatibility adapter:

```sh
nexen stop
nexen start-isolated
```

Sign in with your existing independent-mode account. The login, signup, Owner identification, and original home shell are connected to the local account database. In a browser smoke test the login and home pages made no external requests. `-L` still disables registration at the server. Repeat `start-isolated` when starting an independent session; a plain start uses connected mode.

**This is not a completed local NexChat backend.** The home shell shows empty local server and friend lists; built-in news is still visible. Server creation, actual chat/DMs, profiles/settings, file uploads, calls, admin, Nitro, and realtime are not implemented by this adapter; most interactions on those pages will fail. Do not use this test for real conversations. No existing simple-chat data is deleted, but it is not displayed in the original-UI test. To return to the existing independent chat, stop the server and run:

```sh
nexen start-isolated --basic-ui
```

The independent UI restricts browser resource requests to the local origin and disables WebRTC; it is not a substitute for firewall-level network isolation or a security audit. The server remains plain HTTP. This test does not change connected mode.

## Repair an installation

Run `nexen stop`, then `nexen repair` to reinstall the latest stable version from GitHub while preserving local data, settings and the ID. The server must be stopped. This requires internet access and an existing version of Nexen with the `repair` command; for older installations use the one-time repair script first.

## Updates and preview channels

For an installer-managed installation:

```sh
nexen update       # newest newer stable release or numeric version on main; never B or E
nexen update -B    # newest newer B or E preview release or experimental branch
```

A check may run while Nexen is running. If an update is available, stop Nexen before installing it, then run the update command again. If no matching newer version exists, the CLI prints the corresponding no-updates message. A network or API error is reported as an error instead. Both commands require internet access—even if you use `start-isolated`—and preserve the local data and ID. Beta and experimental versions are opt-in per command; a future stable bug-fix release is available via normal `nexen update`, including to someone running an older beta. The updater does not downgrade a newer installed version.

Stable updates check published stable releases and the numeric version on `main`, choosing the newer. Preview updates (`-B`) check B and E releases and the `experimental` branch when present; they never install a preview without `-B`. Branch downloads are pinned to the commit whose version was checked. Network or malformed-version errors are reported, not treated as “no updates.” A tag or commit must contain the complete application. Older installed versions check releases only: to receive this updater, publish a stable GitHub Release or rerun the installer after pushing this package to main. See `RELEASING.md`.

Stable updates download and run the operating-system installer, which selects a stable release or a pinned main commit and preserves the local data and ID. Preview updates use the staged archive updater and are supported only on installer-managed installations. Downloads are not cryptographically signed. `apt update` and `apt upgrade` cannot update Nexen without a published signed APT repository.

## Connected-mode uploaded wallpapers

Legacy iDrive profile photos and uploaded backgrounds require a working storage signer; otherwise profile photos show an initial instead of a broken image. The previously included browser-side signer exposed secret credentials and was removed. Liquid Glass and background loading are available in Appearance. When no signer is configured, stored uploaded wallpaper keys are left untouched but cannot be loaded; a fallback background is used for Glass. The configured hosted project currently returns 404 for its `nexchat-storage` function; old iDrive images need a signer with access to the existing bucket. New CloudGate uploads additionally need a securely deployed CloudGate proxy and storage-group configuration; exposed default CloudGate credentials were removed. This cannot be fixed by a client-only update.

After deploying and security-reviewing the signer in `supabase/functions/nexchat-storage` with rotated bucket credentials and appropriate bucket CORS, configure its URL (do not enter secret keys here):

```sh
nexen stop
nexen storage-endpoint https://xqzibelnvjlmavgrpyve.supabase.co/functions/v1/nexchat-storage
nexen start
```

The URL is stored outside the application directory and survives `nexen update`. Use `nexen storage-endpoint off` to clear it. Existing wallpapers can load only if the signer can access their original bucket and objects still exist. The upload/sign flow was tested with a mock signer, not the real bucket. URL wallpapers and built-in presets may be used without that signer if accessible from your browser. Never put S3 secrets in this command or browser files.

## Remove independent-mode data

Stop Nexen first. Each command prompts for `YES`; add `--yes` to skip the prompt. These commands only touch independent local data, even if the last session was connected. `anylist` permanently deletes local users (including Owner), sessions, chats, files, and policies. These commands do not touch the hosted database.

```sh
nexen remove usr-list      # removes local users and sessions, including Owner
nexen remove chats         # removes local messages
nexen remove photos        # removes uploaded files identified as images
nexen remove drive-assets  # removes other uploaded files
nexen remove admin-policy  # clears policy entries and local ban flags
nexen remove anylist       # all of the above
```
Removing users requires creating a new Owner on the next independent start. User removal does not by itself remove messages or files. `admin-policy` does not restore NexChat Nitro settings: Nitro is not implemented in the independent backend.

## Connected-mode storage warning

The original repository documentation identifies exposed iDrive credentials in its legacy browser signer. This package removes that signer and its script tags. **Rotate those credentials immediately**, including keys exposed in Git history. Connected-mode uploads and managed attachments will not work until a secure server-side storage signer is configured; see `supabase/README.md` and review its example before deployment. Removing a file from a ZIP does not delete it from an existing Git checkout: explicitly `git rm assets/js/vendor/core/runtime/net/xhr-transport-polyfill.min.js` when applying this package. Git history remains exposed even after deletion.

## Testing and connection troubleshooting

Run `python -m unittest discover -s tests -v` from the repository. Node.js, if installed, is used for an additional embedded JavaScript syntax check. Browser smoke tests covered the basic independent login, chat, upload, reload and logout flows and checked that they made no external requests. The connected login page and hosted authentication endpoint were smoke-tested without a real user account; connected-mode authenticated workflows, the real connected storage signer, Windows installation and all browser/OS combinations have not been verified.

Network outages, firewall rules, unavailable third-party services, and misconfigured storage can still prevent requests from completing; no software can guarantee that fetches never fail. The UI now reports connection errors with guidance. Verify the Nexen process is running and the device can reach port 63936. In connected mode, the browser also needs access to the Supabase project and its CDN. Never expose a database service-role key in the frontend.

### Browser cache on update
Starting with v3.1.6, Nexen sends no-store headers for its UI and requests a browser HTTP-cache flush when the version changes. Open v3.1.6+ tabs check for newer versions and reload when visible; after installing v3.1.6 from an older version, reload the page once. Browsers generally honor Clear-Site-Data only on secure origins (HTTPS or localhost); no-store and versioned URLs also reduce stale assets elsewhere. This does not intentionally clear cookies, localStorage, accounts, or the Nexen ID.
