from slugify import slugify
import json

class GrainModel:
    """Imports grains from the database"""

    def __init__(self):
        self.all_grains = []

        # Populate grains_list with all details from the database
        with open('./ingredients/grains.json', 'r') as f:
            grain_data = json.load(f)
        for grain in grain_data:
            self.all_grains.append(Grain(
                name = grain['name'],
                brand = grain['brand'],
                potential = grain['potential'],
                color = grain['color'],
                max_percent = grain['max_percent'],
                category = grain['category'],
                sensory_data = grain['sensory']
            ))

    def get_all_grains(self):
        """Return a list of all grains as a list of dicts"""
        return [grain.get_grain_data() for grain in self.all_grains]


    def get_by_category(self, category):
        """Return a list of grain objects belonging to the specified categories"""
        return [grain for grain in self.all_grains if grain.category in category]


    def get_all_categories(self, grain_list):
        """Return a list of unique grain categories, optionally filtered on a list of grains"""
        # TODO: Complete this. Not sure if grain_list should be a list of objects or a list of slugs.
        pass


    def get_sensory_keywords(self):
        """Return a list of unique sensory keywords, optionally filtered on a list of grains"""
        # TODO: Add the filtering part, same as above, not sure if filtering on slugs or what
        sensory_keys = []
        for grain in self.all_grains:
            grain_keys = [key for key in grain.sensory_data.keys()]
            for key in grain_keys:
                if key not in sensory_keys:
                    sensory_keys.append(key)
        return sensory_keys



class Grain:
    """Defines a grain and all of its properties."""

    def __init__(self, name, brand, potential, color, max_percent, category, sensory_data):
        self.name = name,
        self.slug = slugify('{}_{}'.format(brand, name), replacements=[["'", ''], ['®', '']])
        self.potential = potential
        self.color = color
        self.max_percent = max_percent
        self.category = category
        self.sensory_data = sensory_data or []
        self.ppg = (self.potential - 1) * 1000


    def get_grain_data(self):
        return {
            'name': self.name,
            'slug': self.slug,
            'potential': self.potential,
            'color': self.color,
            'max_percent': self.max_percent,
            'category': self.category,
            'sensory_data': self.sensory_data,
            'ppg': self.ppg
        }
