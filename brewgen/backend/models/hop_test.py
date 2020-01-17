import hop

hops = hop.HopModel()
mosaic = hops.get_hop_by_name('Mosaic')
amarillo = hops.get_hop_by_name('Amarillo')


hop_bill = hop.HopBill([hop.HopAddition(hops.get_hop_by_name('Magnum (US)'), 60, 'boil', 28),
                        hop.HopAddition(mosaic, 15, 'boil', 28),
                        hop.HopAddition(amarillo, 15, 'boil', 28),
                        hop.HopAddition(mosaic, 15, 'aroma',
                                        28),
                        hop.HopAddition(amarillo, 15, 'aroma',
                                        28),
                        hop.HopAddition(mosaic, 600, 'dry hop',
                                        28),
                        hop.HopAddition(amarillo, 600, 'dry hop',
                                        28)
                        ])

print(hop_bill.get_sensory_data(1.052, 19))
