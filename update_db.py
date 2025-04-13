import sqlite3

conn = sqlite3.connect('users.db')
cursor = conn.cursor()
cursor.execute('ALTER TABLE users ADD COLUMN last_partner TEXT')
conn.commit()
conn.close()
print("Database schema updated successfully.")