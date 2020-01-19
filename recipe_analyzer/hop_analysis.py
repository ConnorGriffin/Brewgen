from pathlib import Path
from matplotlib import pyplot as plt
from pybeerxml import Parser
from scipy import stats
import sys
import numpy as np
import re
import csv
import json
import concurrent.futures
import pandas as pd
import math
import random

sys.path.append('../')
from brewgen.backend.models import grain, category, hop

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


def points(og):
    return (og - 1) * 1000


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

hop_rewrites = [{
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
}]

parser = Parser()

# Get all recipe paths
# brewtoad = list(Path("./brewtoad_scrape").rglob("*.xml"))  # [0:120000]
brewers_friend = list(
    Path("./brewersfriend_scrape/recipes").rglob("*.xml"))  # [0:100000]

# beerxml_list = brewtoad + brewers_friend
beerxml_list = brewers_friend
random.shuffle(beerxml_list)


def parse_beerxml_file(beerxml_file):
    try:
        recipe = parser.parse('./{}'.format(str(beerxml_file)))[0]
        if not recipe.hops:
            raise Exception()
    except:
        return None
        #print("Failed to parse ./{}".format(str(beerxml_file)))


    try:
        style = recipe.style.name

        # Rewrite style names
        for rule in style_rewrites:
            match = re.match(rule['old'], style, flags=re.IGNORECASE)
            if match:
                style = rule['new']
                recipe.style.name = rule['new']
                break

        # Rewrite hop data
        for recipe_hop in recipe.hops:
            for rule in hop_rewrites:
                re_rule = re.compile(rule['match'], flags=re.IGNORECASE)
                match = re.match(re_rule, str(recipe_hop.name).strip())
                if match:
                    recipe_hop.name = re.sub(re_rule, r'{}'.format(
                        rule['replace']), str(recipe_hop.name).strip())
                    break

        return recipe

    except:
        pass


executor = concurrent.futures.ProcessPoolExecutor()
futures = executor.map(
    parse_beerxml_file, beerxml_list[0:50000])  # [0:100000]
parse_results = list(futures)

recipes = [result for result in parse_results if result != None]
styles = np.unique(np.array([recipe.style.name for recipe in recipes]))
all_hops = hop.HopModel()


def hop_analysis(recipe):
    try:
        dry_hops = [hop for hop in recipe.hops if hop.alpha and hop.use.lower() in [
            'dry hop']]
        whirl_hops = [hop for hop in recipe.hops if hop.alpha and hop.use.lower() in [
            'whirlpool', 'aroma']]

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
                
                if h.use.lower() == 'dry hop':
                    dryhop.append(hop.HopAddition(
                        matching_hop, h.time, h.use, h.amount * 1000))
                elif h.use.lower() in ['aroma', 'whirlpool']:
                    # Treat aroma and whirlpool hops as flameout/whirlpool at 0 minutes
                    flameout.append(hop.HopAddition(
                        matching_hop, 0, 'whirlpool', h.amount * 1000))
                elif h.use.lower() in ['boil', 'first wort']:
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

        bill_60 = hop.HopBill(min_60)
        bill_45 = hop.HopBill(min_45)
        bill_30 = hop.HopBill(min_30)
        bill_15 = hop.HopBill(min_15)
        bill_10 = hop.HopBill(min_10)
        bill_5 = hop.HopBill(min_5)
        bill_flameout = hop.HopBill(flameout)
        bill_dryhop = hop.HopBill(dryhop)
        boil = min_60 + min_45 + min_30 + min_15 + min_10 + min_5
        recipe_hops = hop.HopBill(boil + flameout + dryhop)

        if boil:
            boil_bill = hop.HopBill(boil)

            # Exclude recipes with more than 8oz/5gal or 226g/19L in the boil
            if boil_bill.amount() / recipe.batch_size > 11.98:
                raise Exception('More than 8oz/5gal in boil.')

        else:
            # Ignore recipes with no boil hops
            raise Exception('No boil hops.')

        # Exclude recipes with more than 1lb/5gal or 454g/19L in the whirlpool or dry hop
        non_boil_amount = sum(hop.amount for hop in dry_hops + whirl_hops)
        if non_boil_amount / recipe.batch_size > 0.02396:
            raise Exception('More than 1lb/5gal in whirlpool/dryhop.')

        return {
            'status': 'success',
            'recipe': {
                'ibu': recipe_hops.ibu(recipe.og, recipe.batch_size),
                'amount': recipe_hops.amount() / recipe.batch_size,
                'unique_hops': len(recipe_hops.unique_hops()),
                'flavor': recipe_hops.get_sensory_data(recipe.og, recipe.batch_size)
            },
            'additions': {
                '60': {
                    'ibu': bill_60.ibu(recipe.og, recipe.batch_size),
                    'amount': bill_60.amount() / recipe.batch_size,
                    'unique_hops': len(bill_60.unique_hops()),
                    'flavor': bill_60.get_sensory_data(recipe.og, recipe.batch_size)
                },
                '45': {
                    'ibu': bill_45.ibu(recipe.og, recipe.batch_size),
                    'amount': bill_45.amount() / recipe.batch_size,
                    'unique_hops': len(bill_45.unique_hops()),
                    'flavor': bill_45.get_sensory_data(recipe.og, recipe.batch_size)
                },
                '30': {
                    'ibu': bill_30.ibu(recipe.og, recipe.batch_size),
                    'amount': bill_30.amount() / recipe.batch_size,
                    'unique_hops': len(bill_30.unique_hops()),
                    'flavor': bill_30.get_sensory_data(recipe.og, recipe.batch_size)
                },
                '15': {
                    'ibu': bill_15.ibu(recipe.og, recipe.batch_size),
                    'amount': bill_15.amount() / recipe.batch_size,
                    'unique_hops': len(bill_15.unique_hops()),
                    'flavor': bill_15.get_sensory_data(recipe.og, recipe.batch_size)
                },
                '10': {
                    'ibu': bill_10.ibu(recipe.og, recipe.batch_size),
                    'amount': bill_10.amount() / recipe.batch_size,
                    'unique_hops': len(bill_10.unique_hops()),
                    'flavor': bill_10.get_sensory_data(recipe.og, recipe.batch_size)
                },
                '5': {
                    'ibu': bill_5.ibu(recipe.og, recipe.batch_size),
                    'amount': bill_5.amount() / recipe.batch_size,
                    'unique_hops': len(bill_5.unique_hops()),
                    'flavor': bill_5.get_sensory_data(recipe.og, recipe.batch_size)
                },
                'flameout': {
                    'ibu': bill_flameout.ibu(recipe.og, recipe.batch_size),
                    'amount': bill_flameout.amount() / recipe.batch_size,
                    'unique_hops': len(bill_flameout.unique_hops()),
                    'flavor': bill_flameout.get_sensory_data(recipe.og, recipe.batch_size)
                },
                'dryhop': {
                    'ibu': bill_dryhop.ibu(recipe.og, recipe.batch_size),
                    'amount': bill_dryhop.amount() / recipe.batch_size,
                    'unique_hops': len(bill_dryhop.unique_hops()),
                    'flavor': bill_dryhop.get_sensory_data(recipe.og, recipe.batch_size)
                }
            }
        }
    except Exception as e:
        pass
        # print('Exception: {}'.format(e))
        # print('  Batch Size: {} gal'.format(round(recipe.batch_size / .264172)))
        # print('  Hops:')
        # for h in recipe.hops:
        #     print('    {}g {} - {} {} min'.format(round(h.amount * 1000),
        #                                            h.name, h.use, h.time))
        

def ibu_match(low, high, test):
    return (low <= test <= high)


def reject_outliers(data, m=2.):
    d = np.abs(data - np.median(data))
    mdev = np.median(d)
    s = d/mdev if mdev else 0.
    return data[s < m]


def get_stats(data):
    std = np.std(data)
    mean = np.mean(data)
    return {
        'min': max(0, mean - std * 3),
        'max': mean + std * 3,
        'mean': mean,
        'median': np.median(data),
        'std': std
    }

    # return {
    #     'min': min(data),
    #     'max': max(data), 
    #     'mean': np.mean(data),
    #     'median': np.median(data),
    #     'std': np.std(data)
    # }


all_keywords = all_hops.get_sensory_keywords()

for style in ['German Pils']:
    style_flavor = {}
    addition_data = {}
    
    # Analyze the recipes in the style
    style_recipes = [
        recipe for recipe in recipes if recipe.style.name == style]
    executor = concurrent.futures.ProcessPoolExecutor()
    futures = executor.map(
        hop_analysis, style_recipes)
    results = [result for result in list(futures) if result != None]

    # Remove the recipes that don't match the style IBU rangee
    specs = bjcp_name(style)
    min_ibu = float(specs.get('ibu', {}).get('low', 0))*.75
    max_ibu = float(specs.get('ibu', {}).get('high', 999))*1.25
    results = [result for result in results if ibu_match(
        min_ibu, max_ibu, result['recipe']['ibu'])]
    
    # Get the flavor range and dump recipes that are outliers
    flavor_totals = reject_outliers(np.array([result['recipe']['flavor']['total']
                                              for result in results]))
    flavor_min = np.amin(flavor_totals)
    flavor_max = np.amax(flavor_totals) 
    results = [result for result in results if flavor_max > result['recipe']['flavor']['total'] > flavor_min]

    # Build the overall flavor profile data for the style
    for keyword in all_keywords:
        flavor_data = [result['recipe']['flavor']['descriptors'][keyword]
                    for result in results if result['recipe']['flavor']['descriptors'][keyword]]
        nonzero = [value for value in flavor_data if value > 0]
        
        # Filter out hop flavor descriptors that are in less than 5% of recipes
        if len(nonzero) >= len(results) * .05:         
            f_std = np.std(flavor_data)
            f_mean = np.mean(flavor_data)
    
            style_flavor[keyword] = get_stats(flavor_data)
            style_flavor[keyword]['recipe_count'] = len(flavor_data)

    # Get the overall style IBU and hop amounts 
    ibu_data = [result['recipe']['ibu'] for result in results]
    style_ibu = get_stats(ibu_data)

    amt_data = [result['recipe']['amount'] for result in results]
    style_amount = get_stats(amt_data)

    # # Build all of the above data, but specific to each hop addition timing
    # for addition in ['60', '45', '30', '15' '10', '5', 'flameout', 'dryhop']:
    #     flavor_data = 

    
    print(json.dumps({
        'style': style, 
        'recipe_count': len(results),
        'recipe': {
            'ibu': style_ibu, 
            'amount': style_amount, # in g/L
            'unique_hops': int(round(np.mean([result['recipe']['unique_hops'] for result in results]))),
            'flavor': {
                'total': get_stats([result['recipe']['flavor']['total'] for result in results]),
                'descriptors': style_flavor
            }
        }
    }))
