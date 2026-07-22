from flask import Flask, jsonify, request, render_template
from .models import grain, beer, category, equipment, style
from .solver import color as grain_color
from .solver.fermentables import FermentableSolver, SolverConfig
from flask_cors import CORS
from difflib import SequenceMatcher

app = Flask(__name__,
            static_folder='../dist/static',
            template_folder='../dist'
            )
CORS(app)

all_grains = grain.GrainList()
category_model = category.CategoryModel()
all_styles = style.StyleModel()

# Solver deadlines and diversity limits are server configuration, never set by
# the caller, so a slow or malicious request cannot ask for unbounded compute.
SOLVER_CONFIG = SolverConfig()


def _build_fermentable_solver(data):
    """Adapt a request body into a FermentableSolver.

    Reads the shared ``fermentable_list``/``category_model`` shape used by the
    validity, sensory-range, and recipe endpoints.
    """
    grains = []
    for item in data.get('fermentable_list', []):
        matched = all_grains.get_grain_by_slug(item['slug'])
        grains.append(grain.Grain(
            name=matched.name,
            brand=matched.brand,
            potential=matched.potential,
            color=matched.color,
            category=matched.category,
            sensory_data=matched.sensory_data,
            min_percent=item['min_percent'],
            max_percent=item['max_percent'],
        ).get_grain_data())

    categories = [{
        'name': cat['name'],
        'unique_fermentable_count': cat.get('unique_fermentable_count'),
        'min_percent': cat['min_percent'],
        'max_percent': cat['max_percent'],
    } for cat in data.get('category_model', [])]

    return FermentableSolver(
        grains,
        categories,
        max_unique_grains=data.get('max_unique_fermentables', 4),
        sensory_keywords=all_grains.get_sensory_keywords(),
        sensory_bounds=data.get('sensory_model'),
        config=SOLVER_CONFIG,
    )


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
        'unique_fermentable_count': style_object.unique_fermentable_count,
        'hops': {
            'unique_hop_count': style_object.unique_hop_count
        },
        'bjcp_sensory': bjcp_sensory_response
    }), 200


@app.route('/api/v1/styles/<style_slug>/grains', methods=['GET'])
def get_style_grain_data(style_slug):
    """Grain data for a single style"""
    style_object = all_styles.get_style_by_slug(style_slug)
    return jsonify(style_object.grain_list.get_grain_list()), 200


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
def get_fermentable_list_sensory_keywords():
    """GET: All possible sensory keywords
    POST: All possible sensory keywords for the posted grain list (list of slugs)
    """
    if request.method == 'GET':
        return jsonify(sorted(all_grains.get_sensory_keywords())), 200
    elif request.method == 'POST':
        # TODO: Return all possible sensory keywords for the posted grain list
        pass


@app.route('/api/v1/grains/sensory-profiles', methods=['POST'])
def get_fermentable_list_sensory_values():
    """Return all possible sensory value min/max data for the given parameters.
    POST format:
    {
        "fermentable_list": [grain1, grain2],
        "category_model": CategoryModel,
        "sensory_model": SensoryModel,
        "max_unique_fermentables": int,
    }
    """
    data = request.json

    # Achievable min/max of each descriptor under the same cardinality limits
    # as generation. Cardinality-preserving MILP, no color constraints.
    profiles = _build_fermentable_solver(data).sensory_ranges()

    return jsonify(profiles), 200


@app.route('/api/v1/grains/recipes', methods=['POST'])
def get_fermentable_list_recipes():
    """Generate up to five unranked, meaningfully different grain bills.

    Every returned bill is a whole-percentage bill summing to 100 that lands
    inside the requested SRM range; the bills carry no ranking. The response
    exposes an explicit completion status (complete, partial, infeasible, or
    deadline_exceeded) so bounded failures are visible to the caller.

    POST format:
    {
        "fermentable_list": [
            {slug: 'grain1', max_percent: int, min_percent: int},
            {slug: 'grain2'...}
        ],
        "category_model": CategoryModel,
        "sensory_model": SensoryModel,
        "max_unique_fermentables": int,
        "equipment_profile": EquipmentProfile,
        "beer_profile": BeerProfile
    }
    """
    data = request.json

    solver = _build_fermentable_solver(data)

    equipment_profile = equipment.EquipmentProfile(
        target_volume_gallons=data.get('equipment_profile', {}).get(
            'target_volume_gallons', 5.5),
        mash_efficiency=data.get('equipment_profile', {}).get(
            'mash_efficiency', 75)
    )
    beer_profile = beer.BeerProfile(
        min_color_srm=data.get('beer_profile', {}).get('min_color_srm', 0),
        max_color_srm=data.get('beer_profile', {}).get('max_color_srm', 255),
        original_sg=data.get('beer_profile', {}).get('original_sg', 1.05)
    )

    result = solver.generate(
        original_sg=beer_profile.original_sg,
        target_volume_gallons=equipment_profile.target_volume_gallons,
        mash_efficiency=equipment_profile.mash_efficiency,
        min_srm=beer_profile.min_color_srm,
        max_srm=beer_profile.max_color_srm,
    )

    # Serialize each alternative with per-grain pounds derived from the same
    # color math the solver accepted the bill against. Each grain carries the
    # malt metadata the results shelf paints its stack from (name, brand, and
    # Lovibond colour), and each bill carries its per-descriptor sensory values
    # straight from the sensory model so the tastes line is never fabricated.
    by_slug = {g['slug']: g for g in solver.grains}
    slugs = [g['slug'] for g in solver.grains]
    ppgs = [g['ppg'] for g in solver.grains]
    alternatives = []
    for bill in result.alternatives:
        vector = [bill.percents.get(slug, 0) for slug in slugs]
        pounds = grain_color.grain_pounds(
            ppgs, vector, beer_profile.original_sg,
            equipment_profile.target_volume_gallons,
            equipment_profile.mash_efficiency)
        alternatives.append({
            'grains': [
                {'slug': slugs[i], 'use_percent': vector[i],
                 'use_pounds': pounds[i],
                 'name': by_slug[slugs[i]]['name'],
                 'brand': by_slug[slugs[i]]['brand'],
                 'color_lovibond': by_slug[slugs[i]]['color']}
                for i in range(len(slugs)) if vector[i] > 0
            ],
            'srm': bill.srm,
            'sensory': solver.sensory_values(bill.percents),
        })

    return jsonify({
        'status': result.status.value,
        'alternatives': alternatives,
    }), 200


@app.route('/api/v1/helpers/grain-model-valid', methods=['POST'])
def is_grain_model_valid():
    """Returns whether or not a grain model is mathematically valid
    POST format:
    {
        max_unique_fermentables: int,
        category_model: [
            {
                name: str,
                min_percent: int,
                max_percent: int
            }, {
                etc.
            }
        ]
        fermentable_list: [
            {
                slug: str,
                min_percent: int,
                max_percent: int
            }, {
                etc.
            }
        ]
    ]
    """

    data = request.json
    result = _build_fermentable_solver(data).is_valid()
    return jsonify(result), 200
