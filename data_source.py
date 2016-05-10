import sqlite3

conn = sqlite3.connect('javlibrary.db')

c = conn.cursor()

c.execute('''CREATE TABLE jav
          (id INT PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE,
          name TEXT, star TEXT, score REAL,  category TEXT, image TEXT, torrent TEXT);''')

conn.commit()

conn.close()
