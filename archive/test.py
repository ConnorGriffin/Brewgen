from models import beer, category, equipment, grain

grain_list = grain.GrainList()
category_model = category.CategoryModel()
equipment_profile = equipment.EquipmentProfile(mash_efficiency=73, target_volume_gallons=5.75)
beer_profile = beer.BeerProfile(5.4, 5.6, 1.045)

sensory_model = [
    {'name': 'sweet', 'min': 2.8, 'max': 3.0},
    {'name': 'malty', 'min': 1.0, 'max': 2.0},
    {'name': 'bready', 'min': 1.0, 'max': 2.0}
]
grain_bills = grain_list.get_grain_bills(
    beer_profile = beer_profile,
    equipment_profile = equipment_profile,
    category_model = category_model,
    sensory_model = sensory_model,
    max_unique_grains = 4
)
print(len(grain_bills))
sensory_data = grain_list.get_sensory_profiles(category_model=category_model, sensory_model=sensory_model)
print(sensory_data)
#print(get_grain_bills('sensory_data', sensory_model=model))
#print(get_grain_bills('sensory_data'))
#grain_bills = get_grain_bills('grain_bill', sensory_model=model)