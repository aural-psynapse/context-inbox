import json
import os
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECK = os.path.join(REPO, "connector", "check.py")
PAGE = "https://claude.ai/artifact/abc123"


def check(cfg, files=()):
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "p")
        os.makedirs(p)
        open(os.path.join(p, "RULES.md"), "w").close()
        for f in files:
            open(os.path.join(p, f), "w").close()
        with open(os.path.join(p, "config.json"), "w") as fh:
            fh.write(cfg if isinstance(cfg, str) else json.dumps(cfg))
        r = subprocess.run([sys.executable, CHECK, d], capture_output=True, text=True)
        return r.returncode, r.stderr


def slack(channels, **extra):
    return {
        "review_page": PAGE,
        "sources": [{"id": "s", "type": "slack", "reader": "slack", "channels": channels, **extra}],
        "destinations": [{"id": "d", "type": "linear"}],
    }


class ConnectorTest(unittest.TestCase):
    def test_good(self):
        self.assertEqual(check(slack([{"id": "C0123456789", "feeds": ["d"]}]))[0], 0)

    def test_extra_keys_pass(self):
        self.assertEqual(check(slack([{"id": "C0123456789", "feeds": ["d"], "tag": "x"}], base_url="https://x"))[0], 0)

    def test_own_reader_and_guide(self):
        cfg = {
            "review_page": PAGE,
            "sources": [
                {"id": "s", "type": "forum", "reader": "r.py", "channels": [{"id": "support", "feeds": ["d"]}]}
            ],
            "destinations": [{"id": "d", "type": "notion", "guide": "./g.md"}],
        }
        self.assertEqual(check(cfg, ["r.py", "g.md"])[0], 0)

    def test_errors(self):
        bad = {
            "channel name": slack([{"id": "general", "feeds": ["d"]}]),
            "misspelt key": slack([{"id": "C0123456789", "feed": ["d"]}]),
            "wrong case": slack([{"id": "C0123456789", "feeds": ["d"], "Private": True}]),
            "repeated channel": slack([{"id": "C0123456789", "feeds": ["d"]}, {"id": "C0123456789", "feeds": ["d"]}]),
            "unknown destination": slack([{"id": "C0123456789", "feeds": ["x"]}]),
            "channel id list": slack([{"id": ["C1"], "feeds": ["d"]}]),
            "placeholder page": {
                **slack([{"id": "C0123456789", "feeds": ["d"]}]),
                "review_page": "https://claude.ai/artifact/<id>",
            },
            "path outside": {
                **slack([{"id": "C0123456789", "feeds": ["d"]}]),
                "destinations": [{"id": "d", "type": "x", "guide": "../../etc/hosts"}],
            },
            "empty": {"review_page": PAGE, "sources": [], "destinations": []},
            "not an object": "[1, 2]",
        }
        for label, cfg in bad.items():
            with self.subTest(label):
                code, err = check(cfg)
                self.assertEqual(code, 1, err)
                self.assertNotIn("Traceback", err)


if __name__ == "__main__":
    unittest.main()
