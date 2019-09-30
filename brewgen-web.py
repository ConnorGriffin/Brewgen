from flask import Flask, jsonify, request, render_template
import json
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/', methods=['GET'])
def get_brewgen_ui():
    with open('./ingredients/grains.json', 'r') as f:
        grain_data = json.load(f)
    grain_categories = set([grain['category'] for grain in grain_data])

    return render_template('brewgen.html', grain_categories=sorted(grain_categories), grain_data=grain_data)


@app.route('/api/grains', methods=['GET'])
def get_grains():
    # Import the grain list
    with open('./ingredients/grains.json', 'r') as f:
        grain_data = json.load(f)

    return jsonify(grain_data)