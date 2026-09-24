import json

def process_data(data):
    result = json.loads(data)
    return result["name"]

def divide(a, b):
    return a / b
