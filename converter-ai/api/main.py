import shutil
import tempfile
import uuid
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from git import GitCommandError, Repo
from pydantic import BaseModel

from agent import run_migration_agent

load_dotenv()

app = FastAPI(title="Vue to React Migrator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

WORK_DIR = Path(tempfile.gettempdir()) / "converter-ai-jobs"
WORK_DIR.mkdir(exist_ok=True)


class MigrateRequest(BaseModel):
    repo_url: str


def _validate_github_url(repo_url: str) -> str:
    parsed = urlparse(repo_url)
    if parsed.scheme not in ("http", "https") or parsed.netloc != "github.com":
        raise HTTPException(status_code=400, detail="Only public github.com repo URLs are supported")
    return repo_url


@app.post("/api/migrate")
def migrate(request: MigrateRequest):
    repo_url = _validate_github_url(request.repo_url)

    job_id = uuid.uuid4().hex
    job_dir = WORK_DIR / job_id
    clone_dir = job_dir / "repo"
    output_dir = job_dir / "react-output"

    try:
        Repo.clone_from(repo_url, clone_dir, depth=1)
    except GitCommandError as exc:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise HTTPException(status_code=400, detail=f"Failed to clone repo: {exc}") from exc

    output_dir.mkdir(parents=True, exist_ok=True)
    results = run_migration_agent(clone_dir, output_dir)

    if not results:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail="Migration agent did not produce any output files")

    archive_path = shutil.make_archive(str(job_dir / "migrated"), "zip", output_dir)

    return {
        "job_id": job_id,
        "files": results,
        "download_url": f"/api/migrate/{job_id}/download",
    }


@app.get("/api/migrate/{job_id}/download")
def download(job_id: str):
    archive_path = WORK_DIR / job_id / "migrated.zip"
    if not archive_path.exists():
        raise HTTPException(status_code=404, detail="Migration result not found")
    return FileResponse(archive_path, filename="migrated-react.zip", media_type="application/zip")
