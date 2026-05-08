import subprocess
import unittest
from unittest.mock import patch

from scripts import dashboard_server


class DashboardServerGitTests(unittest.TestCase):
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
            ("config", "--get", "remote.origin.url"): "git@github.com:Sapientropic/tg-channel-scanner.git\n",
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
        self.assertEqual(status["repo_url"], "https://github.com/Sapientropic/tg-channel-scanner")
        self.assertIn("Commit or stash", status["message"])

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
                result = dashboard_server._git_pull_latest()

        run_mock.assert_called_once_with(["pull", "--ff-only"], timeout=60)
        self.assertEqual(result["status"], "up_to_date")
        self.assertEqual(result["pull_output"], "Fast-forward")


if __name__ == "__main__":
    unittest.main()
