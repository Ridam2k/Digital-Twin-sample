import nbformat
from github import Github, GithubException
from llama_index.core import Document
from config import (
    GITHUB_TOKEN,
    GITHUB_REPOS,
    GITHUB_ALLOWED_EXTENSIONS,
    GITHUB_IGNORE_PATTERNS,
)


def _should_ignore(path: str) -> bool:
    return any(pattern in path for pattern in GITHUB_IGNORE_PATTERNS)


def _notebook_to_text(raw_content: str) -> str:
    """Extract source cells from a Jupyter notebook into plain text."""
    nb = nbformat.reads(raw_content, as_version=4)
    parts = []
    for cell in nb.cells:
        if cell.cell_type in ("code", "markdown") and cell.source.strip():
            parts.append(f"# [{cell.cell_type.upper()} CELL]\n{cell.source}")
    return "\n\n".join(parts)


def fetch_repo_files(repo_name: str) -> list[dict]:
    """
    Returns a list of dicts, one per eligible file:
    {
        "file_key":   "owner/repo/path/to/file.py",
        "git_sha":    "abc123",
        "content":    "raw text content",
        "file_path":  "path/to/file.py",
        "repo_name":  "owner/repo",
        "source_url": "https://github.com/owner/repo/blob/main/path/to/file.py",
        "extension":  ".py",
    }
    """
    g = Github(GITHUB_TOKEN)
    try:
        repo = g.get_repo(repo_name)
    except GithubException as e:
        print(f"[github] Could not access repo '{repo_name}': {e}")
        return []

    results = []
    default_branch = repo.default_branch

    def traverse(path=""):
        try:
            contents = repo.get_contents(path, ref=default_branch)
        except GithubException as e:
            print(f"[github] Error reading path '{path}' in '{repo_name}': {e}")
            return

        for item in contents:
            if _should_ignore(item.path):
                continue
            if item.type == "dir":
                traverse(item.path)
            elif item.type == "file":
                ext = "." + item.name.rsplit(".", 1)[-1] if "." in item.name else ""
                if ext not in GITHUB_ALLOWED_EXTENSIONS:
                    continue
                try:
                    raw = item.decoded_content.decode("utf-8", errors="ignore")
                    if ext == ".ipynb":
                        raw = _notebook_to_text(raw)
                    results.append({
                        "file_key":   f"{repo_name}/{item.path}",
                        "git_sha":    item.sha,
                        "content":    raw,
                        "file_path":  item.path,
                        "repo_name":  repo_name,
                        "source_url": f"https://github.com/{repo_name}/blob/{default_branch}/{item.path}",
                        "extension":  ext,
                    })
                except Exception as e:
                    print(f"[github] Could not decode '{item.path}': {e}")

    traverse()
    print(f"[github] Found {len(results)} eligible files in '{repo_name}'.")
    return results


def files_to_documents(files: list[dict]) -> list[Document]:
    """Convert raw file dicts into LlamaIndex Document objects with metadata."""
    docs = []
    for f in files:
        doc = Document(
            text=f["content"],
            metadata={
                "doc_id":      f["file_key"],
                "doc_title":   f["file_path"].split("/")[-1],
                "source_type": f["extension"].lstrip("."),
                "source_url":  f["source_url"],
                "repo_name":   f["repo_name"],
                "file_path":   f["file_path"],
            },
            id_=f["file_key"],
        )
        docs.append(doc)
    return docs