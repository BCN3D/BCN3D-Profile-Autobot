import json
import os


def get_data(folder):
    data_files = [f for f in os.listdir(folder) if f.endswith('.json')]
    data = {}
    for filename in data_files:
        with open(os.path.join(folder, filename)) as quality_file:
            file_data = json.load(quality_file)
            data[file_data['id']] = file_data
    return data


qualities = get_data(os.path.join('Profiles Data', 'Quality Presets'))
