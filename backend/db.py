"""PostgreSQL operations for DMM All Stars Pickems."""
import os
import json
from datetime import datetime
from pathlib import Path
from typing import NotRequired, TypedDict

import asyncpg
from dotenv import load_dotenv


PREDICTION_FIELDS = [
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


class SessionParticipant(TypedDict):
    id: int
    display_name: str


class Predictions(TypedDict):
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
    """Return the shared PostgreSQL connection pool."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DATABASE_URL)
    return _pool


async def get_participant_by_session_hash(
    token_hash: str,
) -> SessionParticipant | None:
    """Return the participant belonging to a valid browser session."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        SELECT
            users.id,
            users.display_name
        FROM sessions
        JOIN users ON users.id = sessions.user_id
        WHERE sessions.token_hash = $1
          AND sessions.expires_at > NOW();
        """,
        token_hash,
    )
    if row is None:
        return None
    return {
        "id": row["id"],
        "display_name": row["display_name"],
    }


async def update_display_name(
    participant_id: int,
    display_name: str,
) -> SessionParticipant:
    """Update and return a participant's display name."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        UPDATE users
        SET display_name = $2
        WHERE id = $1
        RETURNING id, display_name;
        """,
        participant_id,
        display_name,
    )
    return {
        "id": row["id"],
        "display_name": row["display_name"],
    }


async def create_participant_with_session(
    token_hash: str,
) -> SessionParticipant:
    """Create an anonymous participant and bind a browser session to it."""
    pool = await get_pool()
    async with pool.acquire() as connection:
        async with connection.transaction():
            participant = await connection.fetchrow(
                """
                INSERT INTO users DEFAULT VALUES
                RETURNING id, display_name;
                """
            )
            await connection.execute(
                """
                INSERT INTO sessions (token_hash, user_id)
                VALUES ($1, $2);
                """,
                token_hash,
                participant["id"],
            )

    return {
        "id": participant["id"],
        "display_name": participant["display_name"],
    }


async def upsert_login_token(participant_id: int, token_hash: str) -> None:
    """Create or rotate a participant's reusable login token."""
    pool = await get_pool()
    await pool.execute(
        """
        INSERT INTO login_tokens (
            user_id,
            token_hash
        )
        VALUES (
            $1,
            $2
        )
        ON CONFLICT (user_id) DO UPDATE
        SET
            token_hash = EXCLUDED.token_hash,
            created_at = NOW();
        """,
        participant_id,
        token_hash,
    )


async def get_participant_id_by_login_token_hash(token_hash: str) -> int | None:
    """Return the participant ID belonging to a reusable login token."""
    pool = await get_pool()
    return await pool.fetchval(
        """
        SELECT user_id
        FROM login_tokens
        WHERE token_hash = $1;
        """,
        token_hash,
    )


async def create_session(token_hash: str, participant_id: int) -> None:
    """Create a browser session for a participant."""
    pool = await get_pool()
    await pool.execute(
        """
        INSERT INTO sessions (
            token_hash,
            user_id
        )
        VALUES (
            $1,
            $2
        );
        """,
        token_hash,
        participant_id,
    )


async def delete_session(token_hash: str) -> None:
    """Delete a browser session."""
    pool = await get_pool()
    await pool.execute(
        """
        DELETE FROM sessions
        WHERE token_hash = $1;
        """,
        token_hash,
    )


async def upsert_predictions(
    participant_id: int,
    predictions: Predictions,
) -> datetime:
    """Insert or replace a participant's predictions."""
    pool = await get_pool()

    columns = ["user_id", *PREDICTION_FIELDS]
    values = [
        participant_id,
        *[
            json.dumps(predictions.get(field, []))
            if field == "team_rankings"
            else predictions.get(field)
            for field in PREDICTION_FIELDS
        ],
    ]

    placeholders = ", ".join(f"${index}" for index in range(1, len(values) + 1))
    column_sql = ", ".join(columns)
    update_sql = ", ".join(
        f"{field} = EXCLUDED.{field}"
        for field in PREDICTION_FIELDS
    )

    return await pool.fetchval(
        f"""
        INSERT INTO predictions (
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


async def get_predictions(participant_id: int) -> Predictions | None:
    """Return a participant's saved predictions, if present."""
    pool = await get_pool()
    row = await pool.fetchrow(
        f"""
        SELECT
            {", ".join(PREDICTION_FIELDS)}
        FROM predictions
        WHERE user_id = $1;
        """,
        participant_id,
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
