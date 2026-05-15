"""Git update helpers for the local dashboard."""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlparse


GIT_TIMEOUT_SECONDS = 25
REPAIRABLE_UPDATE_METADATA_PATHS = {"dashboard/package-lock.json"}


class DashboardGitError(Exception):
    """Raised when repository update checks or pulls cannot be completed safely."""


RunGit = Callable[..., subprocess.CompletedProcess[str]]
GitValue = Callable[[list[str]], str | None]
RefreshDeskBuild = Callable[[], dict]


def run_git(
    args: list[str],
    *,
    project_root: Path,
    timeout: int = GIT_TIMEOUT_SECONDS,
    subprocess_module=subprocess,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess_module.run(
            ["git", *args],
            cwd=project_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        command = " ".join(["git", *args])
        raise DashboardGitError(f"{command} timed out after {timeout} second(s).") from exc
    except OSError as exc:
        raise DashboardGitError(f"Unable to run git: {exc}") from exc


def git_value(args: list[str], *, run_git_fn: RunGit) -> str | None:
    completed = run_git_fn(args)
    if completed.returncode != 0:
        return None
    value = completed.stdout.strip()
    return value or None


def repo_web_url(remote_url: str | None) -> str | None:
    if not remote_url:
        return None
    remote_url = remote_url.strip()
    if remote_url.startswith("git@github.com:"):
        remote_url = "https://github.com/" + remote_url.removeprefix("git@github.com:")
    parsed = urlparse(remote_url)
    if parsed.hostname and parsed.scheme in {"http", "https", "ssh"}:
        path = parsed.path or ""
        if path.endswith(".git"):
            path = path[:-4]
        scheme = "https" if parsed.scheme == "ssh" else parsed.scheme
        return f"{scheme}://{parsed.hostname}{path}"
    if remote_url.endswith(".git"):
        remote_url = remote_url[:-4]
    return remote_url if "@" not in remote_url and ":" not in remote_url else None


def dirty_entries_from_porcelain(dirty_output: str) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for raw in dirty_output.splitlines():
        if len(raw) < 4:
            continue
        status = raw[:2]
        path = raw[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1].strip()
        normalized = path.replace("\\", "/")
        if normalized:
            entries.append((status, normalized))
    return entries


def dirty_paths_from_entries(entries: list[tuple[str, str]]) -> list[str]:
    paths: list[str] = []
    seen: set[str] = set()
    for _, path in entries:
        if path in seen:
            continue
        seen.add(path)
        paths.append(path)
    return paths


def repairable_update_metadata_paths(entries: list[tuple[str, str]]) -> list[str]:
    if not entries:
        return []
    for status, path in entries:
        # Only unstaged working-tree modifications from dependency tooling are
        # safe to repair during the explicit update action. Staged edits,
        # deletes, renames, and unrelated files still belong to the user.
        if status != " M" or path not in REPAIRABLE_UPDATE_METADATA_PATHS:
            return []
    return dirty_paths_from_entries(entries)


def restore_repairable_update_metadata(*, paths: list[str], run_git_fn: RunGit) -> None:
    safe_paths = [path for path in paths if path in REPAIRABLE_UPDATE_METADATA_PATHS]
    if not safe_paths:
        raise DashboardGitError("Generated Desk dependency metadata could not be identified for repair.")
    completed = run_git_fn(["restore", "--worktree", "--", *safe_paths], timeout=30)
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "git restore failed").strip()
        raise DashboardGitError(f"Could not repair generated Desk dependency metadata: {detail}")


def git_update_status(
    *,
    fetch: bool,
    git_value_fn: GitValue,
    run_git_fn: RunGit,
    safe_result_text_fn: Callable[..., str],
    utc_now_fn: Callable[[], str],
) -> dict:
    branch = git_value_fn(["rev-parse", "--abbrev-ref", "HEAD"]) or "unknown"
    upstream = git_value_fn(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"])
    remote_url = git_value_fn(["config", "--get", "remote.origin.url"])
    dirty_completed = run_git_fn(["status", "--porcelain"])
    dirty_output = dirty_completed.stdout if dirty_completed.returncode == 0 else ""
    dirty_entries = dirty_entries_from_porcelain(dirty_output)
    dirty_paths = dirty_paths_from_entries(dirty_entries)
    dirty_count = len(dirty_entries)
    repairable_dirty_paths = repairable_update_metadata_paths(dirty_entries)
    repairable_dirty = dirty_count > 0 and len(repairable_dirty_paths) == dirty_count
    fetch_error = ""

    if fetch:
        completed = run_git_fn(["fetch", "--prune", "origin"], timeout=45)
        if completed.returncode != 0:
            fetch_error = safe_result_text_fn(completed.stderr, completed.stdout) or "git fetch failed"

    head = git_value_fn(["rev-parse", "--short", "HEAD"])
    remote_head = git_value_fn(["rev-parse", "--short", upstream]) if upstream else None
    ahead = 0
    behind = 0
    status = "no_upstream"
    message = "No upstream branch is configured for this local branch."
    pull_allowed = False

    if fetch_error:
        status = "fetch_failed"
        message = fetch_error
    elif upstream:
        compare = git_value_fn(["rev-list", "--left-right", "--count", f"HEAD...{upstream}"])
        if compare:
            parts = compare.split()
            if len(parts) == 2:
                ahead, behind = int(parts[0]), int(parts[1])
        if ahead == 0 and behind == 0:
            status = "up_to_date"
            message = "Local branch is up to date with upstream."
        elif ahead == 0 and behind > 0:
            status = "behind"
            message = f"{behind} upstream commit(s) available."
            pull_allowed = dirty_count == 0 or repairable_dirty
        elif ahead > 0 and behind == 0:
            status = "ahead"
            message = f"Local branch is ahead of upstream by {ahead} commit(s)."
        else:
            status = "diverged"
            message = f"Local branch diverged: {ahead} ahead, {behind} behind."

    if dirty_count:
        if repairable_dirty:
            if status == "behind":
                message = f"{message} Generated Desk dependency metadata will be repaired during update."
        else:
            pull_allowed = False
            if status == "behind":
                message = f"{message} Commit or stash {dirty_count} local change(s) before pulling."

    return {
        "schema_version": "git_update_status_v1",
        "status": status,
        "message": message,
        "branch": branch,
        "upstream": upstream,
        "repo_url": repo_web_url(remote_url),
        "head": head,
        "remote_head": remote_head,
        "ahead": ahead,
        "behind": behind,
        "dirty": dirty_count > 0,
        "dirty_count": dirty_count,
        "dirty_paths": dirty_paths,
        "repairable_dirty": repairable_dirty,
        "repairable_dirty_count": len(repairable_dirty_paths),
        "pull_allowed": pull_allowed,
        "fetched": fetch and not fetch_error,
        "checked_at": utc_now_fn(),
    }


def _desk_build_result(
    *,
    status: str,
    message: str,
    reload_recommended: bool = False,
) -> dict:
    return {
        "desk_build_status": status,
        "desk_build_message": message,
        "desk_reload_recommended": reload_recommended,
    }


def git_pull_latest(
    *,
    git_update_status_fn: Callable[..., dict],
    run_git_fn: RunGit,
    refresh_desk_build_fn: RefreshDeskBuild | None = None,
) -> dict:
    before = git_update_status_fn(fetch=True)
    dirty_repair_applied = False
    if before["dirty"] and before.get("repairable_dirty"):
        restore_repairable_update_metadata(
            paths=[str(path) for path in before.get("dirty_paths", []) if str(path).strip()],
            run_git_fn=run_git_fn,
        )
        dirty_repair_applied = True
        before = git_update_status_fn(fetch=False)
    if before["dirty"]:
        raise DashboardGitError("Working tree has local changes. Commit or stash them before pulling.")
    if before["status"] != "behind" or not before["pull_allowed"]:
        raise DashboardGitError(before["message"])
    completed = run_git_fn(["pull", "--ff-only"], timeout=60)
    if completed.returncode != 0:
        raise DashboardGitError((completed.stderr or completed.stdout or "git pull --ff-only failed").strip())
    after = git_update_status_fn(fetch=False)
    after["pull_output"] = (completed.stdout or "").strip()
    if dirty_repair_applied:
        after["dirty_repair_applied"] = True
    if refresh_desk_build_fn is None:
        after.update(
            _desk_build_result(
                status="skipped",
                message="Desk build refresh was not configured.",
            )
        )
        return after
    try:
        build_result = refresh_desk_build_fn()
    except DashboardGitError as exc:
        build_result = _desk_build_result(status="failed", message=str(exc))
    except Exception:
        build_result = _desk_build_result(status="failed", message="Desk build refresh failed.")
    after.update(build_result)
    return after
