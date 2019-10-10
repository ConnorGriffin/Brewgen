
from pathlib import Path
from pybeerxml import Parser
import sys
import numpy as np
import re
import json

sys.path.append('../')
from brewgen.backend.models import grain, category

# Get all recipe paths
beerxml_list = list(Path("./brewtoad_scrape").rglob("*.xml"))

all_grains = grain.GrainModel()
category_model = category.CategoryModel()
parser = Parser()
recipe_db = []

rewrites = [
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
        'match': '^.*(2|Two)(-| )Row.*$',
        'max_color': 2
    },
    # No sensory available for Maris Otter so lumping that in with Pale Ale Malt
    {
        'name': "Pale Ale Malt",
        'match': '^.*(Pale Ale|Maris|Marris).*$',
        'max_color': 5
    },
    {
        'name': "Carapils Malt",
        'match': '^.*(US.*Carapils|Carapils.*US|Carapils.*Briess|Briess.*Carapils).*$',
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
        'match': '^.*(Pilsen|US.*Pilsner|Pilsner.*US).*$',
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
        'name': "Wheat Malt, White",
        'match': '^.*(White Wheat|Pale Wheat|Wheat Malt|Light Wheat|Wheat.*US).*$'
    },
    {
        'name': "Wheat Malt, Red",
        'match': '^.*(Red.*Wheat|Wheat.*Red).*$'
    },
    {
        'name': "Brewers Torrified Wheat",
        'match': '^.*(Wheat.*Torrified|Torrified Wheat).*$'
    },
    {
        'name': "Weyermann Pale Wheat Malt",
        'match': '^.*((Belgian|German).*Wheat|Wheat.*(DE|BE|Belgian|German)).*$'
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
        'name': "Brewers Oat Flakes",
        'match': '^.*(Oat.*Flaked|Flaked.*Oat).*$'
    },
    {
        'name': "Honey Malt",
        'match': '^.*(Honey.*Malt|Malt.*Honey|Honey.*US|Honey.*CA|Honey.*Gambrinus|Gambrinus.*Honey).*$'
    },
    {
        'name': 'Victory Malt',
        'match': '^.*Victory.*$'
    }
]

# Add rewrites for each Crystal malt
for lov in [10, 20, 30, 40, 60, 80, 90, 120]:
    rewrites.append({
        'name': 'Caramel Malt {}L'.format(lov),
        'match': '^.*(Caramel|Crystal).*{}.*$'.format(lov)
    })

for beerxml_file in beerxml_list[0:50000]:
    try:
        recipes = parser.parse('./{}'.format(str(beerxml_file)))
    except:
        print("Failed to parse ./{}".format(str(beerxml_file)))
        recipes = []

    for recipe in recipes:
        try:
            style = recipe.style.name
            fermentables = []
            total_amount = sum(
                fermentable.amount for fermentable in recipe.fermentables)
            for fermentable in recipe.fermentables:
                fermentable_name = fermentable.name
                # Remove all LME/DME
                extract = re.match(
                    "^.*(CBW|DME|LME|Extract|Malt Syrup).*$", fermentable_name, flags=re.IGNORECASE)
                if extract:
                    #print('Skipping extract: {}'.format(fermentable_name))
                    break

                # Rewrite fermentable names
                for rule in rewrites:
                    match = re.match(
                        rule['match'], fermentable.name, flags=re.IGNORECASE)
                    if match and fermentable.color <= rule.get('max_color', 999):
                        #print('Rewriting {} -> {}'.format(fermentable_name, rule['name']))
                        fermentable_name = rule['name']
                        break

                fermentables.append({
                    'name': fermentable_name,
                    'percent': fermentable.amount / total_amount * 100,
                    'color': fermentable.color,
                    'ppg': fermentable.ppg,
                    'addition': fermentable.addition,
                })
            recipe_db.append({
                'style': style,
                'category': recipe.style.category,
                'og': recipe.og,
                'color': recipe.color,
                'fermentables': fermentables
            })
        except:
            print("Failed to parse recipe in ./{}".format(str(beerxml_file)))

# Get a list of style and grain category games
styles = list(set([recipe['style'] for recipe in recipe_db]))
categories = category_model.get_category_names()

# Create a list of list of dicts containing grains and their usage percents for every style
style_data = []
for style in styles:
    fermentable_list = []
    fermentable_usage = []
    style_grain_usage = []
    style_category_data = []
    style_category_usage = []

    # Calculate the average grain usage from each category, only use recipes with 100% grain coverage, remove any recipes that use extracts
    for recipe in recipe_db:
        if recipe['style'] == style and int(sum(fermentable['percent'] for fermentable in recipe['fermentables'])) == 100:
            # Look up each grain in the recipe and match to a grain in the grain database, remove items with no match (None)
            recipe_fermentables =  [all_grains.get_grain_by_name(fermentable['name']) for fermentable in recipe['fermentables']]
            matched_fermentables = [fermentable for fermentable in recipe_fermentables if fermentable != None]
            
            # We only want recipes with 100% grain coverage to count towards our data, otherwise numbers won't be reliable
            if len(recipe['fermentables']) == len(matched_fermentables):
                for category_name in categories:
                    category_usage = sum(fermentable['percent'] for fermentable in recipe['fermentables'] if all_grains.get_grain_by_name(
                        fermentable['name']).category == category_name)
                    style_category_data.append((category_name, category_usage))
    
    # Get the average fermentable category usage for the style
    for category_name in categories:
        category_usage = [usage for name, usage in style_category_data if name == category_name]
        if category_usage == []:
            category_usage = [0]

        std_dev = np.std(category_usage)
        mean = np.mean(category_usage)

        style_category_usage.append({
            'name': category_name,
            'mean': mean,
            'std_dev': std_dev,
            'usage': {
                'min': max(0, int(mean - 3 * std_dev)),
                'max': min(100, int(mean + 3 * std_dev))
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
                'mean': mean,
                'std_dev': std_dev,
                'usage': {
                    'min': max(0, int(mean - 3 * std_dev)),
                    'max': min(100, int(mean + 3 * std_dev))
                }
            })

    style_data.append({
        'style': style,
        'grain_usage': style_grain_usage,
        'category_usage': style_category_usage
    })

with open('styles.json', 'w') as f:
    json.dump(style_data, f)
