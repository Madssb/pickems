CREATE TABLE users (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    display_name TEXT NOT NULL DEFAULT 'Guest',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE sessions (
    token_hash TEXT PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '90 days'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE login_tokens (
    token_hash TEXT PRIMARY KEY,
    user_id BIGINT UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE predictions (
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
