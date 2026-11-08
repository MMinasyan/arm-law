"""Run with python3 -B test_plugin.py; starts the installed package once."""
import asyncio
import inspect
import json
import os
import re
import shutil
import tempfile
import tomllib
from pathlib import Path

import jsonschema
import yaml
from mcp import ClientSession, StdioServerParameters, stdio_client

from arlis.mcp import mcp

root = Path(__file__).resolve().parent
schema_dir = root / "testdata" / "agent-plugins-1.0"
skill_dir = root / "skills" / "arlis-research"
invalid_url = "անվավեր"
plugin_id = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
mcp_id = "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json"
command = "uvx"
args = ["--python", ">=3.11", "--from", ".", "arlis-mcp"]
copy_entries = (
    "plugin.json", "mcp.json", ".claude-plugin", "pyproject.toml", "README.md",
    "LICENSE",
    "arlis", "skills",
)
private_names = ("PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", "UV_PYTHON")
copy_directory = "arm law plugin — տեղակայում"
moved_directory = "moved law plugin — տեղակայում"
timeout_seconds = 180


def load_schema(name, identifier):
    schema = json.loads((schema_dir / name).read_text(encoding="utf-8"))
    assert schema["$id"] == identifier
    validator = jsonschema.validators.validator_for(schema)
    validator.check_schema(schema)
    return validator(schema), schema


def rejects(validator, manifest):
    try:
        validator.validate(manifest)
    except jsonschema.ValidationError:
        return
    raise AssertionError("a manifest missing a required field passed validation")


def read_frontmatter(text):
    assert text.startswith("---\n")
    return yaml.safe_load(text[4:].split("\n---\n", 1)[0])


def check_frontmatter(data, directory):
    name = data["name"]
    assert name == directory
    assert re.fullmatch(r"[a-z0-9-]{1,64}", name)
    assert not name.startswith("-") and not name.endswith("-")
    assert "--" not in name
    description = data["description"]
    assert isinstance(description, str) and 1 <= len(description) <= 1024
    if "compatibility" in data:
        assert isinstance(data["compatibility"], str)
        assert 1 <= len(data["compatibility"]) <= 500
    if "license" in data:
        assert isinstance(data["license"], str)
    if "allowed-tools" in data:
        assert isinstance(data["allowed-tools"], str)
    if "metadata" in data:
        metadata = data["metadata"]
        assert isinstance(metadata, dict)
        assert all(
            isinstance(key, str) and isinstance(value, str)
            for key, value in metadata.items()
        )


def check_manifests():
    plugin = json.loads((root / "plugin.json").read_text(encoding="utf-8"))
    manifest = json.loads((root / "mcp.json").read_text(encoding="utf-8"))
    plugin_validator, plugin_schema = load_schema("plugin.schema.json", plugin_id)
    mcp_validator, mcp_schema = load_schema("mcp.schema.json", mcp_id)
    assert plugin["$schema"] == plugin_schema["$id"] == plugin_id
    assert manifest["$schema"] == mcp_schema["$id"] == mcp_id
    plugin_validator.validate(plugin)
    mcp_validator.validate(manifest)

    assert plugin["name"] == "arm-law"
    assert plugin["license"] == "MIT"
    assert plugin["extensions"]["com.openai"]["interface"]["displayName"] == "ArmLaw"

    catalog = json.loads(
        (root / ".agents/plugins/marketplace.json").read_text(encoding="utf-8")
    )
    assert catalog["name"] == "arm-law"
    entry, = catalog["plugins"]
    assert entry["name"] == plugin["name"]
    assert entry["source"] == {"source": "local", "path": "./"}
    assert entry["policy"] == {
        "installation": "AVAILABLE", "authentication": "ON_INSTALL",
    }

    scripts = tomllib.loads(
        (root / "pyproject.toml").read_text(encoding="utf-8")
    )["project"].get("scripts", {})
    assert scripts == {"arlis-mcp": "arlis.mcp:mcp.run"}

    # Claude Code adapter: same name and version as the portable manifest and
    # the Python package; the server runs from the installed plugin directory.
    claude = json.loads(
        (root / ".claude-plugin/plugin.json").read_text(encoding="utf-8")
    )
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    assert claude["name"] == plugin["name"]
    assert claude["version"] == plugin["version"] == project["project"]["version"]
    claude_server = claude["mcpServers"]["arlis"]
    assert claude_server["type"] == "stdio"
    assert claude_server["command"] == command
    assert claude_server["args"] == [
        "--python", ">=3.11", "--from", "${CLAUDE_PLUGIN_ROOT}", "arlis-mcp",
    ]
    # Claude Code reads without approval only inside the session's working
    # directory, so acts must stay in the server's default location there.
    assert "env" not in claude_server and "cwd" not in claude_server
    assert not (root / ".mcp.json").exists()
    claude_catalog = json.loads(
        (root / ".claude-plugin/marketplace.json").read_text(encoding="utf-8")
    )
    assert claude_catalog["name"] == plugin["name"]
    claude_entry, = claude_catalog["plugins"]
    assert claude_entry["name"] == plugin["name"]
    assert claude_entry["source"] == "./"
    assert "version" not in claude_entry

    # Claude Code only: a hooks module that approves reads of the skill's
    # bundled references. It sits outside the default hooks/ path and is named
    # only in the Claude manifest, so other hosts do not pick it up.
    # claude plugin test . runs its behaviour tests.
    assert claude["hooks"] == "./claude-code/hooks.json"
    claude_hooks = json.loads(
        (root / "claude-code/hooks.json").read_text(encoding="utf-8")
    )
    assert claude_hooks["modules"] == ["./allow-references.ts"]
    assert "hooks" not in claude_hooks
    assert (root / "claude-code/allow-references.ts").is_file()
    assert (root / "claude-code/allow-references.test.ts").is_file()
    assert "hooks" not in plugin
    assert not (root / "hooks").exists()

    server = manifest["mcpServers"]["arlis"]
    assert server["type"] == "stdio"
    assert server["command"] == command
    assert server["args"] == args
    assert "cwd" not in server and "env" not in server

    # Missing required manifest fields must fail validation before any launch.
    without_name = dict(plugin)
    del without_name["name"]
    without_schema = dict(manifest)
    del without_schema["$schema"]
    rejects(plugin_validator, without_name)
    rejects(mcp_validator, without_schema)


def dump_tools(tools):
    dumps = []
    for tool in tools:
        data = tool.model_dump(mode="json", by_alias=True, exclude_none=True)
        data["description"] = inspect.cleandoc(data["description"])
        dumps.append(data)
    return dumps


def copy_sources(destination):
    destination.mkdir()
    for entry in copy_entries:
        source = root / entry
        if source.is_dir():
            shutil.copytree(
                source, destination / entry,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
        else:
            shutil.copy2(source, destination / entry)


def set_mode(path, directory_mode, file_mode):
    for entry in path.rglob("*"):
        try:
            os.chmod(entry, directory_mode if entry.is_dir() else file_mode)
        except OSError:
            pass
    try:
        os.chmod(path, directory_mode)
    except OSError:
        pass


def snapshot(path):
    return {
        str(entry.relative_to(path)): entry.read_bytes()
        for entry in path.rglob("*")
        if entry.is_file()
    }


async def probe(copy_root, env, oracle, order, session_dir=None):
    manifest_file = ".claude-plugin/plugin.json" if session_dir else "mcp.json"
    manifest = json.loads((copy_root / manifest_file).read_text(encoding="utf-8"))
    server = manifest["mcpServers"]["arlis"]
    parameters = StdioServerParameters(
        command=server["command"],
        args=[
            arg.replace("${CLAUDE_PLUGIN_ROOT}", str(copy_root))
            for arg in server["args"]
        ],
        env=env,
        cwd=str(session_dir or copy_root),
    )
    async with stdio_client(parameters) as (read, write):
        async with ClientSession(read, write) as session:
            async with asyncio.timeout(timeout_seconds):
                await session.initialize()
                tools = dump_tools((await session.list_tools()).tools)
                assert tools == oracle
                assert [
                    list(tool["inputSchema"]["properties"]) for tool in tools
                ] == order
                result = await session.call_tool("get_act", {"url": invalid_url})
                assert result.is_error
                text = "\n".join(
                    getattr(block, "text", "") for block in result.content
                )
                assert invalid_url in text


async def check_launch():
    oracle = dump_tools(await mcp.list_tools())
    order = [list(tool["inputSchema"]["properties"]) for tool in oracle]

    with tempfile.TemporaryDirectory() as temp_dir:
        base = Path(temp_dir).resolve()
        copy_root = base / copy_directory
        copy_sources(copy_root)
        cache, python_dir, tools_dir, data_dir = (
            base / "uv-cache", base / "uv-python", base / "uv-tools", base / "data",
        )
        for directory in (cache, python_dir, tools_dir, data_dir):
            directory.mkdir()
        env = dict(os.environ)
        for name in private_names:
            env.pop(name, None)
        env.update(
            UV_CACHE_DIR=str(cache),
            UV_PYTHON_INSTALL_DIR=str(python_dir),
            UV_TOOL_DIR=str(tools_dir),
            UV_PYTHON_PREFERENCE="only-managed",
            PLUGIN_ROOT=str(copy_root),
            PLUGIN_DATA=str(data_dir),
        )
        before = snapshot(copy_root)
        assert before
        moved_root = None
        try:
            set_mode(copy_root, 0o555, 0o444)
            await probe(copy_root, env, oracle, order)
            assert snapshot(copy_root) == before
            interpreters = [
                entry for entry in python_dir.rglob("*")
                if entry.is_file()
                and entry.name in ("python", "python3", "python.exe")
            ]
            assert interpreters, "uv installed no managed interpreter"
            moved_root = base / moved_directory
            set_mode(copy_root, 0o755, 0o644)
            copy_root.rename(moved_root)
            assert not copy_root.exists()
            set_mode(moved_root, 0o555, 0o444)
            env["PLUGIN_ROOT"] = str(moved_root)
            await probe(moved_root, env, oracle, order)
            assert snapshot(moved_root) == before

            # Claude Code starts the server from the user's session folder.
            session_dir = base / "session"
            session_dir.mkdir()
            claude_env = {
                name: value for name, value in env.items()
                if name not in ("PLUGIN_ROOT", "PLUGIN_DATA")
            }
            await probe(moved_root, claude_env, oracle, order, session_dir)
            assert snapshot(moved_root) == before
        finally:
            for path in (copy_root, moved_root):
                if path is not None and path.exists():
                    set_mode(path, 0o755, 0o644)


def check():
    check_manifests()

    frontmatter = read_frontmatter(
        (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    )
    check_frontmatter(frontmatter, skill_dir.name)
    # Every host reads this file. allowed-tools is experimental in the Agent
    # Skills spec and its values are host-specific, so it does not belong here.
    assert "allowed-tools" not in frontmatter
    try:
        check_frontmatter(dict(frontmatter, description=""), skill_dir.name)
    except AssertionError:
        pass
    else:
        raise AssertionError("accepted an empty skill description")

    asyncio.run(check_launch())
    print(
        "PASS: canonical manifests and cached schemas, skill frontmatter, "
        "cold source launch, moved-copy startup and Claude Code launch"
    )


if __name__ == "__main__":
    check()
