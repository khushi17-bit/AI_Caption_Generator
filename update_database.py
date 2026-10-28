import sqlite3

conn = sqlite3.connect("database.db")

cursor = conn.cursor()

cursor.execute("DROP TABLE IF EXISTS captions")

cursor.execute("""
CREATE TABLE captions(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_name TEXT,
    caption TEXT,
    hashtags TEXT,
    emojis TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()
conn.close()

print("Database updated successfully!")