import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


@unittest.skipUnless(os.name == "nt", "Windows batch smoke tests")
class WindowsBatchTests(unittest.TestCase):
    def test_scan_bat_without_args_reports_missing_channel_list(self):
        result = subprocess.run(
            ["cmd", "/c", "scripts\\scan.bat"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("Missing channel list", result.stdout + result.stderr)

    def test_setup_bat_config_branch_smoke_with_install_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["TG_SCANNER_SETUP_SKIP_INSTALL"] = "1"
            env["TG_SCANNER_CONFIG_DIR"] = tmp

            result = subprocess.run(
                ["cmd", "/c", "setup.bat"],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
            )

            output = result.stdout + result.stderr
            config_exists = (Path(tmp) / "config.toml").exists()

        self.assertEqual(result.returncode, 0, output)
        self.assertIn("Setup complete", output)
        self.assertTrue(config_exists)


if __name__ == "__main__":
    unittest.main()
