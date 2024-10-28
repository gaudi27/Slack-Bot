import mysql.connector

def connect_to_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="your_password",
        database="yourdatabase"
    )


def save_profile_to_db(user_id, profile):
    db = connect_to_db()
    cursor = db.cursor()

    # Upsert query: Insert new row if user_id doesn't exist, otherwise update the existing row
    query = """
    INSERT INTO user_profiles (user_id, full_name, pronouns, location, hometown, education, languages, hobbies, birthday, ask_me_about, bio)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
    full_name = VALUES(full_name),
    pronouns = VALUES(pronouns),
    location = VALUES(location),
    hometown = VALUES(hometown),
    education = VALUES(education),
    languages = VALUES(languages),
    hobbies = VALUES(hobbies),
    birthday = VALUES(birthday),
    ask_me_about = VALUES(ask_me_about),
    bio = VALUES(bio)
    """
    cursor.execute(query, (
        user_id,
        profile.get('full_name', ''),
        profile.get('pronouns', ''),
        profile.get('location', ''),
        profile.get('hometown', ''),
        profile.get('education', ''),
        profile.get('languages', ''),
        profile.get('hobbies', ''),
        profile.get('birthday', ''),
        profile.get('ask_me_about', ''),
        profile.get('bio', '')
    ))

    db.commit()
    cursor.close()
    db.close()


def load_profile_from_db(user_id):
    db = connect_to_db()
    cursor = db.cursor(dictionary=True)

    query = "SELECT * FROM user_profiles WHERE user_id = %s"
    cursor.execute(query, (user_id,))
    result = cursor.fetchone()

    cursor.close()
    db.close()

    return result
