from ortools.sat.python import cp_model
import json
import random
import copy
import models

SCALING = 100

class SolutionPrinter(cp_model.CpSolverSolutionCallback):
    """Print intermediate solutions."""

    def __init__(self, variables):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self.__variables = variables
        self.__solution_count = 0

    def on_solution_callback(self):
        self.__solution_count += 1
        for v in self.__variables:
            print('%s=%i' % (v, self.Value(v)), end=' ')
        print()

    def solution_count(self):
        return self.__solution_count
        # [END print_solution]


category_map = [
    {
        "category": "base",
        "min_percent": 60,
        "max_percent": 100
    },
    {
        "category": "crystal",
        "min_percent": 0,
        "max_percent": 25
    },
    {
        "category": "roasted",
        "min_percent": 0,
        "max_percent": 15
    },
    {
        "category": "specialty",
        "min_percent": 0,
        "max_percent": 15
    }
]

grains = models.GrainModel()
all_grains = grains.get_all_grains()
sensory_keys = grains.get_sensory_keywords()

grain_range = range(len(all_grains))
category_range = range(len(category_map))
sensory_range = range(len(sensory_keys))

# Build a list of all grains and their sensory data
grain_map = []
for grain in all_grains:
    # Build a list of sensory data, add every possible keyword, set to zero if not mapped already
    sensory_data = {}
    for key in sensory_keys:
        sensory_data[key] = int(grain['sensory_data'].get(key, 0) * SCALING)

    grain_map.append({
        'slug': grain['slug'],
        'category': grain['category'],
        'max_percent': grain['max_percent'],
        'sensory_data': sensory_data
    })


"""
Model Details

Constraints:
    Total grain is 100%
    Use between the min and max percent of each grain
    Use less than the specified max for each grain category
    Use less than the specified max for each grain

Goals:
    Return the minimum of each descriptor
    Return the maximum of each descriptor
"""

# Create the model
model = cp_model.CpModel()

# Define model variables
grain_vars = [model.NewIntVar(0, 100, 'grain{}'.format(i)) for i in grain_range]
category_vars = [model.NewIntVar(0, 100, 'category_{}'.format(category['category'])) for category in category_map]
sensory_vars = [model.NewIntVar(0, 1000, 'sensory_{}'.format(key)) for key in sensory_keys]

# Add constraints
# Grain usage total must be 100% - not sure why both of these are needed but it doens't work if they're not
model.Add(sum(grain_vars) == 100)
model.Add(sum(category_vars) == 100)

# Keep each grain under the max amount
for i in grain_range:
    model.Add(grain_vars[i] <= grain_map[i]['max_percent'])

# Keep each grain category at or above the min and at or below the max amounts
for i in category_range:
    category = category_map[i]
    model.Add(category_vars[i] == sum(grain_vars[k] for k in grain_range if grain_map[k]['category'] == category['category']))

    model.Add(category_vars[i] <= category['max_percent'])
    model.Add(category_vars[i] >= category['min_percent'])

# Assign the sensory values
for i in sensory_range:
    sensory_key = sensory_keys[i]
    # Assign sensory var = Sum of all grains (sensory key * usage percent)
    model.Add(sensory_vars[i] * 100 == sum(grain_map[k]['sensory_data'][sensory_key] * grain_vars[k] for k in grain_range))

# Solve for maximizing every descriptor
solver = cp_model.CpSolver()
solution_printer = SolutionPrinter(sensory_vars)
print('Maximum:')
for i in sensory_range:
    model.Maximize(sensory_vars[i])
    status = solver.Solve(model)
    print('  {}: {}'.format(sensory_keys[i], solver.Value(sensory_vars[i])))

print('Minimum:')
for i in sensory_range:
    model.Minimize(sensory_vars[i])
    status = solver.Solve(model)
    print('  {}: {}'.format(sensory_keys[i], solver.Value(sensory_vars[i])))


# Solve the problem
#status = solver.SearchForAllSolutions(model, solution_printer)