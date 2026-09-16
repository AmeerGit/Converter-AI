import os
import re
from pathlib import Path

from anthropic import Anthropic

MODEL = "claude-sonnet-5"

SYSTEM_PROMPT = (
    "You are an expert frontend engineer migrating a Vue 3 single-file component "
    "to a React functional component written in TypeScript (.tsx).\n"
    "Rules:\n"
    "- Preserve the original behavior, props, state, and styling as closely as possible.\n"
    "- Convert the <template> to JSX, <script setup> to hooks (useState, useEffect, etc.), "
    "and <style> to a co-located CSS module or plain CSS class names.\n"
    "- Output ONLY the resulting .tsx file content, no explanations, no markdown fences."
)


def _strip_code_fence(text: str) -> str:
    match = re.match(r"^```[a-zA-Z]*\n(.*)\n```$", text.strip(), re.DOTALL)
    return match.group(1) if match else text.strip()


def migrate_vue_file(client: Anthropic, relative_path: str, vue_source: str) -> str:
    message = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"File: {relative_path}\n\n{vue_source}",
            }
        ],
    )
    text = "".join(block.text for block in message.content if block.type == "text")
    return _strip_code_fence(text)


def find_vue_files(repo_dir: Path) -> list[Path]:
    return [p for p in repo_dir.rglob("*.vue") if "node_modules" not in p.parts]


def migrate_repo(repo_dir: Path, output_dir: Path) -> list[dict]:
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    results = []

    for vue_path in find_vue_files(repo_dir):
        relative_path = vue_path.relative_to(repo_dir)
        vue_source = vue_path.read_text(encoding="utf-8")

        try:
            react_source = migrate_vue_file(client, str(relative_path), vue_source)
            status = "migrated"
        except Exception as exc:
            react_source = f"// Migration failed: {exc}\n"
            status = "failed"

        out_path = output_dir / relative_path.with_suffix(".tsx")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(react_source, encoding="utf-8")

        results.append({"file": str(relative_path), "status": status})

    return results
