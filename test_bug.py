import os

def get_user(id):
    user = db.query(id)
    return user.name
