
from pathlib import Path
from pybeerxml import Parser
import sys
import numpy as np
import re
import json

sys.path.append('../')
from brewgen.backend.models import grain

# Get all recipe paths
beerxml_list = list(Path("./brewtoad_scrape").rglob("*.xml"))

all_grains = grain.GrainModel()
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

for beerxml_file in beerxml_list[0:1000000]:
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

# Get an array of styles and color histogram data
styles = np.unique(np.array([recipe['style'] for recipe in recipe_db]))
color_data = [[recipe['color']
               for recipe in recipe_db if recipe['style'] == style] for style in styles]

# Create a list of list of dicts containing grains and their usage percents for every style and recipe
# [Style:[Grains:{Name, Usage Percent}]]
fermentable_data = []
for i in range(len(styles)):
    fermentable_style_data = []
    recipe_fermentables = [recipe['fermentables']
                           for recipe in recipe_db if recipe['style'] == styles[i]]
    for recipe in recipe_fermentables:
        for fermentable in recipe:
            fermentable_style_data.append(fermentable)
    fermentable_data.append(fermentable_style_data)

# # Histograms for the SRM data for each style
# plt.xlabel('SRM')
# plt.ylabel('Counts')
# bins = range(0, 101)
# for i in range(len(styles)):
#     data = color_data[i]
#     plt.title(styles[i])
#     plt.hist(color_data[i], bins=bins)
#     plt.show()
#     std_dev = np.std(color_data[i])
#     mean = np.mean(color_data[i])
#     print('Mean: {}'.format(mean))
#     print('Standard Dev: {}'.format(std_dev))
#     print('Range (1 std dev): {} - {}'.format(mean - .5 * std_dev, mean + .5 * std_dev))

# Plot grain usage for each style
all_styles_grain_usage = []
for style in range(len(styles)):
    style_grain_usage = []

    # Get unique fermentable names
    names = [fermentable['name']
                for fermentable in fermentable_data[style]]
    unique_names = list(set(names))

    fermentable_usage = []
    for name in range(len(unique_names)):
        usage_list = [fermentable['percent'] for fermentable in fermentable_data[style]
                        if fermentable['name'] == unique_names[name]]
        fermentable_usage.append((unique_names[name], usage_list))

    for fermentable_use in fermentable_usage:
        # Histogram for the grain usage
        #plt.title('{} in {}'.format(unique_names[name], styles[style]))
        grain = all_grains.get_grain_by_name(fermentable_use[0])
        #print(fermentable_use)
        if grain:
            std_dev = np.std(fermentable_use[1])
            mean = np.mean(fermentable_use[1])

            style_grain_usage.append({
                'slug': grain.slug,
                'mean': mean,
                'std_dev': std_dev,
                'usage': {
                    'min': max(0, int(mean - 3 * std_dev)),
                    'max': min(100, int(mean + 3 * std_dev))
                }
                })
    all_styles_grain_usage.append({
        'style': styles[style],
        'grain_usage': style_grain_usage
    })

with open('styles.json', 'w') as f:
    json.dump(all_styles_grain_usage, f)
