"""Tests for Git service operations."""

import uuid
from pathlib import Path

import pytest
from git import Repo

from app.schemas.task import FileStatus
from app.services.git import (
    GitError,
    GitService,
    _extract_file_patch,
    _generate_branch_name,
    _parse_diff_stat_line,
    _parse_name_status,
    _slugify,
    generate_diff,
    get_current_branch,
    parse_hunk_header,
    parse_patch_lines,
    validate_comment_line_number,
)

# =============================================================================
# Diff Generation Tests
# =============================================================================


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
        line10 = next(line for line in lines if line.content == "line 10")
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
    """Integration tests that use GitPython."""

    @pytest.fixture
    def git_repo(self, tmp_path: Path):
        """Create a temporary git repository with some commits."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        # Initialize repo using GitPython
        repo = Repo.init(repo_path)
        repo.config_writer().set_value("user", "email", "test@test.com").release()
        repo.config_writer().set_value("user", "name", "Test").release()

        # Create initial commit on main
        (repo_path / "file.txt").write_text("initial content\n")
        repo.index.add(["file.txt"])
        repo.index.commit("initial")

        return repo_path

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
        repo = Repo(git_repo)
        base_branch = get_current_branch(git_repo)

        # Create a new branch
        repo.create_head("feature")
        repo.heads.feature.checkout()

        # Modify existing file
        (git_repo / "file.txt").write_text("modified content\n")

        # Add new file
        (git_repo / "new_file.txt").write_text("new file\n")

        repo.index.add(["file.txt", "new_file.txt"])
        repo.index.commit("feature changes")

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
        repo = Repo(git_repo)
        base_branch = get_current_branch(git_repo)

        repo.create_head("delete-branch")
        repo.heads["delete-branch"].checkout()

        (git_repo / "file.txt").unlink()
        repo.index.remove(["file.txt"])
        repo.index.commit("delete file")

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


# =============================================================================
# Worktree Management Tests
# =============================================================================


class TestSlugify:
    def test_basic_slug(self):
        assert _slugify("Hello World") == "hello-world"

    def test_special_characters(self):
        assert _slugify("Fix: bug #123!") == "fix-bug-123"

    def test_consecutive_hyphens(self):
        assert _slugify("Hello   World") == "hello-world"

    def test_leading_trailing_hyphens(self):
        assert _slugify("  Hello World  ") == "hello-world"

    def test_max_length(self):
        long_text = "a" * 100
        result = _slugify(long_text, max_length=50)
        assert len(result) == 50

    def test_empty_string(self):
        assert _slugify("") == ""

    def test_only_special_chars(self):
        assert _slugify("!@#$%") == ""


class TestGenerateBranchName:
    def test_basic_branch_name(self):
        task_id = uuid.UUID("12345678-1234-1234-1234-123456789abc")
        branch = _generate_branch_name(task_id, "Implement login feature")
        assert branch == "vk/12345678-implement-login-feature"

    def test_branch_name_with_special_chars(self):
        task_id = uuid.UUID("abcdef12-1234-1234-1234-123456789abc")
        branch = _generate_branch_name(task_id, "Fix: bug #123!")
        assert branch == "vk/abcdef12-fix-bug-123"

    def test_branch_name_short_id(self):
        task_id = uuid.UUID("12345678-1234-1234-1234-123456789abc")
        branch = _generate_branch_name(task_id, "test")
        # Short ID should be first 8 chars of UUID
        assert branch.startswith("vk/12345678-")

    def test_branch_name_long_title_truncated(self):
        task_id = uuid.UUID("12345678-1234-1234-1234-123456789abc")
        long_title = "a" * 100
        branch = _generate_branch_name(task_id, long_title)
        # slug is truncated to 50 chars, plus "vk/" prefix and short id
        assert len(branch) <= 63  # vk/ (3) + short_id (8) + - (1) + slug (50) = 62


class TestGitServiceHelpers:
    """Tests for git service helper functions that don't require git."""

    @pytest.fixture
    def git_service(self, tmp_path):
        return GitService(tmp_path)

    def test_get_bare_repo_path(self, git_service, tmp_path):
        project_id = uuid.uuid4()
        path = git_service._get_bare_repo_path(project_id)
        assert str(project_id) in str(path)
        assert "repos" in str(path)

    def test_get_worktree_path(self, git_service, tmp_path):
        project_id = uuid.uuid4()
        task_id = uuid.uuid4()
        path = git_service._get_worktree_path(project_id, task_id)
        assert str(project_id) in str(path)
        assert str(task_id) in str(path)
        assert "tasks" in str(path)
