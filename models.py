import json

class Category:
    """Defines a category and all of its properties."""

    def __init__(self, name, min_percent, max_percent):
        self.name = name
        self.min_percent = min_percent
        self.max_percent = max_percent


    def get_category_data(self):
        """Return category data as a dict."""
        return {
            'name': self.name,
            'min_percent': self.min_percent,
            'max_percent': self.max_percent
        }


class CategoryModel:
    """Defines a model for interacting with category data."""

    def __init__(self):
        self.category_list = []

        # Populate grains_list with all details from the database as objects
        with open('./ingredients/categories.json', 'r') as f:
            category_data = json.load(f)
        for category in category_data:
            self.category_list.append(Category(
                name = category['name'],
                min_percent = category['min_percent'],
                max_percent = category['max_percent']
            ))


    def get_category_list(self):
        """Return all categories as a list of dicts."""
        return [category.get_category_data() for category in self.category_list]


    def get_category(self, category_names):
        return [category for category in self.category_list if category.name in category_names]


class Grain:
    """Defines a grain and all of its properties."""

    def __init__(self, name, slug, brand, potential, color, max_percent, category, sensory_data, ppg):
        self.name = name
        self.slug = slug
        self.brand = brand
        self.potential = potential
        self.color = color
        self.max_percent = max_percent
        self.category = category
        self.sensory_data = sensory_data or []
        self.ppg = ppg


    def get_grain_data(self):
        """Return grain data as a dict."""
        return {
            'name': self.name,
            'slug': self.slug,
            'brand': self.brand,
            'potential': self.potential,
            'color': self.color,
            'max_percent': self.max_percent,
            'category': self.category,
            'sensory_data': self.sensory_data,
            'ppg': self.ppg
        }


class GrainModel:
    """Defines a Grain Model, used to access data about grains in the grain database."""

    def __init__(self):
        self.grain_list = []

        # Populate grains_list with all details from the database as objects
        with open('./ingredients/grains.json', 'r') as f:
            grain_data = json.load(f)
        for grain in grain_data:
            self.grain_list.append(Grain(
                name = grain['name'],
                slug = grain['slug'],
                brand = grain['brand'],
                potential = grain['potential'],
                color = grain['color'],
                max_percent = grain['max_percent'],
                category = grain['category'],
                sensory_data = grain['sensory'],
                ppg = grain['ppg']
            ))


    def get_grain_list(self):
        """Return a list of all grains as a list of dicts."""
        return [grain.get_grain_data() for grain in self.grain_list]


    def get_grain_by_category(self, category):
        """Return a list of grain objects belonging to the specified categories."""
        return [grain for grain in self.grain_list if grain.category in category]


    def get_grain_by_slug(self, grain_slugs):
        return [grain for grain in self.grain_list if grain.slug in grain_slugs]


    def get_all_categories(self):
        """Return a list of unique grain categories, optionally filtered on a list of grains."""
        # TODO: Complete this. Not sure if grain_list should be a list of objects or a list of slugs.
        pass


    def get_sensory_keywords(self):
        """Return a list of unique sensory keywords, optionally filtered on a list of grains."""
        # TODO: Add the filtering part, same as above, not sure if filtering on slugs or what
        sensory_keys = []
        for grain in self.grain_list:
            grain_keys = [key for key in grain.sensory_data.keys()]
            for key in grain_keys:
                if key not in sensory_keys:
                    sensory_keys.append(key)
        return sensory_keys


    def get_grain_slugs(self):
        """Return a list of grain slugs inside the class"""
        return [grain.slug for grain in self.grain_list]


    def get_sensory_data(self, max_unique_grains=4, category_model=CategoryModel()):
        """Return minimum and maximum sensory data based on grain list and category data."""
        pass

        #return sensory_data


class GrainList(GrainModel):
    """Creates a Grain List object, a list of grains and data about them.
    Args:
        grain_slugs (list): A list of grain slugs used to initialize this object
    """

    def __init__(self, grain_slugs):
        GrainModel.__init__(self)
        self.grain_list = self.get_grain_by_slug(grain_slugs)


    def add_grain(self, grain):
        """Adds a grain to the grain bill object.
        Args:
            grain (Grain()): The grain to add, can be an instance of the Grain() class or a valid grain slug
        """
        self.grain_list.append(grain)
