import sqlite3

database_name = 'CANLink.db'

con = sqlite3.connect(database_name)
cur = con.cursor()



con.commit()
con.close()








