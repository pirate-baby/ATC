import { useState, useCallback, useMemo } from "react";
import {
  CodeDiff,
  FileDiff,
  DiffLine,
  FileStatus,
  FILE_STATUS_CONFIG,
} from "../types/task";
import { LoadingSpinner } from "./LoadingSpinner";
import "./DiffViewer.css";

// Props for the main DiffViewer component
interface DiffViewerProps {
  diff: CodeDiff | null;
  isLoading: boolean;
  error: Error | null;
  onRetry?: () => void;
}

// Props for individual file diff view
interface FileDiffViewProps {
  file: FileDiff;
  isExpanded: boolean;
  onToggle: () => void;
  viewMode: "unified" | "split";
}

// Props for line number display
interface LineNumberProps {
  lineNumber: number | null;
  type: "old" | "new";
}

// Get file extension for syntax class hint
function getFileExtension(path: string): string {
  const parts = path.split(".");
  return parts.length > 1 ? parts[parts.length - 1].toLowerCase() : "";
}

// Get language class for syntax highlighting hint
function getLanguageClass(path: string): string {
  const ext = getFileExtension(path);
  const languageMap: Record<string, string> = {
    ts: "typescript",
    tsx: "typescript",
    js: "javascript",
    jsx: "javascript",
    py: "python",
    rb: "ruby",
    go: "go",
    rs: "rust",
    java: "java",
    kt: "kotlin",
    swift: "swift",
    cs: "csharp",
    cpp: "cpp",
    c: "c",
    h: "c",
    hpp: "cpp",
    css: "css",
    scss: "scss",
    less: "less",
    html: "html",
    xml: "xml",
    json: "json",
    yaml: "yaml",
    yml: "yaml",
    md: "markdown",
    sql: "sql",
    sh: "bash",
    bash: "bash",
    zsh: "bash",
  };
  return languageMap[ext] || "plaintext";
}

// File status badge component
function FileStatusBadge({ status }: { status: FileStatus }) {
  const config = FILE_STATUS_CONFIG[status];
  return (
    <span
      className="diff-file__status-badge"
      style={{ color: config.color, backgroundColor: config.bgColor }}
    >
      <span className="diff-file__status-icon">{config.icon}</span>
      {config.label}
    </span>
  );
}

// Line number component
function LineNumber({ lineNumber, type }: LineNumberProps) {
  return (
    <span className={`diff-line__number diff-line__number--${type}`}>
      {lineNumber ?? ""}
    </span>
  );
}

// Parse unified diff patch into lines when lines array is not provided
function parsePatch(patch: string): DiffLine[] {
  const lines = patch.split("\n");
  const result: DiffLine[] = [];
  let oldLine = 0;
  let newLine = 0;

  for (const line of lines) {
    // Skip diff header lines
    if (
      line.startsWith("diff ") ||
      line.startsWith("index ") ||
      line.startsWith("---") ||
      line.startsWith("+++")
    ) {
      continue;
    }

    // Parse hunk header @@ -start,count +start,count @@
    if (line.startsWith("@@")) {
      const match = line.match(/@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@/);
      if (match) {
        oldLine = parseInt(match[1], 10);
        newLine = parseInt(match[2], 10);
      }
      // Add hunk header as context
      result.push({
        type: "context",
        content: line,
        old_line_number: null,
        new_line_number: null,
      });
      continue;
    }

    // Parse diff lines
    if (line.startsWith("+")) {
      result.push({
        type: "add",
        content: line.substring(1),
        old_line_number: null,
        new_line_number: newLine++,
      });
    } else if (line.startsWith("-")) {
      result.push({
        type: "delete",
        content: line.substring(1),
        old_line_number: oldLine++,
        new_line_number: null,
      });
    } else if (line.startsWith(" ") || line === "") {
      result.push({
        type: "context",
        content: line.startsWith(" ") ? line.substring(1) : line,
        old_line_number: oldLine++,
        new_line_number: newLine++,
      });
    }
  }

  return result;
}

// Unified diff view component
function UnifiedDiffView({
  lines,
  language,
}: {
  lines: DiffLine[];
  language: string;
}) {
  return (
    <div className={`diff-content diff-content--unified language-${language}`}>
      <table className="diff-table">
        <tbody>
          {lines.map((line, index) => (
            <tr key={index} className={`diff-line diff-line--${line.type}`}>
              <td className="diff-line__gutter">
                <LineNumber lineNumber={line.old_line_number} type="old" />
                <LineNumber lineNumber={line.new_line_number} type="new" />
              </td>
              <td className="diff-line__marker">
                {line.type === "add" ? "+" : line.type === "delete" ? "-" : " "}
              </td>
              <td className="diff-line__content">
                <pre>{line.content}</pre>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// Split diff view component - shows old and new side by side
function SplitDiffView({
  lines,
  language,
}: {
  lines: DiffLine[];
  language: string;
}) {
  // Convert unified lines to split format
  const splitLines = useMemo(() => {
    const result: Array<{
      left: DiffLine | null;
      right: DiffLine | null;
    }> = [];

    let i = 0;
    while (i < lines.length) {
      const line = lines[i];

      if (line.type === "context") {
        result.push({ left: line, right: line });
        i++;
      } else if (line.type === "delete") {
        // Check if next line is an add (modification)
        const nextLine = lines[i + 1];
        if (nextLine && nextLine.type === "add") {
          result.push({ left: line, right: nextLine });
          i += 2;
        } else {
          result.push({ left: line, right: null });
          i++;
        }
      } else if (line.type === "add") {
        result.push({ left: null, right: line });
        i++;
      } else {
        i++;
      }
    }

    return result;
  }, [lines]);

  return (
    <div className={`diff-content diff-content--split language-${language}`}>
      <div className="diff-split">
        <div className="diff-split__side diff-split__side--left">
          <div className="diff-split__header">Old</div>
          <table className="diff-table">
            <tbody>
              {splitLines.map((row, index) => (
                <tr
                  key={index}
                  className={`diff-line diff-line--${row.left?.type || "empty"}`}
                >
                  <td className="diff-line__gutter">
                    <LineNumber
                      lineNumber={row.left?.old_line_number ?? null}
                      type="old"
                    />
                  </td>
                  <td className="diff-line__marker">
                    {row.left?.type === "delete" ? "-" : row.left ? " " : ""}
                  </td>
                  <td className="diff-line__content">
                    <pre>{row.left?.content ?? ""}</pre>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="diff-split__side diff-split__side--right">
          <div className="diff-split__header">New</div>
          <table className="diff-table">
            <tbody>
              {splitLines.map((row, index) => (
                <tr
                  key={index}
                  className={`diff-line diff-line--${row.right?.type || "empty"}`}
                >
                  <td className="diff-line__gutter">
                    <LineNumber
                      lineNumber={row.right?.new_line_number ?? null}
                      type="new"
                    />
                  </td>
                  <td className="diff-line__marker">
                    {row.right?.type === "add" ? "+" : row.right ? " " : ""}
                  </td>
                  <td className="diff-line__content">
                    <pre>{row.right?.content ?? ""}</pre>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// Individual file diff component
function FileDiffView({
  file,
  isExpanded,
  onToggle,
  viewMode,
}: FileDiffViewProps) {
  const language = getLanguageClass(file.path);
  const lines = file.lines || parsePatch(file.patch);

  // Get just the filename for display
  const fileName = file.path.split("/").pop() || file.path;
  const directory = file.path.includes("/")
    ? file.path.substring(0, file.path.lastIndexOf("/"))
    : "";

  return (
    <div className="diff-file">
      <div className="diff-file__header" onClick={onToggle}>
        <button className="diff-file__toggle" aria-expanded={isExpanded}>
          <span
            className={`diff-file__chevron ${isExpanded ? "expanded" : ""}`}
          >
            ▶
          </span>
        </button>
        <FileStatusBadge status={file.status} />
        <div className="diff-file__path">
          {directory && (
            <span className="diff-file__directory">{directory}/</span>
          )}
          <span className="diff-file__name">{fileName}</span>
        </div>
        <div className="diff-file__stats">
          {file.additions > 0 && (
            <span className="diff-file__additions">+{file.additions}</span>
          )}
          {file.deletions > 0 && (
            <span className="diff-file__deletions">-{file.deletions}</span>
          )}
        </div>
      </div>
      {isExpanded && (
        <div className="diff-file__body">
          {viewMode === "unified" ? (
            <UnifiedDiffView lines={lines} language={language} />
          ) : (
            <SplitDiffView lines={lines} language={language} />
          )}
        </div>
      )}
    </div>
  );
}

// File list sidebar item
function FileListItem({
  file,
  isSelected,
  onClick,
}: {
  file: FileDiff;
  isSelected: boolean;
  onClick: () => void;
}) {
  const fileName = file.path.split("/").pop() || file.path;
  const config = FILE_STATUS_CONFIG[file.status];

  return (
    <button
      className={`diff-sidebar__file ${isSelected ? "diff-sidebar__file--selected" : ""}`}
      onClick={onClick}
      title={file.path}
    >
      <span className="diff-sidebar__file-icon" style={{ color: config.color }}>
        {config.icon}
      </span>
      <span className="diff-sidebar__file-name">{fileName}</span>
      <span className="diff-sidebar__file-stats">
        <span className="diff-sidebar__additions">+{file.additions}</span>
        <span className="diff-sidebar__deletions">-{file.deletions}</span>
      </span>
    </button>
  );
}

// Main DiffViewer component
export function DiffViewer({
  diff,
  isLoading,
  error,
  onRetry,
}: DiffViewerProps) {
  const [expandedFiles, setExpandedFiles] = useState<Set<string>>(new Set());
  const [viewMode, setViewMode] = useState<"unified" | "split">("unified");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedFile, setSelectedFile] = useState<string | null>(null);

  // Filter files based on search query
  const filteredFiles = useMemo(() => {
    if (!diff) return [];
    if (!searchQuery) return diff.files;
    const query = searchQuery.toLowerCase();
    return diff.files.filter((file) => file.path.toLowerCase().includes(query));
  }, [diff, searchQuery]);

  // Toggle file expansion
  const toggleFile = useCallback((path: string) => {
    setExpandedFiles((prev) => {
      const next = new Set(prev);
      if (next.has(path)) {
        next.delete(path);
      } else {
        next.add(path);
      }
      return next;
    });
  }, []);

  // Expand all files
  const expandAll = useCallback(() => {
    if (!diff) return;
    setExpandedFiles(new Set(diff.files.map((f) => f.path)));
  }, [diff]);

  // Collapse all files
  const collapseAll = useCallback(() => {
    setExpandedFiles(new Set());
  }, []);

  // Scroll to file and expand it
  const scrollToFile = useCallback((path: string) => {
    setSelectedFile(path);
    setExpandedFiles((prev) => new Set(prev).add(path));
    // Use setTimeout to ensure DOM has updated
    setTimeout(() => {
      const element = document.getElementById(
        `diff-file-${path.replace(/\//g, "-")}`,
      );
      element?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 0);
  }, []);

  // Loading state
  if (isLoading) {
    return (
      <div className="diff-viewer diff-viewer--loading">
        <LoadingSpinner message="Loading diff..." />
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="diff-viewer diff-viewer--error">
        <div className="diff-error">
          <h3 className="diff-error__title">Failed to load diff</h3>
          <p className="diff-error__message">{error.message}</p>
          {onRetry && (
            <button className="diff-error__retry" onClick={onRetry}>
              Retry
            </button>
          )}
        </div>
      </div>
    );
  }

  // Empty state
  if (!diff || diff.files.length === 0) {
    return (
      <div className="diff-viewer diff-viewer--empty">
        <div className="diff-empty">
          <h3 className="diff-empty__title">No changes</h3>
          <p className="diff-empty__message">
            There are no code changes to display.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="diff-viewer">
      {/* Header with summary and controls */}
      <div className="diff-header">
        <div className="diff-header__info">
          <div className="diff-header__branches">
            <span className="diff-header__branch">{diff.base_branch}</span>
            <span className="diff-header__arrow">←</span>
            <span className="diff-header__branch diff-header__branch--head">
              {diff.head_branch}
            </span>
          </div>
          <div className="diff-header__stats">
            <span className="diff-header__file-count">
              {diff.files.length} file{diff.files.length !== 1 ? "s" : ""}{" "}
              changed
            </span>
            <span className="diff-header__additions">
              +{diff.total_additions}
            </span>
            <span className="diff-header__deletions">
              -{diff.total_deletions}
            </span>
          </div>
        </div>
        <div className="diff-header__controls">
          <div className="diff-header__view-toggle">
            <button
              className={`diff-header__view-btn ${viewMode === "unified" ? "active" : ""}`}
              onClick={() => setViewMode("unified")}
            >
              Unified
            </button>
            <button
              className={`diff-header__view-btn ${viewMode === "split" ? "active" : ""}`}
              onClick={() => setViewMode("split")}
            >
              Split
            </button>
          </div>
          <div className="diff-header__expand-controls">
            <button className="diff-header__expand-btn" onClick={expandAll}>
              Expand All
            </button>
            <button className="diff-header__expand-btn" onClick={collapseAll}>
              Collapse All
            </button>
          </div>
        </div>
      </div>

      {/* Main content area with sidebar */}
      <div className="diff-main">
        {/* File list sidebar */}
        <div className="diff-sidebar">
          <div className="diff-sidebar__search">
            <input
              type="text"
              className="diff-sidebar__search-input"
              placeholder="Search files..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            {searchQuery && (
              <button
                className="diff-sidebar__search-clear"
                onClick={() => setSearchQuery("")}
                aria-label="Clear search"
              >
                ×
              </button>
            )}
          </div>
          <div className="diff-sidebar__list">
            {filteredFiles.map((file) => (
              <FileListItem
                key={file.path}
                file={file}
                isSelected={selectedFile === file.path}
                onClick={() => scrollToFile(file.path)}
              />
            ))}
            {filteredFiles.length === 0 && searchQuery && (
              <div className="diff-sidebar__no-results">
                No files match "{searchQuery}"
              </div>
            )}
          </div>
        </div>

        {/* File diffs */}
        <div className="diff-files">
          {filteredFiles.map((file) => (
            <div
              key={file.path}
              id={`diff-file-${file.path.replace(/\//g, "-")}`}
              className={`diff-files__item ${selectedFile === file.path ? "diff-files__item--selected" : ""}`}
            >
              <FileDiffView
                file={file}
                isExpanded={expandedFiles.has(file.path)}
                onToggle={() => toggleFile(file.path)}
                viewMode={viewMode}
              />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
