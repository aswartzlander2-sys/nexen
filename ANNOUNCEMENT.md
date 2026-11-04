# Introducing Nexen 3.1.4

Want to run NexChat from your own computer? **Nexen** is a command-line launcher with two ways to get started:

- **Connected mode** hosts the original NexChat interface locally and connects it to the existing NexChat services.
- **Independent mode** serves the original interface with an incomplete local backend. The separate basic local chat is available with `start-isolated --basic-ui`.

The independent original-UI backend is incomplete: its login and home shell work, but servers, chats, DMs, uploads, calls, Nitro, and admin are not implemented. The separate basic interface supports one shared chat and uploads. Accounts, messages, and files are separate in each mode. Connected-mode old iDrive files need a secure signer, and new CloudGate uploads need a secure CloudGate proxy configured by the operator.

## Install Nexen

You'll need **Python 3.9 or newer**. Run the command for your system after the complete package has been pushed to main or a stable GitHub Release has been published.

**Linux**
```sh
curl -fsSL https://raw.githubusercontent.com/aswartzlander2-sys/nexen/main/install.sh -o install.sh && sh install.sh
```

**Windows PowerShell**
```powershell
curl.exe -fsSL https://raw.githubusercontent.com/aswartzlander2-sys/nexen/main/install.ps1 -o install.ps1; if ($LASTEXITCODE -eq 0) { powershell -ExecutionPolicy Bypass -File .\install.ps1 }
```

Reopen your terminal after installation. On Linux, you may need to add `~/.local/bin` to your PATH.

## Start your server

To try the original interface with the incomplete independent backend, run:

```sh
nexen start-isolated
```

For the separate working basic local chat, add `--basic-ui`. The first time, you'll be prompted to choose your Owner username and password. Open **http://localhost:63936** on the host, or `http://<host-LAN-IP>:63936` from another device on the same network.

To block new account creation, stop the server and start it with:

```sh
nexen start-isolated -L
```

A plain `nexen start` always starts connected mode. Use `start-isolated` each time for independent mode. Signups are enabled by default; `-L` disables them for that session only.

```sh
nexen stop
```

Once installed, use `nexen update` for stable updates or `nexen update -B` to check for opt-in beta feature previews. If an update is available, stop Nexen before installing it. The updater keeps your local data and settings.

**Security note:** Nexen currently serves HTTP, not HTTPS, and is not security-audited. Use it on a trusted network or behind a properly configured HTTPS reverse proxy; don't expose it directly to the public internet. See the repository README for data removal commands, backups, security notes, and known limitations.

**Repository:** https://github.com/aswartzlander2-sys/nexen
