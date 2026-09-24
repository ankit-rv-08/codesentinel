import hashlib
import os

API_KEY = "sk-1234567890abcdef"

def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()

def get_user_profile(user_id):
    conn = db.connect()
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return conn.execute(query).fetchone()

def parse_config(path):
    with open(path, "r") as f:
        return f.read()
