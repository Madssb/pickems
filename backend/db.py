import os
from pathlib import Path
from datetime import datetime

import asyncpg
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise SystemExit("DATABASE_URL is not set")

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DATABASE_URL)
    return _pool


async def instantiate_magic_token(user_id: int, token_hash: str) -> None:
    """instantiate magic token record, binding user id to a single-use token.
    """
    pool = await get_pool()
    await pool.execute(
        """
        INSERT INTO magic_tokens (
            user_id,
            token_hash,
            expires_at
        )
        VALUES (
            $1,
            $2,
            NOW() + INTERVAL '24 hours'
        );
        """,
        user_id,
        token_hash,
    )


async def get_or_create_user_id_by_email(email: str, display_name: str | None = None) -> int:
    """Return the user id for an email, creating the user when missing."""
    pool = await get_pool()
    return await pool.fetchval(
        """
        INSERT INTO users (
            email,
            display_name
        )
        VALUES (
            $1,
            COALESCE($2, $1)
        )
        ON CONFLICT (email) DO UPDATE
        SET email = EXCLUDED.email
        RETURNING id;
        """,
        email,
        display_name,
    )

async def consume_magic_link(token_hash: str) -> int | None:
    """Consume a valid magic link and return its user id."""
    pool = await get_pool()
    return await pool.fetchval(
        """
        UPDATE magic_tokens
        SET used_at = NOW()
        WHERE token_hash = $1
          AND used_at IS NULL
          AND expires_at > NOW()
        RETURNING user_id;
        """,
        token_hash,
    )


async def create_session(user_id: int):
    
