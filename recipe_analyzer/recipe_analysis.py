from pathlib import Path
from pybeerxml import Parser
import sys
import numpy as np
import re
import csv
import json
import random
import concurrent.futures

sys.path.append('../')
from brewgen.backend.models import grain, category, hop



def points(og):
    return (og - 1) * 1000


with open('styleguide-2015.json', 'r', encoding='utf8') as f:
    bjcp = json.load(f)


def bjcp_name(name):
    """Return beer stats for a style name"""
    for bev_class in bjcp['styleguide']['class']:
        if bev_class['type'] == 'beer':
            for style_category in bev_class['category']:
                for subcat in style_category['subcategory']:
                    if subcat['name'] == name:
                        return subcat.get('stats', {})


def get_stats(data):
    data = np.array(data)
    if not data.any():
        return {
            'min': 0,
            'max': 0,
            'mean': 0,
            'median': 0,
            'std': 0
        }
    else:
        std = np.std(data)
        mean = np.mean(data)
        return {
            'min': max(0, mean - std * 2),
            'max': mean + std * 2,
            'mean': mean,
            'median': np.median(data),
            'std': std
        }


all_grains = grain.GrainModel()
all_hops = hop.HopModel()
category_model = category.CategoryModel()

fermentable_keywords = all_grains.get_sensory_keywords()
hop_keywords = all_hops.get_sensory_keywords()
fermentable_categories = category_model.get_category_names()

styles = []
for bev_class in bjcp['styleguide']['class']:
    if bev_class['type'] == 'beer':
        for style_category in bev_class['category']:
            for subcat in style_category['subcategory']:
                styles.append(subcat['name'])

parser = Parser()


# Define fermentable, style, and hop rewrite rules
fermentable_rewrites = [
    {
        'name': 'Goldpils Vienna Malt',
        'match': "^.*(Goldpils|Vienna.*US|US.*Vienna|Briess.*Vienna|Vienna.*Briess).*$",
        'max_color': 6
    },
    # as the catchall for Vienna
    {
        'name': 'Vienna Malt',
        'match': '^.*Vienna.*$',
        'max_color': 6
    }, {
        'name': 'Munich Malt I',
        "match": '^.*Munich.*$',
        'max_color': 7
    },
    {
        'name': 'Munich Malt II',
        "match": '^.*Munich.*$',
        'max_color': 9.9
    },
    {
        'name': 'Munich Malt 10L',
        "match": '^.*Munich.*$',
        'max_color': 11
    },
    {
        'name': 'Munich Malt 20L',
        "match": '^.*Munich.*$',
        'max_color': 21
    },
    {
        'name': "Brewer's Malt",
        'match': '^.*((2|Two)(-| )Row|Pale Malt|Ale Malt).*$',
        'max_color': 3.5
    },
    # No sensory available for Maris Otter so lumping that in with Pale Ale Malt
    {
        'name': "Pale Ale Malt",
        'match': '^.*(Pale Ale|Maris|Marris|Ale Malt).*$',
        'max_color': 5
    },
    {
        'name': "Carapils Malt",
        'match': '^.*(Carafoam|US.*Carapils|Carapils.*US|Carapils.*Briess|Briess.*Carapils|Cara-Pils|Dextrine).*$',
        'max_color': 5
    },
    # as the catchall for Carapils
    {
        'name': "Carapils",
        'match': '^.*(Carapils).*$',
        'max_color': 5
    },
    {
        'name': "CaraHell",
        'match': '^.*(Cara Malt|Hell).*$',
        'min_color': 5,
        'max_color': 15
    },
    {
        'name': "CaraHell",
        'match': '^.*Caramel Pils.*$',
        'min_color': 5,
        'max_color': 15
    },
    {
        'name': "Carapils Malt",
        'match': '^.*Caramel Pils.*$',
        'max_color': 5
    },
    {
        'name': "Pilsen Malt",
        'match': '^.*(Pilsen|US.*Pilsner|Pilsner.*US|Lager).*$',
        'max_color': 3
    },
    # as the catchall for Pilsner
    {
        'name': "Pilsner Malt",
        'match': '^.*Pilsner.*$',
        'max_color': 3.5
    },
    {
        'name': "Pale Chocolate Malt",
        'match': '^.*Chocolate.*$',
        'max_color': 240
    },
    {
        'name': "Chocolate Malt",
        'match': '^.*Chocolate.*$',
        'max_color': 360
    },
    # Dark chocolate as the chocolate catchall
    {
        'name': "Dark Chocolate Malt",
        'match': '^.*Chocolate.*$',
    },
    {
        'name': "Special B",
        'match': '^.*Special (W|B).*$'
    },
    {
        'name': "Amber Malt",
        'match': '^(Amber|Amber.*UK.*|(Crisp|British) Amber|.*Amber Malt.*)$'
    },
    {
        'name': "CaraMunich I",
        'match': '^.*Cara ?munich(( I)?|.*Type 1).*$',
        'max_color': 40
    },
    {
        'name': "CaraMunich II",
        'match': '^.*Cara ?munich(( II)?|.*Type 2).*$',
        'max_color': 50
    },
    {
        'name': "CaraMunich III",
        'match': '^.*Cara ?munich(( III)?|.*Type 3).*$',
        'max_color': 60
    },
    {
        'name': "Caramel Malt 10L",
        'match': '^.*(Crystal|Caramel).*15.*$',
        'max_color': 15.1
    },
    {
        'name': "Caramel Malt 20L",
        'match': '^.*(Crystal|Caramel).*15.*$',
        'min_color': 15.1,
        'max_color': 20
    },
    {
        'name': "Pale Wheat Malt",
        'match': '^.*((Belgian|German).*Wheat|Wheat.*(DE|BE|Belgian|German)).*$'
    },
    {
        'name': "Wheat Malt, White",
        'match': '^.*(White Wheat|Pale Wheat|Wheat Malt|Light Wheat|Wheat.*US).*$'
    },
    {
        'name': "Brewers Red Wheat Flakes",
        'match': '^.*(Flak.*Wheat|Wheat.*Flak).*$'
    },
    # Red wheat as the wheat catchall
    {
        'name': "Wheat Malt, Red",
        'match': '^.*Wheat.*$',
        'max_color': 4
    },
    {
        'name': "Lactose (Milk Sugar)",
        'match': '^.*(Lactose|Milk Sugar).*$'
    },
    {
        'name': "Brewers Torrified Wheat",
        'match': '^.*(Wheat.*Torrified|Torrified Wheat).*$'
    },
    {
        'name': "Dextrose (Corn Sugar)",
        'match': '^.*(Corn Sugar|Dextrose).*$'
    },
    {
        'name': "Brewers Barley Flakes",
        'match': '^.*(Barley.*Flaked|Flaked.*Barley).*$'
    },
    {
        'name': "Brewers Rye Flakes",
        'match': '^.*(Rye.*Flaked|Flaked.*Rye).*$'
    },
    {
        'name': 'Flaked Rice',
        'match': '^Rice, Flaked$'
    },
    {
        'name': 'Caramel Vienne Malt 20L',
        'match': '^.*(CaraVienn(a|e)|Cara Vienna).*$'
    },
    {
        'name': "Munich Malt 20L",
        'match': '^.*Aromatic.*$',
        'min_color': 15,
        'max_color': 25
    },
    {
        'name': "Melanoidin Malt",
        'match': '^.*Aromatic.*$',
        'min_color': 25,
        'max_color': 65
    },
    {
        'name': 'Smoked Malt, Mesquite',
        'match': '^.*Smoked Malt.*$',
        'min_color': 4,
        'max_color': 6
    },
    {
        'name': 'Beech Smoked Barley Malt',
        'match': '^.*Smoked Malt.*$',
        'min_color': 1,
        'max_color': 4
    },
    {
        'name': "Brewers Oat Flakes",
        'match': '^.*(Oat.*(Flake|Roll)|(Flake|Roll).*Oat).*$'
    },
    {
        'name': "Brewers Yellow Corn Flakes",
        'match': '^.*((Corn|Maize).*Flaked|Flaked.*(Corn|Maize)).*$'
    },
    {
        'name': "Black Malt",
        'match': '^.*((?!de-?bittered)).*(Black Malt|Black Patent).*$',
        'min_color': 400,
        'max_color': 650
    },
    {
        'name': "Honey Malt",
        'match': '^.*(Honey.*Malt|Malt.*Honey|Honey.*US|Honey.*CA|Honey.*Gambrinus|Gambrinus.*Honey).*$',
        'min_color': 15
    },
    {
        'name': 'Victory Malt',
        'match': '^.*(Victory|Biscuit).*$'
    },
    {
        'name': 'Brown Malt',
        'match': '^.*Brown Malt.*$|^Brown$'
    },
    {
        'name': 'Rye Malt',
        'match': '^.*(US.*Rye|Rye.*US).*$|^Rye$'
    },
    {
        'name': "6-Row Brewers Malt",
        'match': '^.*6.Row.*$',
        'max_color': 4
    },
    {
        'name': "Golden Promise",
        'match': '^.*Golden.*Promise.*$'
    },
    {
        'name': "Roasted Barley",
        'match': '^.*Roast.*Barley.*$'
    },
    {
        'name': "Pale Wheat Malt",
        'match': '^.*Pale Wheat Malt.*$'
    },
    {
        'name': "Acid Malt",
        'match': '^.*Acid.*Malt.*$'
    },
    {
        'name': "Sucrose (Table Sugar)",
        'match': '^.*(Sucrose|Table.*Sugar|Cane.*Sugar).*$'
    },
    {
        'name': "Melanoidin Malt",
        'match': '^.*Mel.noid.*$'
    },
    {
        'name': "Brown Sugar, Light",
        'match': '^.*Brown Sugar.*$',
        'max_color': 20
    },
    {
        'name': "Brown Sugar, Dark",
        'match': '^.*Brown Sugar.*$',
        'max_color': 60
    },
    {
        'name': "Carafa Special I",
        'match': '^.*Carafa.*$',
        'max_color': 375
    },
    {
        'name': "Carafa Special II",
        'match': '^.*Carafa.*$',
        'max_color': 475
    },
    {
        'name': "Carafa Special III",
        'match': '^.*Carafa.*$',
        'max_color': 575
    }
]
style_rewrites = [
    {
        'new': 'California Common',
        'old': '^.*California Common Beer.*$'
    },
    {
        'new': 'Historical Beer: Gose',
        'old': '^.*Gose.*$'
    },
    {
        'new': 'International Dark Lager',
        'old': '^.*Dark American Lager.*$'
    },
    {
        'new': 'Specialty Smoked Beer',
        'old': '^Other Smoked Beer$'
    },
    {
        'new': 'Historical Beer: Pre-Prohibition Lager',
        'old': '^.*(Classic American Pilsner|Pre-Prohibition Lager).*$'
    },
    {
        'new': 'Historical Beer: Kentucky Common',
        'old': '^.*Kentucky Common.*$'
    },
    {
        'new': 'Winter Seasonal Beer',
        'old': '^.*Holiday/Winter Special Spiced Beer.*$'
    },
    {
        'new': 'Ordinary Bitter',
        'old': '^.*Standard/Ordinary Bitter.*$'
    },
    {
        'new': 'British Brown Ale',
        'old': '^.*English Brown.*$'
    },
    {
        'new': 'International Lager',
        'old': '^.*Premium American Lager.*$'
    },
    {
        'new': 'Strong Bitter',
        'old': '^.*Strong Bitter.*$'
    },
    {
        'new': 'Imperial Stout',
        'old': '^.*Imperial Stout.*$'
    },
    {
        'new': 'American Wheat Beer',
        'old': '^.*American (Wheat|Rye).*$'
    },
    {
        'new': 'American Porter',
        'old': '^.*Robust Porter.*$'
    },
    {
        'new': 'Irish Stout',
        'old': '^.*Dry.*Stout.*$'
    },
    {
        'new': 'Experimental Beer',
        'old': '^.*Specialty Beer.*$'
    },
    {
        'new': 'Best Bitter',
        'old': '^.*Best.*Bitter.*$'
    },
    {
        'new': 'Weissbier',
        'old': '^.*(Weizen|Weissbier).*$'
    },
    {
        'new': 'Double IPA',
        'old': '^.*Imperial IPA.*$'
    },
    {
        'new': 'German Pils',
        'old': '^.*German.*Pils.*$'
    },
    {
        'new': 'Märzen',
        'old': '^.*(Oktoberfest|M.rzen).*$'
    },
    {
        'new': 'Altbier',
        'old': '^.*(D.sseldorf|Altbier).*$'
    },
    {
        'new': 'Scottish Export',
        'old': '^.*Scottish.*Export.*$'
    },    {
        'new': 'Kölsch',
        'old': '^.*k.*lsch.*$'
    },    {
        'new': 'Dunkles Bock',
        'old': '^.*Traditional Bock.*$'
    },    {
        'new': 'Schwarzbier',
        'old': '^.*Schwarzbier.*$'
    },
    {
        'new': 'Dark Mild',
        'old': '^Mild$'
    },
    {
        'new': 'Helles Bock',
        'old': '^.*(Maibock|Helles Bock).*$'
    },
    {
        'new': 'Wee Heavy',
        'old': '^.*Strong Scotch.*$'
    },
    {
        'new': 'American Lager',
        'old': '^.*Standard American Lager.*$'
    },
    {
        'new': 'American Light Lager',
        'old': '^.*Li(ght|te) American Lager.*$'
    },
    {
        'new': 'American Light Lager',
        'old': '^.*American Lite Lager.*$'
    },
    {
        'new': 'Czech Premium Pale Lager',
        'old': '^.*Bohemian Pils.*$'
    },
    {
        'new': 'British Brown Ale',
        'old': 'Brown Porter'
    }
]
hop_rewrites = [
    {
        'match': r'^.*east.*kent.*$',
        'replace': 'East Kent Golding (UK)'
    },
    {
        'match': r'^.*Galaxy.*$',
        'replace': 'Galaxy (AU)'
    },
    {
        'match': r'^.*premiant.*$',
        'replace': 'Premiant (CZ)'
    },
    {
        'match': r'^.*sladek.*$',
        'replace': 'Sladek (CZ)'
    },
    {
        'match': r'^.*styrian.*celeia.*$',
        'replace': 'Celeia (SI)'
    },
    {
        'match': r'^.*styrian.*golding.*$',
        'replace': 'Golding (SI)'
    },
    {
        'match': r'(Centennial|Citra|Amarillo|Cascade|Simcoe|Chinook|Columbus|Willamette|Nugget|Mosaic|Warrior|Crystal|Cluster|Summit|Cluster|Crystal|Liberty|Galena|Ahtanum|Sterling|Glacier|Palisade|El Dorado|Apollo|Horizon|Bravo|Calypso|Santiam|Newport|Super Galena).*\(US\)',
        'replace': r'\g<1>'
    },
    {
        'match': r'^.*bobek.*$',
        'replace': 'Bobek (SI)'
    },
    {
        'match': r'^.*eureka.*$',
        'replace': 'Eureka'
    },
    {
        'match': r'^.*h.*mittel.*$|^Mittel.*$',
        'replace': 'Hallertau Mittelfrüh (DE)'
    },
    {
        'match': r'^.*hersbruck.*$',
        'replace': 'Hersbrucker (DE)'
    },
    {
        'match': r'^.*nelson.*$',
        'replace': 'Nelson Sauvin (NZ)'
    },
    {
        'match': r'^.*sorachi.*$',
        'replace': 'Sorachi Ace'
    },
    {
        'match': r'^.*willam.*$',
        'replace': 'Willamette'
    },
    {
        'match': r'^.*william.*$',
        'replace': 'Willamette'
    },
    {
        'match': r'^(.*kent.*|golding.*uk.*|uk.*golding.*|.*ek.*|golding(|s))$',
        'replace': 'East Kent Golding (UK)'
    },
    {
        'match': r'^(.*styrian.*a(|u)rora.*|super.*styrian.*)$',
        'replace': 'Aurora (SI)'
    },
    {
        'match': r'^((ger|hal|gr|de).*magnum|magnum.*(ger|hal|gr|de).*)$',
        'replace': 'Magnum (DE)'
    },
    {
        'match': r'^((Yakima|US) Magnum|Magnum|magnum.*us.*|us.*magnum.*)$',
        'replace': 'Magnum (US)'
    },
    {
        'match': r'^(cz.*saaz|saaz|saaz.*cz.*)$',
        'replace': 'Saaz (CZ)'
    },
    {
        'match': r'^(fugg.*(uk|u\.k\.).*|(uk|u\.k\.).*fugg.*|fuggle(|s))$',
        'replace': 'Fuggle (UK)'
    },
    {
        'match': r'^(fugg.*(us|u\.s\.).*|(us|u\.s\.).*fugg.*)$',
        'replace': 'Fuggle (US)'
    },
    {
        'match': r'^(german |)hallert(au|eau)(|er)(| \(de\))$',
        'replace': 'Hallertau Mittelfrüh (DE)'
    },
    {
        'match': r'^(german |)hallertau(|er)(| \(de\))$',
        'replace': 'Hallertau Mittelfrüh (DE)'
    },
    {
        'match': r'^(gold.*bread.*|.*bread.*gold.*)$',
        'replace': 'Whitbread Golding Variety (UK)'
    },
    {
        'match': r'^(tettn(a|e)ng(|er)|(ger|gr|de).*tettn(a|e)ng(|er)|tettn(a|e)ng(|er).*(ger|gr|de).*)$',
        'replace': 'Tettnang (DE)'
    },
    {
        'match': r'^(tettn(a|e)ng(|er)|(us|ych|u\.s\.).*tettn(a|e)ng(|er)|tettn(a|e)ng(|er).*(us|ych|u\.s\.).*)$',
        'replace': 'Tettnang (US)'
    },
    {
        'match': r'^(us.*golding.*|golding.*us.*)$',
        'replace': 'Golding (US)'
    },
    {
        'match': r'^(us.*saaz|saaz|saaz.*us.*)$',
        'replace': 'Saaz (US)'
    },
    {
        'match': r'^m.*hood.*$',
        'replace': 'Mt. Hood'
    },
    {
        'match': r'Domestic Hallertau',
        'replace': 'Hallertau (US)'
    }
]

# We don't care about these at all, they contribute nothing to the recipes from a flavor perspective
fermentable_bypass = ['Rice Hulls', 'Acid Malt']

# Add fermentable_rewrite for each Crystal malt
for lov in [10, 20, 30, 40, 60, 80, 90, 120]:
    fermentable_rewrites.append({
        'name': 'Caramel Malt {}L'.format(lov),
        'match': '^.*(Caramel|Crystal).*{}.*$'.format(lov)
    })

# Get all recipe paths
brewtoad = list(Path("./brewtoad_scrape").rglob("*.xml"))#[0:1200]
brewers_friend = list(
    Path("./brewersfriend_scrape/recipes").rglob("*.xml"))#[0:1000]
# beersmith = list(
#     Path("./beersmith_scrape/recipes").rglob("*.xml"))

beerxml_list =  brewers_friend + brewtoad # + beersmith
#beerxml_list = brewers_friend
random.shuffle(beerxml_list)


def import_recipe(beerxml_file):
    try:
        recipe = parser.parse('./{}'.format(str(beerxml_file)))[0]
        style = recipe.style.name
        fermentables = []
        addition_data = {}
        fermentable_result = {}
        hop_result = {}

        # Rewrite style names
        for rule in style_rewrites:
            match = re.match(rule['old'], style, flags=re.IGNORECASE)
            if match:
                # print('Rewriting style: {} -> {}'.format(style, rule['new']))
                style = rule['new']
                recipe.style.name = rule['new']
                break

        specs = bjcp_name(style)
        if not specs:
            return {
                'status': 'unmatched_style',
                'data': {
                    'name': style,
                    'type': 'style',
                    'color': None,
                    'recipe_style': None
                }
            }

        # Rewrite fermentable names
        for fermentable in recipe.fermentables:
            fermentable_name = fermentable.name.strip()
            # Remove all LME/DME by raising an exception and killing all future parsing of the recipe
            extract = re.match(
                "^.*(CBW|DME|LME|Extract|Malt Syrup).*$", fermentable_name, flags=re.IGNORECASE)
            if extract:
                fermentable_result = {
                    'status': 'uses_extract',
                    'data': fermentable_name
                }

            # Rewrite fermentable names
            for rule in fermentable_rewrites:
                match = re.match(
                    rule['match'], fermentable.name, flags=re.IGNORECASE)
                if match and rule.get('min_color', 0) <= fermentable.color <= rule.get('max_color', 999):
                    fermentable.name = rule['name']
                    break

        # Rewrite hop names
        for recipe_hop in recipe.hops:
            for rule in hop_rewrites:
                re_rule = re.compile(rule['match'], flags=re.IGNORECASE)
                match = re.match(re_rule, str(recipe_hop.name).strip())
                if match:
                    recipe_hop.name = re.sub(re_rule, r'{}'.format(
                        rule['replace']), str(recipe_hop.name).strip())
                    break

        # Analyze recipe after importing and rewriting
        og_match = points(float(specs.get('og', {}).get('low', 1)))*.75 <= points(
            recipe.og) <= points(float(specs.get('og', {}).get('high', 1.400)))*1.25
        srm_match = float(specs.get('srm', {}).get('low', 0))*.75 <= recipe.color <= float(
            specs.get('srm', {}).get('high', 999))*1.25
        ibu_match = float(specs.get('ibu', {}).get('low', 0))*.75 <= recipe.ibu <= float(
            specs.get('ibu', {}).get('high', 999))*1.25

        # Fermentable Analysis: only include recipes with a to-style OG and color
        if not (og_match and srm_match):
            fermentable_result = {
                'status': 'not_to_style',
                'data': {
                    'og_match': og_match,
                    'srm_match': srm_match
                }
            }
        else:
            fermentables = []
            for fermentable in recipe.fermentables:
                # Don't worry about malts in our bypass list, pretend they don't exist and go to the next one
                if fermentable.name in fermentable_bypass:
                    break

                matched_fermentable = all_grains.get_grain_by_name(
                    fermentable.name)
                if not matched_fermentable:
                    # Skip fermentable analysis if we can't match all fermentables in the recipe
                    fermentable_result = {
                        'status': 'unmatched_fermentable',
                        'data': {
                            'name': fermentable.name,
                            'type': 'fermentable',
                            'color': fermentable.color,
                            'recipe_style': style
                        }
                    }
                    break

                # Calculate total amount of grains ignoring the bypass list
                total_amount = sum(
                    fermentable.amount for fermentable in recipe.fermentables if fermentable.name not in fermentable_bypass)

                fermentables.append({
                    'name': fermentable.name,
                    'category': matched_fermentable.category,
                    'percent': fermentable.amount / total_amount * 100,
                    'color': fermentable.color,
                    'ppg': fermentable.ppg,
                    'addition': fermentable.addition,
                    'matched_fermentable': matched_fermentable
                })

            if not fermentable_result:
                grain_bill = grain.GrainBill(
                    [fermentable['matched_fermentable']
                    for fermentable in fermentables],
                    [fermentable['percent']
                    for fermentable in fermentables]
                )
                fermentable_result = {
                    'status': 'success',
                    'data': {
                        'fermentables': fermentables,
                        'grain_bill': grain_bill,
                        'sensory_data': grain_bill.get_sensory_data()
                    }
                }
        # Hop Analysis: only include recipes with to-style IBUs
        if not ibu_match:
            hop_result = {
                'status': 'not_to_style',
                'data': None
            }
        else:
            try:
                dryhop = []
                flameout = []
                min_5 = []
                min_10 = []
                min_15 = []
                min_30 = []
                min_45 = []
                min_60 = []

                for h in recipe.hops:
                    matching_hop = all_hops.get_hop_by_name(h.name)
                    if matching_hop:
                        # Use the actual recipe hop alpha, not the theoritical
                        matching_hop.alpha = h.alpha

                        # Fix recipes with first wort boil time set to 0 for some reason
                        if h.use.lower() == 'first wort' and h.time < recipe.boil_time:
                            h.time = recipe.boil_time

                        if str(h.use).lower() == 'dry hop':
                            dryhop.append(hop.HopAddition(
                                matching_hop, h.time, str(h.use), h.amount * 1000))
                        elif str(h.use).lower() in ['aroma', 'whirlpool']:
                            # Treat aroma and whirlpool hops as flameout/whirlpool at 0 minutes
                            flameout.append(hop.HopAddition(
                                matching_hop, 0, 'whirlpool', h.amount * 1000))
                        elif str(h.use).lower() in ['boil', 'first wort']:
                            # Treat 0-2 minute boil additions as flameout
                            if h.time < 2.5:
                                flameout.append(hop.HopAddition(
                                    matching_hop, 0, 'whirlpool', h.amount * 1000))
                            # Round to closest boil addition for the rest, don't adjust the timing though
                            elif h.time < 7.5:
                                min_5.append(hop.HopAddition(
                                    matching_hop, h.time, h.use, h.amount * 1000))
                            elif h.time < 12.5:
                                min_10.append(hop.HopAddition(
                                    matching_hop, h.time, h.use, h.amount * 1000))
                            elif h.time < 22.5:
                                min_15.append(hop.HopAddition(
                                    matching_hop, h.time, h.use, h.amount * 1000))
                            elif h.time < 37.5:
                                min_30.append(hop.HopAddition(
                                    matching_hop, h.time, h.use, h.amount * 1000))
                            elif h.time < 52.5:
                                min_45.append(hop.HopAddition(
                                    matching_hop, h.time, h.use, h.amount * 1000))
                            else:
                                min_60.append(hop.HopAddition(
                                    matching_hop, h.time, h.use, h.amount * 1000))
                    else:
                        # Ignore recipes where we can't match all hops
                        raise Exception('Unmatched hop: {}'.format(h.name))

                    boil = min_60 + min_45 + min_30 + min_15 + min_10 + min_5
                    recipe_hops = hop.HopBill(boil + flameout + dryhop)

                    if boil:
                        boil_bill = hop.HopBill(boil)

                        # Exclude recipes with more than 12oz/5gal or 339g/19L in the boil
                        if boil_bill.amount() / recipe.batch_size > 17.97:
                            raise Exception('More than 12oz/5gal in boil.')

                    else:
                        # Ignore recipes with no boil hops
                        raise Exception('No boil hops.')

                    if min_60:
                        bill = hop.HopBill(min_60)
                        addition_data['60'] = {
                            'ibu': bill.ibu(recipe.og, recipe.batch_size),
                            'amount': bill.amount() / recipe.batch_size,
                            'unique_hops': len(bill.unique_hops()),
                            'flavor': bill.get_sensory_data(recipe.og, recipe.batch_size, per_liter=True)
                        }
                    if min_45:
                        bill = hop.HopBill(min_45)
                        addition_data['45'] = {
                            'ibu': bill.ibu(recipe.og, recipe.batch_size),
                            'amount': bill.amount() / recipe.batch_size,
                            'unique_hops': len(bill.unique_hops()),
                            'flavor': bill.get_sensory_data(recipe.og, recipe.batch_size, per_liter=True)
                        }
                    if min_30:
                        bill = hop.HopBill(min_30)
                        addition_data['45'] = {
                            'ibu': bill.ibu(recipe.og, recipe.batch_size),
                            'amount': bill.amount() / recipe.batch_size,
                            'unique_hops': len(bill.unique_hops()),
                            'flavor': bill.get_sensory_data(recipe.og, recipe.batch_size, per_liter=True)
                        }
                    if min_15:
                        bill = hop.HopBill(min_15)
                        addition_data['15'] = {
                            'ibu': bill.ibu(recipe.og, recipe.batch_size),
                            'amount': bill.amount() / recipe.batch_size,
                            'unique_hops': len(bill.unique_hops()),
                            'flavor': bill.get_sensory_data(recipe.og, recipe.batch_size, per_liter=True)
                        }
                    if min_10:
                        bill = hop.HopBill(min_10)
                        addition_data['10'] = {
                            'ibu': bill.ibu(recipe.og, recipe.batch_size),
                            'amount': bill.amount() / recipe.batch_size,
                            'unique_hops': len(bill.unique_hops()),
                            'flavor': bill.get_sensory_data(recipe.og, recipe.batch_size, per_liter=True)
                        }
                    if min_5:
                        bill = hop.HopBill(min_5)
                        addition_data['5'] = {
                            'ibu': bill.ibu(recipe.og, recipe.batch_size),
                            'amount': bill.amount() / recipe.batch_size,
                            'unique_hops': len(bill.unique_hops()),
                            'flavor': bill.get_sensory_data(recipe.og, recipe.batch_size, per_liter=True)
                        }
                    if flameout:
                        bill = hop.HopBill(flameout)
                        addition_data['flameout'] = {
                            'ibu': bill.ibu(recipe.og, recipe.batch_size),
                            'amount': bill.amount() / recipe.batch_size,
                            'unique_hops': len(bill.unique_hops()),
                            'flavor': bill.get_sensory_data(recipe.og, recipe.batch_size, per_liter=True)
                        }
                    if dryhop:
                        bill = hop.HopBill(dryhop)
                        addition_data['dryhop'] = {
                            'ibu': bill.ibu(recipe.og, recipe.batch_size),
                            'amount': bill.amount() / recipe.batch_size,
                            'unique_hops': len(bill.unique_hops()),
                            'flavor': bill.get_sensory_data(recipe.og, recipe.batch_size, per_liter=True)
                        }

                    # Exclude recipes with more than 1lb/5gal or 454g/19L in the whirlpool or dry hop
                    non_boil_bill = hop.HopBill(flameout + dryhop)
                    if non_boil_bill.amount() / recipe.batch_size > 23.96:
                        raise Exception(
                            'More than 1lb/5gal in whirlpool/dryhop.')

                    hop_result = {
                        'status': 'success',
                        'data': {
                            'recipe': {
                                'ibu': recipe_hops.ibu(recipe.og, recipe.batch_size),
                                'amount': recipe_hops.amount() / recipe.batch_size,
                                'unique_hops': len(recipe_hops.unique_hops()),
                                'flavor': recipe_hops.get_sensory_data(recipe.og, recipe.batch_size, per_liter=True)
                            },
                            'additions': addition_data
                        }
                    }
            except Exception as e:
                hop_result = {
                    'status': 'error',
                    'data': e
                }

        return {
            'status': 'success',
            'style': recipe.style.name,
            'og': recipe.og,
            'color': recipe.color,
            'fermentable_data': fermentable_result,
            'hop_data': hop_result
        }

    except Exception as e:
        return {
            'status': 'Unable to import recipe',
            'data': e
        }

if __name__ == '__main__':
    
    print('Executing analysis')
    # Parse the recipes (multi-process)
    executor = concurrent.futures.ProcessPoolExecutor()
    # futures = executor.map(import_recipe, beerxml_list)  # [0:10000])
    futures = executor.map(import_recipe, beerxml_list)
    parse_results = list(futures)
    recipe_results = [result
                    for result in parse_results if result['status'] == 'success']

    style_results = []
    for style in styles:
        fermentable_analysis = None
        hop_analysis = None
        style_flavor = {}
        style_grain_usage = []
        style_sensory_data = []
        addition_data = {}
        style_category_usage = []

        results = [result for result in recipe_results if result['style'] == style]

        if not results:
            print('No recipes for {}'.format(style))
            continue

        # Analyze hop data
        try:
            hop_results = [result['hop_data']['data']
                        for result in results if result.get('hop_data', {}).get('status') == 'success']
            # Get the flavor range and dump recipes that are outliers
            flavor_totals = np.array([result['recipe']['flavor']['total']
                                    for result in hop_results])
            flavor_stats = get_stats(flavor_totals)
            flavor_min = flavor_stats['min']
            flavor_max = flavor_stats['max']

            hop_results = [result for result in hop_results if flavor_max >
                        result['recipe']['flavor']['total'] > flavor_min]

            if not hop_results:
                print('No hops for {}'.format(style))
                continue

            # Build the overall flavor profile data for the style
            for keyword in hop_keywords:
                flavor_data = [result['recipe']['flavor']['descriptors'][keyword]
                            for result in hop_results if result['recipe']['flavor']['descriptors'][keyword]]
                nonzero = [value for value in flavor_data if value > 0]

                # Filter out hop flavor descriptors that are in less than 5% of recipes
                if len(nonzero) >= len(results) * .05:
                    f_std = np.std(flavor_data)
                    f_mean = np.mean(flavor_data)

                    style_flavor[keyword] = get_stats(flavor_data)
                    style_flavor[keyword]['recipe_count'] = len(flavor_data)

            # Get the overall style IBU and hop amounts
            ibu_data = [result['recipe']['ibu'] for result in hop_results]
            style_ibu = get_stats(ibu_data)

            amt_data = [result['recipe']['amount'] for result in hop_results]
            style_amount = get_stats(amt_data)

            # Build all of the above data, but specific to each hop addition timing
            for addition in ['60', '45', '30', '15' '10', '5', 'flameout', 'dryhop']:
                addition_flavor = {}
                addition_results = [result['additions'].get(
                    addition) for result in hop_results if result['additions'].get(addition, None)]

                if addition_results:
                    # Parse flavor results only for keywords that are in the overall style data as well
                    for keyword in style_flavor.keys():
                        keyword_results = [result['flavor']['descriptors']
                                        [keyword] for result in addition_results]
                        addition_flavor[keyword] = get_stats(keyword_results)
                        addition_flavor[keyword]['recipe_count'] = sum(
                            1 for result in keyword_results if result > 0)

                    unique_hops_list = np.array([result['unique_hops']
                                                for result in addition_results])

                    if unique_hops_list.any():
                        unique_hops = int(round(np.mean(unique_hops_list)))
                    else:
                        unique_hops = 0

                    addition_data[addition] = {
                        'ibu': get_stats([result['ibu'] for result in addition_results]),
                        'amount': get_stats([result['amount'] for result in addition_results]),
                        'unique_hops': unique_hops,
                        'flavor': {
                            'total': get_stats([result['flavor']['total'] for result in addition_results]),
                            'descriptors': addition_flavor
                        },
                        'recipe_count': len(addition_results)
                    }
        except Exception as e:
            print("Error analyzing hops for {}: {}".format(style, e))
            continue

        try:
            unique_hops = int(
                round(np.mean([result['recipe']['unique_hops'] for result in hop_results])))
        except:
            unique_hops = 1

        hop_analysis = {
            'recipe_count': len(hop_results),
            'recipe': {
                'ibu': style_ibu,
                'amount': style_amount,  # in g/L
                'unique_hops': unique_hops,
                'flavor': {
                    'total': get_stats([result['recipe']['flavor']['total'] for result in hop_results]),
                    'descriptors': style_flavor
                }
            },
            'additions': addition_data
        }

        try:
            fermentable_results = [result['fermentable_data']['data']
                                for result in results if result['fermentable_data']['status'] == 'success']

            # Get the average fermentable category usage for the style
            for category_name in fermentable_categories:
                category_usage_list = [[fermentable['percent']
                                        for fermentable in result['fermentables'] if fermentable['category'] == category_name] for result in fermentable_results]
                category_usage = np.array(
                    [sum(usage) for usage in category_usage_list])
                category_stats = get_stats(category_usage)

                print(category_stats)

                if category_usage.any():
                    category_unique_fermentables = np.array(
                        [len(usage) for usage in category_usage_list if len(usage) > 0])
                    unique_fermentables = int(
                        round(np.mean(category_unique_fermentables)))
                    usage_min = int(round(max(0, category_stats['min'])))
                    usage_max = int(round(min(100, category_stats['max'])))
                    recipe_count = np.count_nonzero(category_usage)

                else:
                    unique_fermentables = 0
                    usage_min = 0
                    usage_max = 0
                    recipe_count = 0

                style_category_usage.append({
                    'name': category_name,
                    'stats': category_stats,
                    'usage': {
                        'min': usage_min,
                        'max': usage_max
                    },
                    'unique_fermentables': unique_fermentables,
                    'category_object': category.Category(category_name, unique_fermentables, usage_min, usage_max),
                    'recipe_count': recipe_count
                })
        except Exception as e:
            print('Error processing fermentable categories for {}: {}'.format(style, e))
            continue

        try:
            # Get the average usage for each fermentable
            fermentable_list = []
            recipe_fermentables = [recipe['fermentables']
                                for recipe in fermentable_results]
            for recipe in recipe_fermentables:
                for recipe_fermentable in recipe:
                    fermentable_list.append(recipe_fermentable)

            # Get unique fermentable names
            names = [fermentable['name']
                    for fermentable in fermentable_list]
            unique_names = list(set(names))

            # Iterate over each fermentable, getting its average usage and adding to the style database
            for fermentable_name in unique_names:
                # Check if the name exists in our grain db, only add to the database if we have it
                matched_fermentable = all_grains.get_grain_by_name(
                    fermentable_name)
                if matched_fermentable:
                    # Get the fermentable usage
                    usage = [fermentable['percent'] for fermentable in fermentable_list
                            if fermentable['name'] == fermentable_name]
                    fermentable_usage_stats = get_stats(usage)
                    fermentable_usage_min = int(
                        round(fermentable_usage_stats['min']))
                    fermentable_usage_max = int(
                        round(fermentable_usage_stats['max']))
                    style_grain_usage.append({
                        'slug': matched_fermentable.slug,
                        'stats': get_stats(usage),
                        'usage': {
                            'min': max(0, fermentable_usage_min),
                            'max': min(100, fermentable_usage_max)
                        },
                        'fermentable_object': grain.Grain(
                            name=matched_fermentable.name,
                            brand=matched_fermentable.brand,
                            potential=matched_fermentable.potential,
                            color=matched_fermentable.color,
                            category=matched_fermentable.category,
                            sensory_data=matched_fermentable.sensory_data,
                            min_percent=max(0, fermentable_usage_min),
                            max_percent=min(100, fermentable_usage_max)
                        ),
                        'recipe_count': len(usage)
                    })
        except Exception as e:
            print('Error processing fermentables for {}: {}'.format(style, e))
            continue

        try:
            # Get min/max style data for the given grain profile
            try:
                style_fermentable_list = grain.GrainList(
                    [style_fermentable['fermentable_object'] for style_fermentable in style_grain_usage])
                category_profile = category.CategoryProfile(
                    [style_category['category_object'] for style_category in style_category_usage])
                style_sensory_minmax = style_fermentable_list.get_sensory_profiles(
                    category_profile)
            except Exception as e:
                print('Failed to get recipe data for {}: {}'.format(style, e))
                continue

            # Iterate over each sensory keyword, get the average values for each keyword in the style
            for keyword in fermentable_keywords:
                # Get average sensory data for the given style data for all recipes
                sensory_values = np.array([recipe['sensory_data'][keyword]
                                        for recipe in fermentable_results])

                # Get the sensory data possible from the grain profile
                for sensory_minmax in style_sensory_minmax:
                    if sensory_minmax['name'] == keyword:
                        sensory_from_grains = sensory_minmax
                        break

                if not sensory_from_grains:
                    sensory_from_grains = {
                        'name': keyword,
                        'min': 0,
                        'max': 0
                    }

                stats = get_stats(sensory_values)
                style_sensory_data.append({
                    'name': keyword,
                    'min': round(max(0, stats['min'], sensory_from_grains['min']), 3),
                    'max': round(min(5, stats['max'], sensory_from_grains['max']), 3),
                    'stats': stats
                })

            # Remove the fermentable object, can't export it to JSON
            for style_fermentable in style_grain_usage:
                del style_fermentable['fermentable_object']

            for category_usage in style_category_usage:
                del category_usage['category_object']

            fermentable_analysis = {
                'recipe_count': len(fermentable_results),
                'grain_usage': style_grain_usage,
                'unique_fermentables': int(round(np.mean([len(recipe['fermentables']) for recipe in fermentable_results]))),
                'category_usage': style_category_usage,
                'sensory_data': style_sensory_data
            }

        except Exception as e:
            print("Error analyzing fermentable data for {}: {}".format(style, e))
            continue

        if fermentable_analysis:  # and hop_analysis:
            style_results.append({
                'style': style,
                'recipe_count': len(results),
                'fermentables': fermentable_analysis,
                'hops': hop_analysis
            })

    with open('styles.json', 'w') as f:
        json.dump(style_results, f)
