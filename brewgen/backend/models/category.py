import json
import os.path


class Category:
    """Defines a category and all of its properties."""

    def __init__(self, name, unique_fermentable_count, min_percent, max_percent):
        self.name = name
        self.unique_fermentable_count = unique_fermentable_count
        self.min_percent = int(min_percent)
        self.max_percent = int(max_percent)

    def get_category_data(self):
        """Return category data as a dict."""
        return {
            'name': self.name,
            'unique_fermentable_count': self.unique_fermentable_count,
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
        with open(path, 'r', encoding='utf-8') as f:
            category_data = json.load(f)
        for category in category_data:
            self.category_list.append(Category(
                name=category['name'],
                unique_fermentable_count=None,
                min_percent=category['min_percent'],
                max_percent=category['max_percent']
            ))

    def get_category_list(self):
        """Return all categories as a list of dicts."""
        return [category.get_category_data() for category in self.category_list]

    def get_category(self, category_names):
        """Return a single or list of category objects based on an input list of names"""
        category_match = [
            category for category in self.category_list if category.name in category_names]
        if type(category_names) is list:
            return category_match
        else:
            return category_match[0]

    def get_category_data(self, category_name):
        """Return category data for a single category_name."""
        pass

    def get_category_names(self):
        """Return a list of category names"""
        return [category.name for category in self.category_list]


class CategoryProfile(CategoryModel):
    """Defines a list of categories and their properties to create a profile."""

    def __init__(self, categories):
        self.category_list = list(categories)
