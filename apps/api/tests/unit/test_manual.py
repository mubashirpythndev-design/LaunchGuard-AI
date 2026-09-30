from rule_engine import (
    ManualInputSet,
    Severity,
    Thresholds,
    evaluate_manual_inputs,
    get_missing_mandatory_inputs,
)


def test_missing_mandatory_inputs_detection() -> None:
    assert len(get_missing_mandatory_inputs(None)) == 4
    assert len(get_missing_mandatory_inputs(ManualInputSet())) == 4

    partial = ManualInputSet(wind_speed_ms=5.0, visibility="good")
    missing = get_missing_mandatory_inputs(partial)
    assert "precipitation" in missing
    assert "area_cleared" in missing
    assert "wind_speed_ms" not in missing


def test_wind_boundaries_and_thresholds() -> None:
    t = Thresholds(wind_warning_ms=10.0, wind_critical_ms=15.0)

    # 10.0 is boundary (<= 10.0 is OK, > 10.0 is WARNING)
    f_10 = evaluate_manual_inputs(ManualInputSet(wind_speed_ms=10.0), thresholds=t)
    wind_10 = next(f for f in f_10 if f.check_id == "manual.wind")
    assert wind_10.severity == Severity.OK

    f_10_1 = evaluate_manual_inputs(ManualInputSet(wind_speed_ms=10.1), thresholds=t)
    wind_10_1 = next(f for f in f_10_1 if f.check_id == "manual.wind")
    assert wind_10_1.severity == Severity.WARNING

    # 15.0 is boundary (<= 15.0 is WARNING, > 15.0 is CRITICAL)
    f_15 = evaluate_manual_inputs(ManualInputSet(wind_speed_ms=15.0), thresholds=t)
    wind_15 = next(f for f in f_15 if f.check_id == "manual.wind")
    assert wind_15.severity == Severity.WARNING

    f_15_1 = evaluate_manual_inputs(ManualInputSet(wind_speed_ms=15.1), thresholds=t)
    wind_15_1 = next(f for f in f_15_1 if f.check_id == "manual.wind")
    assert wind_15_1.severity == Severity.CRITICAL


def test_visibility_and_precipitation_rules() -> None:
    f_vis_good = evaluate_manual_inputs(ManualInputSet(visibility="good"))
    f_good_vis = next(f for f in f_vis_good if f.check_id == "manual.visibility")
    assert f_good_vis.severity == Severity.OK

    f_vis_poor = evaluate_manual_inputs(ManualInputSet(visibility="poor"))
    f_poor_vis = next(f for f in f_vis_poor if f.check_id == "manual.visibility")
    assert f_poor_vis.severity == Severity.WARNING

    f_precip_heavy = evaluate_manual_inputs(ManualInputSet(precipitation="heavy"))
    f_heavy_precip = next(f for f in f_precip_heavy if f.check_id == "manual.precipitation")
    assert f_heavy_precip.severity == Severity.WARNING


def test_area_not_cleared_is_critical() -> None:
    f_clear = evaluate_manual_inputs(ManualInputSet(area_cleared=True))
    f_cleared = next(f for f in f_clear if f.check_id == "manual.area_cleared")
    assert f_cleared.severity == Severity.OK

    f_not_clear = evaluate_manual_inputs(ManualInputSet(area_cleared=False))
    f_uncleared = next(f for f in f_not_clear if f.check_id == "manual.area_cleared")
    assert f_uncleared.severity == Severity.CRITICAL
