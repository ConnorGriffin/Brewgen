import hop

hops = hop.HopModel()
matching_hop = hops.get_hop_by_name('Amarillo')


flavor = hop.HopAddition(matching_hop, 15, 'boil',
                         28).get_sensory_data(1.052, 19)


flavor = [hop.HopAddition(matching_hop, 60, 'boil', 28).get_sensory_data(1.052, 19)['Grapefruit'],
          hop.HopAddition(matching_hop, 15, 'boil', 28).get_sensory_data(
              1.052, 19)['Grapefruit'],
          hop.HopAddition(matching_hop, 600, 'dry hop',
                          28).get_sensory_data(1.052, 19)['Grapefruit'],
          hop.HopAddition(matching_hop, 15, 'aroma',
                          28).get_sensory_data(1.052, 19)['Grapefruit'],
          ]

print(flavor)
