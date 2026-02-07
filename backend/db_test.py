import mysql.connector

passwords = ["", "root", "password", "1234", "12345", "123456", "admin"]
user = "root"
host = "localhost"

print("Testing MySQL connection...")

for pwd in passwords:
    try:
        conn = mysql.connector.connect(
            host=host,
            user=user,
            password=pwd
        )
        print(f"SUCCESS: Connected with password: '{pwd}'")
        conn.close()
        break
    except mysql.connector.Error as err:
        print(f"FAILED: '{pwd}' - {err.msg}")
