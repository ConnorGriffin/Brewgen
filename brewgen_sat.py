from ortools.sat.python import cp_model
import json
import os
import copy

# Equipment profile
TARGET_OG = 1.054
MASH_EFFICIENCY = .73
TARGET_VOLUME = 5.75
TARGET_COLOR = 4
TARGET_SWEETNESS = .95
MAX_UNIQUE_GRAINS = 4
SCALING = 10000

grain_bills = []


class SolutionPrinter(cp_model.CpSolverSolutionCallback):
    """Print intermediate solutions."""

    def __init__(self, grains_list):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self.__grains = grains_list
        self.__solution_count = 0

    def OnSolutionCallback(self):
        grain_bill = []
        i = 0
        for grain in self.__grains:
            if self.Value(grain) > 0:
                grain_bill.append({
                    'grain_data': grain_data[i],
                    'use_percent': self.Value(grain) / 100
                })
            i += 1
        grain_bills.append(grain_bill)
        self.__solution_count += 1

    def SolutionCount(self):
        return self.__solution_count


def sg_to_ppg(sg):
    return (sg - 1) * 1000


def calc_beer_color(grains, target_volume=TARGET_VOLUME, target_og=TARGET_OG, mash_efficiency=MASH_EFFICIENCY):
    gravity_points_needed = sg_to_ppg(target_og) * target_volume
    average_ppg = sum([sg_to_ppg(grain['grain_data']['potential']) * (grain['use_percent'] / 100) for grain in grains])
    for grain in grains:
        grain['use_pounds'] = gravity_points_needed / (average_ppg * mash_efficiency) * (grain['use_percent'] / 100)
    mash_color_units = sum([(grain['grain_data']['color'] * grain['use_pounds'])/target_volume for grain in grains])
    morey = 1.4922 * mash_color_units ** 0.6859
    return morey


# Import the grain list
with open('./ingredients/grains.json', 'r') as f:
    grain_data = json.load(f)

num_grains = len(grain_data)
all_grains = range(num_grains)

# Scale any non-integer grain properties
grain_data_scaled = []
for grain in copy.deepcopy(grain_data):
    grain['color'] = round(grain['color'] * SCALING)
    grain['potential'] = round((grain['potential'] - 1) * SCALING * MASH_EFFICIENCY)
    grain['sweetness'] = round(grain['sweetness'] * SCALING)
    grain_data_scaled.append(grain)

# Scale the equipment profile
target_sweetness_int = int(TARGET_SWEETNESS * SCALING)

# Define the model
model = cp_model.CpModel()

# Create the variables for the model
grain_list = [model.NewIntVar(0, 100, 'grain{}'.format(i)) for i in all_grains]

# Grain usage percent must equal 100
model.Add(sum(grain_list) == 100)

# Keep each grain under the max amount
for i in all_grains:
    model.Add(grain_list[i] <= grain_data_scaled[i]['max_percent'])

# Limit the max number of grains to the specified limit
grain_used = [model.NewBoolVar('grain{}_used'.format(i)) for i in all_grains]
for i in all_grains:
    model.Add(grain_list[i] == 0).OnlyEnforceIf(grain_used[i].Not())
    model.Add(grain_list[i] > 0).OnlyEnforceIf(grain_used[i])
model.Add(sum(grain_used) <= MAX_UNIQUE_GRAINS)

# Limit sweetness based on target_sweetness
model.Add(sum(grain_data_scaled[i]['sweetness'] * grain_list[i] for i in all_grains) == target_sweetness_int * 100)

# Find all solutions and print the details
solver = cp_model.CpSolver()
solution_printer = SolutionPrinter(grain_list)
status = solver.SearchForAllSolutions(model, solution_printer)

print('Solutions found : %i' % solution_printer.SolutionCount())

if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
    beers = []
    # Calculate the SRM for each grain bill
    for grain_bill in grain_bills:
        beer = {
            'grain_bill': grain_bill,
            'srm': calc_beer_color(grain_bill)
        }
        beer['srm_distance_from_target'] = abs(beer['srm'] - TARGET_COLOR)
        beers.append(beer)

    # Find the index of the beer with the color closest to the target:
    closest_color = min(range(len(beers)), key=lambda index: beers[index]['srm_distance_from_target'])

    # Print all beer details
    i = 1
    for beer in beers:
        print('Beer {}:'.format(i))
        print('  Grain Weight: {:0.2f} pounds'.format(sum(grain['use_pounds'] for grain in beer['grain_bill'])))
        print('  Color: {:0.1f}'.format(beer['srm']))
        print('  Grains:')
        for grain in beer['grain_bill']:
            print('    {}: {:0.2f} pounds'.format(grain['grain_data']['name'], grain['use_pounds']))
        print()

        i += 1

    # Print the chosen beer
    print('Closest Beer: Beer {}'.format(closest_color +1))
    closest_beer = beers[closest_color]
    print('  Grain Weight: {:0.2f} pounds'.format(sum(grain['use_pounds'] for grain in closest_beer['grain_bill'])))
    print('  Color: {:0.1f}'.format(closest_beer['srm']))
    print('  Grains:')
    for grain in closest_beer['grain_bill']:
        print('    {}: {:0.2f} pounds'.format(grain['grain_data']['name'], grain['use_pounds']))

if status == cp_model.INFEASIBLE:
    print('Infeasible')
