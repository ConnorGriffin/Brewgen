"""
Grain weight:
    grain_percent
    grain_ppg
    target_og
    mash_efficiency
    volume_gallons


points_needed:  (target_og - 1 * 1000) * volume_gallons
weighted_ppg:   sum of each grain: (grain_ppg * grain_percent)
grain_weight:   points_needed / (weighted_ppg * mash_efficiency) * grain_percent

Beer Color:
    Add all MCU values, then apply Morey equation
    MCU = (grain_color * grain_weight_lbs)/volume_gallons
    SRM_Color = 1.4922 * [MCU ^ 0.6859]
"""

import numpy as np
from scipy.optimize import minimize
import pprint
pp = pprint.PrettyPrinter()

# Equipment profile
TARGET_OG = 1.054
MASH_EFFICIENCY = .73
TARGET_VOLUME = 5.75

def sg_to_ppg(sg):
    return (sg - 1) * 1000


def calc_grain_weights(grains, target_og=TARGET_OG, mash_efficiency=MASH_EFFICIENCY, target_volume=TARGET_VOLUME):
    points_needed = (target_og - 1) * 1000 * target_volume
    weighted_ppg = sum([sg_to_ppg(grain['potential']) * (grain['use_percent'] / 100) for grain in grains])
    return_grains = []
    for grain in grains:
        grain['use_pounds'] = points_needed / (weighted_ppg * mash_efficiency )* (grain['use_percent']/100)
        return_grains.append(grain)
    return return_grains


def calc_beer_color(grains, target_volume=TARGET_VOLUME):
    mash_color_units = sum([(grain['color'] * grain['use_pounds'])/target_volume for grain in grains])
    morey = 1.4922 * mash_color_units ** 0.6859
    return morey


def calc_beer_sweetness(grains):
    weighted_sweetness = [(grain['sweetness'] * (grain['use_percent'] / 100)) for grain in grains]
    return sum(weighted_sweetness)


# Define our objective, the return of this is to be minimized
def objective(x):
    grains[0]['use_percent'] = x[0]
    grains[1]['use_percent'] = x[1]
    grains[2]['use_percent'] = x[2]
    grains[3]['use_percent'] = x[3]

    needed_grains = calc_grain_weights(grains)
    color = calc_beer_color(needed_grains)
    sweetness = calc_beer_sweetness(needed_grains)

    # Calc how fare off we are. This is what we want to minimize
    badness = (color - TARGET_COLOR)**2 + (sweetness - TARGET_SWEETNESS)**2
    return badness


# All percents should total to 100
def constraint_percents(x):
    return 100 - sum(x)


# Load constraints into dictionary form
cons = []
cons.append({'type': 'eq', 'fun':constraint_percents})

# Define our grains, hardcoded for now
grains = [
    {
        "name": "pale 2-row",
        "color": 1.8,
        "potential": 1.037,
        "max_percent": 100,
        "sweetness": 1,
        "bitterness": 0
    },
    {
        "name": "crystal 40",
        "color": 40,
        "potential": 1.032,
        "max_percent": 25,
        "sweetness": 4,
        "bitterness": 0
    },
    {
        "name": "crystal 120",
        "color": 120,
        "potential": 1.032,
        "max_percent": 15,
        "sweetness": 10,
        "bitterness": 0
    },
    {
        "name": "chocolate malt (us)",
        "color": 350,
        "potential": 1.035,
        "max_percent": 15,
        "sweetness": 6,
        "bitterness": 0
    }
]

# Load guess values into numpy array
x0 = np.array([100, 0, 0, 0])

# Variables must be positive and less than or equal to 100
bounds = ((0, 100), (0, 100), (0, 100), (0, 100))

# Call solver to minimize the objective function given the constraints
TARGET_COLOR = 30
TARGET_SWEETNESS = 1.5
sol = minimize(objective, x0, method='SLSQP', constraints=cons, options={'disp':True}, bounds=bounds)

grains[0]['use_percent'] = round(sol['x'][0],2)
grains[1]['use_percent'] = round(sol['x'][1], 2)
grains[2]['use_percent'] = round(sol['x'][2], 2)
grains[3]['use_percent'] = round(sol['x'][3], 2)

needed_grains = calc_grain_weights(grains)
color = calc_beer_color(needed_grains)
sweetness = calc_beer_sweetness(needed_grains)

print(sol)
print('Color: {0:.1f} SRM\nSweetness: {1:.1f}/10'.format(color, sweetness))
for grain in needed_grains:
    if grain['use_percent'] > 0:
        print('{0}: {1:.2f}%, {2:.2f} pounds'.format(grain['name'], grain['use_percent'], grain['use_pounds']))
