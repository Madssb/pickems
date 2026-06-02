"""PostgreSQL queries for the Dmm All Stars Pickems & Crystal Ball project backend.
"""
import os
import json
from datetime import datetime
from pathlib import Path
from typing import NotRequired, TypedDict

import asyncpg
from dotenv import load_dotenv


SUBMISSION_FIELDS = [
    "team_rankings",
    "first_kill",
    "first_death",
    "most_kills",
    "fewest_kills",
    "most_kills_team",
    "most_deaths",
    "most_deaths_team",
    "least_deaths_team",
    "first_fire_cape",
    "first_infernal_cape",
    "first_deep_delve",
    "first_voidwaker",
    "first_vls",
    "most_xp",
    "most_quest_points",
]
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise SystemExit("DATABASE_URL is not set")

_pool: asyncpg.Pool | None = None


class SessionUser(TypedDict):
    id: int
    email: str
    display_name: str


class Submission(TypedDict):
    team_rankings: NotRequired[list[str]]
    first_kill: NotRequired[str | None]
    first_death: NotRequired[str | None]
    most_kills: NotRequired[str | None]
    fewest_kills: NotRequired[str | None]
    most_kills_team: NotRequired[str | None]
    most_deaths: NotRequired[str | None]
    most_deaths_team: NotRequired[str | None]
    least_deaths_team: NotRequired[str | None]
    first_fire_cape: NotRequired[str | None]
    first_infernal_cape: NotRequired[str | None]
    first_deep_delve: NotRequired[str | None]
    first_voidwaker: NotRequired[str | None]
    first_vls: NotRequired[str | None]
    most_xp: NotRequired[str | None]
    most_quest_points: NotRequired[str | None]


async def get_pool() -> asyncpg.Pool:
    """Shared pool by all postgre ops for backend
    """
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
        SET display_name = EXCLUDED.display_name
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


async def create_session(session_id: str, user_id: int) -> None:
    """Create a browser session for a logged-in user."""
    pool = await get_pool()
    await pool.execute(
        """
        INSERT INTO sessions (
            id,
            user_id,
            expires_at
        )
        VALUES (
            $1,
            $2,
            NOW() + INTERVAL '30 days'
        );
        """,
        session_id,
        user_id,
    )


async def delete_session(session_id: str) -> None:
    """Delete a browser session."""
    pool = await get_pool()
    await pool.execute(
        """
        DELETE FROM sessions
        WHERE id = $1;
        """,
        session_id,
    )


async def get_user_by_session(session_id: str) -> SessionUser | None:
    """Return safe user display fields for a valid, unexpired session."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        SELECT
            users.id,
            users.email,
            users.display_name
        FROM sessions
        JOIN users ON users.id = sessions.user_id
        WHERE sessions.id = $1
          AND sessions.expires_at > NOW();
        """,
        session_id,
    )
    if row is None:
        return None
    return {
        "id": row["id"],
        "email": row["email"],
        "display_name": row["display_name"],
    }


async def upsert_submission(user_id: int, submission: Submission) -> datetime:
    """Insert or update user submitted predictions"""
    pool = await get_pool()

    columns = ["user_id", *SUBMISSION_FIELDS]
    values = [
        user_id,
        *[
            json.dumps(submission.get(field, []))
            if field == "team_rankings"
            else submission.get(field)
            for field in SUBMISSION_FIELDS
        ],
    ]

    placeholders = ", ".join(f"${index}" for index in range(1, len(values) + 1))
    column_sql = ", ".join(columns)
    update_sql = ", ".join(
        f"{field} = EXCLUDED.{field}"
        for field in SUBMISSION_FIELDS
    )

    return await pool.fetchval(
        f"""
        INSERT INTO submissions (
            {column_sql}
        )
        VALUES (
            {placeholders}
        )
        ON CONFLICT (user_id) DO UPDATE
        SET
            {update_sql},
            updated_at = NOW()
        RETURNING updated_at;
        """,
        *values,
    )


async def get_user_id_by_session_id(session_id: str) -> int | None:
    """Return the user id for a valid, unexpired session."""
    pool = await get_pool()
    return await pool.fetchval(
        """
        SELECT user_id
        FROM sessions
        WHERE id = $1
          AND expires_at > NOW();
        """,
        session_id,
    )

async def get_user_predictions(user_id: int) -> Submission | None:
    """Return saved predictions for a user, if present."""
    pool = await get_pool()
    row = await pool.fetchrow(
        f"""
        SELECT
            {", ".join(SUBMISSION_FIELDS)}
        FROM submissions
        WHERE user_id = $1;
        """,
        user_id,
    )
    if row is None:
        return None

    team_rankings = row["team_rankings"]
    if isinstance(team_rankings, str):
        team_rankings = json.loads(team_rankings)

    return {
        "team_rankings": team_rankings,
        "first_kill": row["first_kill"],
        "first_death": row["first_death"],
        "most_kills": row["most_kills"],
        "fewest_kills": row["fewest_kills"],
        "most_kills_team": row["most_kills_team"],
        "most_deaths": row["most_deaths"],
        "most_deaths_team": row["most_deaths_team"],
        "least_deaths_team": row["least_deaths_team"],
        "first_fire_cape": row["first_fire_cape"],
        "first_infernal_cape": row["first_infernal_cape"],
        "first_deep_delve": row["first_deep_delve"],
        "first_voidwaker": row["first_voidwaker"],
        "first_vls": row["first_vls"],
        "most_xp": row["most_xp"],
        "most_quest_points": row["most_quest_points"],
    }
