USE slackdb;

CREATE TABLE IF NOT EXISTS pairings (
    pairing_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id1 VARCHAR(50),
    user_id2 VARCHAR(50),
    pairing_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);