import math
from datetime import date

from app.climate.eto import eto_penman_monteith, extraterrestrial_radiation, radiation_to_mj


def test_fao56_example_18_bruxelas():
    ea = 1.409
    tdew = 237.3 * math.log(ea / 0.6108) / (17.27 - math.log(ea / 0.6108))
    eto = eto_penman_monteith(tmax=21.5, tmin=12.3, rs=22.07, u2=2.078, lat_deg=50.8, day=date(2025, 7, 6), elevation_m=100, tdew=tdew)
    assert abs(eto - 3.9) < 0.1


def test_fao56_example_8_ra():
    assert abs(extraterrestrial_radiation(-20, date(2025, 9, 3)) - 32.2) < 0.1


def test_radiation_units():
    assert radiation_to_mj(10, "MJ/m^2/day") == 10
    assert abs(radiation_to_mj(5, "kW-hr/m^2/day") - 18.0) < 1e-9
    assert radiation_to_mj(5, "furlongs") is None
