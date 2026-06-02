CREATE TABLE users (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE magic_tokens (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE submissions (
    user_id BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    team_rankings JSONB NOT NULL DEFAULT '[]',
    first_kill TEXT,
    first_death TEXT,
    most_kills TEXT,
    fewest_kills TEXT,
    most_kills_team TEXT,
    most_deaths TEXT,
    most_deaths_team TEXT,
    least_deaths_team TEXT,
    first_fire_cape TEXT,
    first_infernal_cape TEXT,
    first_deep_delve TEXT,
    first_voidwaker TEXT,
    first_vls TEXT,
    most_xp TEXT,
    most_quest_points TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_magic_tokens_expires_at
ON magic_tokens(expires_at);
