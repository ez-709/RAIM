import json
import csv


def json_to_py(cd_json):
    with open(cd_json, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data

def csv_to_py(cd_csv):
    with open(cd_csv, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        data = []
        for row in reader:
            data.append({
                'time': int(row['time']),
                'X': float(row['X']),
                'Y': float(row['Y']),
                'Z': float(row['Z'])
            })
    return data