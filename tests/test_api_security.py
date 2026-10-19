"""Passwords are stored hashed and tokens only work while they are genuine, fresh and complete."""
import base64
import json
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

import jwt

from src.api import security
from src.api.security import MAX_LOGIN_TEXT, create_token, hash_password, read_token, verify_password
from src.api.settings import Settings
from src.api.tables import User

SETTINGS = Settings(jwt_secret="test-secret-0123456789abcdef0123456789")
AMY = User(id=7, username="amy", display_name="Amy")


def segment(data):
    """One base64url part of a hand-built token."""
    return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()


class PasswordTests(unittest.TestCase):
    def test_a_hash_hides_the_password_and_checks_it(self):
        hashed = hash_password("password123")
        self.assertNotIn("password123", hashed)
        self.assertTrue(verify_password("password123", hashed))
        self.assertFalse(verify_password("password124", hashed))

    def test_no_password_matches_a_user_without_a_hash(self):
        for hashed in (None, ""):
            with self.subTest(hashed=hashed):
                self.assertFalse(verify_password("anything", hashed))

    def test_an_overlong_password_is_refused_without_normalising_all_of_it(self):
        hashed = hash_password("password123")
        lengths, original = [], security.normalized
        with mock.patch.object(security, "normalized", side_effect=lambda text: lengths.append(len(text)) or original(text)):
            self.assertFalse(verify_password("p" * 100_000, hashed))
        self.assertTrue(lengths)
        self.assertLessEqual(max(lengths), MAX_LOGIN_TEXT)


class TokenTests(unittest.TestCase):
    def test_a_token_names_the_user_by_id_and_key(self):
        self.assertEqual(read_token(create_token(AMY, SETTINGS), SETTINGS), (7, AMY.token_key))

    def test_every_user_gets_a_different_key(self):
        self.assertNotEqual(AMY.token_key, User(username="bob", display_name="Bob").token_key)

    def test_an_expired_token_is_refused(self):
        issued = datetime.now(timezone.utc) - timedelta(minutes=SETTINGS.jwt_expire_minutes + 1)
        self.assertIsNone(read_token(create_token(AMY, SETTINGS, now=issued), SETTINGS))

    def test_a_token_signed_with_another_secret_is_refused(self):
        other = Settings(jwt_secret="another-secret-0123456789abcdef012345")
        self.assertIsNone(read_token(create_token(AMY, other), SETTINGS))

    def test_a_token_missing_a_claim_is_refused(self):
        expires = datetime.now(timezone.utc) + timedelta(minutes=5)
        for claims in ({"sub": "7", "key": AMY.token_key}, {"key": AMY.token_key, "exp": expires},
                       {"sub": "7", "exp": expires}):
            with self.subTest(claims=sorted(claims)):
                token = jwt.encode(claims, SETTINGS.jwt_secret, algorithm="HS256")
                self.assertIsNone(read_token(token, SETTINGS))

    def test_an_unsigned_token_is_refused(self):
        expires = int((datetime.now(timezone.utc) + timedelta(minutes=5)).timestamp())
        unsigned = (segment({"alg": "none", "typ": "JWT"}) + "."
                    + segment({"sub": "7", "key": AMY.token_key, "exp": expires}) + ".")
        self.assertIsNone(read_token(unsigned, SETTINGS))

    def test_garbage_is_refused(self):
        self.assertIsNone(read_token("not.a.token", SETTINGS))


if __name__ == "__main__":
    unittest.main()
