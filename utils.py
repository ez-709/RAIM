import os
import json
import csv

DATA_DIR = os.path.join("data", "tech_data")
LOG_FILE = os.path.join(DATA_DIR, "log.txt")


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


def write_logs(cd_logs, text, update=True):
    mode = 'a' if update else 'w'
    with open(cd_logs, mode, encoding='utf-8') as f:
        f.write(text)


def clear_all_logs(cd_logs_back, cd_logs_htpp, cd_logs_tech):
    with open(cd_logs_back, 'w') as f:
        pass
    with open(cd_logs_htpp, 'w') as f:
        pass
    with open(cd_logs_tech, 'w') as f:
        pass


def read_config(cd_config,
                observer_longitude=True,
                observer_latitude=True,
                observer_altitude=True,
                timezone_utc=True,
                days_back=True,
                output_dir=True,
                timeout_listing=True,
                timeout_file=True,
                log_file=True,
                stations=True):
    config = json_to_py(cd_config)
    out = []
    if observer_longitude:
        out.append(config["observer"]["longitude"])
    if observer_latitude:
        out.append(config["observer"]["latitude"])
    if observer_altitude:
        out.append(config["observer"]["altitude"])
    if timezone_utc:
        out.append(config["observer"]["timezone_utc"])
    if days_back:
        out.append(config["download"]["days_back"])
    if output_dir:
        out.append(config["download"]["output_dir"])
    if timeout_listing:
        out.append(config["download"]["timeout_listing"])
    if timeout_file:
        out.append(config["download"]["timeout_file"])
    if log_file:
        out.append(config["logs"]["log_file"])
    if stations:
        out.append([s["code"] for s in config["stations"]])
    return out


def log(msg, reset=False):
    os.makedirs(DATA_DIR, exist_ok=True)
    mode = "w" if reset else "a"
    with open(LOG_FILE, mode) as f:
        f.write(msg + "\n")
    print(msg)


def write_csv(path, header, rows):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for row in rows:
            w.writerow(row)


def read_csv(path):
    with open(path, "r") as f:
        return list(csv.DictReader(f))