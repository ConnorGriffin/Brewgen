from pathlib import Path
import sys

sys.path.append('../../../')
from brewgen.backend.models import beer, category, equipment, grain, style

ipa = style.StyleModel().get_style_by_slug('american-ipa')
grain_list = ipa.grain_list
category_profile = category.CategoryProfile(ipa.category_list)
equipment_profile = equipment.EquipmentProfile(
    mash_efficiency=73, target_volume_gallons=5.75)
beer_profile = beer.BeerProfile(0, 999, 1.060)

sensory_model = [{'name': 'bitter', 'min': 0.0, 'max': 0.2}, {'name': 'burnt', 'min': 0.0, 'max': 0.1}, {'name': 'roasted', 'min': 0.0, 'max': 0.45}, {'name': 'coffee', 'min': 0.0, 'max': 0.638}, {'name': 'cocoa', 'min': 0.0, 'max': 0.826}, {'name': 'dark_chocolate', 'min': 0.0, 'max': 0.728}, {'name': 'milk_chocolate', 'min': 0.0, 'max': 0.15}, {'name': 'sweet', 'min': 2.11, 'max': 4.2}, {'name': 'roasted_almond', 'min': 0.0, 'max': 1.75}, {'name': 'dried_fruit', 'min': 0.0, 'max': 0.98}, {'name': 'wood_smoke', 'min': 0.0, 'max': 0.2}, {'name': 'clove', 'min': 0.0, 'max': 1.0}, {'name': 'almond', 'min': 0.0, 'max': 1.905}, {'name': 'hazelnut', 'min': 0.0, 'max': 2.075}, {'name': 'raisin', 'min': 0.0, 'max': 1.545}, {
    'name': 'vanilla', 'min': 0.0, 'max': 1.225}, {'name': 'honey', 'min': 0.0, 'max': 2.2}, {'name': 'biscuit', 'min': 0.68, 'max': 1.49}, {'name': 'marmalade', 'min': 0.0, 'max': 0.86}, {'name': 'malty', 'min': 1.53, 'max': 4.2}, {'name': 'toffee', 'min': 0.0, 'max': 1.64}, {'name': 'caramel', 'min': 0.0, 'max': 1.645}, {'name': 'dark_caramel', 'min': 0.0, 'max': 0.96}, {'name': 'sour', 'min': 0.0, 'max': 0.795}, {'name': 'bready', 'min': 0.0, 'max': 2.2}, {'name': 'graham_cracker', 'min': 0.0, 'max': 2.0}, {'name': 'nutty', 'min': 0.0, 'max': 1.0}, {'name': 'toast', 'min': 0.0, 'max': 2.0}, {'name': 'grainy', 'min': 0.0, 'max': 2.0}, {'name': 'wheat_flour', 'min': 0.0, 'max': 0.0}, {'name': 'bread_dough', 'min': 0.0, 'max': 0.0}]
sensory_model = []

grain_bills = grain_list.get_grain_bills(
    beer_profile=beer_profile,
    equipment_profile=equipment_profile,
    category_model=category_profile,
    sensory_model=sensory_model,
    max_unique_grains=4
)
print(grain_bills)
#print(len(grain_bills))
#sensory_data = grain_list.get_sensory_profiles(
#    category_model=category_profile, sensory_model=sensory_model)
#print(sensory_data)
#print(get_grain_bills('sensory_data', sensory_model=model))
# print(get_grain_bills('sensory_data'))
#grain_bills = get_grain_bills('grain_bill', sensory_model=model)
