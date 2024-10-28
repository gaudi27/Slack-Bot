CREATE DATABASE IF NOT EXISTS slackdb;

USE slackdb;

CREATE TABLE IF NOT EXISTS user_profiles (
    user_id VARCHAR(50) PRIMARY KEY,
    full_name VARCHAR(100),
    pronouns VARCHAR(50),
    location VARCHAR(100),
    hometown VARCHAR(100),
    education VARCHAR(200),
    languages VARCHAR(200),
    hobbies VARCHAR(200),
    birthday VARCHAR(50),
    ask_me_about TEXT,
    bio TEXT
);
