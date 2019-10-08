import json
import os.path
import copy

from slugify import slugify
from ortools.sat.python import cp_model


class Grain:
    """Defines a grain and all of its properties."""

    def __init__(self, name, brand, potential, color, category, sensory_data, min_percent=0, max_percent=100):
        self.name = name
        self.slug = slugify('{}_{}'.format(brand, name),
                            replacements=[["'", ''], ['®', '']])
        self.brand = brand
        self.potential = potential
        self.color = color
        self.min_percent = min_percent
        self.max_percent = max_percent
        self.category = category
        self.sensory_data = sensory_data or {}
        self.ppg = (self.potential - 1) * 1000

    def get_grain_data(self):
        """Return grain data as a dict."""
        return {
            'name': self.name,
            'slug': self.slug,
            'brand': self.brand,
            'potential': self.potential,
            'color': self.color,
            'max_percent': self.max_percent,
            'min_percent': self.min_percent,
            'category': self.category,
            'sensory_data': self.sensory_data,
            'ppg': self.ppg
        }


class GrainModel:
    """Defines a Grain Model, used to access data about grains in the grain database."""

    def __init__(self):
        self.grain_list = []

        # Populate grains_list with all details from the database as objects
        path_list = os.path.abspath(__file__).split(os.sep)
        script_directory = path_list[0:len(path_list)-2]
        path = "/".join(script_directory) + "/data/grains.json"
        with open(path, 'r') as f:
            grain_data = json.load(f)
        for grain in grain_data:
            self.grain_list.append(Grain(
                name=grain['name'],
                brand=grain['brand'],
                potential=grain['potential'],
                color=grain['color'],
                max_percent=grain['max_percent'],
                category=grain['category'],
                sensory_data=grain['sensory']
            ))

    def get_grain_list(self):
        """Return a list of all grains as a list of dicts."""
        return [grain.get_grain_data() for grain in self.grain_list]

    def get_grain_by_category(self, category):
        """Return a list of grain objects belonging to the specified categories."""
        return [grain for grain in self.grain_list if grain.category in category]

    def get_grain_by_slug(self, grain_slugs):
        return [grain for grain in self.grain_list if grain.slug in grain_slugs]

    def get_grain_by_name(self, grain_name):
        if type(grain_name) is str:
            result = [
                grain for grain in self.grain_list if grain.name in [grain_name]]
            if result:
                return result[0]
        elif type(grain_name) is dict:
            result = [
                grain for grain in self.grain_list if grain.name in grain_name]
            if result:
                return result

    def get_all_categories(self):
        """Return a list of unique grain categories."""
        return list(set(grain.category for grain in self.grain_list))

    def get_sensory_keywords(self):
        """Return a list of unique sensory keywords, optionally filtered on a list of grains."""
        # TODO: Add the filtering part, same as above, not sure if filtering on slugs or what
        sensory_keys = []
        for grain in self.grain_list:
            if grain.sensory_data:
                grain_keys = [key for key in grain.sensory_data.keys()]
                for key in grain_keys:
                    if key not in sensory_keys:
                        sensory_keys.append(key)
        return sensory_keys

    def get_grain_slugs(self):
        """Return a list of grain slugs inside the class"""
        return [grain.slug for grain in self.grain_list]


class GrainList(GrainModel):
    """Creates a Grain List object, a list of grains and data about them.
    Args:
        grain_objects (list): A list of grain objects used to initialize this object. If provided grain_slugs is ignored.
        grain_slugs (list): A list of grain slugs used to initialize this object
    """

    def __init__(self, grain_objects=None, grain_slugs=None):
        GrainModel.__init__(self)
        if grain_objects:
            self.grain_list = grain_objects
        elif grain_slugs:
            self.grain_list = self.get_grain_by_slug(grain_slugs)

    def __calculate_wort_properties(self, mode, max_unique_grains, grain_list, category_model, sensory_model):
        """Return a beer grain bill or sensory data based on input data.
        Args:
            mode (string): Defines which mode to use, either return a list of grain bills or a list of sensory data.
                Valid options: grain_bill, sensory_data
            max_unique_grains (int): Maximum number of unique grains to use in the recipe. Defaults to 4.
            grain_list (GrainList)
            category_model (CategoryModel)
            sensory_model (SensoryModel)
        """

        max_unique_grains = int(max_unique_grains)
        grain_bills = []

        class SolutionPrinter(cp_model.CpSolverSolutionCallback):
            """Add intermediate solutions to a global array for use later."""

            def __init__(self, grains_list):
                cp_model.CpSolverSolutionCallback.__init__(self)
                self.__grains = grains_list
                self.__solution_count = 0

            def OnSolutionCallback(self):
                grain_bill = [self.Value(
                    grain) for grain in self.__grains]
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
                sensory_data[key] = int(
                    grain['sensory_data'].get(key, 0) * scaling)

            grain_map.append({
                'category': grain['category'],
                'min_percent': grain['min_percent'],
                'max_percent': grain['max_percent'],
                'sensory_data': sensory_data
            })

        # Create the model
        model = cp_model.CpModel()

        # Define model variables
        grain_vars = [model.NewIntVar(
            0, 100, 'grain{}'.format(i)) for i in grain_range]
        category_vars = [model.NewIntVar(0, 100, 'category_{}'.format(
            category['name'])) for category in category_data]
        grain_used = [model.NewBoolVar(
            'grain{}_used'.format(i)) for i in grain_map]

        # Define constraints
        # Grain usage total must be 100% - not sure why both of these are needed but it doens't work if they're not
        model.Add(sum(grain_vars) == 100)
        model.Add(sum(category_vars) == 100)

        # Limit the max number of grains to the specified limit
        for i in grain_range:
            model.Add(grain_vars[i] == 0).OnlyEnforceIf(grain_used[i].Not())
            model.Add(grain_vars[i] > 0).OnlyEnforceIf(grain_used[i])
        model.Add(sum(grain_used) <= max_unique_grains)

        # Keep each grain between the min and max percents, but only if they're in use
        for i in grain_range:
            model.Add(grain_vars[i] <= grain_map[i]
                      ['max_percent']).OnlyEnforceIf(grain_used[i])
            model.Add(grain_vars[i] >= grain_map[i]
                      ['min_percent']).OnlyEnforceIf(grain_used[i])

        # Keep each grain category at or above the min and at or below the max amounts
        for i in category_range:
            category = category_data[i]
            model.Add(category_vars[i] == sum(
                grain_vars[k] for k in grain_range if grain_map[k]['category'] == category['name']))

            model.Add(category_vars[i] <= category['max_percent'])
            model.Add(category_vars[i] >= category['min_percent'])

        # If a sensory model is provided we need to add more constraints
        if sensory_model:
            sensory_model_scaled = copy.deepcopy(sensory_model)
            sensory_model_range = range(len(sensory_model))
            sensory_model_vars = [model.NewIntVar(
                0, 5 * 100 * scaling, 'sensory_model_{}'.format(i['name'])) for i in sensory_model]

            # Scale the sensory data provided
            for descriptor in sensory_model_scaled:
                descriptor['min'] = int(descriptor['min'] * scaling)
                descriptor['max'] = int(descriptor['max'] * scaling)

            # Ensure the grain bill stays within the sensory boundaries for each descriptor
            for i in sensory_model_range:
                sensory_key = sensory_model_scaled[i]['name']
                model.Add(sensory_model_vars[i] * 100 == sum(
                    grain_map[k]['sensory_data'][sensory_key] * grain_vars[k] for k in grain_range))
                model.Add(sensory_model_vars[i] >=
                          sensory_model_scaled[i]['min'])
                model.Add(sensory_model_vars[i] <=
                          sensory_model_scaled[i]['max'])

        # If the goal is to return a sensory model we need to adjust our model
        if mode == 'sensory_data':
            sensory_vars = [model.NewIntVar(
                0, 5 * 100 * scaling, 'sensory_{}'.format(key)) for key in sensory_keys]
            sensory_range = range(len(sensory_keys))

            # Solve for minimizing and maximizing each descriptor
            solver = cp_model.CpSolver()
            sensory_data = []
            for i in sensory_range:
                sensory_key = sensory_keys[i]
                # Assign sensory var = Sum of all grains (sensory key * usage percent)
                model.Add(sensory_vars[i] * 100 == sum(grain_map[k]['sensory_data']
                                                       [sensory_key] * grain_vars[k] for k in grain_range))

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
            # Find all solutions with a time limit, return the usage_percent for each solution
            solver = cp_model.CpSolver()
            solver.parameters.max_time_in_seconds = 1
            solution_printer = SolutionPrinter(grain_vars)
            status = solver.SearchForAllSolutions(model, solution_printer)

            return grain_bills

    def get_grain_bills(self, beer_profile, equipment_profile, category_model, sensory_model=None, max_unique_grains=4):
        """Return a list of GrainBill objects for valid recipes given the input parameters.
        Args:
            beer_profile (BeerProfile)
            equipment_profile (EquipmentProfile)
            category_model (CategoryModel)
            sensory_model (SensoryModel): defaults to None
            max_unique_grains (int): defaults to 4
        """

        # Get grain bill percent arrays for all possible grain bills given the input parameters
        grain_bill_percents = self.__calculate_wort_properties(
            mode='grain_bill',
            max_unique_grains=max_unique_grains,
            grain_list=self,
            category_model=category_model,
            sensory_model=sensory_model
        )

        # Create a grain bill object for each one
        grain_bills = [GrainBill(self.grain_list, grain_percents)
                       for grain_percents in grain_bill_percents]

        # Calculate the color of each grain bill given the equipment profile, only return if within the specified color range
        valid_grain_bills = []
        for grain_bill in grain_bills:
            color = grain_bill.get_beer_srm(
                beer_profile.original_sg, equipment_profile)
            if beer_profile.min_color_srm <= color <= beer_profile.max_color_srm:
                valid_grain_bills.append(grain_bill)

        return valid_grain_bills

    def get_sensory_profiles(self, category_model, sensory_model=None, max_unique_grains=4):
        """Return a sensory model (min and max descriptor values) for valid recipes given the input parameters.
        Args:
            category_model (CategoryModel)
            sensory_model (SensoryModel): defaults to None
            max_unique_grains (int): defaults to 4
        """
        sensory_model = self.__calculate_wort_properties(
            mode='sensory_data',
            sensory_model=sensory_model,
            category_model=category_model,
            max_unique_grains=max_unique_grains,
            grain_list=self
        )
        return sensory_model

    def add_grain(self, grain):
        """Adds a grain to the grain list object.
        Args:
            grain (Grain()): The grain to add
        """
        # TODO: Accept slug as well
        self.grain_list.append(grain)


class GrainBill(GrainModel):
    """Creates a Grain Bill, a list of grains and their usage percentage in a recipe.
    Args:
        grain_list (list): A GrainList object
        use_percent (list): A list of percentages (as int(0-100)) of each grain in grain_list to use
    """

    def __init__(self, grain_list, use_percent):
        self.grain_list = grain_list
        self.use_percent = use_percent
        self.__grain_range = range(len(grain_list))

    def __sg_to_ppg(self, sg):
        return (sg - 1) * 1000

    def get_beer_srm(self, original_sg, equipment_profile):
        """Calculate the resulting beer's color from this grain bill based on equipment profile and target gravity.
        Args:
            original_sg (float): Target starting gravity in (1.xxx) format
            equipment_profile (EquipmentProfile): Equipment profile used to calculate the color
        """
        # Get grain pounds, calculate mcu, then apply Morey Equation and return the result
        use_pounds = self.__get_grain_pounds(original_sg, equipment_profile)
        mash_color_units = sum(
            self.grain_list[i].color * use_pounds[i] / equipment_profile.target_volume_gallons for i in self.__grain_range)
        return 1.4922 * mash_color_units ** 0.6859

    def __get_grain_pounds(self, original_sg, equipment_profile):
        sg_points_needed = self.__sg_to_ppg(
            original_sg) * equipment_profile.target_volume_gallons
        average_ppg = sum(
            self.grain_list[i].ppg * (self.use_percent[i] / 100) for i in self.__grain_range)

        use_pounds = []
        for i in self.__grain_range:
            use_pounds.append(sg_points_needed / (average_ppg *
                                                  equipment_profile.mash_efficiency) * (self.use_percent[i]))
        return use_pounds

    def get_recipe(self, original_sg, equipment_profile):
        """Return the recipe as a dict
        Args:
            original_sg
            equipment_profile
        """

        use_pounds = self.__get_grain_pounds(original_sg, equipment_profile)
        grain_list = []

        for i in self.__grain_range:
            if self.use_percent[i] > 0:
                grain_dict = {
                    "slug": self.grain_list[i].slug,
                    "use_percent": self.use_percent[i],
                    "use_pounds": use_pounds[i]
                }
                grain_list.append(grain_dict)

        return {
            "grains": grain_list,
            "srm": self.get_beer_srm(original_sg, equipment_profile)
        }
