import json
import os.path

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
        path_list = os.path.abspath(__file__).split(os.sep)
        script_directory = path_list[0:len(path_list)-2]
        path = "/".join(script_directory) + "/data/categories.json"
        with open(path, 'r') as f:
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


class CategoryProfile(CategoryModel):
    """Defines a list of categories and their properties to create a profile."""

    def __init__(self, categories):
        self.category_list = list(categories)

