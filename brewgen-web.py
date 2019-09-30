from flask import Flask, jsonify, request, render_template
import json
from slugify import slugify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/', methods=['GET'])
def index():
    """Brewgen main page"""
    with open('./ingredients/grains.json', 'r') as f:
        grain_data = json.load(f)
    grain_categories = set([grain['category'] for grain in grain_data])
    for grain in grain_data:
        grain['slug'] = slugify('{}_{}'.format(grain['brand'], grain['name']), replacements=[["'", ''], ['®', '']])
    return render_template('brewgen.html', grain_categories=sorted(grain_categories), grain_data=grain_data)


@app.route('/api/v1/grains', methods=['GET'])
def get_grains():
    """All grains"""
    # Return the grains list
    with open('./ingredients/grains.json', 'r') as f:
        grain_data = json.load(f)
    for grain in grain_data:
        grain['slug'] = slugify('{}_{}'.format(grain['brand'], grain['name']), replacements=[["'", ''], ['®', '']])
    return jsonify(grain_data)


@app.route('/api/v1/grains/<grain>', methods=['GET'])
def get_grain():
    """Details for a single grain"""
    # Return the grains list
    with open('./ingredients/grains.json', 'r') as f:
        grain_data = json.load(f)
    for grain in grain_data:
        grain['slug'] = slugify('{}_{}'.format(grain['brand'], grain['name']), replacements=[["'", ''], ['®', '']])
    return jsonify(grain_data)

@app.route('/api/v1/grains/categories', methods=['GET'])
def get_grain_categories():
    """All grain categories"""
    pass


@app.route('/api/v1/grains/categories/<category>', methods=['GET'])
def get_grain_category(category):
    """Grains for a single category"""
    pass


@app.route('/api/v1/grains/sensory', methods=['GET', 'POST'])
def get_grain_sensory():
    """
    GET: All possible sensory keywords
    POST: All possible sensory keywords for the posted grain list (list of slugs)
    """
    pass
