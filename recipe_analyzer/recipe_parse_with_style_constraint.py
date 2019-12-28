from pathlib import Path
from pybeerxml import Parser
import sys
import numpy as np
import re
import csv
import json
import concurrent.futures

sys.path.append('../')
from brewgen.backend.models import grain, category

def points(og):
    return (og - 1) * 1000


with open('styleguide-2015.json', 'r') as f:
    bjcp = json.load(f)


def bjcp_name(name):
    """Return beer stats for a style name"""
    for bev_class in bjcp['styleguide']['class']:
        if bev_class['type'] == 'beer':
            for style_category in bev_class['category']:
                for subcat in style_category['subcategory']:
                    if subcat['name'] == name:
                        return subcat.get('stats', {})


all_grains = grain.GrainModel()
category_model = category.CategoryModel()
parser = Parser()
recipe_db = []

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

# We don't care about these at all, they contribute nothing to the recipes from a flavor perspective
fermentable_bypass = ['Rice Hulls', 'Acid Malt']

# Add fermentable_rewrite for each Crystal malt
for lov in [10, 20, 30, 40, 60, 80, 90, 120]:
    fermentable_rewrites.append({
        'name': 'Caramel Malt {}L'.format(lov),
        'match': '^.*(Caramel|Crystal).*{}.*$'.format(lov)
    })

# Get all recipe paths
brewtoad = list(Path("./brewtoad_scrape").rglob("*.xml"))  # [0:120000]
brewers_friend = list(
    Path("./brewersfriend_scrape/recipes").rglob("*.xml"))  # [0:100000]
beersmith = list(
    Path("./beersmith_scrape/recipes").rglob("*.xml"))

beerxml_list = brewtoad + brewers_friend + beersmith

def parse_beerxml_file(beerxml_file):
    try:
        recipe = parser.parse('./{}'.format(str(beerxml_file)))[0]
    except:
        print("Failed to parse ./{}".format(str(beerxml_file)))
        recipes = []
    
    try:
        style = recipe.style.name

        # Rewrite style names
        for rule in style_rewrites:
            match = re.match(rule['old'], style, flags=re.IGNORECASE)
            if match:
                #print('Rewriting style: {} -> {}'.format(style, rule['new']))
                style = rule['new']
                break

        specs = bjcp_name(style)
        if specs:
            og_match = points(float(specs.get('og', {}).get('low', 1)))*.75 <= points(
                 recipe.og) <= points(float(specs.get('og', {}).get('high', 1.400)))*1.25
            srm_match = float(specs.get('srm', {}).get('low', 0))*.75 <= recipe.color <= float(
                 specs.get('srm', {}).get('high', 999))*1.25
            # ibu_match = float(specs.get('ibu', {}).get('low', 0))*.5 <= recipe.ibu <= float(
            #     specs.get('ibu', {}).get('high', 999))*1.5
            ibu_match = True

            # Only include recipes with a to-style OG and color
            if og_match and srm_match and ibu_match:
                fermentables = []
                for fermentable in recipe.fermentables:
                    fermentable_name = fermentable.name.strip()
                    # Remove all LME/DME by raising an exception and killing all future parsing of the recipe
                    extract = re.match(
                        "^.*(CBW|DME|LME|Extract|Malt Syrup).*$", fermentable_name, flags=re.IGNORECASE)
                    if extract:
                        return {
                            'status': 'uses_extract',
                            'data': fermentable_name
                        }                

                    # Rewrite fermentable names
                    for rule in fermentable_rewrites:
                        match = re.match(
                            rule['match'], fermentable.name, flags=re.IGNORECASE)
                        if match and rule.get('min_color', 0) <= fermentable.color <= rule.get('max_color', 999):
                            # print('Rewriting {} -> {}'.format(fermentable_name, rule['name']))
                            fermentable_name = rule['name']
                            break

                    # Don't worry about malts in our bypass list, pretend they don't exist and go to the next one
                    if fermentable_name in fermentable_bypass:
                        break

                    matched_fermentable = all_grains.get_grain_by_name(
                        fermentable_name)
                    if not matched_fermentable:
                        return {
                            'status': 'unmatched_fermentable',
                            'data': {
                                'name': fermentable_name,
                                'type': 'fermentable',
                                'color': fermentable.color,
                                'recipe_style': style
                            }
                        }         
                        

                    # Calculate total amount of grains ignoring the bypass list
                    total_amount = sum(
                        fermentable.amount for fermentable in recipe.fermentables if fermentable_name not in fermentable_bypass)

                    fermentables.append({
                        'name': fermentable_name,
                        'category': matched_fermentable.category,
                        'percent': fermentable.amount / total_amount * 100,
                        'color': fermentable.color,
                        'ppg': fermentable.ppg,
                        'addition': fermentable.addition,
                        'matched_fermentable': matched_fermentable
                    })

                grain_bill = grain.GrainBill(
                    [fermentable['matched_fermentable']
                        for fermentable in fermentables],
                    [fermentable['percent']
                        for fermentable in fermentables]
                )
                return {
                    'status': 'success',
                    'data': {
                        'style': style,
                        'category': recipe.style.category,
                        'og': recipe.og,
                        'color': recipe.color,
                        'fermentables': fermentables,
                        'grain_bill': grain_bill,
                        'sensory_data': grain_bill.get_sensory_data()
                    }
                }

            else:
                # style_spec = {
                #     'og': {
                #         'low': points(float(specs.get('og', {}).get('low', 1))),
                #         'high': points(float(specs.get('og', {}).get('high', 1.200))),
                #         'recipe': points(recipe.og)
                #     },
                #     'srm': {
                #         'low': float(specs.get('srm', {}).get('low', 0)),
                #         'high': float(specs.get('srm', {}).get('high', 999)),
                #         'recipe': recipe.color
                #     },
                #     'ibu': {
                #         'low': float(specs.get('ibu', {}).get('low', 0)),
                #         'high': float(specs.get('ibu', {}).get('high', 999)),
                #         'recipe': recipe.ibu
                #     }
                # }
                return {
                    'status': 'not_to_style',
                    'data': 'Recipe not to style'
                }         
        else:
            return {
                    'status': 'unmatched_style',
                    'data': {
                        'name': style,
                        'type': 'style',
                        'color': None,
                        'recipe_style': None
                    }
                } 

    except Exception as err:
        return {
            'status': 'failure',
            'data': err
        }
        # print(err)
        # print("Failed to parse recipe in ./{}".format(str(beerxml_file)))

# Parse the recipes (multi-process)
executor = concurrent.futures.ProcessPoolExecutor()
futures = executor.map(parse_beerxml_file, beerxml_list)
parse_results = list(futures)

recipe_db = [result['data'] for result in parse_results if result['status'] == 'success']

# Get a list of style and grain category games
styles = list(set([recipe['style'] for recipe in recipe_db]))
categories = category_model.get_category_names()

print('Unmatched Style:       {}'.format(sum(1 for result in parse_results if result['status'] == 'unmatched_style')))
print('Unmatched Fermentable: {}'.format(sum(1 for result in parse_results if result['status'] == 'unmatched_fermentable')))
print('Not to Style:          {}'.format(sum(1 for result in parse_results if result['status'] == 'not_to_style')))
print('Contains Extract:      {}'.format(sum(1 for result in parse_results if result['status'] == 'uses_extract')))
print('TOTAL RECIPES:         {}'.format(sum(1 for result in parse_results)))
print('USABLE RECIPES:        {}'.format(sum(1 for result in parse_results if result['status'] == 'success')))


def analyze_style(style):
    recipe_count = 0
    fermentable_list = []
    fermentable_usage = []
    style_grain_usage = []
    style_category_data = []
    style_category_usage = []
    style_category_fermentable_count = []
    style_sensory_data = []
    style_unique_fermentables = []

    # Calculate the average grain usage from each category, only use recipes with 100% grain coverage, remove any recipes that use extracts
    for recipe in recipe_db:
        if recipe['style'] == style:
            recipe_count += 1
            style_unique_fermentables.append(len(recipe['fermentables']))
            for category_name in categories:
                category_usage = sum(
                    fermentable['percent'] for fermentable in recipe['fermentables'] if fermentable['category'] == category_name)
                style_category_data.append((category_name, category_usage))
                style_category_fermentable_count.append((category_name, sum(1 for fermentable in recipe['fermentables'] if fermentable['category'] == category_name)))

    # Get the average fermentable category usage for the style
    for category_name in categories:
        category_usage = [usage for name,
                          usage in style_category_data if name == category_name]
        if category_usage == []:
            category_usage = [0]
        
        category_unique_fermentables = [count for name, count in style_category_fermentable_count if name == category_name and count > 0]
        if category_unique_fermentables == []:
            category_unique_fermentables = [0]

        std_dev = np.std(category_usage)
        mean = np.mean(category_usage)
        median = np.median(category_usage)

        style_category_usage.append({
            'name': category_name,
            'stats': {
                'mean': mean,
                'median': median,
                'std_dev': std_dev,
                'min': int(np.min(category_usage)),
                'max': int(np.max(category_usage))
            },
            'usage': {
                'min': max(0, int(mean - 1 * std_dev)),
                'max': min(100, int(mean + 1 * std_dev))
            },
            'unique_fermentables': int(round(np.median(category_unique_fermentables))),
            'category_object': category.Category(category_name, int(np.min(category_usage)), int(np.max(category_usage)))
        })

    # Add fermentables for each recipe in the style to fermentable_data
    recipe_fermentables = [recipe['fermentables']
                           for recipe in recipe_db if recipe['style'] == style]
    for recipe in recipe_fermentables:
        for fermentable in recipe:
            fermentable_list.append(fermentable)

    # Get unique fermentable names
    names = [fermentable['name']
             for fermentable in fermentable_list]
    unique_names = list(set(names))

    # Iterate over each fermentable, getting its average usage and adding to the style database
    for fermentable_name in unique_names:
        # Check if the name exists in our grain db, only add to the database if we have it
        matched_fermentable = all_grains.get_grain_by_name(fermentable_name)
        if matched_fermentable:
            # Get the fermentable usage
            usage = [fermentable['percent'] for fermentable in fermentable_list
                     if fermentable['name'] == fermentable_name]
            std_dev = np.std(usage)
            mean = np.mean(usage)

            style_grain_usage.append({
                'slug': matched_fermentable.slug,
                'stats': {
                    'mean': mean,
                    'median': int(np.median(usage)),
                    'std_dev': std_dev,
                    'min': int(np.min(usage)),
                    'max': int(np.max(usage))
                },
                'usage': {
                    'min': max(0, int(mean - 1 * std_dev)),
                    'max': min(100, int(mean + 1 * std_dev))
                },
                'fermentable_object': grain.Grain(
                    name=matched_fermentable.name,
                    brand=matched_fermentable.brand,
                    potential=matched_fermentable.potential,
                    color=matched_fermentable.color,
                    category=matched_fermentable.category,
                    sensory_data=matched_fermentable.sensory_data,
                    min_percent=max(0, int(mean - 1 * std_dev)),
                    max_percent=min(100, int(mean + 1 * std_dev))
                )
            })

    # Get min/max style data for the given grain profile
    try:
        style_fermentable_list = grain.GrainList(
            [style_fermentable['fermentable_object'] for style_fermentable in style_grain_usage])
        category_profile = category.CategoryProfile(
            [style_category['category_object'] for style_category in style_category_usage])
        style_sensory_minmax = style_fermentable_list.get_sensory_profiles(
            category_profile)
    except Exception as err:
        print('Failed to get recipe data for {}'.format(style))
        return

    # Iterate over each sensory keyword, get the average values for each keyword in the style
    for keyword in all_grains.get_sensory_keywords():
        # Get average sensory data for the given style style data for all recipes
        sensory_values = [recipe['sensory_data'][keyword]
                          for recipe in recipe_db if recipe['style'] == style]
        std_dev = np.std(sensory_values)
        mean = np.mean(sensory_values)

        # Get the sensory data possible from the grain profile
        for sensory_minmax in style_sensory_minmax:
            if sensory_minmax['name'] == keyword:
                sensory_from_grains = sensory_minmax
                break

        if not sensory_from_grains:
            sensory_from_grains = {
                'name': keyword,
                'min': 0,
                'max': 5
            }

        style_sensory_data.append({
            'name': keyword,
            'min': round(max(0, mean - 2 * std_dev, sensory_from_grains['min']), 3),
            'max': round(min(5, mean + 2 * std_dev, sensory_from_grains['max']), 3),
            'stats': {
                'mean': mean,
                'median': np.median(sensory_values),
                'std_dev': std_dev,
                'min': min(sensory_values),
                'max': max(sensory_values)
            }
        })

    # Remove the fermentable object, can't export it to JSON
    for style_fermentable in style_grain_usage:
        del style_fermentable['fermentable_object']

    for category_usage in style_category_usage:
        del category_usage['category_object']

    return {
        'style': style,
        'recipe_count': recipe_count,
        'grain_usage': style_grain_usage,
        'unique_fermentables': int(round(np.median(style_unique_fermentables))),
        'category_usage': style_category_usage,
        'sensory_data': style_sensory_data
    }

# Parse the recipes (multi-process)
executor = concurrent.futures.ProcessPoolExecutor()
futures = executor.map(analyze_style, styles)
style_data = list(futures)

with open('styles.json', 'w') as f:
    json.dump(style_data, f)

for recipe in recipe_db:
    del recipe['grain_bill']
    for fermentable in recipe['fermentables']:
        del fermentable['matched_fermentable']

with open('recipe_db.json', 'w') as f:
    json.dump(recipe_db, f)

with open('unmatched.csv', 'w') as f:
    writer = csv.DictWriter(
        f, fieldnames=['name', 'type', 'color', 'recipe_style'])
    writer.writeheader()
    writer.writerows([result['data'] for result in parse_results if result['status'] == 'unmatched_fermentable'])
