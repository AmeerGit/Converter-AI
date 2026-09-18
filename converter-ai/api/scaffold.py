import json
from pathlib import Path

BASE_DEPENDENCIES = {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
}

DEV_DEPENDENCIES = {
    "@types/react": "^18.3.12",
    "@types/react-dom": "^18.3.1",
    "@vitejs/plugin-react": "^4.3.4",
    "typescript": "^5.6.3",
    "vite": "^5.4.11",
}


def build_package_json(extra_dependencies: dict[str, str]) -> str:
    dependencies = {**BASE_DEPENDENCIES, **extra_dependencies}
    package = {
        "name": "migrated-react-app",
        "private": True,
        "version": "0.0.0",
        "type": "module",
        "scripts": {
            "dev": "vite",
            "build": "tsc -b && vite build",
            "preview": "vite preview",
        },
        "dependencies": dict(sorted(dependencies.items())),
        "devDependencies": dict(sorted(DEV_DEPENDENCIES.items())),
    }
    return json.dumps(package, indent=2) + "\n"

INDEX_HTML = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Migrated React App</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
"""

VITE_CONFIG = """import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
})
"""

TSCONFIG_JSON = """{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true
  },
  "include": ["src"]
}
"""

MAIN_TSX = """import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
"""

GITIGNORE = """node_modules/
dist/
"""


def _component_name(relative_path: str) -> str:
    stem = Path(relative_path).stem
    return "".join(part.capitalize() for part in stem.replace("-", "_").split("_")) or "Component"


def _import_path(relative_path: str) -> str:
    return "./migrated/" + Path(relative_path).with_suffix("").as_posix()


def build_app_tsx(migrated_files: list[str]) -> str:
    imports = []
    elements = []
    seen_names: set[str] = {"App"}

    for relative_path in migrated_files:
        name = _component_name(relative_path)
        while name in seen_names:
            name += "_"
        seen_names.add(name)

        imports.append(f"import {name} from '{_import_path(relative_path)}'")
        elements.append(f"      <{name} />")

    imports_block = "\n".join(imports)
    elements_block = "\n".join(elements) if elements else "      <p>No components were migrated.</p>"

    return f"""{imports_block}

function App() {{
  return (
    <div>
{elements_block}
    </div>
  )
}}

export default App
"""


def write_scaffold(project_dir: Path, migrated_files: list[str], extra_dependencies: dict[str, str] | None = None) -> None:
    src_dir = project_dir / "src"
    src_dir.mkdir(parents=True, exist_ok=True)

    (project_dir / "package.json").write_text(build_package_json(extra_dependencies or {}), encoding="utf-8")
    (project_dir / "index.html").write_text(INDEX_HTML, encoding="utf-8")
    (project_dir / "vite.config.ts").write_text(VITE_CONFIG, encoding="utf-8")
    (project_dir / "tsconfig.json").write_text(TSCONFIG_JSON, encoding="utf-8")
    (project_dir / ".gitignore").write_text(GITIGNORE, encoding="utf-8")
    (src_dir / "main.tsx").write_text(MAIN_TSX, encoding="utf-8")
    (src_dir / "App.tsx").write_text(build_app_tsx(migrated_files), encoding="utf-8")
