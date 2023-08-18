CREATE TABLE lol_profile (

    profile_uuid UUID NOT NULL PRIMARY KEY,
    region VARCHAR(4) NOT NULL,
    username VARCHAR(16) NOT NULL,
    main_champion VARCHAR(14) NOT NULL,
    rank VARCHAR(25)

);

CREATE TABLE discord_user (

    discord_user_id BIGINT NOT NULL PRIMARY KEY,
    profile_uuid UUID REFERENCES lol_profile (profile_uuid),
    UNIQUE (profile_uuid)

);

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";