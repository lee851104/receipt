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
                        "**/.env", "**/.env.*", "**/*.db", "invoice-insights-private.html", "**/results/",
                        "**/outputs/", "models/", "runtime/", "experiments/", "src/web/", "**/*-data.js", ".git/"):
            with self.subTest(pattern=pattern):
                self.assertIn(pattern, patterns)

    def test_compose_publishes_the_port_on_this_computer_only_and_keeps_two_volumes(self):
        text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn('"127.0.0.1:8000:8000"', text)
        for volume in ("db:/data", "models:/models"):
            self.assertIn(volume, text)
        self.assertNotIn("JWT_SECRET=", text)  # the container keeps its own in the data volume

    def test_compose_takes_the_llama_server_address_from_its_own_variable(self):
        # Compose reads the root .env, which start.bat makes with LLAMA_SERVER_URL=http://127.0.0.1:8080: inside the
        # container that address is the container itself, not the computer running llama-server.
        text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn("LLAMA_SERVER_URL: ${DOCKER_LLAMA_SERVER_URL:-http://host.docker.internal:8080}", text)
        self.assertNotIn("${LLAMA_SERVER_URL", text)

    def test_compose_passes_the_attribute_model_choice_with_the_fake_as_default(self):
        text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn("ATTRIBUTES_MODEL: ${ATTRIBUTES_MODEL:-fake}", text)


class WorkflowTests(unittest.TestCase):
    def test_ci_runs_both_test_suites_with_the_fakes_and_builds_the_image(self):
        text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        for needed in ('python-version: "3.12"', 'node-version: "24"', "python -m unittest discover -s tests",
                       'node --test "tests/*.test.cjs"', "CATEGORY_MODEL: fake", "ATTRIBUTES_MODEL: fake",
                       "docker build", "/api/health"):
            with self.subTest(needed=needed):
                self.assertIn(needed, text)

    def test_ci_starts_the_compose_demo_and_checks_its_demo_users(self):
        # What a person runs (docker compose up: DEMO_MODE=1, the volumes, 127.0.0.1:8000) is what CI starts.
        text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        for needed in ("docker compose up", '"demo_mode":true', "/api/auth/demo-users", "docker compose logs",
                       "docker compose down -v"):
            with self.subTest(needed=needed):
                self.assertIn(needed, text)
        self.assertNotIn("docker run -d", text)

    def test_ci_always_tears_the_demo_down_and_cannot_hang_or_write(self):
        text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertRegex(text, r"if: always\(\)\s+run: docker compose down -v")
        self.assertEqual(text.count("timeout-minutes: 15"), 2)  # the tests job and the docker job
        self.assertIn("permissions:\n  contents: read", text)


if __name__ == "__main__":
    unittest.main()
