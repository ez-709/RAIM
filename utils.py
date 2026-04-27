import os
import json
import csv

DATA_DIR = os.path.join("data", "tech_data")


def json_to_py(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def read_config(path):
    cfg = json_to_py(path)
    return (
        cfg["download"]["mode"],
        cfg["download"]["days_back"],
        cfg["download"]["output_dir"],
        cfg["download"]["timeout_listing"],
        cfg["download"]["timeout_file"],
        [s["code"] for s in cfg["stations"]],
    )


def write_csv(path, header, rows):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
