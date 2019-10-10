import json
import os.path
from slugify import slugify
from . import grain, category


class Style:
    """Defines a style and all of its properties."""

    def __init__(self, name, grain_list, category_list):
        self.name = name
        self.slug = slugify(name, replacements=[["'", ''], ['®', '']])
        self.grain_list = grain_list
        self.category_list = category_list

    def get_style_data(self):
        """Return the style in dict format"""
        return {
            'name': self.name,
            'slug': self.slug,
            'grain_list': [grain_object.get_grain_data() for grain_object in self.grain_list],
            'category_list': [category_object.get_category_data() for category_object in self.category_list]
        }

    def get_grain_usage(self):
        """Return grains and their min/max usage"""
        grain_data = []
        for grain_object in self.grain_list.grain_list:
            grain_data.append({
                'name': grain_object.name,
                'slug': grain_object.slug,
                'min_percent': grain_object.min_percent,
                'max_percent': grain_object.max_percent
            })
        return grain_data

    def get_category_usage(self):
        """Return categories and their min/max usage"""
        category_data = []
        for category_object in self.category_list:
            category_data.append({
                'name': category_object.name,
                'min_percent': category_object.min_percent,
                'max_percent': category_object.max_percent
            })
        return category_data


class StyleModel:
    """Defines a Style Model, used to access data about styles in the style database."""

    def __init__(self):
        self.style_list = []

        # Populate grains_list with all details from the database as objects
        path_list = os.path.abspath(__file__).split(os.sep)
        script_directory = path_list[0:len(path_list)-2]
        path = "/".join(script_directory) + "/data/styles.json"
        with open(path, 'r') as f:
            style_data = json.load(f)
        for style in style_data:
            style_grain_list = []
            style_category_list = []

            for grain_data in style['grain_usage']:
                matching_grain = grain.GrainModel.get_grain_by_slug(grain.GrainModel(), grain_data['slug'])[
                    0]
                style_grain_list.append(grain.Grain(
                    name=matching_grain.name,
                    brand=matching_grain.brand,
                    potential=matching_grain.potential,
                    color=matching_grain.color,
                    min_percent=grain_data['usage']['min'],
                    max_percent=grain_data['usage']['max'],
                    category=matching_grain.category,
                    sensory_data=matching_grain.sensory_data
                ))

            for category_data in style['category_usage']:
                style_category_list.append(category.Category(
                    name=category_data['name'],
                    min_percent=category_data['usage']['min'],
                    max_percent=category_data['usage']['max']
                ))

            self.style_list.append(Style(
                name=style['style'],
                grain_list=grain.GrainList(style_grain_list),
                category_list=style_category_list
                # TODO: Add BJCP data, OG, color and stuff
            ))

    def get_style_names(self):
        """Return a list of style names"""
        return [style.name for style in self.style_list]

    def get_style_slugs(self):
        """Return a list of style names"""
        return [style.slug for style in self.style_list]

    def get_style_names_and_slugs(self):
        return [{'name': style.name, 'slug': style.slug} for style in self.style_list]

    def get_style_by_slug(self, style_slug):
        for style in self.style_list:
            if style.slug == style_slug:
                return style
