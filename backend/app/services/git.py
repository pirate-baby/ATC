"""Git operations service for diff generation and worktree management.

Uses GitPython for git operations instead of subprocess calls.
"""

import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from git import GitCommandError, InvalidGitRepositoryError, Repo
from pydantic import BaseModel

from app.schemas.task import FileDiff, FileStatus


class GitError(Exception):
    """Exception raised for git operation errors."""

    pass


class WorktreeExistsError(GitError):
    """Raised when a worktree already exists for a task."""


class BranchExistsError(GitError):
    """Raised when a branch already exists with the same name."""


class RepositoryNotFoundError(GitError):
    """Raised when the repository is not found or not accessible."""


# =============================================================================
# Diff Generation
# =============================================================================


@dataclass
class DiffResult:
    """Result of a git diff operation."""

    base_branch: str
    head_branch: str
    files: list[FileDiff]


def get_current_branch(repo_path: str | Path) -> str:
    """Get the current branch name.

    Args:
        repo_path: Path to the git repository.

    Returns:
        Current branch name.

    Raises:
        GitError: If repository is invalid or operation fails.
    """
    try:
        repo = Repo(repo_path)
        return repo.active_branch.name
    except InvalidGitRepositoryError as e:
        raise GitError(f"Invalid git repository: {repo_path}") from e
    except TypeError:
        # Detached HEAD state
        return repo.head.commit.hexsha[:8]
    except Exception as e:
        raise GitError(f"Failed to get current branch: {e}") from e


def _parse_diff_stat_line(line: str) -> tuple[str, FileStatus, int, int] | None:
    """Parse a single line from git diff --numstat output.

    Args:
        line: A line from numstat output (e.g., "10\t5\tpath/to/file.py")

    Returns:
        Tuple of (path, status, additions, deletions) or None if line is invalid.
    """
    parts = line.split("\t")
    if len(parts) != 3:
        return None

    additions_str, deletions_str, path = parts

    # Binary files show "-" for additions/deletions
    additions = 0 if additions_str == "-" else int(additions_str)
    deletions = 0 if deletions_str == "-" else int(deletions_str)

    # Determine status based on additions/deletions
    # This is a simplified heuristic; actual status comes from --name-status
    if deletions == 0 and additions > 0:
        status = FileStatus.ADDED
    elif additions == 0 and deletions > 0:
        status = FileStatus.DELETED
    else:
        status = FileStatus.MODIFIED

    return path, status, additions, deletions


def _parse_name_status(output: str) -> dict[str, FileStatus]:
    """Parse git diff --name-status output to get file statuses.

    Args:
        output: Output from git diff --name-status.

    Returns:
        Dict mapping file paths to their status.
    """
    status_map = {
        "A": FileStatus.ADDED,
        "M": FileStatus.MODIFIED,
        "D": FileStatus.DELETED,
        "R": FileStatus.RENAMED,
    }

    result: dict[str, FileStatus] = {}
    for line in output.strip().split("\n"):
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) >= 2:
            status_char = parts[0][0]  # First char of status (R100 -> R)
            path = parts[-1]  # Last part is the new name (for renames)
            result[path] = status_map.get(status_char, FileStatus.MODIFIED)

    return result


def _extract_file_patch(full_diff: str, file_path: str) -> str:
    """Extract the patch for a specific file from a full diff output.

    Args:
        full_diff: Full git diff output.
        file_path: Path to extract patch for.

    Returns:
        Unified diff patch for the file, or empty string if not found.
    """
    # Escape special regex characters in file path
    escaped_path = re.escape(file_path)

    # Pattern to match file header and capture until next file or end
    # Handles both regular and renamed files
    pattern = rf"(diff --git [^\n]*{escaped_path}[^\n]*\n(?:(?!diff --git ).)*)"

    match = re.search(pattern, full_diff, re.DOTALL)
    if match:
        return match.group(1).strip()

    return ""


def generate_diff(
    repo_path: str | Path,
    base_branch: str,
    head_branch: str | None = None,
) -> DiffResult:
    """Generate a diff between two branches.

    Args:
        repo_path: Path to the git repository (or worktree).
        base_branch: Base branch to compare against.
        head_branch: Head branch (current branch if None).

    Returns:
        DiffResult with parsed diff information.

    Raises:
        GitError: If diff generation fails.
    """
    try:
        repo = Repo(repo_path)
    except InvalidGitRepositoryError as e:
        raise GitError(f"Invalid git repository: {repo_path}") from e

    if head_branch is None:
        head_branch = get_current_branch(repo_path)

    try:
        # Get the merge base to find common ancestor
        try:
            merge_base = repo.git.merge_base(base_branch, head_branch).strip()
        except GitCommandError:
            # If merge-base fails, try direct comparison
            merge_base = base_branch

        # Get file statuses
        name_status_output = repo.git.diff("--name-status", merge_base, head_branch)
        file_statuses = _parse_name_status(name_status_output)

        # Get numstat for additions/deletions count
        numstat_output = repo.git.diff("--numstat", merge_base, head_branch)

        # Get full diff for patches
        full_diff = repo.git.diff(merge_base, head_branch)

        # Parse numstat and combine with status and patches
        files: list[FileDiff] = []
        for line in numstat_output.strip().split("\n"):
            if not line:
                continue

            parsed = _parse_diff_stat_line(line)
            if parsed is None:
                continue

            path, _, additions, deletions = parsed

            # Get actual status from name-status (more accurate)
            status = file_statuses.get(path, FileStatus.MODIFIED)

            # Extract patch for this file
            patch = _extract_file_patch(full_diff, path)

            files.append(
                FileDiff(
                    path=path,
                    status=status,
                    additions=additions,
                    deletions=deletions,
                    patch=patch,
                )
            )

        return DiffResult(
            base_branch=base_branch,
            head_branch=head_branch,
            files=files,
        )
    except GitCommandError as e:
        raise GitError(f"Git diff failed: {e.stderr}") from e


def get_diff_for_file(
    repo_path: str | Path,
    base_branch: str,
    file_path: str,
    head_branch: str | None = None,
) -> FileDiff | None:
    """Get diff for a specific file.

    Args:
        repo_path: Path to the git repository.
        base_branch: Base branch to compare against.
        file_path: Path to the file to diff.
        head_branch: Head branch (current branch if None).

    Returns:
        FileDiff for the file, or None if file has no changes.
    """
    diff_result = generate_diff(repo_path, base_branch, head_branch)

    for file_diff in diff_result.files:
        if file_diff.path == file_path:
            return file_diff

    return None


def parse_hunk_header(header: str) -> tuple[int, int, int, int] | None:
    """Parse a unified diff hunk header.

    Args:
        header: Hunk header line (e.g., "@@ -10,5 +12,7 @@")

    Returns:
        Tuple of (old_start, old_count, new_start, new_count) or None if invalid.
    """
    match = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", header)
    if not match:
        return None

    old_start = int(match.group(1))
    old_count = int(match.group(2)) if match.group(2) else 1
    new_start = int(match.group(3))
    new_count = int(match.group(4)) if match.group(4) else 1

    return old_start, old_count, new_start, new_count


@dataclass
class DiffLine:
    """Represents a single line in a diff."""

    type: str  # 'add', 'delete', 'context'
    content: str
    old_line_number: int | None  # Line number in old file (None for additions)
    new_line_number: int | None  # Line number in new file (None for deletions)


def parse_patch_lines(patch: str) -> list[DiffLine]:
    """Parse a unified diff patch into individual lines with line numbers.

    Args:
        patch: Unified diff patch string.

    Returns:
        List of DiffLine objects with line number information.
    """
    lines: list[DiffLine] = []
    old_line = 0
    new_line = 0

    for line in patch.split("\n"):
        if line.startswith("@@"):
            parsed = parse_hunk_header(line)
            if parsed:
                old_line, _, new_line, _ = parsed
                # Don't decrement here; first line starts at the header position
                old_line -= 1
                new_line -= 1
            continue

        if line.startswith("diff --git") or line.startswith("index "):
            continue
        if line.startswith("---") or line.startswith("+++"):
            continue

        if line.startswith("+"):
            new_line += 1
            lines.append(
                DiffLine(
                    type="add",
                    content=line[1:],
                    old_line_number=None,
                    new_line_number=new_line,
                )
            )
        elif line.startswith("-"):
            old_line += 1
            lines.append(
                DiffLine(
                    type="delete",
                    content=line[1:],
                    old_line_number=old_line,
                    new_line_number=None,
                )
            )
        elif line.startswith(" ") or line == "":
            old_line += 1
            new_line += 1
            lines.append(
                DiffLine(
                    type="context",
                    content=line[1:] if line.startswith(" ") else "",
                    old_line_number=old_line,
                    new_line_number=new_line,
                )
            )

    return lines


def validate_comment_line_number(
    patch: str,
    line_number: int,
    side: str = "new",
) -> bool:
    """Validate that a line number exists in the diff for commenting.

    Args:
        patch: Unified diff patch string.
        line_number: Line number to validate.
        side: Which side to check - 'old' or 'new'.

    Returns:
        True if the line number exists in the diff.
    """
    diff_lines = parse_patch_lines(patch)

    for diff_line in diff_lines:
        if side == "new" and diff_line.new_line_number == line_number:
            return True
        if side == "old" and diff_line.old_line_number == line_number:
            return True

    return False


# =============================================================================
# Worktree Management
# =============================================================================


class WorktreeResult(BaseModel):
    """Result of a worktree creation operation."""

    worktree_path: str
    branch_name: str


def _slugify(text: str, max_length: int = 50) -> str:
    """Convert text to a git-branch-safe slug.

    - Lowercase
    - Replace spaces/special chars with hyphens
    - Remove consecutive hyphens
    - Truncate to max_length
    """
    slug = text.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    slug = slug.strip("-")
    return slug[:max_length]


def _generate_branch_name(task_id: UUID, title: str) -> str:
    """Generate a unique branch name for a task.

    Format: vk/{short_task_id}-{slugified_title}
    Example: vk/a1b2c3d4-implement-login
    """
    short_id = str(task_id)[:8]
    slug = _slugify(title)
    return f"vk/{short_id}-{slug}"


def clone_bare_repository(git_url: str, target_path: Path) -> Repo:
    """Clone a repository as a bare repository for worktree management.

    Args:
        git_url: URL of the git repository
        target_path: Path where to clone the bare repository

    Returns:
        The cloned Repo object.

    Raises:
        GitError: If clone fails
    """
    if target_path.exists():
        return Repo(target_path)

    target_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        return Repo.clone_from(git_url, target_path, bare=True)
    except GitCommandError as e:
        raise GitError(f"Failed to clone repository: {e.stderr}") from e


def fetch_updates(bare_repo_path: Path) -> None:
    """Fetch updates from the remote repository.

    Args:
        bare_repo_path: Path to the bare repository

    Raises:
        GitError: If fetch fails
        RepositoryNotFoundError: If repository doesn't exist
    """
    if not bare_repo_path.exists():
        raise RepositoryNotFoundError(f"Repository not found: {bare_repo_path}")

    try:
        repo = Repo(bare_repo_path)
        for remote in repo.remotes:
            remote.fetch(prune=True)
    except InvalidGitRepositoryError as e:
        raise RepositoryNotFoundError(f"Invalid repository: {bare_repo_path}") from e
    except GitCommandError as e:
        raise GitError(f"Failed to fetch updates: {e.stderr}") from e


def branch_exists(repo: Repo, branch_name: str) -> bool:
    """Check if a branch exists in the repository.

    Args:
        repo: GitPython Repo object
        branch_name: Name of the branch to check

    Returns:
        True if branch exists, False otherwise
    """
    return branch_name in [ref.name for ref in repo.references if ref.name == branch_name]


def get_worktrees(repo: Repo) -> dict[str, str]:
    """Get all worktrees for a repository.

    Args:
        repo: GitPython Repo object

    Returns:
        Dict mapping worktree paths to branch names
    """
    worktrees = {}
    try:
        output = repo.git.worktree("list", "--porcelain")
        current_path = None
        for line in output.split("\n"):
            if line.startswith("worktree "):
                current_path = line[9:]
            elif line.startswith("branch ") and current_path:
                branch = line[7:].replace("refs/heads/", "")
                worktrees[current_path] = branch
                current_path = None
    except GitCommandError:
        pass
    return worktrees


def worktree_exists_at_path(repo: Repo, worktree_path: Path) -> bool:
    """Check if a worktree exists at the given path.

    Args:
        repo: GitPython Repo object
        worktree_path: Path to check

    Returns:
        True if worktree exists at path, False otherwise
    """
    worktrees = get_worktrees(repo)
    return str(worktree_path) in worktrees


def create_worktree(
    repo: Repo,
    worktree_path: Path,
    branch_name: str,
    base_branch: str = "main",
) -> None:
    """Create a new worktree with a new branch.

    Args:
        repo: GitPython Repo object (bare repository)
        worktree_path: Path where to create the worktree
        branch_name: Name of the new branch to create
        base_branch: Base branch to branch from (default: main)

    Raises:
        WorktreeExistsError: If worktree already exists at the path
        BranchExistsError: If branch already exists
        GitError: If worktree creation fails
    """
    if worktree_exists_at_path(repo, worktree_path):
        raise WorktreeExistsError(f"Worktree already exists at {worktree_path}")

    if branch_exists(repo, branch_name):
        raise BranchExistsError(f"Branch already exists: {branch_name}")

    worktree_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        repo.git.worktree("add", "-b", branch_name, str(worktree_path), base_branch)
    except GitCommandError as e:
        raise GitError(f"Failed to create worktree: {e.stderr}") from e


def remove_worktree(repo: Repo, worktree_path: Path, force: bool = False) -> None:
    """Remove a worktree.

    Args:
        repo: GitPython Repo object
        worktree_path: Path of the worktree to remove
        force: If True, force removal even with uncommitted changes

    Raises:
        GitError: If worktree removal fails
    """
    if not worktree_exists_at_path(repo, worktree_path):
        return

    try:
        args = ["remove"]
        if force:
            args.append("--force")
        args.append(str(worktree_path))
        repo.git.worktree(*args)
    except GitCommandError as e:
        raise GitError(f"Failed to remove worktree: {e.stderr}") from e


def delete_branch(repo: Repo, branch_name: str, force: bool = False) -> None:
    """Delete a branch from the repository.

    Args:
        repo: GitPython Repo object
        branch_name: Name of the branch to delete
        force: If True, force delete even if not merged

    Raises:
        GitError: If branch deletion fails
    """
    if not branch_exists(repo, branch_name):
        return

    try:
        flag = "-D" if force else "-d"
        repo.git.branch(flag, branch_name)
    except GitCommandError as e:
        raise GitError(f"Failed to delete branch: {e.stderr}") from e


class GitService:
    """Service for managing git worktrees for task isolation.

    Each task gets its own worktree and branch, allowing parallel
    development without interference between tasks.
    """

    def __init__(self, worktrees_base_path: Path):
        """Initialize the GitService.

        Args:
            worktrees_base_path: Base directory for storing worktrees
        """
        self.worktrees_base_path = worktrees_base_path
        self.worktrees_base_path.mkdir(parents=True, exist_ok=True)

    def _get_bare_repo_path(self, project_id: UUID) -> Path:
        """Get the path to the bare repository for a project."""
        return self.worktrees_base_path / "repos" / str(project_id)

    def _get_worktree_path(self, project_id: UUID, task_id: UUID) -> Path:
        """Get the worktree path for a specific task."""
        return self.worktrees_base_path / "tasks" / str(project_id) / str(task_id)

    def ensure_repository(self, project_id: UUID, git_url: str) -> Repo:
        """Ensure the bare repository exists and is up-to-date.

        Args:
            project_id: Project UUID
            git_url: Git repository URL

        Returns:
            GitPython Repo object for the bare repository
        """
        bare_repo_path = self._get_bare_repo_path(project_id)

        if not bare_repo_path.exists():
            return clone_bare_repository(git_url, bare_repo_path)
        else:
            fetch_updates(bare_repo_path)
            return Repo(bare_repo_path)

    def create_task_worktree(
        self,
        project_id: UUID,
        task_id: UUID,
        task_title: str,
        git_url: str,
        base_branch: str = "main",
    ) -> WorktreeResult:
        """Create a worktree for a task.

        Args:
            project_id: Project UUID
            task_id: Task UUID
            task_title: Task title (used for branch name generation)
            git_url: Git repository URL
            base_branch: Base branch to branch from

        Returns:
            WorktreeResult with worktree_path and branch_name

        Raises:
            WorktreeExistsError: If worktree already exists for this task
            BranchExistsError: If generated branch name conflicts
            GitError: If worktree creation fails
        """
        repo = self.ensure_repository(project_id, git_url)
        worktree_path = self._get_worktree_path(project_id, task_id)
        branch_name = _generate_branch_name(task_id, task_title)

        create_worktree(repo, worktree_path, branch_name, base_branch)

        return WorktreeResult(
            worktree_path=str(worktree_path),
            branch_name=branch_name,
        )

    def cleanup_task_worktree(
        self,
        project_id: UUID,
        task_id: UUID,
        branch_name: str | None = None,
        force: bool = False,
        should_delete_branch: bool = False,
    ) -> None:
        """Clean up a task's worktree and optionally delete the branch.

        Args:
            project_id: Project UUID
            task_id: Task UUID
            branch_name: Branch name to delete (if should_delete_branch is True)
            force: Force removal even with uncommitted changes
            should_delete_branch: If True, also delete the branch
        """
        bare_repo_path = self._get_bare_repo_path(project_id)
        worktree_path = self._get_worktree_path(project_id, task_id)

        if bare_repo_path.exists():
            try:
                repo = Repo(bare_repo_path)
                remove_worktree(repo, worktree_path, force=force)

                if should_delete_branch and branch_name:
                    delete_branch(repo, branch_name, force=force)
            except InvalidGitRepositoryError:
                pass

        if worktree_path.exists():
            shutil.rmtree(worktree_path, ignore_errors=True)

    def get_task_worktree_path(self, project_id: UUID, task_id: UUID) -> Path | None:
        """Get the worktree path for a task if it exists.

        Args:
            project_id: Project UUID
            task_id: Task UUID

        Returns:
            Path to the worktree if it exists, None otherwise
        """
        worktree_path = self._get_worktree_path(project_id, task_id)
        return worktree_path if worktree_path.exists() else None
