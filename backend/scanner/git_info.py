from __future__ import annotations
import git
from git.exc import InvalidGitRepositoryError


def read_git_info(path: str) -> dict:
    try:
        repo = git.Repo(path)
        try:
            branch = repo.active_branch.name
        except TypeError:
            branch = str(repo.head.commit)[:8]

        last_commit = None
        if not repo.head.is_detached or repo.head.commit:
            last_commit = repo.head.commit.message.strip().splitlines()[0]

        return {
            "branch": branch,
            "dirty": repo.is_dirty(untracked_files=True),
            "last_commit": last_commit,
        }
    except InvalidGitRepositoryError:
        return {"branch": None, "dirty": False, "last_commit": None}
