from flask import Flask, jsonify, request, send_from_directory
from .models import grain, beer, category, equipment
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

all_grains = grain.GrainList()

@app.route('/', methods=['GET'])
def index():
    """Brewgen main page"""
    return send_from_directory('templates', 'index.html')


@app.route('/api/v1/grains', methods=['GET'])
def get_grains():
    """All grains"""
    slugs_only = request.args.get('slugs')
    if slugs_only == 'true':
        response = all_grains.get_grain_slugs()
    else:
        response = all_grains.get_grain_list()
    return jsonify(response), 200


@app.route('/api/v1/grains/<grain>', methods=['GET'])
def get_grain():
    """Details for a single grain"""
    #return jsonify(grain_data)
    pass

@app.route('/api/v1/grains/categories', methods=['GET'])
def get_grain_categories():
    """All grain categories"""
    return jsonify(sorted(all_grains.get_all_categories())), 200


@app.route('/api/v1/grains/categories/<category>', methods=['GET'])
def get_grain_category(category):
    """Grains for a single category"""
    pass


@app.route('/api/v1/grains/sensory-keywords', methods=['GET', 'POST'])
def get_grain_list_sensory_keywords():
    """GET: All possible sensory keywords
    POST: All possible sensory keywords for the posted grain list (list of slugs)
    """
    if request.method == 'GET':
        return jsonify(sorted(all_grains.get_sensory_keywords())), 200
    elif request.method == 'POST':
        # TODO: Return all possible sensory keywords for the posted grain list
        pass

@app.route('/api/v1/grains/sensory-profiles', methods=['POST'])
def get_grain_list_sensory_values():
    """Return all possible sensory value min/max data for the given parameters.
    POST format:
    {
        "grain_list": [grain1, grain2],
        "category_model": CategoryModel,
        "sensory_model": SensoryModel,
        "max_unique_grains": int,
    }
    """
    data = request.json

    # Create a grain object from the list of slugs
    grain_list = grain.GrainList(data.get('grain_list', []))

    # Create a category profile from the category data provided
    categories = []
    for category_data in data.get('category_model', []):
        categories.append(category.Category(category_data['name'], category_data['min_percent'], category_data['max_percent']))
    category_model = category.CategoryProfile(categories)

    # Get the profile list and return to the client
    profiles = grain_list.get_sensory_profiles(
        category_model = category_model,
       # sensory_model = data.get('sensory_model'),
        max_unique_grains = data.get('max_unique_grains')
    )

    return jsonify(profiles), 200

