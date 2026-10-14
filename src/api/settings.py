"""Server settings from environment variables; docs/team/overview.md section 5.10 lists them."""
from dataclasses import dataclass

CATEGORY_MODELS = ("fake", "tfidf", "embedding", "bert")
ATTRIBUTE_MODELS = ("fake", "qwen")
MIN_SECRET = 32  # characters; HS256 wants a key at least as long as its 256-bit hash


@dataclass(frozen=True)
class Settings:
    jwt_secret: str
    jwt_expire_minutes: int = 1440
    demo_mode: bool = False
    database_url: str = "sqlite:///data/app.db"
    llama_server_url: str = "http://127.0.0.1:8080"
    category_model: str = "fake"
    attributes_model: str = "fake"
    category_min_prob: float = 0.5

    @classmethod
    def from_env(cls, env):
        """Settings from a mapping such as os.environ; a weak secret or an unknown model name stops the server."""
        secret = env.get("JWT_SECRET", "")
        if len(secret) < MIN_SECRET:
            raise ValueError(f"JWT_SECRET must be at least {MIN_SECRET} characters; see .env.example")
        settings = cls(
            jwt_secret=secret,
            jwt_expire_minutes=int(env.get("JWT_EXPIRE_MINUTES", cls.jwt_expire_minutes)),
            demo_mode=env.get("DEMO_MODE", "0") == "1",
            database_url=env.get("DATABASE_URL", cls.database_url),
            llama_server_url=env.get("LLAMA_SERVER_URL", cls.llama_server_url).rstrip("/"),
            category_model=env.get("CATEGORY_MODEL", cls.category_model),
            attributes_model=env.get("ATTRIBUTES_MODEL", cls.attributes_model),
            category_min_prob=float(env.get("CATEGORY_MIN_PROB", cls.category_min_prob)),
        )
        if settings.category_model not in CATEGORY_MODELS:
            raise ValueError("CATEGORY_MODEL must be one of " + ", ".join(CATEGORY_MODELS))
        if settings.attributes_model not in ATTRIBUTE_MODELS:
            raise ValueError("ATTRIBUTES_MODEL must be one of " + ", ".join(ATTRIBUTE_MODELS))
        return settings
