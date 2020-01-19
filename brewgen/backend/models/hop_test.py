import hop

hops = hop.HopModel()
mosaic = hops.get_hop_by_name('Mosaic')
amarillo = hops.get_hop_by_name('Amarillo')


hop_bill = hop.HopBill([hop.HopAddition(hops.get_hop_by_name('Mosaic'), 60, 'boil', 28),
                        hop.HopAddition(hops.get_hop_by_name(
                            'Amarillo'), 5, 'boil', 68)
                        ])

print(hop_bill.get_sensory_data(1.052, 19))
print(hop_bill.ibu(1.052, 19))
