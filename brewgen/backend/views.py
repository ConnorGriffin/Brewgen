from flask import Flask, jsonify, request, render_template
from werkzeug.middleware.proxy_fix import ProxyFix
from .models import grain, category, style
from .solver import color as grain_color
from .solver.fermentables import (
    FermentableSolver, SolverConfig, ColorContext, CheckStatus, GenerationStatus)
from . import envelope
from . import style_defaults
from .brief import BriefContract
from .envelope import compute_endpoint, ok_json, problem
from difflib import SequenceMatcher

app = Flask(__name__,
            static_folder='../dist/static',
            template_folder='../dist'
            )

# Resolve the client address as exactly one trusted proxy hop. The public deploy
# (#12/#16) puts the API a single relay behind the visitor, so the last
# X-Forwarded-For entry is the real client; ProxyFix(x_for=1) rewrites
# remote_addr to it. Raw remote_addr would collapse every visitor to the relay,
# and a blindly trusted full X-Forwarded-For chain would be spoofable. The
# deploy must forward exactly one hop for the per-visitor rate limit to hold.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)

all_grains = grain.GrainList()
category_model = category.CategoryModel()
all_styles = style.StyleModel()

# The versioned brief contract resolves every solver input from the shipped
# grain catalog and style model instead of trusting client-supplied models.
CONTRACT = BriefContract(all_grains, all_styles)

# Solver deadlines and diversity limits are server configuration, never set by
# the caller, so a slow or malicious request cannot ask for unbounded compute.
SOLVER_CONFIG = SolverConfig()


def _build_fermentable_solver(brief):
    """Adapt a validated, server-derived brief into a FermentableSolver."""
    return FermentableSolver(
        brief.grains,
        brief.categories,
        max_unique_grains=brief.max_unique,
        sensory_keywords=brief.sensory_keywords,
        sensory_bounds=brief.sensory_bounds,
        config=SOLVER_CONFIG,
    )


def _color_context(brief):
    """Build the gravity, equipment, and SRM context from a derived brief."""
    return ColorContext(
        original_sg=brief.original_sg,
        target_volume_gallons=brief.target_volume_gallons,
        mash_efficiency=brief.mash_efficiency,
        min_srm=brief.min_srm,
        max_srm=brief.max_srm,
    )


@app.route('/healthz')
def healthz():
    return jsonify({'status': 'ok'}), 200


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
    if style_object is None:
        return jsonify({'error': 'unknown style'}), 404

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
        'bjcp_sensory': bjcp_sensory_response,
        # The committed default the editor opens on. It rides along here rather
        # than costing a second request, and nothing is computed to produce it.
        'default': style_defaults.default_for(style_object.slug)
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


@app.route('/api/v1/grains/sensory-range', methods=['POST'])
@compute_endpoint('sensory_range', CONTRACT, require_descriptor=True)
def get_fermentable_sensory_range(brief):
    """Return the exact achievable min/max for one named sensory descriptor.

    Holds every other configured constraint fixed and excludes the target
    descriptor's own bound, so the range is its full editable span. This is the
    focused replacement for the retired all-descriptor sweep; one request asks
    about exactly one flavor.

    Accepts the strict choice brief plus one ``descriptor`` field.
    """
    solver = _build_fermentable_solver(brief)
    result = solver.sensory_range(
        brief.descriptor, color_context=_color_context(brief))

    if result.status == CheckStatus.FEASIBLE:
        return ok_json({'status': 'feasible', 'name': result.name,
                        'min': result.minimum, 'max': result.maximum},
                       outcome='feasible')
    if result.status == CheckStatus.INFEASIBLE:
        return problem(422, 'infeasible')
    if result.status == CheckStatus.DEADLINE_EXCEEDED:
        return problem(503, 'deadline')
    return problem(422, 'invalid')


@app.route('/api/v1/grains/feasibility', methods=['POST'])
@compute_endpoint('feasibility', CONTRACT)
def get_fermentable_brief_feasibility(brief):
    """Report whether one complete grain-bill brief is feasible.

    Applies sensory, color, category, cardinality, gravity, and equipment
    constraints together and returns a stable status without leaking solver
    internals.

    The style-model constraints are derived from the submitted style slug.
    """
    solver = _build_fermentable_solver(brief)
    context = _color_context(brief)
    result = solver.feasibility(color_context=context)

    if result.status == CheckStatus.FEASIBLE:
        return ok_json({'status': 'feasible'}, outcome='feasible')
    if result.status == CheckStatus.INFEASIBLE:
        return problem(422, 'infeasible')
    return problem(503, 'deadline')  # DEADLINE_EXCEEDED


@app.route('/api/v1/grains/recipes', methods=['POST'])
@compute_endpoint('recipes', CONTRACT)
def get_fermentable_list_recipes(brief):
    """Generate up to five unranked, meaningfully different grain bills.

    Every returned bill is a whole-percentage bill summing to 100 that lands
    inside the requested SRM range; the bills carry no ranking. ``complete`` and
    ``partial`` sets are returned as 200 so partial results show honestly;
    ``infeasible`` and ``deadline_exceeded`` are surfaced as the locked 422/503
    problem+json outcomes.

    Accepts only the strict ``version: 1`` choice brief.
    """
    solver = _build_fermentable_solver(brief)

    result = solver.generate(
        original_sg=brief.original_sg,
        target_volume_gallons=brief.target_volume_gallons,
        mash_efficiency=brief.mash_efficiency,
        min_srm=brief.min_srm,
        max_srm=brief.max_srm,
    )

    if result.status == GenerationStatus.INFEASIBLE:
        return problem(422, 'infeasible')
    if result.status == GenerationStatus.DEADLINE_EXCEEDED:
        return problem(503, 'deadline')

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
            ppgs, vector, brief.original_sg,
            brief.target_volume_gallons,
            brief.mash_efficiency)
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

    return ok_json({
        'status': result.status.value,
        'alternatives': alternatives,
    }, outcome=result.status.value)
