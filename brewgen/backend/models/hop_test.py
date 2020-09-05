import hop
import math
from ortools.sat.python import cp_model

# hops = hop.HopModel()
# amarillo = hops.get_hop_by_name('Amarillo')
# hop_bill = hop.HopBill([hop.HopAddition(hops.get_hop_by_name(
#     'Amarillo'), 5, 'boil', 76)
# ])

# print(hop_bill.get_sensory_data(1.052, 19))
# print(hop_bill.ibu(1.052, 19))


def calculate_hop_bill(og, batch_size, enabled_hops, recipe_data, addition_data, flavor_descriptors):
    """Generate hop bills
    Notes:
    - Flavors and amounts scaled by 100 on input and output, should be scaled down in frontend or API
    """

    class VarArraySolutionPrinter(cp_model.CpSolverSolutionCallback):
        """Print intermediate solutions."""

        def __init__(self, total_ibu, total_amount, total_flavor, hop_amounts, hop_flavors):
            cp_model.CpSolverSolutionCallback.__init__(self)
            self.__hop_amounts = hop_amounts
            self.__hop_flavors = hop_flavors
            self.__solution_count = 0

        def on_solution_callback(self):
            self.__solution_count += 1
            ibu = 'IBU: {}'.format(
                round(self.Value(total_ibu) / ibu_scale))
            amt = 'Amount: {} g'.format(
                round(self.Value(total_amount) / scale * batch_size))
            amount_output = ['{}: {} g'.format(
                v, round(self.Value(v) / scale * batch_size)) for v in self.__hop_amounts if self.Value(v) > 0]
            flavor_output = ['{}: {}'.format(
                v, round(self.Value(v) / flavor_scale * batch_size)) for v in self.__hop_flavors if self.Value(v) > 0]
            print('{}, {}, Flavor: {} \n  {}\n  {}'.format(
                ibu, amt, round(self.Value(total_flavor) / flavor_scale * batch_size), '\n  '.join(amount_output), '\n  '.join(flavor_output)))

        def solution_count(self):
            return self.__solution_count

    hm = hop.HopModel()
    sensory_keys = hm.get_sensory_keywords()
    scale = 5
    ibu_scale = scale ** 2 * 100
    # TODO: Streamline scaling and handle decimal batch sizes (for gallon/liter conversion)
    flavor_scale = 10000 * 100 * scale

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

    # TODO: Rework the flavor formula, it's an arbitrary mess. It's based on the inverse IBU formula, but has some arbitrary stuff added in,
    # Flavor Formula: bigness_factor * multiplier ** 2 / batch_divider
    batch_factor = (1.65 * .000125 ** (og - 1)) / \
        (batch_size / 3.78541) * 3.5274 * 10000
    flavor_util = {
        '60': int(round(
            batch_factor * (math.e ** (-.04 * 60)) ** 2
        )),
        '45': int(round(
            batch_factor * (math.e ** (-.04 * 45)) ** 2
        )),
        '30': int(round(
            batch_factor * (math.e ** (-.04 * 30)) ** 2
        )),
        '15': int(round(
            batch_factor * (math.e ** (-.04 * 15)) ** 2
        )),
        '10': int(round(
            batch_factor * (math.e ** (-.04 * 10)) ** 2
        )),
        '5': int(round(
            batch_factor * (math.e ** (-.04 * 5)) ** 2
        )),
        'flameout': int(round(
            batch_factor * 1.15 ** 2
        )),
        'dryhop': int(round(
            batch_factor * 1.25 ** 2
        ))
    }

    # Built a dict of enabled hops and their data
    enabled_hop_vars = {}
    for hop_name in enabled_hops:
        enabled_hop_vars[hop_name] = {}
        hop_object = hm.get_hop_by_name(hop_name)
        hop_object.alpha = int(round(hop_object.alpha * 10))
        enabled_hop_vars[hop_name]['data'] = hop_object
        enabled_hop_vars[hop_name]['aroma'] = {}
        for key in sensory_keys:
            enabled_hop_vars[hop_name]['aroma'][key] = int(round(
                hop_object.aroma.get(key, 0) * hop_object.total_oil * 100
            ))

    # Create the model
    model = cp_model.CpModel()

    # Create variables for entire recipe
    total_ibu = model.NewIntVar(int(round(ibu_scale * recipe_data['ibu']['min'])), int(
        round(ibu_scale * recipe_data['ibu']['max'])), 'total_ibu')
    total_flavor = model.NewIntVar(int(round(flavor_scale * recipe_data['flavor']['min'] / batch_size)), int(
        round(flavor_scale * recipe_data['flavor']['max'] / batch_size)), 'total_flavor')
    #total_flavor = model.NewIntVar(0, 0, 'total_flavor')
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
            # NOTE: Flavor is being calculated on a per-liter basis, then the output is converted to batch. Need to fix this mess.
            'flavor': model.NewIntVar(int(round(flavor_scale * recipe_data['flavor']['min'] / batch_size)), int(
                round(flavor_scale * recipe_data['flavor']['max'] / batch_size)), 'add_{}_flavor'.format(timing)),
            'hop_used': [model.NewBoolVar('add_{}_{}_used'.format(timing, hop_name)) for hop_name in enabled_hops]
        }

        # Variables for every hop per addition
        for hop_name in enabled_hops:
            hop_data = enabled_hop_vars[hop_name]['data']
            hop_aroma = enabled_hop_vars[hop_name]['aroma']

            # Each individual hop has a min of 0 and a max of the overall addition max
            enabled_hop_vars[hop_name][timing] = {
                'ibu': model.NewIntVar(0, int(round(ibu_scale * value['ibu']['max'])), 'add_{}_{}_ibu'.format(timing, hop_name)),
                'amount': model.NewIntVar(0, int(round(scale * value['amount']['max'])), 'add_{}_{}'.format(timing, hop_name)),
                'flavor': model.NewIntVar(0, int(round(flavor_scale * value['flavor']['max'] / batch_size)), 'add_{}_{}_flavor'.format(timing, hop_name)),
                'sensory_data': [model.NewIntVar(0, int(round(flavor_scale * value['flavor']['max'] / batch_size)), 'add_{}_{}_sensory_{}'.format(timing, hop_name, sensory_key)) for sensory_key in sensory_keys]
            }

            # Set the flavor values for each sensory key
            for index, key in enumerate(sensory_keys):
                model.Add(enabled_hop_vars[hop_name][timing]['sensory_data'][index] == hop_aroma[key] *
                          enabled_hop_vars[hop_name][timing]['amount'] *
                          flavor_util[timing])

            # Set the bool var for whether the hop is used or not - force amount to zero if not used and vice versa
            hop_index = enabled_hops.index(hop_name)
            model.Add(enabled_hop_vars[hop_name][timing]['amount'] > 0).OnlyEnforceIf(
                add_vars[timing]['hop_used'][hop_index])
            model.Add(enabled_hop_vars[hop_name][timing]['amount'] == 0).OnlyEnforceIf(
                add_vars[timing]['hop_used'][hop_index].Not())

            # Calculate hop IBUs: amount in g/L * aa_util * aa% as int
            model.Add(enabled_hop_vars[hop_name][timing]['ibu'] == enabled_hop_vars[hop_name]
                      [timing]['amount'] * aa_util[timing] * hop_data.alpha)

            # Calculate the hop flavor addition
            model.Add(enabled_hop_vars[hop_name][timing]['flavor'] == sum(
                sensory_value for sensory_value in enabled_hop_vars[hop_name][timing]['sensory_data']))

        # Ensure hop addition totals equals addition totals
        model.Add(add_vars[timing]['ibu'] == sum(addition[timing]['ibu'] for addition in [
            hop_vars for hop_vars in enabled_hop_vars.values()]))
        model.Add(add_vars[timing]['amount'] == sum(addition[timing]['amount'] for addition in [
            hop_vars for hop_vars in enabled_hop_vars.values()]))
        model.Add(add_vars[timing]['flavor'] == sum(addition[timing]['flavor'] for addition in [
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
    model.Add(total_flavor == sum(addition['flavor']
                                  for addition in add_vars.values()))

    # Solve
    solver = cp_model.CpSolver()
    solution_printer = VarArraySolutionPrinter(total_ibu, total_amount, total_flavor,
                                               [
                                                   enabled_hop_vars['warrior']['60']['amount'],
                                                   enabled_hop_vars['amarillo']['60']['amount'],
                                                   enabled_hop_vars['warrior']['5']['amount'],
                                                   enabled_hop_vars['amarillo']['5']['amount']
                                               ],
                                               [
                                                   enabled_hop_vars['warrior']['60']['flavor'],
                                                   enabled_hop_vars['amarillo']['60']['flavor'],
                                                   enabled_hop_vars['warrior']['5']['flavor'],
                                                   enabled_hop_vars['amarillo']['5']['flavor']
                                               ]
                                               )
    status = solver.SearchForAllSolutions(model, solution_printer)

    if status in [cp_model.FEASIBLE, cp_model.OPTIMAL]:
        return True
    else:
        return False


# enabled_hops = ['mosaic', 'amarillo', 'cascade',
#                 'centennial', 'chinook', 'warrior']
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
        'min': 0,
        'max': 650
    },
    'unique_hops': 1
}
addition_data = {
    '60': {
        'ibu': {
            'min': 30,
            'max': 50
        },
        'amount': {
            'min': 0,
            'max': 2.93
        },
        'flavor': {
            'min': 0,
            'max': 20
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
            'max': 400
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
