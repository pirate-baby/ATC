"""Git operations service for diff generation and worktree management."""

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.schemas.task import FileDiff, FileStatus


class GitError(Exception):
    """Exception raised for git operation errors."""

    pass


@dataclass
class DiffResult:
    """Result of a git diff operation."""

    base_branch: str
    head_branch: str
    files: list[FileDiff]


def _run_git_command(args: list[str], cwd: str | Path) -> str:
    """Run a git command and return the output.

    Args:
        args: Git command arguments (without 'git' prefix).
        cwd: Working directory for the command.

    Returns:
        Command stdout as string.

    Raises:
        GitError: If the command fails.
    """
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        raise GitError(f"Git command failed: {e.stderr.strip()}") from e
    except FileNotFoundError as e:
        raise GitError("Git is not installed or not in PATH") from e


def get_current_branch(repo_path: str | Path) -> str:
    """Get the current branch name.

    Args:
        repo_path: Path to the git repository.

    Returns:
        Current branch name.
    """
    output = _run_git_command(["rev-parse", "--abbrev-ref", "HEAD"], repo_path)
    return output.strip()


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
    repo_path = Path(repo_path)

    if head_branch is None:
        head_branch = get_current_branch(repo_path)

    # Get the merge base to find common ancestor
    try:
        merge_base = _run_git_command(
            ["merge-base", base_branch, head_branch], repo_path
        ).strip()
    except GitError:
        # If merge-base fails, try direct comparison
        merge_base = base_branch

    # Get file statuses
    name_status_output = _run_git_command(
        ["diff", "--name-status", merge_base, head_branch], repo_path
    )
    file_statuses = _parse_name_status(name_status_output)

    # Get numstat for additions/deletions count
    numstat_output = _run_git_command(
        ["diff", "--numstat", merge_base, head_branch], repo_path
    )

    # Get full diff for patches
    full_diff = _run_git_command(["diff", merge_base, head_branch], repo_path)

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
