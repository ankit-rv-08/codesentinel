import os
import sqlite3

def get_users(username):
    conn = sqlite3.connect("users.db")
    query = f"SELECT * FROM users WHERE name = '{username}'"
    return conn.execute(query).fetchall()

def calculate_average(numbers):
    total = 0
    for n in numbers:
        total += n
    return total / len(numbers)
