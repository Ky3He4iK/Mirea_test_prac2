CREATE TABLE IF NOT EXISTS stats
(
    dice INTEGER NOT NULL,
    result INTEGER NOT NULL,
    count INTEGER NOT NULL,
    PRIMARY KEY(dice, result)
);

CREATE TABLE IF NOT EXISTS custom_rolls
(
    user_id INTEGER NOT NULL,
    shortcut TEXT NOT NULL,
    count INTEGER NOT NULL,
    dice INTEGER NOT NULL,
    mod_act TEXT(1) NULL,
    mod_num TEXT NULL,
    PRIMARY KEY(user_id, shortcut)
);

CREATE TABLE IF NOT EXISTS global_rolls
(
    shortcut TEXT NOT NULL PRIMARY KEY,
    count INTEGER NOT NULL,
    dice INTEGER NOT NULL,
    mod_act TEXT(1) NULL,
    mod_num TEXT NULL
);

CREATE TABLE IF NOT EXISTS counted_rolls
(
    chat_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    command TEXT NOT NULL,
    count INTEGER NOT NULL,
    PRIMARY KEY(chat_id, user_id, command)
);
