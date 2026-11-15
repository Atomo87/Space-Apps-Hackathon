from dataclasses import replace
from copy import deepcopy
from app.catalog.loader import load_catalog
from app.catalog.evidence import crop_evidence


def test_reference_for_kc_does_not_validate_other_parameters():
    evidence = crop_evidence(load_catalog().crop('soja'))
    assert evidence['parameters']['kc']['status'] == 'matches_reference'
    assert evidence['parameters']['ph_range']['status'] == 'context_only_not_parameter_validation'
    assert evidence['overall_status'] == 'not_regionally_validated'


def test_changed_value_cannot_inherit_reference_verification():
    crop = load_catalog().crop('soja')
    raw = deepcopy(crop.raw)
    raw['kc']['mid'] = .2
    evidence = crop_evidence(replace(crop, raw=raw))
    assert evidence['parameters']['kc']['status'] == 'not_verified_in_this_review'
    assert 'reference' not in evidence['parameters']['kc']


def test_range_selection_is_explicit():
    evidence = crop_evidence(load_catalog().crop('sorgo'))
    assert evidence['parameters']['kc']['status'] == 'selected_from_reference_range'
    assert evidence['parameters']['kc']['regional_validation'] == 'pending'


def test_contextual_ranges_do_not_silently_replace_catalog_values():
    crop = load_catalog().crop('soja')
    original = deepcopy(crop.raw)
    review = crop_evidence(crop)['parameters']['ph_range']
    assert review['catalog_value'] == [5.5, 7.0]
    assert review['published_context'] == [5.5, 7.8]
    assert review['status'] != 'matches_reference'
    assert crop.raw == original
