import hop
import math
from ortools.sat.python import cp_model

hops = hop.HopModel()
mosaic = hops.get_hop_by_name('Mosaic')
amarillo = hops.get_hop_by_name('Amarillo')


# hop_bill = hop.HopBill([hop.HopAddition(hops.get_hop_by_name('Mosaic'), 60, 'boil', 28),
#                         hop.HopAddition(hops.get_hop_by_name(
#                             'Amarillo'), 5, 'boil', 68)
#                         ])

# print(hop_bill.get_sensory_data(1.052, 19))
# print(hop_bill.ibu(1.052, 19))


# enabled_hops = ['mosaic', 'amarillo', 'cascade',
#                 'centennial', 'chinook', 'warrior']


def calculate_hop_bill(og, batch_size, enabled_hops, recipe_data, addition_data, flavor_descriptors):
    """Generate hop bills
    Notes:
    - Flavors and amounts scaled by 100 on input and output, should be scaled down in frontend or API
    """

    class VarArraySolutionPrinter(cp_model.CpSolverSolutionCallback):
        """Print intermediate solutions."""

        def __init__(self, total_ibu, total_amount, hops):
            cp_model.CpSolverSolutionCallback.__init__(self)
            self.__variables = hops
            self.__solution_count = 0

        def on_solution_callback(self):
            self.__solution_count += 1
            ibu = 'IBU: {}'.format(
                round(self.Value(total_ibu) / ibu_scale))
            amt = 'Amount: {} oz'.format(
                round(self.Value(total_amount) / scale * batch_size / 28.35, 2))
            variables_output = ['{}: {} oz'.format(
                v, round(self.Value(v) / scale * batch_size / 28.35, 2)) for v in self.__variables if self.Value(v) > 0]
            print('{}, {} | {}'.format(ibu, amt, ', '.join(variables_output)))

        def solution_count(self):
            return self.__solution_count

    hm = hop.HopModel()
    scale = 5
    ibu_scale = scale ** 2 * 100

    aa_factor = 100 * 1.15 * scale * 1.65 * 0.000125 ** (og - 1)
    aa_util = {
        '60': int(round(aa_factor * (1 - math.e ** (-.04*60)) / 4.15)),
        '45': int(round(aa_factor * (1 - math.e ** (-.04*45)) / 4.15)),
        '30': int(round(aa_factor * (1 - math.e ** (-.04*30)) / 4.15)),
        '15': int(round(aa_factor * (1 - math.e ** (-.04*15)) / 4.15)),
        '10': int(round(aa_factor * (1 - math.e ** (-.04*10)) / 4.15)),
        '5': int(round(aa_factor * (1 - math.e ** (-.04*5)) / 4.15)),
        'flameout': 0,
        'dryhop': 0
    }

    # Built a dict of enabled hops and their data
    enabled_hop_vars = {}
    for hop_name in enabled_hops:
        enabled_hop_vars[hop_name] = {}
        hop_object = hm.get_hop_by_name(hop_name)
        hop_object.alpha = int(round(hop_object.alpha * 10))
        enabled_hop_vars[hop_name]['data'] = hop_object

    # Create the model
    model = cp_model.CpModel()

    # Create variables for entire recipe
    total_ibu = model.NewIntVar(int(round(ibu_scale * recipe_data['ibu']['min'])), int(
        round(ibu_scale * recipe_data['ibu']['max'])), 'total_ibu')
    # total_flavor = model.NewIntVar(int(round(scale * recipe_data['flavor']['min'])), int(
    #     round(scale * recipe_data['flavor']['max'])), 'total_flavor')
    total_amount = model.NewIntVar(int(round(scale * recipe_data['amount']['min'])), int(
        round(scale * recipe_data['amount']['max'])), 'total')
    hop_used = [model.NewBoolVar('{}_used'.format(hop_name))
                for hop_name in enabled_hops]
    hop_amount = [model.NewIntVar(int(round(scale * recipe_data['amount']['min'])), int(
        round(scale * recipe_data['amount']['max'])), '{}'.format(hop_name)) for hop_name in enabled_hops]

    # Create variables for hop additions
    add_vars = {}
    for timing, value in addition_data.items():
        # Variables for hop addition timing totals
        add_vars[timing] = {
            'ibu': model.NewIntVar(
                int(round(ibu_scale * value['ibu']['min'])), int(round(ibu_scale * value['ibu']['max'])), 'add_{}_ibu'.format(timing)),
            'amount': model.NewIntVar(
                int(round(scale * value['amount']['min'])), int(round(scale * value['amount']['max'])), 'add_{}'.format(timing)),
            'hop_used': [model.NewBoolVar('add_{}_{}_used'.format(timing, hop_name)) for hop_name in enabled_hops]
        }

        # Variables for every hop per addition
        for hop_name in enabled_hops:
            hop_data = enabled_hop_vars[hop_name]['data']

            # Each individual hop has a min of 0 and a max of the overall addition max
            enabled_hop_vars[hop_name][timing] = {
                'ibu': model.NewIntVar(0, int(round(ibu_scale * value['ibu']['max'])), 'add_{}_{}_ibu'.format(timing, hop_name)),
                'amount': model.NewIntVar(0, int(round(scale * value['amount']['max'])), 'add_{}_{}'.format(timing, hop_name))
            }

            # Set the bool var for whether the hop is used or not - force amount to zero if not used and vice versa
            hop_index = enabled_hops.index(hop_name)
            model.Add(enabled_hop_vars[hop_name][timing]['amount'] > 0).OnlyEnforceIf(
                add_vars[timing]['hop_used'][hop_index])
            model.Add(enabled_hop_vars[hop_name][timing]['amount'] == 0).OnlyEnforceIf(
                add_vars[timing]['hop_used'][hop_index].Not())

            # Calculate hop IBUs: amount in g/L * aa_util * aa% as int
            model.Add(enabled_hop_vars[hop_name][timing]['ibu'] == enabled_hop_vars[hop_name]
                      [timing]['amount'] * aa_util[timing] * hop_data.alpha)

        # Ensure hop addition totals equals addition totals
        model.Add(add_vars[timing]['ibu'] == sum(addition[timing]['ibu'] for addition in [
            hop_vars for hop_vars in enabled_hop_vars.values()]))
        model.Add(add_vars[timing]['amount'] == sum(addition[timing]['amount'] for addition in [
            hop_vars for hop_vars in enabled_hop_vars.values()]))

        # Keep addition unique hop count in check
        model.Add(sum(add_vars[timing]['hop_used']) <= value['unique_hops'])

    # Set hop_used boolean for each enabled hop
    for hop_name in enabled_hops:
        hop_index = enabled_hops.index(hop_name)
        usage = [enabled_hop_vars[hop_name][timing]['amount']
                 for timing in addition_data.keys()]
        model.Add(hop_amount[hop_index] == sum(usage))
        model.Add(hop_amount[hop_index] > 0).OnlyEnforceIf(hop_used[hop_index])
        model.Add(hop_amount[hop_index] == 0).OnlyEnforceIf(
            hop_used[hop_index].Not())

    # Ensure recipe unique hops is within range
    model.Add(sum(hop_used) <= recipe_data['unique_hops'])

    # Ensure addition totals add up to recipe totals
    model.Add(total_ibu == sum(addition['ibu']
                               for addition in add_vars.values()))
    model.Add(total_amount == sum(addition['amount']
                                  for addition in add_vars.values()))

    # Solve
    solver = cp_model.CpSolver()
    solution_printer = VarArraySolutionPrinter(total_ibu, total_amount, [enabled_hop_vars['warrior']['60']['amount'], enabled_hop_vars['amarillo']
                                                                         ['60']['amount'], enabled_hop_vars['warrior']['5']['amount'], enabled_hop_vars['amarillo']['5']['amount']])
    status = solver.SearchForAllSolutions(model, solution_printer)

    if status in [cp_model.FEASIBLE, cp_model.OPTIMAL]:
        return True
    else:
        return False


enabled_hops = ['amarillo', 'warrior']
recipe_data = {
    'ibu': {
        'min': 50,
        'max': 70
    },
    'amount': {
        'min': 0,
        'max': 13.97
    },
    'flavor': {
        'min': 400,
        'max': 650
    },
    'unique_hops': 1
}
addition_data = {
    '60': {
        'ibu': {
            'min': 30,
            'max': 40
        },
        'amount': {
            'min': 0,
            'max': 2.93
        },
        'flavor': {
            'min': 0,
            'max': 2
        },
        'unique_hops': 1
    },
    '5': {
        'ibu': {
            'min': 5,
            'max': 20
        },
        'amount': {
            'min': 0,
            'max': 4.1
        },
        'flavor': {
            'min': 0,
            'max': 300
        },
        'unique_hops': 2
    }
    # 'flameout': {
    #     'ibu': {
    #         'min': 0,
    #         'max': 0
    #     },
    #     'amount': {
    #         'min': 0,
    #         'max': 5.5
    #     },
    #     'flavor': {
    #         'min': 0,
    #         'max': 400
    #     },
    #     'unique_hops': 2
    # },
    # 'dryhop': {
    #     'ibu': {
    #         'min': 0,
    #         'max': 0
    #     },
    #     'amount': {
    #         'min': 0,
    #         'max': 6.35
    #     },
    #     'flavor': {
    #         'min': 0,
    #         'max': 500
    #     },
    #     'unique_hops': 2
    # }
}
flavor_descriptors = {
    'piney': {
        'min': 100,
        'max': 400
    }
}

result = calculate_hop_bill(1.052, 19, enabled_hops, recipe_data,
                            addition_data, flavor_descriptors)
print(result)
