import json
import os.path
from slugify import slugify


class Hop:
    """Defines a hop and all of its properties."""

    def __init__(self, name, alpha, beta, cohumulone, total_oil):
        self.name = name
        self.slug = slugify(name, replacements=[["'", ''], ['®', '']])
        self.alpha = alpha
        self.beta = beta
        self.cohumulone = cohumulone
        self.total_oil = total_oil


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
                name=hop['Name'],
                alpha=(hop['AlphaMin'] + hop['AlphaMax']) / 2,
                beta=(hop['BetaMin'] + hop['BetaMax']) / 2,
                cohumulone=(hop['CoHumuloneMin'] + hop['CoHumuloneMax']) / 2,
                total_oil=(hop['TotalOilMin'] + hop['TotalOilMax']) / 2
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
