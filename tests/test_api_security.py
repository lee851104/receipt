"""Passwords are stored hashed and tokens only work while they are genuine and fresh."""
import unittest
from datetime import datetime, timedelta, timezone

from src.api.security import create_token, hash_password, read_token, verify_password
from src.api.settings import Settings

SETTINGS = Settings(jwt_secret="test-secret-0123456789abcdef0123456789")


class PasswordTests(unittest.TestCase):
    def test_a_hash_hides_the_password_and_checks_it(self):
        hashed = hash_password("password123")
        self.assertNotIn("password123", hashed)
        self.assertTrue(verify_password("password123", hashed))
        self.assertFalse(verify_password("password124", hashed))

    def test_no_password_matches_a_user_without_a_hash(self):
        self.assertFalse(verify_password("anything", None))


class TokenTests(unittest.TestCase):
    def test_a_token_names_the_user_it_was_issued_for(self):
        self.assertEqual(read_token(create_token(7, SETTINGS), SETTINGS), 7)

    def test_an_expired_token_is_refused(self):
        issued = datetime.now(timezone.utc) - timedelta(minutes=SETTINGS.jwt_expire_minutes + 1)
        self.assertIsNone(read_token(create_token(7, SETTINGS, now=issued), SETTINGS))

    def test_a_token_signed_with_another_secret_is_refused(self):
        other = Settings(jwt_secret="another-secret-0123456789abcdef012345")
        self.assertIsNone(read_token(create_token(7, other), SETTINGS))

    def test_garbage_is_refused(self):
        self.assertIsNone(read_token("not.a.token", SETTINGS))


if __name__ == "__main__":
    unittest.main()
