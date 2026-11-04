# Introducing Nexen 1.0.0

Want to run NexChat from your own computer? **Nexen** is a command-line launcher with two ways to get started:

- **Connected mode** hosts the original NexChat interface locally and connects it to the existing NexChat services.
- **Independent mode** runs a separate local chat backend on your hardware. Create an Owner account, invite people on your network, send messages, and upload files without connecting to NexChat's hosted database.

Independent mode is an early version: it has a simplified interface and one shared chat. It does **not yet** include the original NexChat UI, servers, DMs, calls, Nitro, or the full admin system. Accounts, messages, and files are separate in each mode. Connected-mode file uploads need a secure storage signer configured by the operator.

## Install Nexen

You'll need **Python 3.9 or newer**. Run the command for your system after the Nexen files have been published to the `main` branch of the GitHub repository.

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

For an independent local chat, run:

```sh
nexen start --no-contact
```

The first time, you'll be prompted to choose your Owner username and password. Open **http://localhost:63936** on the host, or `http://<host-LAN-IP>:63936` from another device on the same network.

To block new account creation, stop the server and start it with:

```sh
nexen start --no-contact -L
```

Nexen remembers your mode and login-only setting, so after stopping it you can use `nexen start` to restart with the same settings. To allow signups again, use `nexen start --allow-signup` while stopped. To return to connected mode, use `nexen start --connected --allow-signup` while stopped.

```sh
nexen stop
```

Once installed, run `nexen update` while Nexen is stopped to fetch the latest version from GitHub. The updater keeps your local data and settings.

**Security note:** Nexen currently serves HTTP, not HTTPS, and is not security-audited. Use it on a trusted network or behind a properly configured HTTPS reverse proxy; don't expose it directly to the public internet. See the repository README for data removal commands, backups, security notes, and known limitations.

**Repository:** https://github.com/aswartzlander2-sys/nexen
