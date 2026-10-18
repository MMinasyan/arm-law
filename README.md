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

```sh
git clone https://github.com/MMinasyan/arm-law.git ~/plugins/arm-law
cd ~/plugins/arm-law
python3 -m pip install .
```

Then ask your assistant:

```text
Can an employer dismiss an employee during sick leave under Armenian law?
Cite the provisions and explain any exceptions.
```

The assistant searches ARLIS, reads the saved acts and answers with citations.
The steps between the clone and the question depend on the client; see
[Installation](#installation).

## Usage

- Explain a provision: conditions, definitions, exceptions, consequences.
- Apply the law to facts: qualify each condition, state what must be proved.
- Compare provisions: scope, legal force, collision rules.
- Check a statement or citation against the retrieved text.
- Find Cassation Court or ECtHR decisions on a question.

For the full method, read
[skills/arlis-research/SKILL.md](skills/arlis-research/SKILL.md).

## Installation

### Python dependencies

The MCP server runs on Python 3.11+ and needs the packages from
[pyproject.toml](pyproject.toml) in the environment the client will use:

```sh
python3 -m pip install .
```

[mcp.json](mcp.json) starts the server with `python3 -m arlis`, resolving
`python3` from the client's `PATH`.

### Agent Plugins clients

The repository root is an [Agent Plugins 1.0.0](https://agent-plugins.org/specification)
package: `plugin.json`, `mcp.json`, `skills/`. Load it through your client's
plugin installer. Clients that install through marketplaces need a catalog
entry pointing at this checkout; this repo is the package, not a marketplace.

### ChatGPT desktop app

Register the checkout in a personal marketplace at
`~/.agents/plugins/marketplace.json`:

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

The path is relative to your home directory. Restart the app, open
**Plugins**, install ArmLaw, then start a new local Work or Codex conversation.

### Clients without a plugin loader

Install `skills/arlis-research/` as an Agent Skill, then register a local MCP
server yourself: command `python3`, arguments `-m arlis`, working directory
the repository root.

## Notes

- Search returns the latest versions, newest first by enactment date. Use
  `limit` to set the maximum number of entries (default: 5); duplicates can appear.
- `get_act` returns a file path; the assistant must read the file to use the
  text. Files are saved to `.arlis/` in the plugin directory unless
  `output_dir` is set.
- A cloud-only assistant cannot read saved files through an MCP tunnel; local
  execution is required.
- The server sends queries to ARLIS; tool results and text the assistant reads
  go to the client's model provider.

## Contributing

Open an issue or pull request at
[MMinasyan/arm-law](https://github.com/MMinasyan/arm-law).

## License

[MIT](LICENSE).
