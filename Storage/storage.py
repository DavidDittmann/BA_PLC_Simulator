import json
import os
from Log import log

logger = log.Logger().get_logger()

def read_json(filepath):
    json_content = None
    with open(filepath, 'r') as json_file:
        json_content = json.load(json_file)
    return json_content

def write_json(filepath, data):
    with open(filepath, 'w') as json_file:
        json.dump(data, json_file)

def write_file(filepath, data, append=False):
    if append:
        with open(filepath, 'a') as file:
            file.write(data + "\n")
    else:
        with open(filepath, 'w') as file:
            file.write(data)

def read_file(filepath):
    with open(filepath, 'r') as file:
        content = file.read()
    return content

def is_available(filepath):
    if os.path.isfile(filepath):
        return True
    logger.warning("Specified file does not exist")
    return False
