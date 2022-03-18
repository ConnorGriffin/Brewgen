import cfscrape
import re
from time import sleep
from bs4 import BeautifulSoup as bs
from pathlib import Path


beerxml_list = list(Path("./recipes").rglob("*.xml"))

recipe_numbers = [re.sub('\.xml', '', recipe.name.split('_')[1])
                  for recipe in beerxml_list]

scraper = cfscrape.create_scraper()

for page in range(1, 7080):
    links = []
    uri = "https://www.brewersfriend.com/homebrew-recipes/page/{}/?sort=titledown".format(
        page)
    page = scraper.get(uri).content
    soup = bs(page, 'html.parser')
    for link in soup.findAll('a', attrs={'href': re.compile("^/homebrew/recipe/view.*$")}):
        success = False
        while not success:
            recipe_num = link.get('href').split('/')[4]

            if recipe_num in recipe_numbers:
                print('skipping {}'.format(recipe_num))
                break

            export_page = "https://www.brewersfriend.com/homebrew/recipe/beerxml1.0/{}".format(
                recipe_num)
            export = scraper.get(export_page)
            if export.status_code == 200:
                success = True
                with open('./recipes/recipe_{}.xml'.format(recipe_num), 'wb') as f:
                    f.write(export.content)
                sleep(.5)
            else:
                if export.status_code == 429:
                    print('Timing out, sleeping...')
                    sleep(5)
                else:
                    print("Can't export recipe {}".format(recipe_num))
                    success = True
