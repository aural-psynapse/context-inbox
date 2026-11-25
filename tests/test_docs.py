import os
import re
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(*parts):
    with open(os.path.join(REPO, *parts)) as f:
        return f.read()


class DocsTest(unittest.TestCase):
    """The docs name what the code ships, so a new script, integration or page option cannot go unmentioned."""

    def setUp(self):
        self.docs = {name: read(name) for name in ("README.md", "AGENTS.md", "llms.txt")}
        self.runner_docs = read("runner", "README.md")

    def test_each_runner_script_is_named(self):
        for script in sorted(os.listdir(os.path.join(REPO, "runner"))):
            if not script.endswith(".sh"):
                continue
            with self.subTest(script):
                self.assertIn(f"runner/{script}", self.docs["llms.txt"] + self.docs["README.md"])
                self.assertIn(script, self.runner_docs)

    def test_each_integration_is_named(self):
        for name in sorted(os.listdir(os.path.join(REPO, "integrations"))):
            if not os.path.isdir(os.path.join(REPO, "integrations", name)) or name.startswith("__"):
                continue
            with self.subTest(name):
                self.assertIn(f"integrations/{name}/", self.docs["llms.txt"])

    def test_each_review_page_option_is_named(self):
        flags = set(re.findall(r'add_argument\("(--[a-z-]+)"', read("integrations", "sqlite", "serve.py")))
        guide = read("integrations", "sqlite", "guide.md")
        for flag in sorted(flags - {"--port", "--host", "--config"}):
            with self.subTest(flag):
                self.assertIn(flag, self.docs["README.md"])
                self.assertIn(flag, self.docs["AGENTS.md"])
                self.assertIn(flag, guide)


if __name__ == "__main__":
    unittest.main()
