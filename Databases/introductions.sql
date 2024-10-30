USE slackdb;

CREATE TABLE IF NOT EXISTS introductions (
    intro_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(50),
    intro_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
