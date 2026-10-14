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


if __name__ == "__main__":
    unittest.main()
