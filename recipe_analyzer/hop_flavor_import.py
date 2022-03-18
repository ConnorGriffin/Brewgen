import json
import csv
import os.path


def avg(x, y):
    return round((x + y) / 2, 2)


path_list = os.path.abspath(__file__).split(os.sep)
script_directory = path_list[0:len(path_list)-2]
hop_path = "/".join(script_directory) + "/brewgen/backend/data/hops.json"
export_path = "/".join(script_directory) + "/brewgen/backend/data/hop_db.json"
aroma_path = "/".join(script_directory) + "/recipe_analyzer/HopAroma.csv"
hop_export = []

with open(hop_path, 'r') as f:
    hop_data = json.load(f)

with open(aroma_path, 'r') as f:
    reader = csv.reader(f)
    aroma_data = []
    for row in reader:
        if row[1] != '#N/A':
            aroma = dict()
            for descriptor in row[1].split('\n'):
                aroma[descriptor.strip()] = 1
            aroma_data.append({
                'name': row[0],
                'aroma': aroma
            })

for hop in hop_data:
    export_data = {
        'name': hop['Name'],
        'alpha': avg(hop['AlphaMin'], hop['AlphaMax']),
        'beta': avg(hop['BetaMin'], hop['BetaMax']),
        'cohumulone': avg(hop['CoHumuloneMin'], hop['CoHumuloneMax']),
        'total_oil': avg(hop['TotalOilMin'], hop['TotalOilMax']),
        'aroma': {}
    }

    matching_hop = list(
        filter(lambda x: (x['name'] == hop['Name']), aroma_data))
    if matching_hop:
        export_data['aroma'] = matching_hop[0]['aroma']

    hop_export.append(export_data)

with open(export_path, 'w') as f:
    json.dump(hop_export, f)
