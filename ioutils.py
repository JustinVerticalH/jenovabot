import json, os
from discord import Embed, Color

DATA_FILE = os.getenv("DATA_FILE")

class RandomColorEmbed(Embed):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, color=Color.random(), **kwargs)

def read_json(*path: list[str | int]):
    """Read JSON object data from a file."""
    
    with open(DATA_FILE, "r") as file:
        position = json.load(file)
    for key in path:
        if key is None or position is None:
            return None
        position = position.get(str(key), None)
    return position

def write_json(*path: any, value: any):
    with open(DATA_FILE, "r+") as file:
        file_json = json.load(file)
        position = file_json
        for key in path:
            if position.get(str(key)) is None:
                position[str(key)] = dict()
            previous_position = position
            position = position.get(str(key))

        previous_position[str(key)] = value
        file.seek(0)
        json.dump(file_json, file, indent=2)
        file.truncate()