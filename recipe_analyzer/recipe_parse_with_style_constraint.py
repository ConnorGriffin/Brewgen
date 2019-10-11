from pathlib import Path
from pybeerxml import Parser
import sys
import numpy as np
import re
import csv
import json

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


def bjcp_id(id):
    """Return beer stats for a style ID"""
    for bev_class in bjcp['styleguide']['class']:
        if bev_class['type'] == 'beer':
            for style_category in bev_class['category']:
                for subcat in style_category['subcategory']:
                    if subcat['id'] == id:
                        return subcat['stats']


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
    # Weyermann as the catchall for Vienna
    {
        'name': 'Weyermann Vienna Malt',
        'match': '^.*Vienna.*$',
        'max_color': 6
    }, {
        'name': 'Weyermann Munich Malt I',
        "match": '^.*Munich.*$',
        'max_color': 7
    },
    {
        'name': 'Weyermann Munich Malt II',
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
        'match': '^.*((2|Two)(-| )Row|Pale Malt).*$',
        'max_color': 3.5
    },
    # No sensory available for Maris Otter so lumping that in with Pale Ale Malt
    {
        'name': "Pale Ale Malt",
        'match': '^.*(Pale Ale|Maris|Marris).*$',
        'max_color': 5
    },
    {
        'name': "Carapils Malt",
        'match': '^.*(Carafoam|US.*Carapils|Carapils.*US|Carapils.*Briess|Briess.*Carapils|Cara-Pils|Dextrine).*$',
        'max_color': 5
    },
    # Weyermann as the catchall for Carapils
    {
        'name': "Weyermann Carapils",
        'match': '^.*(Carapils).*$',
        'max_color': 5
    },
    {
        'name': "Pilsen Malt",
        'match': '^.*(Pilsen|US.*Pilsner|Pilsner.*US|Lager).*$',
        'max_color': 3
    },
    # Weyermann as the catchall for Pilsner
    {
        'name': "Weyermann Pilsner Malt",
        'match': '^.*Pilsner.*$',
        'max_color': 3
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
        'name': "Weyermann Caramunich I",
        'match': '^.*Cara ?munich(( I)?|.*Type 1).*$',
        'max_color': 40
    },
    {
        'name': "Weyermann Caramunich II",
        'match': '^.*Cara ?munich(( II)?|.*Type 2).*$',
        'max_color': 50
    },
    {
        'name': "Weyermann Caramunich III",
        'match': '^.*Cara ?munich(( III)?|.*Type 3).*$',
        'max_color': 60
    },
    {
        'name': "Weyermann Pale Wheat Malt",
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
        'name': "Munich Malt 20L",
        'match': '^.*Aromatic.*$',
        'min_color': 15,
        'max_color': 25
    },
    {
        'name': "Weyermann Melanoidin Malt",
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
        'name': 'Weyermann Beech Smoked Barley Malt',
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
        'name': "Weyermann Pale Wheat Malt",
        'match': '^.*Weyermann Pale Wheat Malt.*$'
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
        'name': "Weyermann Melanoidin Malt",
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

unmatched = []
not_to_style = 0
unmatched_fermentable = 0
unmatched_style = 0

# Get all recipe paths
#beerxml_list = list(Path("./brewtoad_scrape").rglob("*.xml"))
beerxml_list = list(Path("./brewersfriend_scrape/recipes").rglob("*.xml"))
for beerxml_file in beerxml_list:
    try:
        recipes = parser.parse('./{}'.format(str(beerxml_file)))
    except:
        print("Failed to parse ./{}".format(str(beerxml_file)))
        recipes = []

    for recipe in recipes:
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
                og_match = points(float(specs.get('og', {}).get('low', 1)))*.5 <= points(
                    recipe.og) <= points(float(specs.get('og', {}).get('high', 1.200)))*1.5
                srm_match = float(specs.get('srm', {}).get('low', 0))*.5 <= recipe.color <= float(
                    specs.get('srm', {}).get('high', 999))*1.5
                ibu_match = float(specs.get('ibu', {}).get('low', 0))*.5 <= recipe.ibu <= float(
                    specs.get('ibu', {}).get('high', 999))*1.5

                # Only include recipes with a to-style OG and color
                if og_match and srm_match and ibu_match:
                    fermentables = []
                    for fermentable in recipe.fermentables:
                        fermentable_name = fermentable.name.strip()
                        # Remove all LME/DME by raising an exception and killing all future parsing of the recipe
                        extract = re.match(
                            "^.*(CBW|DME|LME|Extract|Malt Syrup).*$", fermentable_name, flags=re.IGNORECASE)
                        if extract:
                            raise Exception(
                                'Recipe contains extract: {}'.format(fermentable_name))

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
                            unmatched_fermentable += 1
                            unmatched.append({
                                'name': fermentable_name,
                                'type': 'fermentable'
                            })
                            raise Exception(
                                'Recipe contains unmatched fermentable: {}'.format(fermentable_name))

                        # Calculate total amount of grains ignoring the bypass list
                        total_amount = sum(
                            fermentable.amount for fermentable in recipe.fermentables if fermentable_name not in fermentable_bypass)
                        fermentables.append({
                            'name': fermentable_name,
                            'category': matched_fermentable.category,
                            'percent': fermentable.amount / total_amount * 100,
                            'color': fermentable.color,
                            'ppg': fermentable.ppg,
                            'addition': fermentable.addition
                        })

                    recipe_db.append({
                        'style': style,
                        'category': recipe.style.category,
                        'og': recipe.og,
                        'color': recipe.color,
                        'fermentables': fermentables
                    })
                else: 
                    style_spec = {
                        'og': {
                            'low': points(float(specs.get('og', {}).get('low', 1))),
                            'high': points(float(specs.get('og', {}).get('high', 1.200))),
                            'recipe': points(recipe.og)
                        },
                        'srm': {
                            'low': float(specs.get('srm', {}).get('low', 0)),
                            'high': float(specs.get('srm', {}).get('high', 999)),
                            'recipe': recipe.color
                        },
                        'ibu': {
                            'low': float(specs.get('ibu', {}).get('low', 0)),
                            'high': float(specs.get('ibu', {}).get('high', 999)),
                            'recipe': recipe.ibu
                        }
                    }
                    not_to_style += 1
            else:
                unmatched_style += 1
                unmatched.append({
                    'name': style,
                    'type': 'style'
                })
                raise Exception('No style found: {}'.format(style))

        except Exception as err:
            pass
            #print(err)
            # print("Failed to parse recipe in ./{}".format(str(beerxml_file)))

    # Get a list of style and grain category games
    styles = list(set([recipe['style'] for recipe in recipe_db]))
    categories = category_model.get_category_names()

print('Unmatched Style:       {}'.format(unmatched_style))
print('Unmatched Fermentable: {}'.format(unmatched_fermentable))
print('Not to Style:          {}'.format(not_to_style))

# Create a list of list of dicts containing grains and their usage percents for every style
style_data = []
for style in styles:
    recipe_count = 0
    fermentable_list = []
    fermentable_usage = []
    style_grain_usage = []
    style_category_data = []
    style_category_usage = []

    # Calculate the average grain usage from each category, only use recipes with 100% grain coverage, remove any recipes that use extracts
    for recipe in recipe_db:
        if recipe['style'] == style:
            recipe_count += 1
            for category_name in categories:
                category_usage = sum(
                    fermentable['percent'] for fermentable in recipe['fermentables'] if fermentable['category'] == category_name)
                style_category_data.append((category_name, category_usage))

    # Get the average fermentable category usage for the style
    for category_name in categories:
        category_usage = [usage for name,
                          usage in style_category_data if name == category_name]
        if category_usage == []:
            category_usage = [0]

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
                'min': max(0, int(median - 1 * std_dev)),
                'max': min(100, int(median + 1 * std_dev))
            }
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
        grain = all_grains.get_grain_by_name(fermentable_name)
        if grain:
            # Get the fermentable usage
            usage = [fermentable['percent'] for fermentable in fermentable_list
                     if fermentable['name'] == fermentable_name]
            std_dev = np.std(usage)
            mean = np.mean(usage)

            style_grain_usage.append({
                'slug': grain.slug,
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
                }
            })

    style_data.append({
        'style': style,
        'grain_usage': style_grain_usage,
        'category_usage': style_category_usage,
        'recipe_count': recipe_count
    })

with open('styles.json', 'w') as f:
    json.dump(style_data, f)

with open('unmatched.csv', 'w') as f:
    writer = csv.DictWriter(f, fieldnames=['name', 'type'])
    writer.writeheader()
    writer.writerows(unmatched)
