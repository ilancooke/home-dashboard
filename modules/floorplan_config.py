"""Approved sensor placement, in the original floorplan's pixel coordinates.

Numbers and entity IDs follow temp/sensors.csv. This module and the static image
are the production source; deployment does not depend on the ignored temp folder.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Sensor:
    id: int
    name: str
    entity_id: str
    x: int
    y: int
    bx: int
    by: int
    open_state: str = 'on'
    closed_state: str = 'off'


SENSORS = (
    Sensor(1, 'Lounge Patio Door', 'binary_sensor.back_patio_door_opening_2', 963, 461, 908, 431),
    Sensor(2, 'Entry Foyer Door', 'binary_sensor.back_patio_door_opening', 552, 409, 580, 358),
    Sensor(3, 'Door to Garage', 'binary_sensor.linkind_door_sensor_2_ias_zone', 501, 689, 454, 713),
    Sensor(4, 'Eilah BR Left Window', 'binary_sensor.br2_window_1_opening', 1211, 459, 1275, 435),
    Sensor(5, 'Eilah BR Right Window', 'binary_sensor.window_2_opening', 1211, 516, 1275, 525),
    Sensor(6, 'Front Door', 'binary_sensor.lumi_lumi_sensor_magnet_aq2_e1834708_on_off', 777, 848, 778, 920),
    Sensor(7, 'Large Garage Door', 'binary_sensor.lk_zb_doorsensor_d0003_84f273fe_ias_zone', 201, 812, 132, 812),
    Sensor(8, 'Laundry Room Left Window', 'binary_sensor.window_left_opening', 535, 885, 524, 964),
    Sensor(9, 'Lounge Left Window', 'binary_sensor.left_window_opening', 1167, 345, 1234, 333),
    Sensor(10, 'Maya BR Window', 'binary_sensor.br2_window_opening', 980, 130, 916, 130),
    Sensor(11, 'MBR Patio Door', 'binary_sensor.mbr_patio_door_opening', 500, 297, 562, 271),
    Sensor(12, 'Office Window Left', 'binary_sensor.office_window_1_opening', 1168, 786, 1236, 784),
    Sensor(13, 'Office Window Right', 'binary_sensor.office_window_2_opening', 1168, 871, 1236, 872),
    Sensor(14, 'Living Room Sliding Door', 'binary_sensor.patio_sliding_door_opening', 850, 490, 819, 420),
    Sensor(15, 'Laundry Room Right Window', 'binary_sensor.right_window_opening', 574, 885, 614, 964),
    Sensor(16, 'Lounge Right Window', 'binary_sensor.lumi_lumi_sensor_magnet_aq2_opening', 1167, 393, 1234, 391),
    Sensor(17, 'Small Garage Door', 'binary_sensor.lk_zb_doorsensor_d0003_202b7bfe_ias_zone', 117, 648, 98, 718),
)
