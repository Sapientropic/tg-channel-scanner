import subprocess
import unittest
import json
from contextlib import AbstractContextManager
from unittest.mock import patch

from scripts import dashboard_server, desk_git


class DashboardGitTests(unittest.TestCase):
    def test_dashboard_server_reexports_git_error(self):
        self.assertIs(dashboard_server.DashboardGitError, desk_git.DashboardGitError)


    def test_close_after_use_closes_connection_handle(self):
        class FakeConnection:
            closed = False

            def close(self):
                self.closed = True

        fake = FakeConnection()

        with dashboard_server.close_after_use(fake) as conn:
            self.assertIs(conn, fake)
            self.assertIsInstance(dashboard_server.close_after_use(fake), AbstractContextManager)

        self.assertTrue(fake.closed)


    def test_run_git_wraps_timeout(self):
        with patch.object(
            dashboard_server.subprocess,
            "run",
            side_effect=subprocess.TimeoutExpired(cmd=["git", "fetch"], timeout=1),
        ):
            with self.assertRaises(dashboard_server.DashboardGitError) as raised:
                dashboard_server._run_git(["fetch"], timeout=1)

        self.assertIn("git fetch timed out", str(raised.exception))


    def test_run_git_wraps_missing_git_binary(self):
        with patch.object(dashboard_server.subprocess, "run", side_effect=OSError("git not found")):
            with self.assertRaises(dashboard_server.DashboardGitError) as raised:
                dashboard_server._run_git(["status"])

        self.assertIn("Unable to run git", str(raised.exception))


    def test_update_status_blocks_pull_when_worktree_is_dirty(self):
        outputs = {
            ("rev-parse", "--abbrev-ref", "HEAD"): "main\n",
            ("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"): "origin/main\n",
            ("config", "--get", "remote.origin.url"): "git@github.com:Sapientropic/T-Sense.git\n",
            ("status", "--porcelain"): " M dashboard/src/main.tsx\n",
            ("fetch", "--prune", "origin"): "",
            ("rev-parse", "--short", "HEAD"): "abc123\n",
            ("rev-parse", "--short", "origin/main"): "def456\n",
            ("rev-list", "--left-right", "--count", "HEAD...origin/main"): "0\t2\n",
        }

        def fake_run(args, *, timeout=dashboard_server.GIT_TIMEOUT_SECONDS):
            return subprocess.CompletedProcess(args, 0, stdout=outputs[tuple(args)])

        with patch.object(dashboard_server, "_run_git", side_effect=fake_run):
            status = dashboard_server._git_update_status(fetch=True)

        self.assertEqual(status["status"], "behind")
        self.assertTrue(status["dirty"])
        self.assertFalse(status["pull_allowed"])
        self.assertEqual(status["dirty_count"], 1)
        self.assertEqual(status["repo_url"], "https://github.com/Sapientropic/T-Sense")
        self.assertIn("Commit or stash", status["message"])


    def test_update_status_allows_repairable_dashboard_lockfile_churn(self):
        outputs = {
            ("rev-parse", "--abbrev-ref", "HEAD"): "main\n",
            ("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"): "origin/main\n",
            ("config", "--get", "remote.origin.url"): "git@github.com:Sapientropic/T-Sense.git\n",
            ("status", "--porcelain"): " M dashboard/package-lock.json\n",
            ("fetch", "--prune", "origin"): "",
            ("rev-parse", "--short", "HEAD"): "abc123\n",
            ("rev-parse", "--short", "origin/main"): "def456\n",
            ("rev-list", "--left-right", "--count", "HEAD...origin/main"): "0\t2\n",
        }

        def fake_run(args, *, timeout=dashboard_server.GIT_TIMEOUT_SECONDS):
            return subprocess.CompletedProcess(args, 0, stdout=outputs[tuple(args)])

        with patch.object(dashboard_server, "_run_git", side_effect=fake_run):
            status = dashboard_server._git_update_status(fetch=True)

        self.assertEqual(status["status"], "behind")
        self.assertTrue(status["dirty"])
        self.assertTrue(status["repairable_dirty"])
        self.assertEqual(status["repairable_dirty_count"], 1)
        self.assertEqual(status["dirty_paths"], ["dashboard/package-lock.json"])
        self.assertTrue(status["pull_allowed"])
        self.assertIn("Generated Desk dependency metadata", status["message"])
        self.assertNotIn("Commit or stash", status["message"])


    def test_git_update_status_redacts_remote_and_fetch_error(self):
        secret_token = "123456:ABCDEF_secret"
        outputs = {
            ("rev-parse", "--abbrev-ref", "HEAD"): "main\n",
            ("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"): "origin/main\n",
            ("config", "--get", "remote.origin.url"): "https://ghp_private@github.com/Sapientropic/T-Sense.git\n",
            ("status", "--porcelain"): "",
            ("rev-parse", "--short", "HEAD"): "abc123\n",
            ("rev-parse", "--short", "origin/main"): "def456\n",
        }

        def fake_run(args, *, timeout=dashboard_server.GIT_TIMEOUT_SECONDS):
            if args == ["fetch", "--prune", "origin"]:
                return subprocess.CompletedProcess(
                    args,
                    1,
                    stdout="",
                    stderr=(
                        f"fatal token {secret_token} OPENAI_API_KEY=sk-localSecret12345 "
                        "argv=['git','fetch'] C:\\Users\\Administrator\\private\\repo"
                    ),
                )
            return subprocess.CompletedProcess(args, 0, stdout=outputs[tuple(args)])

        with patch.object(dashboard_server, "_run_git", side_effect=fake_run):
            status = dashboard_server._git_update_status(fetch=True)

        rendered = json.dumps(status, ensure_ascii=False)
        self.assertEqual(status["status"], "fetch_failed")
        self.assertEqual(status["repo_url"], "https://github.com/Sapientropic/T-Sense")
        self.assertNotIn("remote_url", status)
        self.assertNotIn("ghp_private", rendered)
        self.assertNotIn(secret_token, rendered)
        self.assertNotIn("sk-localSecret12345", rendered)
        self.assertNotIn("C:\\Users\\Administrator", rendered)
        self.assertNotIn("['git','fetch']", rendered)


    def test_git_update_status_reports_packaged_runtime_without_raw_git_error(self):
        def fake_run(args, *, timeout=dashboard_server.GIT_TIMEOUT_SECONDS):
            return subprocess.CompletedProcess(
                args,
                128,
                stdout="",
                stderr="fatal: not a git repository (or any of the parent directories): .git",
            )

        with patch.object(dashboard_server, "_run_git", side_effect=fake_run):
            status = dashboard_server._git_update_status(fetch=True)

        self.assertEqual(status["status"], "not_git_repository")
        self.assertEqual(status["branch"], "unknown")
        self.assertFalse(status["pull_allowed"])
        self.assertFalse(status["fetched"])
        self.assertIn("not a Git checkout", status["message"])
        self.assertNotIn("fatal:", json.dumps(status))


    def test_pull_latest_uses_fast_forward_only_after_clean_check(self):
        before = {
            "dirty": False,
            "status": "behind",
            "pull_allowed": True,
            "message": "1 upstream commit available.",
        }
        after = {
            "dirty": False,
            "status": "up_to_date",
            "pull_allowed": False,
            "message": "Local branch is up to date with upstream.",
        }

        with patch.object(dashboard_server, "_git_update_status", side_effect=[before, after]):
            with patch.object(
                dashboard_server,
                "_run_git",
                return_value=subprocess.CompletedProcess(["pull"], 0, stdout="Fast-forward\n"),
            ) as run_mock:
                with patch.object(
                    dashboard_server,
                    "_refresh_dashboard_build",
                    return_value={
                        "desk_build_status": "success",
                        "desk_build_message": "Desk was rebuilt locally.",
                        "desk_reload_recommended": True,
                    },
                ) as build_mock:
                    with patch.object(
                        dashboard_server,
                        "_schedule_dashboard_restart_after_update",
                        return_value=True,
                        create=True,
                    ) as restart_mock:
                        result = dashboard_server._git_pull_latest()

        run_mock.assert_called_once_with(["pull", "--ff-only"], timeout=60)
        build_mock.assert_called_once_with()
        restart_mock.assert_called_once_with()
        self.assertEqual(result["status"], "up_to_date")
        self.assertEqual(result["pull_output"], "Fast-forward")
        self.assertEqual(result["desk_build_status"], "success")
        self.assertTrue(result["desk_reload_recommended"])
        self.assertTrue(result["desk_restart_scheduled"])
        self.assertGreaterEqual(result["desk_reload_delay_ms"], 1500)


    def test_pull_latest_restores_repairable_dashboard_lockfile_before_pull(self):
        before = {
            "dirty": True,
            "repairable_dirty": True,
            "dirty_paths": ["dashboard/package-lock.json"],
            "status": "behind",
            "pull_allowed": True,
            "message": "2 upstream commits available. Generated Desk dependency metadata will be repaired during update.",
        }
        after_repair = {
            "dirty": False,
            "repairable_dirty": False,
            "dirty_paths": [],
            "status": "behind",
            "pull_allowed": True,
            "message": "2 upstream commits available.",
        }
        after_pull = {
            "dirty": False,
            "repairable_dirty": False,
            "dirty_paths": [],
            "status": "up_to_date",
            "pull_allowed": False,
            "message": "Local branch is up to date with upstream.",
        }
        statuses = [before, after_repair, after_pull]
        calls: list[list[str]] = []

        def fake_status(*, fetch):
            self.assertEqual(fetch, len(statuses) == 3)
            return statuses.pop(0)

        def fake_run(args, *, timeout=dashboard_server.GIT_TIMEOUT_SECONDS):
            calls.append(args)
            return subprocess.CompletedProcess(args, 0, stdout="Fast-forward\n")

        result = desk_git.git_pull_latest(
            git_update_status_fn=fake_status,
            run_git_fn=fake_run,
            refresh_desk_build_fn=lambda: {
                "desk_build_status": "success",
                "desk_build_message": "Desk was rebuilt locally.",
                "desk_reload_recommended": True,
            },
        )

        self.assertEqual(calls[0], ["restore", "--worktree", "--", "dashboard/package-lock.json"])
        self.assertEqual(calls[1], ["pull", "--ff-only"])
        self.assertTrue(result["dirty_repair_applied"])
        self.assertEqual(result["status"], "up_to_date")


    def test_pull_latest_returns_build_failure_after_successful_pull(self):
        before = {
            "dirty": False,
            "status": "behind",
            "pull_allowed": True,
            "message": "1 upstream commit available.",
        }
        after = {
            "dirty": False,
            "status": "up_to_date",
            "pull_allowed": False,
            "message": "Local branch is up to date with upstream.",
        }

        result = desk_git.git_pull_latest(
            git_update_status_fn=lambda *, fetch: before if fetch else after,
            run_git_fn=lambda args, *, timeout=dashboard_server.GIT_TIMEOUT_SECONDS: subprocess.CompletedProcess(
                args,
                0,
                stdout="Fast-forward\n",
            ),
            refresh_desk_build_fn=lambda: (_ for _ in ()).throw(desk_git.DashboardGitError("Desk rebuild failed.")),
        )

        self.assertEqual(result["status"], "up_to_date")
        self.assertEqual(result["desk_build_status"], "failed")
        self.assertEqual(result["desk_build_message"], "Desk rebuild failed.")
        self.assertFalse(result["desk_reload_recommended"])


    def test_refresh_dashboard_build_runs_dependency_sync_before_build(self):
        calls: list[list[str]] = []

        def fake_run(args, *, cwd, check, capture_output, text, timeout):
            calls.append(args)
            self.assertEqual(cwd, dashboard_server.PROJECT_ROOT / "dashboard")
            self.assertFalse(check)
            self.assertTrue(capture_output)
            self.assertTrue(text)
            self.assertEqual(timeout, dashboard_server.DESK_DASHBOARD_BUILD_TIMEOUT_SECONDS)
            return subprocess.CompletedProcess(args, 0, stdout="ok\n")

        with patch.object(dashboard_server.shutil, "which", return_value="npm"):
            with patch.object(dashboard_server.subprocess, "run", side_effect=fake_run):
                result = dashboard_server._refresh_dashboard_build()

        self.assertEqual(calls, [["npm", "ci", "--no-audit", "--no-fund"], ["npm", "run", "build"]])
        self.assertEqual(result["desk_build_status"], "success")
        self.assertTrue(result["desk_reload_recommended"])



if __name__ == "__main__":
    unittest.main()
