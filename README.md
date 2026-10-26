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

See [Installation](#installation) for setup commands.

Example question:

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

Use the host's Agent Plugins 1.0 installer with this repository or an
unchanged checkout. The repository root is the plugin.

### Runtime prerequisite

The MCP backend needs `uvx`, which ships with
[uv](https://docs.astral.sh/uv/getting-started/installation/). uv installs
Python 3.11+ and dependencies on first start.

macOS/Linux:

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Windows PowerShell:

```powershell
irm https://astral.sh/uv/install.ps1 | iex
```

Check `uvx --version` in the environment that launches MCP servers. A
desktop app may not inherit the terminal's PATH. If it cannot find `uvx`,
install uv into a trusted directory already on the backend's PATH using
[`UV_INSTALL_DIR`](https://docs.astral.sh/uv/reference/installer/).

POSIX, with `UV_BIN_DIR` set to that directory:

```sh
curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR="$UV_BIN_DIR" UV_NO_MODIFY_PATH=1 sh
```

PowerShell, with `$uvBinDir` set to that directory:

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

The installer replaces existing uv binaries in the target directory; inspect
an existing installation first. Keep `mcp.json` unchanged and retry startup.

### ChatGPT desktop

Request write access to the Codex data directory (`CODEX_HOME`, default
`~/.codex`), not individual files such as `config.toml`.

```sh
codex --enable plugins plugin marketplace add MMinasyan/arm-law
codex --enable plugins plugin add arm-law@arm-law --json
codex --enable plugins plugin list --marketplace arm-law --json
```

For a branch or tag, add `--ref <ref>` to the first command. The feature flag
applies only to these commands; plugin support must also be enabled in the host.
Check that the result lists `arm-law@arm-law` as installed and enabled.

### Hermes Agent

```sh
hermes plugins install MMinasyan/arm-law --enable
hermes plugins list
```

Restart Hermes if needed to activate the newly enabled plugin, then verify
its tools.

### First start

If the host times out while uv downloads Python and dependencies, warm the
cache from a checkout in a writable directory, then retry plugin loading.

POSIX:

```sh
git clone https://github.com/MMinasyan/arm-law.git arm-law-warmup
cd arm-law-warmup
uvx --python ">=3.11" --from . arlis-mcp </dev/null
```

PowerShell:

```powershell
git clone https://github.com/MMinasyan/arm-law.git arm-law-warmup
Set-Location arm-law-warmup
$null | uvx --python ">=3.11" --from . arlis-mcp
```

Reuse an existing checkout when available. Closed stdin lets the server exit
after environment setup. This warms the cache; it does not install the plugin.

### Verification

Confirm the `arlis-research` skill and both tools are available. Search with
`search_acts`, retrieve a result with `get_act`, and read the saved Markdown.

## Notes

- Search returns the latest versions in ARLIS's default order. Use
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
