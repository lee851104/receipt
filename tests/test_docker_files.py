"""The Docker files keep private data out of the image and run the container start-up (design D14)."""
import unittest

from src.api.db import ROOT

IGNORED = ROOT / ".dockerignore"


class DockerFileTests(unittest.TestCase):
    def test_the_image_takes_only_the_service(self):
        lines = [line.split() for line in (ROOT / "Dockerfile").read_text(encoding="utf-8").splitlines()]
        copies = [words[1:] for words in lines if words and words[0] == "COPY"]
        self.assertEqual(copies, [["requirements.txt", "requirements-docker.txt", "./"], ["configs", "./configs"],
                                  ["src", "./src"]])
        self.assertIn(["FROM", "python:3.12-slim"], lines)
        self.assertIn('CMD ["python", "-m", "src.api.container"]', (ROOT / "Dockerfile").read_text(encoding="utf-8"))

    def test_the_ignore_file_names_every_kind_of_private_file(self):
        patterns = {line.strip() for line in IGNORED.read_text(encoding="utf-8").splitlines()
                    if line.strip() and not line.startswith("#")}
        for pattern in ("rawdata/", "data/", "**/*.csv", "**/*.rar", "**/*.zip", "**/*.7z", ".env", ".env.*",
                        "models/", "runtime/", "experiments/", "src/web/", "**/*-data.js", ".git/"):
            with self.subTest(pattern=pattern):
                self.assertIn(pattern, patterns)

    def test_compose_publishes_the_port_on_this_computer_only_and_keeps_two_volumes(self):
        text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn('"127.0.0.1:8000:8000"', text)
        for volume in ("db:/data", "models:/models"):
            self.assertIn(volume, text)
        self.assertNotIn("JWT_SECRET=", text)  # the container keeps its own in the data volume


if __name__ == "__main__":
    unittest.main()
