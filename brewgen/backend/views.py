from flask import Flask, jsonify, request, render_template
from .models import grain, beer, category, equipment, style
from flask_cors import CORS
from difflib import SequenceMatcher
from ortools.sat.python import cp_model

app = Flask(__name__,
            static_folder='../dist/static',
            template_folder='../dist'
            )
CORS(app)

all_grains = grain.GrainList()
category_model = category.CategoryModel()
all_styles = style.StyleModel()


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    return render_template("index.html")


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
    pass


@app.route('/api/v1/grains/categories', methods=['GET'])
def get_grain_categories():
    """All grain categories"""
    return jsonify(sorted(all_grains.get_all_categories())), 200


@app.route('/api/v1/grains/categories/<category_name>', methods=['GET'])
def get_grains_in_category(category_name):
    """All grains in a category_name"""
    category_grains = [grain.get_grain_data()
                       for grain in all_grains.get_grain_by_category(category_name)]
    return jsonify(category_grains), 200


@app.route('/api/v1/style-data/grains/categories', methods=['GET'])
def get_grain_categories_style_data():
    # TODO: Develop this properly, add styles and add a style-data/<style> endpoint
    """Style data for all grain categories"""
    return jsonify(category_model.get_category_list()), 200


@app.route('/api/v1/styles', methods=['GET'])
def get_styles():
    """List of styles and their summaries"""
    response = []
    for style_object in all_styles.style_list:
        response.append({
            'name': style_object.name,
            'slug': style_object.slug,
            'category': style_object.category,
            'stats': style_object.stats
        })
    return jsonify(response), 200


@app.route('/api/v1/styles/<style_slug>', methods=['GET'])
def get_style_data(style_slug):
    """Data for a single style"""
    style_object = all_styles.get_style_by_slug(style_slug)

    # Format the BJCP sensory data
    bjcp_sensory = style_object.get_bjcp_sensory_descriptors()
    bjcp_sensory_response = {}

    # Get a unique  list of keywords in both datasets, probably a better way to do this...
    keywords = []
    for attrib in ['flavor', 'aroma']:
        for key, _ in bjcp_sensory[attrib].items():
            keywords.append(key)
    keywords = list(set(keywords))

    # Build the response {'keyword': [sentences]}
    for keyword in keywords:
        # Get all the sentences, then remove ones that are too similar (many flavor and aroma sentences are nearly identical)
        aroma_sentences = bjcp_sensory['aroma'].get(keyword, [])
        flavor_sentences = bjcp_sensory['flavor'].get(keyword, [])
        keyword_sentences = aroma_sentences + flavor_sentences
        for sentence in keyword_sentences:
            sans_sentence = [s for s in keyword_sentences if s != sentence]
            seq = SequenceMatcher()
            seq.set_seq1(sentence.lower())
            for compare_sentence in sans_sentence:
                seq.set_seq2(compare_sentence.lower())
                ratio = seq.ratio() * 100
                if ratio >= 80:
                    keyword_sentences.remove(compare_sentence)

        bjcp_sensory_response[keyword] = keyword_sentences

    return jsonify({
        'name': style_object.name,
        'slug': style_object.slug,
        'stats': style_object.get_stats(),
        'grain_usage': style_object.get_grain_usage(),
        'category_usage': style_object.get_category_usage(),
        'sensory_data': style_object.sensory_data,
        'bjcp_sensory': bjcp_sensory_response
    }), 200


@app.route('/api/v1/styles/<style_slug>/grains', methods=['GET'])
def get_style_grain_data(style_slug):
    """Grain data for a single style"""
    style_object = all_styles.get_style_by_slug(style_slug)
    return jsonify(style_object.grain_list.get_grain_list(), 200)


@app.route('/api/v1/styles/<style_slug>/bjcp-sensory', methods=['GET'])
def get_style_bjcp_descriptors(style_slug):
    """Grain data for a single style"""
    style_object = all_styles.get_style_by_slug(style_slug)
    bjcp_sensory = style_object.get_bjcp_sensory_descriptors()
    response = {}

    # Get a unique  list of keywords in both datasets, probably a better way to do this...
    keywords = []
    for attrib in ['flavor', 'aroma']:
        for key, _ in bjcp_sensory[attrib].items():
            keywords.append(key)
    keywords = list(set(keywords))

    # Build the response {'keyword': [sentences]}
    for keyword in keywords:
        # Get all the sentences, then remove ones that are too similar (many flavor and aroma sentences are nearly identical)
        aroma_sentences = bjcp_sensory['aroma'].get(keyword, [])
        flavor_sentences = bjcp_sensory['flavor'].get(keyword, [])
        keyword_sentences = aroma_sentences + flavor_sentences
        for sentence in keyword_sentences:
            sans_sentence = [s for s in keyword_sentences if s != sentence]
            seq = SequenceMatcher()
            seq.set_seq1(sentence.lower())
            for compare_sentence in sans_sentence:
                seq.set_seq2(compare_sentence.lower())
                ratio = seq.ratio() * 100
                if ratio >= 80:
                    keyword_sentences.remove(compare_sentence)

        response[keyword] = keyword_sentences

    return jsonify(response), 200


@app.route('/api/v1/style-data/grains/categories/<category_name>', methods=['GET'])
def get_grain_category_style_data(category_name):
    """Style details for a single category"""
    category_data = category_model.get_category(
        category_name).get_category_data()
    return jsonify(category_data), 200


@app.route('/api/v1/grains/categories/<category_name>', methods=['GET'])
def get_grain_category(category_name):
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
    fermentable_list = []
    for fermentable in data.get('grain_list', []):
        fermentable_obj = all_grains.get_grain_by_slug(fermentable['slug'])
        fermentable_obj.set_usage(
            fermentable['min_percent'], fermentable['max_percent'])
        fermentable_list.append(fermentable_obj)
    fermentable_list_obj = grain.GrainList(fermentable_list)

    # Create a category profile from the category data provided
    categories = []
    for category_data in data.get('category_model', []):
        categories.append(category.Category(
            category_data['name'], category_data['min_percent'], category_data['max_percent']))
    category_profile = category.CategoryProfile(categories)

    # Get the profile list and return to the client
    profiles = fermentable_list_obj.get_sensory_profiles(
        category_model=category_profile,
        sensory_model=data.get('sensory_model'),
        max_unique_grains=data.get('max_unique_grains')
    )

    return jsonify(profiles), 200


@app.route('/api/v1/grains/recipes', methods=['POST'])
def get_grain_list_recipes():
    """Return all (or up to limit) possible recipies for the given parameters. Optionally return color distribution only.
    Parameters:
        coloronly=true: Return only color distribution data
        chartrange=x1,x2: Returns color data that contains at least x1 through x2, even if values are 0
    POST format:
    {
        "grain_list": [
            {slug: 'grain1', max_percent: int, min:percent: int},
            {slug: 'grain2'...}
        ],
        "category_model": CategoryModel,
        "sensory_model": SensoryModel,
        "max_unique_grains": int,
        "equipment_profile": EquipmentProfile,
        "style": str(style-slug)
    }
    """
    data = request.json
    print(data)

    # Create a grain object from the list of slugs
    fermentable_list = []
    for fermentable in data.get('grain_list', []):
        fermentable_obj = all_grains.get_grain_by_slug(fermentable['slug'])
        fermentable_obj.set_usage(
            fermentable['min_percent'], fermentable['max_percent'])
        fermentable_list.append(fermentable_obj)
    fermentable_list_obj = grain.GrainList(fermentable_list)

    # Create a category profile from the category data provided
    categories = []
    for category_data in data.get('category_model', []):
        categories.append(category.Category(
            category_data['name'], category_data['min_percent'], category_data['max_percent']))
    category_profile = category.CategoryProfile(categories)

    # Create an equipment profile from the parameters
    equipment_profile = equipment.EquipmentProfile(
        target_volume_gallons=data.get('equipment_profile', {}).get(
            'target_volume_gallons', 5.5),
        mash_efficiency=data.get('equipment_profile', {}).get(
            'mash_efficiency', 75)
    )

    # Create a beer profile from the parameters
    beer_profile = beer.BeerProfile(
        min_color_srm=data.get('beer_profile', {}).get('min_color_srm', 0),
        max_color_srm=data.get('beer_profile', {}).get('max_color_srm', 255),
        original_sg=data.get('beer_profile', {}).get('original_sg', 1.05)
    )

    # Get the recipe list and return to the client
    recipes = fermentable_list_obj.get_grain_bills(
        category_model=category_profile,
        sensory_model=data.get('sensory_model'),
        max_unique_grains=data.get('max_unique_grains'),
        equipment_profile=equipment_profile,
        beer_profile=beer_profile
    )

    recipe_response = []
    for recipe in recipes:
        recipe_response.append(recipe.get_recipe(
            beer_profile.original_sg, equipment_profile))

    color_only = request.args.get('coloronly')

    if color_only == 'true':
        srm_data = [int(recipe['srm']) for recipe in recipe_response]

        chart_range = request.args.get('chartrange')
        if chart_range:
            # Set the return x data points to at least the provided chart range
            chart_range = chart_range.split(',')
            lowest = min(int(chart_range[0]), int(min(srm_data)))
            highest = max(int(chart_range[1]), int(max(srm_data)))
        else:
            lowest = int(min(srm_data))
            highest = int(max(srm_data))

        srm_ints = list(range(lowest, highest+1))
        srm_dist = []
        for i in range(len(srm_ints)):
            srm_count = sum(
                1 for srm_value in srm_data if srm_value == srm_ints[i])
            srm_dist.append({
                "srm": srm_ints[i],
                "count": srm_count
            })
        response = srm_dist
    else:
        response = recipe_response

    return jsonify(response), 200


@app.route('/api/v1/helpers/grain-model', methods=['POST'])
def is_grain_model_valid():
    """Returns whether or not a grain model is mathematically valid
    POST format:
    {
        max_unique_fermentables: int,
        category_data: [
            {
                name: str,
                min_percent: int,
                max_percent: int
            }, {
                etc.
            }
        ]
        fermentable_data: [
            {
                slug: str,
                category: str,
                min_percent: int,
                max_percent: int
            }, {
                etc.
            }
        ]
    ]
    """

    data = request.json
    category_profile = category.CategoryProfile([category.Category(
        cat['name'], cat['min_percent'], cat['max_percent']) for cat in data['category_data']])

    fermentable_list = []
    for data_fermentable in data['fermentable_data']:
        matched_fermentable = all_grains.get_grain_by_slug(
            data_fermentable['slug'])
        fermentable_list.append(
            grain.Grain(
                name=matched_fermentable.name,
                brand=matched_fermentable.brand,
                potential=matched_fermentable.potential,
                color=matched_fermentable.color,
                category=matched_fermentable.category,
                sensory_data=matched_fermentable.sensory_data,
                min_percent=data_fermentable['min_percent'],
                max_percent=data_fermentable['max_percent']
            )
        )

    fermentable_profile = grain.GrainList(fermentable_list)
    result = fermentable_profile.is_valid_model(
        category_profile, data['max_unique_grains'])

    return jsonify(result), 200
