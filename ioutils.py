import json

def read(file_name: str, *path: list[str | int]):
    with open(file_name, "r") as file:
        position = json.load(file)
    for key in path:
        if key is None:
            return None
        position = position.get(str(key), None)
    return position
    
def write(file_name: str, value: any, *path: list[str | int]):
    with open(file_name, "r+") as file:
        file_json = json.load(file)
        position = file_json
        for key in path:
            print(position)
            if position.get(str(key)) is None:
                position[str(key)] = dict()
            previous_position = position
            position = position.get(str(key))

        previous_position[str(key)] = value
        file.seek(0)
        json.dump(file_json, file, indent=2)
        file.truncate()