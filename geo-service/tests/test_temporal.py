"""Anomalias controladas: comparabilidade, limites e ausencia de evidencia."""
from app.engine.temporal import compare_seasons


def profile(values):
    return {'yearly': {'years': list(values)}, 'monthly': [
        {'month': m, 'rain_by_year': {str(y): v for y, v in values.items()},
         'eto_by_year': {str(y): 50 for y in values}} for m in range(1, 13)]}


def row(result, year):
    return next(r for r in result['seasons'] if r['sowing_year'] == year)


def test_dry_outlier_does_not_dilute_own_reference():
    p = profile({**dict.fromkeys(range(2015, 2021), 100), 2021: 10})
    r = row(compare_seasons(p, [1, 2], 2021), 2021)
    assert r['classification'] == 'mais_seca'
    assert r['reference_count'] == 6
    assert r['reference_median_mm'] == 200
    assert r['rain_difference_pct'] == -90


def test_wet_outlier_and_tolerance_boundary():
    p = profile({**dict.fromkeys(range(2015, 2021), 100), 2021: 120})
    assert row(compare_seasons(p, [1, 2], 2021), 2021)['classification'] == 'dentro_da_faixa'
    p['monthly'][0]['rain_by_year']['2021'] = 121
    assert row(compare_seasons(p, [1, 2], 2021), 2021)['classification'] == 'mais_chuvosa'
    assert row(compare_seasons(p, [1, 2], 2021, 30), 2021)['classification'] == 'dentro_da_faixa'


def test_zero_reference_uses_absolute_floor_without_division():
    p = profile({**dict.fromkeys(range(2015, 2021), 0), 2021: 40})
    r = row(compare_seasons(p, [1], 2021), 2021)
    assert r['rain_difference_pct'] is None
    assert r['tolerance_mm'] == 30
    assert r['classification'] == 'mais_chuvosa'


def test_short_reference_and_future_are_not_classified():
    result = compare_seasons(profile({2020: 100, 2021: 90}), [1, 2], 2026)
    assert not result['requested_year_available']
    assert all(r['classification'] == 'referencia_insuficiente' for r in result['seasons'])


def test_cross_year_alignment_and_missing_eto():
    p = profile(dict.fromkeys(range(2015, 2023), 100))
    p['monthly'][0]['rain_by_year']['2016'] = 900
    result = compare_seasons(p, [12, 1], 2022)
    assert row(result, 2015)['rain_mm'] == 1000
    assert row(result, 2022)['classification'] == 'sem_dados'
    assert row(result, 2022)['missing_months'] == ['2023-01']
    p['monthly'][11]['eto_by_year']['2015'] = None
    assert row(compare_seasons(p, [12, 1], 2015), 2015)['rain_mm'] is None


def test_robust_variability_can_exceed_percent_tolerance():
    p = profile({2015: 20, 2016: 50, 2017: 80, 2018: 120, 2019: 150, 2020: 180, 2021: 200})
    r = row(compare_seasons(p, [1], 2021), 2021)
    assert r['tolerance_mm'] > 100
    assert r['classification'] == 'dentro_da_faixa'
