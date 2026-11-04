# Publishing Nexen versions

These files do not publish themselves. The maintainer must push them and create GitHub Releases. Installers and the updater select **published GitHub Releases**, not whatever happens to be on the development branch. The public repository had no releases when this package was prepared.

## Stable and bug fixes

1. On the stable code you intend to ship, set `VERSION` in `identity.py` to a numeric version such as `2.1.1`. Run the tests. Existing UI version labels read the value dynamically.
2. Push the code and create a matching Git tag, e.g. `git tag v2.1.1` then `git push origin main --tags`.
3. In GitHub, create a **non-prerelease** Release from that tag. Only then do normal installers and `nexen update` see it. A bug-fix release can be published straight to this channel; it does not have to wait for an E or B build.

## Beta feature previews (B)

When you choose to preview a feature, set `identity.py`'s version to the desired preview version, e.g. `2.2.0B`, create a matching tag `v2.2.0B`, push it, and publish a GitHub Release marked prerelease. Only `nexen update -B` selects B tags. Use a numerically newer version than the installed stable release; the updater will not downgrade.

## Experimental development (E)

Keep the newest development work on a separate `experimental` branch and mark its version with `E`, e.g. `2.2.0E`. E builds are for direct development/testing and are excluded from both automatic update commands. This package does not create a remote branch or publish releases on your behalf.

Branch maintenance, merging and GitHub publication are manual. Tags must match `identity.VERSION` exactly (apart from the tag's optional leading `v`); the updater verifies this before replacing installed files. The current updater trusts GitHub HTTPS and release tags; it does not provide signed release verification.
