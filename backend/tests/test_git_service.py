"""Tests for Git service operations."""

import subprocess
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from app.services.git import (
    DiffLine,
    DiffResult,
    GitError,
    _extract_file_patch,
    _parse_diff_stat_line,
    _parse_name_status,
    generate_diff,
    get_current_branch,
    parse_hunk_header,
    parse_patch_lines,
    validate_comment_line_number,
)
from app.schemas.task import FileStatus


class TestParseDiffStatLine:
    def test_parse_basic_line(self):
        result = _parse_diff_stat_line("10\t5\tpath/to/file.py")
        assert result is not None
        path, status, additions, deletions = result
        assert path == "path/to/file.py"
        assert additions == 10
        assert deletions == 5

    def test_parse_only_additions(self):
        result = _parse_diff_stat_line("10\t0\tnew_file.py")
        assert result is not None
        path, status, additions, deletions = result
        assert path == "new_file.py"
        assert status == FileStatus.ADDED
        assert additions == 10
        assert deletions == 0

    def test_parse_only_deletions(self):
        result = _parse_diff_stat_line("0\t10\tdeleted_file.py")
        assert result is not None
        path, status, additions, deletions = result
        assert path == "deleted_file.py"
        assert status == FileStatus.DELETED
        assert additions == 0
        assert deletions == 10

    def test_parse_binary_file(self):
        result = _parse_diff_stat_line("-\t-\tbinary.png")
        assert result is not None
        path, status, additions, deletions = result
        assert path == "binary.png"
        assert additions == 0
        assert deletions == 0

    def test_parse_invalid_line(self):
        result = _parse_diff_stat_line("invalid line format")
        assert result is None


class TestParseNameStatus:
    def test_parse_added_file(self):
        output = "A\tnew_file.py"
        result = _parse_name_status(output)
        assert result["new_file.py"] == FileStatus.ADDED

    def test_parse_modified_file(self):
        output = "M\tmodified_file.py"
        result = _parse_name_status(output)
        assert result["modified_file.py"] == FileStatus.MODIFIED

    def test_parse_deleted_file(self):
        output = "D\tdeleted_file.py"
        result = _parse_name_status(output)
        assert result["deleted_file.py"] == FileStatus.DELETED

    def test_parse_renamed_file(self):
        output = "R100\told_name.py\tnew_name.py"
        result = _parse_name_status(output)
        assert result["new_name.py"] == FileStatus.RENAMED

    def test_parse_multiple_files(self):
        output = "A\tnew_file.py\nM\tmodified.py\nD\tdeleted.py"
        result = _parse_name_status(output)
        assert len(result) == 3
        assert result["new_file.py"] == FileStatus.ADDED
        assert result["modified.py"] == FileStatus.MODIFIED
        assert result["deleted.py"] == FileStatus.DELETED


class TestExtractFilePatch:
    def test_extract_single_file(self):
        full_diff = """diff --git a/file.py b/file.py
index abc123..def456 100644
--- a/file.py
+++ b/file.py
@@ -1,3 +1,4 @@
 line1
+added line
 line2
 line3"""
        result = _extract_file_patch(full_diff, "file.py")
        assert "diff --git" in result
        assert "+added line" in result

    def test_extract_from_multiple_files(self):
        full_diff = """diff --git a/first.py b/first.py
--- a/first.py
+++ b/first.py
@@ -1 +1,2 @@
 first
+new
diff --git a/second.py b/second.py
--- a/second.py
+++ b/second.py
@@ -1 +1,2 @@
 second
+another"""
        result = _extract_file_patch(full_diff, "first.py")
        assert "first" in result
        assert "second" not in result

    def test_extract_nonexistent_file(self):
        full_diff = """diff --git a/file.py b/file.py
--- a/file.py
+++ b/file.py
@@ -1 +1 @@
-old
+new"""
        result = _extract_file_patch(full_diff, "nonexistent.py")
        assert result == ""


class TestParseHunkHeader:
    def test_parse_basic_header(self):
        result = parse_hunk_header("@@ -10,5 +12,7 @@")
        assert result is not None
        old_start, old_count, new_start, new_count = result
        assert old_start == 10
        assert old_count == 5
        assert new_start == 12
        assert new_count == 7

    def test_parse_single_line_old(self):
        result = parse_hunk_header("@@ -10 +12,5 @@")
        assert result is not None
        old_start, old_count, new_start, new_count = result
        assert old_start == 10
        assert old_count == 1  # Default for single line
        assert new_start == 12
        assert new_count == 5

    def test_parse_single_line_both(self):
        result = parse_hunk_header("@@ -10 +12 @@")
        assert result is not None
        old_start, old_count, new_start, new_count = result
        assert old_start == 10
        assert old_count == 1
        assert new_start == 12
        assert new_count == 1

    def test_parse_invalid_header(self):
        result = parse_hunk_header("not a hunk header")
        assert result is None


class TestParsePatchLines:
    def test_parse_simple_patch(self):
        patch = """diff --git a/file.py b/file.py
index abc123..def456 100644
--- a/file.py
+++ b/file.py
@@ -1,3 +1,4 @@
 context line
-deleted line
+added line
 more context"""
        lines = parse_patch_lines(patch)
        assert len(lines) == 4

        assert lines[0].type == "context"
        assert lines[0].content == "context line"
        assert lines[0].old_line_number == 1
        assert lines[0].new_line_number == 1

        assert lines[1].type == "delete"
        assert lines[1].content == "deleted line"
        assert lines[1].old_line_number == 2
        assert lines[1].new_line_number is None

        assert lines[2].type == "add"
        assert lines[2].content == "added line"
        assert lines[2].old_line_number is None
        assert lines[2].new_line_number == 2

        assert lines[3].type == "context"
        assert lines[3].content == "more context"
        assert lines[3].old_line_number == 3
        assert lines[3].new_line_number == 3

    def test_parse_multiple_hunks(self):
        patch = """@@ -1,2 +1,2 @@
 line 1
-old line 2
+new line 2
@@ -10,2 +10,3 @@
 line 10
+inserted line
 line 11"""
        lines = parse_patch_lines(patch)
        # First hunk: 3 lines
        # Second hunk: 3 lines
        assert len(lines) == 6

        # Check line numbers in second hunk
        line10 = next(l for l in lines if l.content == "line 10")
        assert line10.old_line_number == 10
        assert line10.new_line_number == 10


class TestValidateCommentLineNumber:
    def test_validate_new_line_exists(self):
        patch = """@@ -1,3 +1,4 @@
 line 1
+new line 2
 line 3
 line 4"""
        assert validate_comment_line_number(patch, 2, "new") is True
        assert validate_comment_line_number(patch, 1, "new") is True
        assert validate_comment_line_number(patch, 3, "new") is True

    def test_validate_new_line_not_exists(self):
        patch = """@@ -1,2 +1,2 @@
 line 1
 line 2"""
        assert validate_comment_line_number(patch, 100, "new") is False

    def test_validate_old_line_exists(self):
        patch = """@@ -1,3 +1,2 @@
 line 1
-deleted line
 line 3"""
        assert validate_comment_line_number(patch, 2, "old") is True

    def test_validate_old_line_not_in_diff(self):
        patch = """@@ -1,2 +1,2 @@
 line 1
 line 2"""
        assert validate_comment_line_number(patch, 100, "old") is False


class TestGitOperationsIntegration:
    """Integration tests that use actual git commands."""

    @pytest.fixture
    def git_repo(self, tmp_path: Path):
        """Create a temporary git repository with some commits."""
        repo = tmp_path / "repo"
        repo.mkdir()

        # Initialize repo
        subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=repo,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=repo,
            capture_output=True,
            check=True,
        )

        # Create initial commit on main
        (repo / "file.txt").write_text("initial content\n")
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "initial"],
            cwd=repo,
            capture_output=True,
            check=True,
        )

        return repo

    def test_get_current_branch(self, git_repo: Path):
        branch = get_current_branch(git_repo)
        assert branch in ("main", "master")

    def test_generate_diff_no_changes(self, git_repo: Path):
        """Test diff when there are no changes."""
        branch = get_current_branch(git_repo)
        result = generate_diff(git_repo, branch)
        assert result.files == []

    def test_generate_diff_with_changes(self, git_repo: Path):
        """Test diff with actual file changes."""
        base_branch = get_current_branch(git_repo)

        # Create a new branch
        subprocess.run(
            ["git", "checkout", "-b", "feature"],
            cwd=git_repo,
            capture_output=True,
            check=True,
        )

        # Modify existing file
        (git_repo / "file.txt").write_text("modified content\n")

        # Add new file
        (git_repo / "new_file.txt").write_text("new file\n")

        subprocess.run(["git", "add", "."], cwd=git_repo, capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "feature changes"],
            cwd=git_repo,
            capture_output=True,
            check=True,
        )

        result = generate_diff(git_repo, base_branch, "feature")

        assert result.base_branch == base_branch
        assert result.head_branch == "feature"
        assert len(result.files) == 2

        # Check file statuses
        file_paths = {f.path: f for f in result.files}
        assert "file.txt" in file_paths
        assert "new_file.txt" in file_paths
        assert file_paths["new_file.txt"].status == FileStatus.ADDED

    def test_generate_diff_deleted_file(self, git_repo: Path):
        """Test diff with file deletion."""
        base_branch = get_current_branch(git_repo)

        subprocess.run(
            ["git", "checkout", "-b", "delete-branch"],
            cwd=git_repo,
            capture_output=True,
            check=True,
        )

        (git_repo / "file.txt").unlink()
        subprocess.run(["git", "add", "."], cwd=git_repo, capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "delete file"],
            cwd=git_repo,
            capture_output=True,
            check=True,
        )

        result = generate_diff(git_repo, base_branch, "delete-branch")
        assert len(result.files) == 1
        assert result.files[0].path == "file.txt"
        assert result.files[0].status == FileStatus.DELETED

    def test_generate_diff_invalid_repo(self, tmp_path: Path):
        """Test that invalid repo raises GitError."""
        with pytest.raises(GitError):
            generate_diff(tmp_path, "main")

    def test_generate_diff_invalid_branch(self, git_repo: Path):
        """Test that invalid branch raises GitError."""
        with pytest.raises(GitError):
            generate_diff(git_repo, "nonexistent-branch")
