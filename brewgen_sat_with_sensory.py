import models
import random
from ortools.sat.python import cp_model

TARGET_OG = 1.054
MASH_EFFICIENCY = .73
TARGET_VOLUME = 5.75
TARGET_COLOR = 20

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


def get_grain_bills(mode, max_unique_grains=4,
             grain_list=models.GrainList(models.GrainModel().get_grain_slugs()),
             category_model=models.CategoryModel(),
             sensory_model=None):
    """Return a beer grain bill or sensory data based on input data.
    Args:
        mode (string): Defines which mode to use, either return a list of grain bills or a list of sensory data.
            Valid options: grain_bill, sensory_data
        max_unique_grains (int): Maximum number of unique grains to use in the recipe. Defaults to 4.
        grain_list (GrainList object):
    """

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


    scaling = 10000

    # Init the category, grain, and sensory data
    category_data = category_model.get_category_list()
    grain_data = grain_list.get_grain_list()
    sensory_keys = grain_list.get_sensory_keywords()

    # Set the ranges, we'll need to index into things a lot
    grain_range = range(len(grain_data))
    category_range = range(len(category_data))

    # Build a list of all grains and their sensory data
    grain_map = []
    for grain in grain_data:
        # Build a list of sensory data, add every possible keyword, set to zero if not mapped already
        sensory_data = {}
        for key in sensory_keys:
            sensory_data[key] = int(grain['sensory_data'].get(key, 0) * scaling)

        grain_map.append({
            'slug': grain['slug'],
            'category': grain['category'],
            'max_percent': grain['max_percent'],
            'sensory_data': sensory_data
        })

    # Create the model
    model = cp_model.CpModel()

    # Define model variables
    grain_vars = [model.NewIntVar(0, 100, 'grain{}'.format(i)) for i in grain_range]
    category_vars = [model.NewIntVar(0, 100, 'category_{}'.format(category['name'])) for category in category_data]
    grain_used = [model.NewBoolVar('grain{}_used'.format(i)) for i in grain_map]

    # Define constraints
    # Grain usage total must be 100% - not sure why both of these are needed but it doens't work if they're not
    model.Add(sum(grain_vars) == 100)
    model.Add(sum(category_vars) == 100)

    # Limit the max number of grains to the specified limit
    for i in grain_range:
        model.Add(grain_vars[i] == 0).OnlyEnforceIf(grain_used[i].Not())
        model.Add(grain_vars[i] > 0).OnlyEnforceIf(grain_used[i])
    model.Add(sum(grain_used) <= max_unique_grains)

    # Keep each grain under the max amount
    for i in grain_range:
        model.Add(grain_vars[i] <= grain_map[i]['max_percent'])

    # Keep each grain category at or above the min and at or below the max amounts
    for i in category_range:
        category = category_data[i]
        model.Add(category_vars[i] == sum(grain_vars[k] for k in grain_range if grain_map[k]['category'] == category['name']))

        model.Add(category_vars[i] <= category['max_percent'])
        model.Add(category_vars[i] >= category['min_percent'])

    # If a sensory model is provided we need to add more constraints
    if sensory_model:
        sensory_model_range = range(len(sensory_model))
        sensory_model_vars = [model.NewIntVar(0, 5 * 100 * scaling, 'sensory_model_{}'.format(i['name'])) for i in sensory_model]

        # Scale the sensory data provided
        for descriptor in sensory_model:
            descriptor['min'] = int(descriptor['min'] * scaling)
            descriptor['max'] = int(descriptor['max'] * scaling)

        # Ensure the grain bill stays within the sensory boundaries for each descriptor
        for i in sensory_model_range:
            sensory_key = sensory_model[i]['name']
            model.Add(sensory_model_vars[i] * 100 == sum(grain_map[k]['sensory_data'][sensory_key] * grain_vars[k] for k in grain_range))
            model.Add(sensory_model_vars[i] >= sensory_model[i]['min'])
            model.Add(sensory_model_vars[i] <= sensory_model[i]['max'])

    # If the goal is to return a sensory model we need to adjust our model
    if mode == 'sensory_data':
        sensory_vars = [model.NewIntVar(0, 5 * 100 * scaling, 'sensory_{}'.format(key)) for key in sensory_keys]
        sensory_range = range(len(sensory_keys))

        # Solve for minimizing and maximizing each descriptor
        solver = cp_model.CpSolver()
        sensory_data = []
        for i in sensory_range:
            sensory_key = sensory_keys[i]
            # Assign sensory var = Sum of all grains (sensory key * usage percent)
            model.Add(sensory_vars[i] * 100 == sum(grain_map[k]['sensory_data'][sensory_key] * grain_vars[k] for k in grain_range))

            model.Maximize(sensory_vars[i])
            status = solver.Solve(model)
            maximum = solver.Value(sensory_vars[i])

            model.Minimize(sensory_vars[i])
            status = solver.Solve(model)
            minimum = solver.Value(sensory_vars[i])

            sensory_data.append({
                "name": sensory_keys[i],
                "min": minimum / scaling,
                "max": maximum / scaling
            })

        return sensory_data

    # Return a grain bill if
    if mode == 'grain_bill':
        # Find all solutions and print the details
        solver = cp_model.CpSolver()
        # Sets a time limit of 10 seconds.
        solver.parameters.max_time_in_seconds = 10.0

        solution_printer = SolutionPrinter(grain_vars)
        status = solver.SearchForAllSolutions(model, solution_printer)

        return grain_bills


model = [
    {'name': 'sweet', 'min': 2.8, 'max': 3.0},
    {'name': 'bready', 'min': 1.25, 'max': 2.0},
    {'name': 'honey', 'min': 1.5, 'max': 2.0},
    {'name': 'graham_cracker', 'min': 1.4, 'max': 1.5}
]
#print(get_grain_bills('sensory_data', sensory_model=model))
#print(get_grain_bills('sensory_data'))
grain_bills = get_grain_bills('grain_bill', sensory_model=model)

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

# # Find a random beer that's close enough
all_closest = [beer for beer in beers if beer['srm_distance_from_target'] <= 2]
random_closest = random.randrange(0, len(all_closest))


# Print all beer details
# i = 1
# for beer in beers:
#     print('Beer {}:'.format(i))
#     print('  Grain Weight: {:0.2f} pounds'.format(sum(grain['use_pounds'] for grain in beer['grain_bill'])))
#     print('  Color: {:0.1f}'.format(beer['srm']))
#     print('  Grains:')
#     for grain in beer['grain_bill']:
#         print('    {}: {:0.2f} pounds'.format(grain['grain_data']['name'], grain['use_pounds']))
#     print()

#     i += 1

# Print the chosen perfect beer
print('Closest Beer: Beer {}'.format(closest_color +1))
closest_beer = beers[closest_color]
print('  Grain Weight: {:0.2f} pounds'.format(sum(grain['use_pounds'] for grain in closest_beer['grain_bill'])))
print('  Color: {:0.1f}'.format(closest_beer['srm']))
print('  Grains:')
for grain in closest_beer['grain_bill']:
    print('    {}: {:0.2f} pounds'.format(grain['grain_data']['name'], grain['use_pounds']))
print()

# # Print the chosen close enough beer
print('Random Close Enough: Close Beer {}'.format(random_closest +1))
closest_beer = all_closest[random_closest]
print('  Grain Weight: {:0.2f} pounds'.format(sum(grain['use_pounds'] for grain in closest_beer['grain_bill'])))
print('  Color: {:0.1f}'.format(closest_beer['srm']))
print('  Grains:')
for grain in closest_beer['grain_bill']:
    print('    {}: {:0.2f} pounds'.format(grain['grain_data']['name'], grain['use_pounds']))
