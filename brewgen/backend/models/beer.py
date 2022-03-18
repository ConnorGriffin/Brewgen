class BeerProfile:
    """Defines a list of properties of a target beer.
    Args:
        min_color_srm: Target beer's minimum color in SRM
        max_color_srm: Target beer's maximum color in SRM
        original_specific_gravity: Target beer's starting specific gravity in SG (1.xxx)
    """

    def __init__(self, min_color_srm, max_color_srm, original_sg):
        self.min_color_srm = min_color_srm
        self.max_color_srm = max_color_srm
        self.original_sg = original_sg

