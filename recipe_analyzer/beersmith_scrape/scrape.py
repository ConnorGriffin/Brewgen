import cfscrape
import re
from time import sleep
from bs4 import BeautifulSoup as bs
from pathlib import Path
import concurrent.futures

scraper = cfscrape.create_scraper()
def export_recipe(recipe_id):
    export_page = 'https://beersmithrecipes.com/download.php?id={}'.format(recipe_id)
    export = scraper.get(export_page)
    if export.status_code == 200:
        if export.text != "You don't have permission to access this recipe or recipe is invalid.\n":
            success = True
            print('Exported {}'.format(recipe_id))
            with open('./recipes/recipe_{}.xml'.format(recipe_id), 'wb') as f:
                f.write(export.content)
    else:
        if export.status_code == 429:
            print('Timing out, sleeping...')
            sleep(5)
        else:
            print("Can't export recipe {}".format(recipe_id))
            success = True

for recipe_id in range(459, 1072000):
    export_recipe(recipe_id)
    sleep(.1)
