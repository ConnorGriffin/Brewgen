#!/usr/bin/env python
# coding: utf-8

# In[13]:


from brewgen.backend.models import grain
from pathlib import Path
from os import listdir
from os.path import isfile, join
from pybeerxml import Parser
import sys
import pandas as pd
import numpy as np
import re
from matplotlib import pyplot as plt
sys.path.append('../')

# In[ ]:


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
        'match': '^.*(Pale Ale|Maris).*$',
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
        'match': '^.*(White Wheat|Pale Wheat|Wheat Malt|Light Wheat|Wheat \\(US\\)).*$'
    },
    {
        'name': "Wheat Malt, Red",
        'match': '^.*(Red.*Wheat|Wheat.*Red|).*$'
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
        'match': '^.*(Honey.*Malt|Malt.*Honey).*$'
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


# In[ ]:


# In[ ]:


# Get all recipe paths
beerxml_list = list(Path("./brewtoad_scrape").rglob("*.xml"))


# In[ ]:


parser = Parser()
recipe_db = []


# In[ ]:


# Create a list of all fermentables in all recipes
fermentables = []
for beerxml_file in beerxml_list:
    try:
        recipes = parser.parse('./{}'.format(str(beerxml_file)))
    except:
        print("Failed to parse ./{}".format(str(beerxml_file)))
        recipes = []

    for recipe in recipes:
        try:
            total_amount = sum(
                fermentable.amount for fermentable in recipe.fermentables)
            for fermentable in recipe.fermentables:
                fermentable_name = fermentable.name
                # Remove all LME/DME
                extract = re.match("^.*(DME|LME|Extract).*$", fermentable_name)
                if extract:
                    #print('Skipping extract: {}'.format(fermentable_name))
                    break

                for rule in rewrites:
                    match = re.match(rule['match'], fermentable.name)
                    if match and fermentable.color <= rule.get('max_color', 100):
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
        except:
            print("Failed to parse recipe in ./{}".format(str(beerxml_file)))


# In[ ]:


# Create a list of unique fermentable names
fermentable_names = list(
    set(fermentable['name'] for fermentable in fermentables))


# In[ ]:


# Create a list of tuples containing each fermentable name and its usage count, sort by descending usage count
fermentable_frequency = []
for name in fermentable_names:
    count = sum(
        1 for fermentable in fermentables if fermentable['name'] == name)
    fermentable_frequency.append((name, count))
fermentable_frequency = sorted(
    fermentable_frequency, key=lambda tup: tup[1], reverse=True)


# In[ ]:


# Get the average properties of each fermentable by name
fermentable_avg_data = []
for name, count in fermentable_frequency:
    matching_fermentables = [
        fermentable for fermentable in fermentables if fermentable['name'] == name]
    fermentable_avg_data.append({
        'name': name,
        'occurances': count,
        'color': np.mean([fermentable['color'] for fermentable in matching_fermentables if fermentable['color']]),
        'ppg': np.mean([fermentable['ppg'] for fermentable in matching_fermentables])
    })


# In[ ]:


# Export the data to CSV (using pandas is quick)
pd.DataFrame(fermentable_avg_data).to_csv(r'GrainFrequency.csv')


# In[28]:


# In[ ]:
