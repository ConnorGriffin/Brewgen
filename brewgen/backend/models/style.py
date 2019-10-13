import json
import os.path
from slugify import slugify
from . import grain, category


class Style:
    """Defines a style and all of its properties."""

    def __init__(self, name, bjcp_id, bjcp_category, impression, aroma, appearance, flavor, mouthfeel, comments, history, ingredients, comparison, examples, tags, stats, grain_list, category_list, sensory_data):
        self.name = name
        self.slug = slugify(name, replacements=[["'", ''], ['®', '']])
        self.id = bjcp_id
        self.category = bjcp_category
        self.impression = impression
        self.aroma = aroma
        self.appearance = appearance
        self.flavor = flavor
        self.mouthfeel = mouthfeel
        self.comments = comments
        self.history = history
        self.ingredients = ingredients
        self.comparison = comparison
        self.examples = examples
        self.tags = tags
        self.stats = stats
        self.grain_list = grain_list
        self.category_list = category_list
        self.sensory_data = sensory_data
        self.exceptions = self.stats.get('exceptions', None)

    def get_style_data(self):
        """Return the style in dict format"""
        return {
            'name': self.name,
            'slug': self.slug,
            'grain_list': [grain_object.get_grain_data() for grain_object in self.grain_list],
            'category_list': [category_object.get_category_data() for category_object in self.category_list],
            'sensory_data': self.sensory_data
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

    def og_range(self):
        """Return OG range as a tuple, may also return an exception if style is variable."""
        if self.exceptions:
            return self.exceptions
        else:
            return (float(self.stats['og']['low']), float(self.stats['og']['high']))

    def fg_range(self):
        """Return FG range as a tuple, may also return an exception if style is variable."""
        if self.exceptions:
            return self.exceptions
        else:
            return (float(self.stats['fg']['low']), float(self.stats['fg']['high']))

    def ibu_range(self):
        """Return IBU range as a tuple, may also return an exception if style is variable."""
        if self.exceptions:
            return self.exceptions
        else:
            return (float(self.stats['ibu']['low']), float(self.stats['ibu']['high']))

    def srm_range(self):
        """Return SRM range as a tuple, may also return an exception if style is variable."""
        if self.exceptions:
            return self.exceptions
        else:
            return (float(self.stats['srm']['low']), float(self.stats['srm']['high']))

    def abv_range(self):
        """Return ABV range as a tuple, may also return an exception if style is variable."""
        if self.exceptions:
            return self.exceptions
        else:
            return (float(self.stats['abv']['low']), float(self.stats['abv']['high']))

    def get_stats(self):
        """Return stats as a dict with float converted data"""
        if not self.exceptions:
            og = self.og_range()
            fg = self.fg_range()
            ibu = self.ibu_range()
            srm = self.srm_range()
            abv = self.abv_range()
            return {
                'og': {
                    'low': og[0],
                    'high': og[1]
                },
                'fg': {
                    'low': fg[0],
                    'high': fg[1]
                },
                'ibu': {
                    'low': ibu[0],
                    'high': ibu[1]
                },
                'srm': {
                    'low': srm[0],
                    'high': srm[1]
                },
                'abv': {
                    'low': abv[0],
                    'high': abv[1]
                }
            }


class StyleModel:
    """Defines a Style Model, used to access data about styles in the style database."""

    def __init__(self):
        self.style_list = []

        # Populate grains_list with all details from the database as objects
        path_list = os.path.abspath(__file__).split(os.sep)
        script_directory = path_list[0:len(path_list)-2]
        style_usage_path = "/".join(script_directory) + "/data/styles.json"
        bjcp_path = "/".join(script_directory) + "/data/bjcp-2015.json"

        with open(bjcp_path, 'r') as f:
            self.bjcp_data = json.load(f)

        with open(style_usage_path, 'r') as f:
            style_data = json.load(f)

        for style in style_data:
            bjcp_style = self.__bjcp_lookup(style['style'])
            bjcp_category = self.__bjcp_lookup(
                style['style'], return_category=True)
            style_grain_list = []
            style_category_list = []
            style_sensory_data = []

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

            for sensory_keyword in style['sensory_data']:
                style_sensory_data.append({
                    'name': sensory_keyword['name'],
                    'min': sensory_keyword['min'],
                    'max': sensory_keyword['max']
                })

            self.style_list.append(Style(
                # Remove Historical Beer:, Specialty IPA: etc from start of names
                name=style['style'].split(':')[-1].strip(),
                bjcp_id=bjcp_style.get('id'),
                bjcp_category=bjcp_category.get('name'),
                impression=bjcp_style.get('impression'),
                aroma=bjcp_style.get('aroma'),
                appearance=bjcp_style.get('appearance'),
                flavor=bjcp_style.get('flavor'),
                mouthfeel=bjcp_style.get('mouthfeel'),
                comments=bjcp_style.get('comments'),
                history=bjcp_style.get('history'),
                ingredients=bjcp_style.get('ingredients'),
                comparison=bjcp_style.get('comparison'),
                examples=bjcp_style.get('examples'),
                tags=bjcp_style.get('tags'),
                stats=bjcp_style.get('stats'),
                grain_list=grain.GrainList(style_grain_list),
                category_list=style_category_list,
                sensory_data=style_sensory_data
            ))

    def __bjcp_lookup(self, name, return_category=False):
        """Return bjcp data for a style name"""
        for bev_class in self.bjcp_data['styleguide']['class']:
            if bev_class['type'] == 'beer':
                for style_category in bev_class['category']:
                    for subcat in style_category['subcategory']:
                        if subcat['name'] == name:
                            if not return_category:
                                return subcat
                            else:
                                return style_category

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
