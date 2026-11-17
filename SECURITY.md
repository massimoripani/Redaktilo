# Security Policy

## Supported versions

Only the latest release of Redaktilo receives security fixes.
Please check that the problem is present in the
[latest release](https://github.com/massimoripani/Redaktilo/releases/latest)
before reporting it.

## Reporting a vulnerability

Please **do not open a public issue** for security problems.

Use GitHub's private reporting instead:

1. Go to the [Security tab](https://github.com/massimoripani/Redaktilo/security) of this repository.
2. Choose **Report a vulnerability**
   (direct link: https://github.com/massimoripani/Redaktilo/security/advisories/new).
3. Describe the problem, the version you tested, your operating system and,
   if possible, the steps or a sample file to reproduce it.

This is a small project maintained by one person, so replies are made on a
best-effort basis. You can expect an acknowledgement within about 7 days. Once a
fix is released, the report can be published and you will be credited, unless
you prefer to stay anonymous.

## Scope

Redaktilo is a local text editor: it makes no network connections of its own
and has no accounts or server component. Reports about the following are in scope:

- code execution or command injection triggered by opening, editing or saving a file;
- crashes or freezes caused by crafted input (for example inefficient regular
  expressions or XML parsing problems);
- unsafe handling of paths, settings files or language packs;
- vulnerabilities in the release packages or in the build workflow.

## Plugins

Plugins (`.py` files in the `kromprogramoj/` folder) are ordinary Python code
and run with the same permissions as the editor. This is by design.
**Only install plugins from sources you trust**, and keep the plugin folder
writable only by you. A malicious plugin that you installed yourself is not
considered a vulnerability in Redaktilo.

## Verifying downloads

Each release includes a `SHA256SUMS.txt` file. Compare the checksum of the
package you downloaded with it before running the program:

- Linux / macOS: `sha256sum -c SHA256SUMS.txt` (macOS: `shasum -a 256 -c SHA256SUMS.txt`)
- Windows (PowerShell): `Get-FileHash .\Redaktilo-<version>-windows.zip -Algorithm SHA256`

The packages are not code-signed, so Windows or macOS may show a warning on the
first launch.

## Automated checks

Every push and pull request runs a Security Audit workflow (Bandit and Ruff
security rules), and the repository is analysed with CodeQL. Dependencies are
monitored with Dependabot.
