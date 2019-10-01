import models
from ortools.sat.python import cp_model

def get_wort(mode, max_unique_grains=4,
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

    scaling = 100

    # Init the category, grain, and sensory data
    category_data = category_model.get_category_list()
    grain_data = grain_list.get_grain_list()
    sensory_keys = grain_list.get_sensory_keywords()

    # Set the ranges, we'll need to index into things a lot
    grain_range = range(len(grain_data))
    category_range = range(len(category_data))
    sensory_range = range(len(sensory_keys))

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
    sensory_vars = [model.NewIntVar(0, 1000, 'sensory_{}'.format(key)) for key in sensory_keys]
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

    # Assign the sensory values
    for i in sensory_range:
        sensory_key = sensory_keys[i]
        # Assign sensory var = Sum of all grains (sensory key * usage percent)
        model.Add(sensory_vars[i] * 100 == sum(grain_map[k]['sensory_data'][sensory_key] * grain_vars[k] for k in grain_range))

    # Solve for minimizing and maximizing each descriptor
    solver = cp_model.CpSolver()
    sensory_data = {}
    for i in sensory_range:
        model.Maximize(sensory_vars[i])
        status = solver.Solve(model)
        maximum = solver.Value(sensory_vars[i])

        model.Minimize(sensory_vars[i])
        status = solver.Solve(model)
        minimum = solver.Value(sensory_vars[i])

        sensory_data[sensory_keys[i]] = {
            "min": minimum / scaling,
            "max": maximum / scaling
        }

    return sensory_data

print(get_wort('sensory_data'))