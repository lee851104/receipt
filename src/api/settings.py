"""Server settings from environment variables; docs/team/overview.md section 5.10 lists them."""
from dataclasses import dataclass, field

CATEGORY_MODELS = ("fake", "tfidf", "embedding", "bert")
ATTRIBUTE_MODELS = ("fake", "qwen")
MIN_SECRET = 32  # characters; HS256 wants a key at least as long as its 256-bit hash


def text(env, name, default):
    """A value from env without surrounding spaces; the default when it is unset or blank."""
    return env.get(name, "").strip() or default


def number(env, name, default, kind):
    """text() read as kind (int or float); a value that is not a number stops the server, naming the variable."""
    value = text(env, name, None)
    if value is None:
        return default
    try:
        return kind(value)
    except ValueError:
        raise ValueError(f"{name} must be a number, got {value!r}") from None


@dataclass(frozen=True)
class Settings:
    jwt_secret: str = field(repr=False)  # kept out of printed settings and failing test messages
    jwt_expire_minutes: int = 1440
    demo_mode: bool = False
    database_url: str = "sqlite:///data/app.db"
    llama_server_url: str = "http://127.0.0.1:8080"
    category_model: str = "fake"
    attributes_model: str = "fake"
    category_min_prob: float = 0.5

    @classmethod
    def from_env(cls, env):
        """Settings from a mapping such as os.environ, where a blank value means the default. A weak secret,
        a bad number or an unknown model name stops the server with a message naming the variable."""
        secret = text(env, "JWT_SECRET", "")
        if len(secret) < MIN_SECRET:
            raise ValueError(f"JWT_SECRET must be at least {MIN_SECRET} characters; see .env.example")
        settings = cls(
            jwt_secret=secret,
            jwt_expire_minutes=number(env, "JWT_EXPIRE_MINUTES", cls.jwt_expire_minutes, int),
            demo_mode=text(env, "DEMO_MODE", "0") == "1",
            database_url=text(env, "DATABASE_URL", cls.database_url),
            llama_server_url=text(env, "LLAMA_SERVER_URL", cls.llama_server_url).rstrip("/"),
            category_model=text(env, "CATEGORY_MODEL", cls.category_model),
            attributes_model=text(env, "ATTRIBUTES_MODEL", cls.attributes_model),
            category_min_prob=number(env, "CATEGORY_MIN_PROB", cls.category_min_prob, float),
        )
        if settings.jwt_expire_minutes <= 0:
            raise ValueError(f"JWT_EXPIRE_MINUTES must be above 0, got {settings.jwt_expire_minutes}")
        # Written this way round so nan fails too.
        if not 0 <= settings.category_min_prob <= 1:
            raise ValueError(f"CATEGORY_MIN_PROB must be from 0 to 1, got {settings.category_min_prob}")
        if settings.category_model not in CATEGORY_MODELS:
            raise ValueError(f"CATEGORY_MODEL must be one of {', '.join(CATEGORY_MODELS)}; got {settings.category_model!r}")
        if settings.attributes_model not in ATTRIBUTE_MODELS:
            raise ValueError(f"ATTRIBUTES_MODEL must be one of {', '.join(ATTRIBUTE_MODELS)}; got {settings.attributes_model!r}")
        # Only plain SQLite URLs get the root-relative path, foreign keys and write-ahead logging (db.make_engine).
        # The message leaves the value out: a rejected URL may carry a password.
        if settings.database_url != "sqlite://" and not settings.database_url.startswith("sqlite:///"):
            raise ValueError("DATABASE_URL must be a SQLite URL such as sqlite:///data/app.db")
        return settings
