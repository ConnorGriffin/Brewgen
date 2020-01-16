import json
import os.path
import math
from slugify import slugify


class Hop:
    """Defines a hop and all of its properties."""

    def __init__(self, name, alpha, beta, cohumulone, total_oil, aroma=dict()):
        self.name = name
        self.slug = slugify(name, replacements=[["'", ''], ['®', '']])
        self.alpha = alpha
        self.beta = beta
        self.cohumulone = cohumulone
        self.total_oil = total_oil
        self.aroma = aroma


class HopModel:
    """Defines a Hop Model, used to access data about hops in the hop database."""

    def __init__(self):
        self.hop_list = []

        # Populate grains_list with all details from the database as objects
        path_list = os.path.abspath(__file__).split(os.sep)
        script_directory = path_list[0:len(path_list)-2]
        hop_path = "/".join(script_directory) + "/data/hops.json"

        with open(hop_path, 'r') as f:
            hop_data = json.load(f)

        for hop in hop_data:
            self.hop_list.append(Hop(
                name=hop['name'],
                alpha=hop['alpha'],
                beta=hop['beta'],
                cohumulone=hop['cohumulone'],
                total_oil=hop['total_oil'],
                aroma=hop['aroma']
            ))

    def get_hop_names(self):
        """Return a list of hop names"""
        return [hop.name for hop in self.hop_list]

    def get_hop_slugs(self):
        """Return a list of hop slugs"""
        return [hop.slug for hop in self.hop_list]

    def get_hop_by_slug(self, slug):
        for hop in self.hop_list:
            if hop.slug == slug:
                return hop

    def get_hop_by_name(self, name):
        for hop in self.hop_list:
            if hop.name == name:
                return hop

    def get_sensory_keywords(self):
        """Return a list of unique sensory keywords"""
        sensory_keys = []
        for hop in self.hop_list:
            if hop.aroma:
                hop_keys = [key for key in hop.aroma.keys()]
                for key in hop_keys:
                    if key not in sensory_keys:
                        sensory_keys.append(key)
        return sensory_keys


class HopAddition:
    """Defines a hop addition to a recipe.
    Args:
        hop: Hop object
        time: Hop duration in minutes
        usage: Hop usage (first wort, boil, aroma, whirlpool, dry hop)
        amount: Hop amount in grams
    """

    def __init__(self, hop, time, usage, amount):
        self.hop = hop
        self.time = time
        self.usage = usage.lower()
        self.amount = amount

    def __flavor_factor(self, og, batch_size):
        if self.usage in ['boil', 'first wort']:
            multiplier = (math.e ** (-.04 * self.time))
        elif self.usage in ['aroma', 'whirlpool']:
            multiplier = 1.15
        elif self.usage in ['dry hop']:
            multiplier = 1.25
        else:
            raise Exception("Unknown Usage method {}!".format(self.usage))

        bigness_factor = 1.65 * .000125 ** (og - 1) * multiplier
        return (multiplier * bigness_factor / (batch_size / 3.78541))

    def get_sensory_data(self, og, batch_size):
        """Returns sensory data for the given grain bill
        Args:
            og: Recipe OG in specific gravity (1.xxx)
            batch_size: Recipe batch size in liters
        """

        sensory_data = {}
        # Iterate over every possible keyword, not just the possible ones in the hop list
        for sensory_keyword in HopModel.get_sensory_keywords(HopModel()):
            sensory_data[sensory_keyword] = 0
            # Sum the sensory value contributions of each hop
            for key, value in self.hop.aroma.items():
                if key == sensory_keyword:
                    hop_flavor = value * self.hop.total_oil
                    sensory_data[key] = self.amount * hop_flavor * \
                        self.__flavor_factor(og, batch_size) * 3.5274

        return sensory_data
