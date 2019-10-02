class EquipmentProfile:
    """Defines an equipment profile and all of its properties.
    Args:
        mash_efficiency (float): Mash efficiency on a 0-100 or 0.00 to 1.00 scale
        target_volume_gallons (float): Target final kettle volume in gallons
    """

    def __init__(self, mash_efficiency, target_volume_gallons, ):
        # Accept mash efficiency as percent (.73) or whole number (73)
        if mash_efficiency > 1:
            self.mash_efficiency = mash_efficiency
        else:
            self.mash_efficiency = mash_efficiency * 100

        self.target_volume_gallons = target_volume_gallons
