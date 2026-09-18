import json
import os
import subprocess
from pathlib import Path

from anthropic import Anthropic

MODEL = "claude-sonnet-5"
MAX_TURNS = 40
COMMAND_TIMEOUT_SECONDS = 180

MIGRATION_PLAYBOOK_PATH = Path(__file__).parent / "MIGRATION.md"

TOOLS = [
    {
        "name": "list_dir",
        "description": "List files and directories at a path. Prefix the path with 'repo:' to list the source Vue project, or 'output:' to list the in-progress React project.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    {
        "name": "read_file",
        "description": "Read a file's contents. Prefix the path with 'repo:' or 'output:'.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Write a file's contents. Path must be prefixed with 'output:' — you may only write inside the output project.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "run_command",
        "description": "Run an npm command (e.g. 'install', 'run build') with cwd set to the output project root. Only npm is permitted.",
        "input_schema": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
    },
]


class ToolError(Exception):
    pass


def _resolve(root: Path, prefixed_path: str, prefix: str) -> Path:
    if not prefixed_path.startswith(prefix):
        raise ToolError(f"Path must start with '{prefix}': {prefixed_path!r}")
    relative = prefixed_path[len(prefix):].lstrip("/")
    resolved = (root / relative).resolve()
    if resolved != root and root not in resolved.parents:
        raise ToolError(f"Path escapes allowed root: {prefixed_path!r}")
    return resolved


class ToolRunner:
    def __init__(self, repo_dir: Path, output_dir: Path):
        self.repo_dir = repo_dir.resolve()
        self.output_dir = output_dir.resolve()
        self.files_written: list[str] = []

    def _resolve_read(self, path: str) -> Path:
        if path.startswith("repo:"):
            return _resolve(self.repo_dir, path, "repo:")
        if path.startswith("output:"):
            return _resolve(self.output_dir, path, "output:")
        raise ToolError(f"Path must be prefixed with 'repo:' or 'output:': {path!r}")

    def list_dir(self, path: str) -> str:
        target = self._resolve_read(path)
        if not target.is_dir():
            raise ToolError(f"Not a directory: {path!r}")
        entries = sorted(
            f"{p.name}/" if p.is_dir() else p.name
            for p in target.iterdir()
            if p.name != "node_modules"
        )
        return "\n".join(entries) if entries else "(empty)"

    def read_file(self, path: str) -> str:
        target = self._resolve_read(path)
        if not target.is_file():
            raise ToolError(f"Not a file: {path!r}")
        return target.read_text(encoding="utf-8")

    def write_file(self, path: str, content: str) -> str:
        target = _resolve(self.output_dir, path, "output:")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        relative = str(target.relative_to(self.output_dir))
        self.files_written.append(relative)
        return f"Wrote {len(content)} bytes to {relative}"

    def run_command(self, command: str) -> str:
        parts = command.strip().split()
        if not parts:
            raise ToolError("Empty command")
        if parts[0] == "npm":
            parts = parts[1:]
        try:
            result = subprocess.run(
                ["npm", *parts],
                cwd=self.output_dir,
                capture_output=True,
                text=True,
                timeout=COMMAND_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            return f"Command timed out after {COMMAND_TIMEOUT_SECONDS}s"

        output = f"exit code: {result.returncode}\nstdout:\n{result.stdout[-4000:]}\nstderr:\n{result.stderr[-4000:]}"
        return output

    def dispatch(self, name: str, tool_input: dict) -> str:
        try:
            if name == "list_dir":
                return self.list_dir(tool_input["path"])
            if name == "read_file":
                return self.read_file(tool_input["path"])
            if name == "write_file":
                return self.write_file(tool_input["path"], tool_input["content"])
            if name == "run_command":
                return self.run_command(tool_input["command"])
            raise ToolError(f"Unknown tool: {name}")
        except ToolError as exc:
            return f"ERROR: {exc}"


def run_migration_agent(repo_dir: Path, output_dir: Path) -> list[dict]:
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    runner = ToolRunner(repo_dir, output_dir)

    system_prompt = MIGRATION_PLAYBOOK_PATH.read_text(encoding="utf-8").format(
        repo_dir=str(runner.repo_dir), output_dir=str(runner.output_dir)
    )

    messages = [
        {
            "role": "user",
            "content": (
                "Begin the migration. The source Vue project is available via "
                "'repo:' paths, and you should write the migrated React project via "
                "'output:' paths. Start by exploring the repo structure."
            ),
        }
    ]

    for _ in range(MAX_TURNS):
        response = client.messages.create(
            model=MODEL,
            max_tokens=8192,
            system=system_prompt,
            tools=TOOLS,
            messages=messages,
        )

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            break

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            result_text = runner.dispatch(block.name, block.input)
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_text,
                }
            )

        messages.append({"role": "user", "content": tool_results})

    return [{"file": path, "status": "written"} for path in runner.files_written]
