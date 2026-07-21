import json
import os.path

from slugify import slugify


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

    def set_usage(self, min_percent, max_percent):
        """Set the min and max usage percents for the grain"""
        self.min_percent = min_percent
        self.max_percent = max_percent


class GrainModel:
    """Defines a Grain Model, used to access data about grains in the grain database."""

    def __init__(self):
        self.grain_list = []

        # Populate grains_list with all details from the database as objects
        path_list = os.path.abspath(__file__).split(os.sep)
        script_directory = path_list[0:len(path_list)-2]
        path = "/".join(script_directory) + "/data/grains.json"
        with open(path, 'r', encoding='utf-8') as f:
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

    def get_grain_by_slug(self, grain_slug):
        if type(grain_slug) is str:
            result = [
                grain for grain in self.grain_list if grain.slug == grain_slug]
            if result:
                return result[0]
        elif type(grain_slug) is list:
            result = []
            for slug in grain_slug:
                for grain in self.grain_list:
                    if grain.slug == slug:
                        result.append(grain)
            if result:
                return result

    def get_grain_by_name(self, grain_name):
        if type(grain_name) is str:
            result = [
                grain for grain in self.grain_list if grain.name == grain_name]
            if result:
                return result[0]
        elif type(grain_name) is list:
            result = []
            for name in grain_name:
                for grain in self.grain_list:
                    if grain.name == name:
                        result.append(grain)
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
            try:
                if grain.sensory_data:
                    grain_keys = [key for key in grain.sensory_data.keys()]
                    for key in grain_keys:
                        if key not in sensory_keys:
                            sensory_keys.append(key)
            except:
                print(grain.get_grain_data())
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
        grain_list (object): A GrainList object
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

    def get_sensory_data(self):
        """Returns sensory data for the given grain bill"""

        sensory_data = {}
        # Iterate over every possible keyword, not just the possible ones in the grain bill
        for sensory_keyword in GrainModel.get_sensory_keywords(GrainModel()):
            sensory_value = 0
            #  Sum the sensory value contributions of each grain proportional to their usage percent
            for i in self.__grain_range:
                fermentable = self.grain_list[i]
                for key, value in fermentable.sensory_data.items():
                    if key == sensory_keyword:
                        sensory_value += value * self.use_percent[i] / 100

            sensory_data[sensory_keyword] = sensory_value

        return sensory_data
