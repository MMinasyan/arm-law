# ArmLaw

> Legal research on Armenian law for AI assistants, powered by ARLIS.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Agent Plugins 1.0.0](https://img.shields.io/badge/Agent_Plugins-1.0.0-purple.svg)](https://agent-plugins.org)

ArmLaw combines a research skill for Armenian law with tools for searching
[ARLIS](https://www.arlis.am/) and retrieving documents.

## Features

- `search_acts`: find ARLIS acts by title or content, filter by status and
  enactment date.
- `get_act`: download any ARLIS act, save it as Markdown with metadata and
  cross-links.
- `arlis-research` skill: instructions covering act hierarchy, statutory
  authorisation, interpretation of provisions, collisions, temporal
  applicability, court decisions and application to facts.
- Bundled text of the Law on Regulatory Legal Acts, in Armenian and English.

## Quickstart

Install `https://github.com/MMinasyan/arm-law` with your assistant's
Agent Plugins 1.0 installer. The repository root is the plugin.
See [Installation](#installation) for prerequisites and examples.

Then ask your assistant:

```text
Can an employer dismiss an employee during sick leave under Armenian law?
Cite the provisions and explain any exceptions.
```

The assistant searches ARLIS, reads the saved acts and answers with citations.

## Usage

- Explain a provision: conditions, definitions, exceptions, consequences.
- Apply the law to facts: qualify each condition, state what must be proved.
- Compare provisions: scope, legal force, collision rules.
- Check a statement or citation against the retrieved text.
- Find Cassation Court or ECtHR decisions on a question.

For the full method, read
[skills/arlis-research/SKILL.md](skills/arlis-research/SKILL.md).

## Installation

ArmLaw is an Agent Plugins 1.0 package. Install this repository through your
assistant's normal plugin installer, or supply an unchanged checkout if its
installer accepts a directory. No public marketplace listing is needed.

### Runtime prerequisite

The environment running the MCP server needs `uvx`, which ships with uv.
The installing agent sets this up when missing; you do not need to prepare
Python, install Python packages or create a virtual environment yourself.
uv obtains Python 3.11+ and the declared dependencies on first server start.

Official uv installer for macOS/Linux:

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Official uv installer from PowerShell on Windows:

```powershell
irm https://astral.sh/uv/install.ps1 | iex
```

Use the installer in the environment where the assistant runs local MCP
servers, which may differ from the computer displaying its interface.
Restart the assistant, then check `uvx --version` in its MCP execution
environment and confirm the actual assistant can start ArmLaw. Restarting
does not itself guarantee that a GUI backend reads shell-profile changes.
A shell-only check is not completion.

If that backend still reports `uvx` missing, use its documented diagnostics
or execution-environment settings to obtain its actual executable-search
directories. Select an existing, trusted OS installation directory that the
backend already searches; do not guess from an unrelated terminal's PATH.
Install uv there using Astral's supported `UV_INSTALL_DIR` option. The
variables below hold that verified directory, not a new Python environment.

POSIX (`UV_BIN_DIR` is the selected directory):

```sh
curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR="$UV_BIN_DIR" UV_NO_MODIFY_PATH=1 sh
```

PowerShell (`$uvBinDir` is the selected directory):

```powershell
$oldInstallDir = $env:UV_INSTALL_DIR
$oldNoModifyPath = $env:UV_NO_MODIFY_PATH
try {
    $env:UV_INSTALL_DIR = $uvBinDir
    $env:UV_NO_MODIFY_PATH = "1"
    irm https://astral.sh/uv/install.ps1 | iex
} finally {
    $env:UV_INSTALL_DIR = $oldInstallDir
    $env:UV_NO_MODIFY_PATH = $oldNoModifyPath
}
```

For example, `/usr/local/bin` is suitable only if this backend searches it.
Use the OS's normal installation approval for the selected directory. The uv
installer replaces existing uv binaries there, so inspect an existing
installation before replacing it. Restart and verify actual backend loading
again. This changes the standard tool's installation location, not ArmLaw's
MCP profile; do not add an alias, wrapper or absolute-command override. If no
normal installation/search configuration makes the runner reachable, leave
the installation incomplete rather than claim success.

### Example: Hermes Agent

With uvx available to the Hermes backend, install and enable the unlisted
GitHub repository with Hermes's own command:

```sh
hermes plugins install MMinasyan/arm-law --enable
```

Restart Hermes, then check:

```sh
hermes plugins list
```

Confirm `arm-law` is enabled and ask the assistant to use its ARLIS tools.
This is Hermes's plugin-install command; ArmLaw does not provide a separate
installer. Hermes's private package-manager uv is not a substitute for an
accessible `uvx` command in the MCP backend.

### Example: ChatGPT desktop app, local Work

Use a local checkout:

```sh
git clone https://github.com/MMinasyan/arm-law.git "$HOME/plugins/arm-law"
```

If that directory already exists, inspect and reuse/update it instead of
overwriting a modified checkout.

ChatGPT discovers local plugins through a personal registration file named
`~/.agents/plugins/marketplace.json`. This local file does not publish ArmLaw
to a marketplace. For a new file, use:

```json
{
  "name": "arm-law-local",
  "interface": { "displayName": "Local ArmLaw" },
  "plugins": [
    {
      "name": "arm-law",
      "source": { "source": "local", "path": "./plugins/arm-law" },
      "policy": { "installation": "AVAILABLE", "authentication": "ON_INSTALL" },
      "category": "Productivity"
    }
  ]
}
```

If the file already exists, retain its catalog name and unrelated entries;
add or update only the ArmLaw entry in `plugins`. The local source path above
is relative to your home directory.

Restart ChatGPT. Open the Plugins Directory, choose **Local ArmLaw** (or your
existing personal catalog), open ArmLaw and install it. Start a new local
Work conversation and ask the assistant to use its ARLIS tools.

These are examples of existing assistant installers, not an app support list.
Other Agent Plugins 1.0 applications load the same package through their own
normal installation mechanism. The package has no editor-specific integration.

### First start and verification

The first start may take longer while uv downloads Python and dependencies.
If the assistant's normal MCP startup allowance is too short, the installing
agent can warm the declared server command from a local checkout, then retry
normal plugin loading. Reuse the checkout above, or obtain one with that same
clone command. From a POSIX shell:

```sh
cd "$HOME/plugins/arm-law"
uvx --python ">=3.11" --from . arlis-mcp </dev/null
```

From PowerShell:

```powershell
Set-Location "$HOME/plugins/arm-law"
$null | uvx --python ">=3.11" --from . arlis-mcp
```

Closed stdin lets the server exit after standard environment setup. This
warms uv's caches; it does not install the plugin into the assistant. Do not
change `mcp.json` to an absolute executable path or a hand-built environment.

Confirm the research skill and the ARLIS tools are available in the assistant.
Ask it to search ARLIS, retrieve one result and read the saved Markdown file.
Report unsupported or disabled components separately from a fully working
research workflow.

`uvx --python ">=3.11" --from . arlis-mcp` is the MCP server-start command,
not a universal command for installing a plugin into an assistant.

## Notes

- Search returns the latest versions, newest first by enactment date. Use
  `limit` to set the maximum number of entries (default: 5); duplicates can appear.
- `get_act` returns a file path; the assistant must read the file to use the
  text. Files are saved to .arlis under the host's PLUGIN_DATA directory,
  or under the server working directory when PLUGIN_DATA is unset or empty,
  unless output_dir is set.
- A cloud-only assistant cannot read saved files through an MCP tunnel; local
  execution is required.
- The server sends queries to ARLIS; tool results and text the assistant reads
  go to the client's model provider.

## Development

From a writable checkout, run the checks without creating a project environment:

```sh
uv run --no-project --python ">=3.11" --with ".[verify]" python -B test_search.py
uv run --no-project --python ">=3.11" --with ".[verify]" python -B test_act.py
uv run --no-project --python ">=3.11" --with ".[verify]" python -B test_plugin.py
```

Build a Python wheel from the repository with:

```sh
uv build --wheel
```

The wheel goes into `dist/`. It is a Python-package artifact, not a separate
self-contained plugin bundle; the repository directory remains the plugin.

## Contributing

Open an issue or pull request at
[MMinasyan/arm-law](https://github.com/MMinasyan/arm-law).

## License

[MIT](LICENSE).
