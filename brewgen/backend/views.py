import os
import time

from flask import Flask, jsonify, request, render_template
from .models import grain, category, style
from .solver import color as grain_color
from .solver.fermentables import (
    FermentableSolver, SolverConfig, ColorContext, CheckStatus, GenerationStatus)
from flask_cors import CORS
from difflib import SequenceMatcher

from . import envelope
from .brief import parse_brief, BriefError
from .envelope import compute_endpoint, problem, solver_slot

app = Flask(__name__,
            static_folder='../dist/static',
            template_folder='../dist'
            )

# The public compute surface is anonymous and same-origin: the built frontend is
# served by this app. Cross-origin access is off unless a deployment names the
# allowed origins, so the browser is never handed a wide-open policy.
_cors_origins = [o for o in os.environ.get("BREWGEN_CORS_ORIGINS", "").split(",") if o]
CORS(app, resources={r"/api/*": {"origins": _cors_origins}})

# Refuse an over-cap body before Werkzeug reads it, so the 64 KiB limit bites
# before any JSON parsing (issue #29).
app.config['MAX_CONTENT_LENGTH'] = envelope.MAX_BODY_BYTES

all_grains = grain.GrainList()
category_model = category.CategoryModel()
all_styles = style.StyleModel()

# Solver deadlines and diversity limits are server configuration, never set by
# the caller, so a slow or malicious request cannot ask for unbounded compute.
SOLVER_CONFIG = SolverConfig()

# The monotonic clock every public solve shares. A module attribute so a test
# can drive the shared deadline with a fake clock through the public interface.
_clock = time.monotonic


def _solver_for(derived):
    """Build the shared MILP from a validated, server-derived brief."""
    return FermentableSolver(
        derived.grains,
        derived.categories,
        max_unique_grains=derived.max_unique,
        sensory_keywords=derived.sensory_keywords,
        sensory_bounds=derived.sensory_bounds,
        config=SOLVER_CONFIG,
    )


def _color_context(derived):
    """The gravity/equipment/SRM color band the brief pins."""
    return ColorContext(
        original_sg=derived.original_sg,
        target_volume_gallons=derived.target_volume_gallons,
        mash_efficiency=derived.mash_efficiency,
        min_srm=derived.min_srm,
        max_srm=derived.max_srm,
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


@app.route('/api/v1/grains/sensory-range', methods=['POST'])
@compute_endpoint("sensory_range")
def get_fermentable_sensory_range(payload, request_id):
    """Return the exact achievable min/max for one named sensory descriptor.

    Holds every other configured constraint fixed (including the brief's colour
    band) and excludes the target descriptor's own bound, so the range is its
    full editable span. One request asks about exactly one flavour: the brief
    carries a sibling ``descriptor`` naming it.
    """
    derived = parse_brief(payload, all_grains, all_styles, allow_extra=("descriptor",))
    descriptor = payload.get("descriptor")
    if not isinstance(descriptor, str) or descriptor not in derived.sensory_keywords:
        raise BriefError("invalid_brief", 422, [{"path": "descriptor"}])

    solver = _solver_for(derived)
    with solver_slot():
        result = solver.sensory_range(
            descriptor, color_context=_color_context(derived), clock=_clock)

    body = {'status': result.status.value, 'name': result.name}
    if result.status == CheckStatus.FEASIBLE:
        body['min'] = result.minimum
        body['max'] = result.maximum
    return jsonify(body), result.status.value


@app.route('/api/v1/grains/feasibility', methods=['POST'])
@compute_endpoint("feasibility")
def get_fermentable_brief_feasibility(payload, request_id):
    """Report whether one complete grain-bill brief is feasible.

    Applies sensory, colour, category, cardinality, gravity, and equipment
    constraints together and returns a stable status without leaking solver
    internals. Server-derives the category/style-model constraints from the
    brief's style slug.
    """
    derived = parse_brief(payload, all_grains, all_styles)
    solver = _solver_for(derived)
    with solver_slot():
        result = solver.feasibility(
            color_context=_color_context(derived), clock=_clock)
    return jsonify({'status': result.status.value}), result.status.value


@app.route('/api/v1/grains/recipes', methods=['POST'])
@compute_endpoint("generate")
def get_fermentable_list_recipes(payload, request_id):
    """Generate up to five unranked, meaningfully different grain bills.

    Accepts the strict ``version: 1`` brief and derives the category/style-model
    constraints server-side. Every returned bill is a whole-percentage bill
    summing to 100 that lands inside the requested SRM range; the bills carry no
    ranking. ``complete`` and ``partial`` are HTTP 200; an infeasible brief is
    422 ``infeasible`` and an exhausted deadline is 503 ``deadline_exceeded``.
    """
    derived = parse_brief(payload, all_grains, all_styles)
    solver = _solver_for(derived)
    with solver_slot():
        result = solver.generate(
            original_sg=derived.original_sg,
            target_volume_gallons=derived.target_volume_gallons,
            mash_efficiency=derived.mash_efficiency,
            min_srm=derived.min_srm,
            max_srm=derived.max_srm,
            clock=_clock,
        )

    if result.status == GenerationStatus.INFEASIBLE:
        return problem("infeasible", 422, request_id), "infeasible"
    if result.status == GenerationStatus.DEADLINE_EXCEEDED:
        return problem("deadline_exceeded", 503, request_id), "deadline_exceeded"

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
            ppgs, vector, derived.original_sg,
            derived.target_volume_gallons, derived.mash_efficiency)
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
    }), result.status.value
