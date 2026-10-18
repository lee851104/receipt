"""Settings come from the environment, with the defaults the team overview lists."""
import unittest

from src.api.settings import Settings

SECRET = "s" * 32


class SettingsTests(unittest.TestCase):
    def test_only_the_secret_is_required_and_the_rest_has_the_listed_defaults(self):
        settings = Settings.from_env({"JWT_SECRET": SECRET})
        self.assertEqual(settings, Settings(
            jwt_secret=SECRET, jwt_expire_minutes=1440, demo_mode=False, database_url="sqlite:///data/app.db",
            llama_server_url="http://127.0.0.1:8080", category_model="fake", attributes_model="fake",
            category_min_prob=0.5))

    def test_every_variable_is_read(self):
        settings = Settings.from_env({
            "JWT_SECRET": SECRET, "JWT_EXPIRE_MINUTES": "60", "DEMO_MODE": "1", "DATABASE_URL": "sqlite://",
            "LLAMA_SERVER_URL": "http://10.0.0.5:8080/", "CATEGORY_MODEL": "bert", "ATTRIBUTES_MODEL": "qwen",
            "CATEGORY_MIN_PROB": "0.6"})
        self.assertEqual(settings, Settings(
            jwt_secret=SECRET, jwt_expire_minutes=60, demo_mode=True, database_url="sqlite://",
            llama_server_url="http://10.0.0.5:8080", category_model="bert", attributes_model="qwen",
            category_min_prob=0.6))

    def test_demo_mode_is_on_only_for_exactly_1(self):
        for value in ("0", "true", "yes", ""):
            with self.subTest(value=value):
                self.assertFalse(Settings.from_env({"JWT_SECRET": SECRET, "DEMO_MODE": value}).demo_mode)

    def test_a_missing_or_short_secret_stops_the_server(self):
        for env in ({}, {"JWT_SECRET": ""}, {"JWT_SECRET": "s" * 31}):
            with self.subTest(env=env), self.assertRaisesRegex(ValueError, "JWT_SECRET"):
                Settings.from_env(env)

    def test_unknown_model_names_stop_the_server(self):
        for key in ("CATEGORY_MODEL", "ATTRIBUTES_MODEL"):
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, key):
                Settings.from_env({"JWT_SECRET": SECRET, key: "gpt"})

    def test_a_database_other_than_plain_sqlite_stops_the_server(self):
        for url in ("postgresql://localhost/app", "sqlite+pysqlite:///data/app.db", "sqlite://foo",
                    "postgresql://amy:secret@localhost/app"):
            with self.subTest(url=url), self.assertRaisesRegex(ValueError, "DATABASE_URL") as caught:
                Settings.from_env({"JWT_SECRET": SECRET, "DATABASE_URL": url})
            # A rejected URL may carry a password, so the message never repeats it.
            self.assertNotIn(url, str(caught.exception))

    def test_blank_values_mean_the_default(self):
        settings = Settings.from_env({"JWT_SECRET": SECRET, "JWT_EXPIRE_MINUTES": "", "DATABASE_URL": "  ",
                                      "CATEGORY_MODEL": "", "CATEGORY_MIN_PROB": " "})
        self.assertEqual(settings, Settings(jwt_secret=SECRET))

    def test_spaces_around_values_are_ignored(self):
        settings = Settings.from_env({"JWT_SECRET": f" {SECRET} ", "DEMO_MODE": " 1 ", "CATEGORY_MODEL": "tfidf ",
                                      "ATTRIBUTES_MODEL": " qwen", "JWT_EXPIRE_MINUTES": " 30 "})
        self.assertEqual((settings.jwt_secret, settings.demo_mode, settings.category_model,
                          settings.attributes_model, settings.jwt_expire_minutes), (SECRET, True, "tfidf", "qwen", 30))

    def test_bad_or_out_of_range_numbers_stop_the_server_naming_the_variable(self):
        cases = [("JWT_EXPIRE_MINUTES", value) for value in ("abc", "1.5", "0", "-5")]
        cases += [("CATEGORY_MIN_PROB", value) for value in ("abc", "1.5", "-0.1", "nan")]
        for key, value in cases:
            with self.subTest(key=key, value=value), self.assertRaisesRegex(ValueError, key):
                Settings.from_env({"JWT_SECRET": SECRET, key: value})

    def test_the_category_model_folder_repo_and_revision_have_defaults(self):
        settings = Settings.from_env({"JWT_SECRET": SECRET})
        self.assertEqual((settings.category_model_dir, settings.category_model_repo, settings.category_model_revision),
                         ("models/category", "", ""))

    def test_a_repo_needs_a_fixed_revision(self):
        with self.assertRaisesRegex(ValueError, "CATEGORY_MODEL_REVISION"):
            Settings.from_env({"JWT_SECRET": SECRET, "CATEGORY_MODEL_REPO": "someone/receipt-bert"})
        settings = Settings.from_env({"JWT_SECRET": SECRET, "CATEGORY_MODEL_REPO": " someone/receipt-bert ",
                                      "CATEGORY_MODEL_REVISION": "abc123", "CATEGORY_MODEL_DIR": "/models/category"})
        self.assertEqual((settings.category_model_repo, settings.category_model_revision, settings.category_model_dir),
                         ("someone/receipt-bert", "abc123", "/models/category"))

    def test_a_space_without_a_repo_names_the_repo_not_the_revision(self):
        # The revision and the checksum are fine here: the one thing missing is where the model comes from, and the
        # message used to blame the revision.
        env = {"JWT_SECRET": SECRET, "CATEGORY_MODEL_REPO_TYPE": "space", "CATEGORY_MODEL_REVISION": "a" * 40,
               "CATEGORY_MODEL_SHA256": "b" * 64}
        message = ("CATEGORY_MODEL_REPO must name the protected Space whenever CATEGORY_MODEL_REPO_TYPE=space")
        for changes in ({}, {"CATEGORY_MODEL_REVISION": ""}, {"CATEGORY_MODEL_REPO": "  "}):
            with self.subTest(changes=changes), self.assertRaises(ValueError) as caught:
                Settings.from_env({**env, **changes})
            self.assertEqual(str(caught.exception), message)

    def test_a_space_with_a_repo_still_needs_a_full_commit_and_a_checksum(self):
        env = {"JWT_SECRET": SECRET, "CATEGORY_MODEL_REPO_TYPE": "space", "CATEGORY_MODEL_REPO": "someone/receipt-bert",
               "CATEGORY_MODEL_REVISION": "a" * 40, "CATEGORY_MODEL_SHA256": "b" * 64}
        self.assertEqual(Settings.from_env(env).category_model_repo, "someone/receipt-bert")
        for changes, message in (({"CATEGORY_MODEL_REVISION": "abc123"},
                                  "CATEGORY_MODEL_REVISION must be a full commit for a Space"),
                                 ({"CATEGORY_MODEL_SHA256": ""}, "CATEGORY_MODEL_SHA256 is required for a Space")):
            with self.subTest(changes=changes), self.assertRaises(ValueError) as caught:
                Settings.from_env({**env, **changes})
            self.assertEqual(str(caught.exception), message)

    def test_the_secret_is_never_printed(self):
        self.assertNotIn(SECRET, repr(Settings.from_env({"JWT_SECRET": SECRET})))


if __name__ == "__main__":
    unittest.main()
