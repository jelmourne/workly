import json
import os

with open ('config.json') as config_file:
    config = json.load(config_file)

class Config:
    email = config.get('email'),
    password = config.get('password'),
    