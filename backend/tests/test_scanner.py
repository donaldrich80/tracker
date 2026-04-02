import os
import subprocess
import tempfile
import pytest
from backend.scanner.git_info import read_git_info
from backend.scanner.detector import is_project_dir, detect_stack


def make_git_repo(path: str):
    subprocess.run(["git", "init", path], check=True, capture_output=True)
    subprocess.run(["git", "-C", path, "config", "user.email", "t@t.com"], check=True)
    subprocess.run(["git", "-C", path, "config", "user.name", "T"], check=True)
    subprocess.run(["git", "-C", path, "config", "commit.gpgsign", "false"], check=True)
    (os.path.join(path, "README.md") and open(os.path.join(path, "README.md"), "w").write("hi"))
    subprocess.run(["git", "-C", path, "add", "."], check=True)
    subprocess.run(["git", "-C", path, "commit", "-m", "init"], check=True, capture_output=True)


def test_is_project_dir_requires_git_and_marker():
    with tempfile.TemporaryDirectory() as d:
        assert not is_project_dir(d)  # no git, no marker
        make_git_repo(d)
        assert not is_project_dir(d)  # git but no marker
        open(os.path.join(d, "package.json"), "w").write("{}")
        assert is_project_dir(d)  # git + marker


def test_detect_stack():
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "pyproject.toml"), "w").write("")
        open(os.path.join(d, "Dockerfile"), "w").write("")
        stack = detect_stack(d)
        assert "python" in stack
        assert "docker" in stack


def test_read_git_info():
    with tempfile.TemporaryDirectory() as d:
        make_git_repo(d)
        info = read_git_info(d)
        assert info["branch"] is not None
        assert info["last_commit"] is not None
        assert info["dirty"] is False
