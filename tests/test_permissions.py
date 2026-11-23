import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class PermissionsTest(unittest.TestCase):
    def test_run_may_start_only_named_programs_and_edit_none_of_them(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "p")
            shutil.copytree(os.path.join(REPO, "projects-example", "acme"), p)
            os.makedirs(os.path.join(p, "readers"))
            open(os.path.join(p, "readers", "own.py"), "w").close()
            with open(os.path.join(p, "config.json")) as f:
                cfg = json.load(f)
            cfg["sources"][0]["reader"] = "readers/own.py"
            cfg["review_page"] = "http://127.0.0.1:47821"
            with open(os.path.join(p, "config.json"), "w") as f:
                json.dump(cfg, f)
            env = {**os.environ, "CONTEXT_INBOX_MCP_CONFIG": os.path.join(d, "server.json")}
            out = subprocess.run(
                [sys.executable, os.path.join(REPO, "runner", "permissions.py"), p],
                capture_output=True,
                text=True,
                env=env,
                check=True,
            )
            perms = json.loads(out.stdout)["permissions"]
            real = os.path.abspath(p)
            self.assertEqual(perms["defaultMode"], "default")
            resolved = os.path.realpath(p)
            self.assertIn(f"Bash(python3 {resolved}/readers/own.py:*)", perms["allow"])
            self.assertFalse([a for a in perms["allow"] if a.startswith("Bash(git")])
            attio = [a for a in perms["allow"] if "attio/upload.py" in a]
            self.assertIn(f"Bash(python3 {REPO}/integrations/attio/upload.py {resolved}/config.json:*)", attio)
            # One rule per spelling of the path: two on macOS, where /var links to /private/var, one on Linux.
            spellings = {os.path.join(real, "config.json"), os.path.join(resolved, "config.json")}
            self.assertEqual(len(attio), len(spellings))
            self.assertIn(f"Edit(/{resolved}/readers/**)", perms["deny"])
            self.assertNotIn("Write", perms["allow"])
            self.assertNotIn("Edit", perms["allow"])
            self.assertIn(f"Edit(/{real}/**)", perms["allow"])
            self.assertIn(f"Edit(/{REPO}/**)", perms["deny"])
            self.assertIn(f"Read(/{os.path.abspath(d)}/server.json)", perms["deny"])
            self.assertIn(f"Read(/{os.path.realpath(d)}/server.json)", perms["deny"])


if __name__ == "__main__":
    unittest.main()
