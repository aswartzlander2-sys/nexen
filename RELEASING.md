# Publishing Nexen versions

These files do not publish themselves. The maintainer must push them to GitHub. The installer and updater can use a numeric stable version on main or a stable GitHub Release; older installed updaters need a published release or a one-time reinstall.

## Stable and bug fixes

1. On the stable code you intend to ship, set `VERSION` in `identity.py` to a numeric version such as `3.0.2`. Run the tests. Existing UI version labels read the value dynamically.
2. Push the code and create a matching Git tag, e.g. `git tag v3.0.2` then `git push origin main --tags`.
3. In GitHub, create a **non-prerelease** Release from that tag. Publishing a release also makes it visible to older release-only installers and updaters. Newer installers and updaters can use the numeric version on main without a release. A bug-fix release can be published straight to this channel; it does not have to wait for an E or B build.

## Beta feature previews (B)

When you choose to preview a feature, set `identity.py`'s version to the desired preview version, e.g. `3.1.0B`, create a matching tag `v3.1.0B`, push it, and publish a GitHub Release marked prerelease. Only `nexen update -B` selects B tags. Use a numerically newer version than the installed stable release; the updater will not downgrade.

## Experimental development (E)

Keep the newest development work on a separate `experimental` branch and mark its version with `E`, e.g. `3.1.0E`. E builds are experimental and can be installed only with the explicit `nexen update -B` preview command. This package does not create a remote branch or publish releases on your behalf.

Branch maintenance, merging and GitHub publication are manual. Tags must match `identity.VERSION` exactly (apart from the tag's optional leading `v`); the updater verifies this before replacing installed files. The current updater trusts GitHub HTTPS and release tags; it does not provide signed release verification.

## Main and preview branches
Numeric versions on main are stable update candidates even without a GitHub Release. `nexen update -B` opts into B and E release tags and B/E versions on the experimental branch. Normal update never selects B or E. Branch downloads are pinned to the checked commit. Publish a normal release so older release-only Nexen clients can upgrade.
