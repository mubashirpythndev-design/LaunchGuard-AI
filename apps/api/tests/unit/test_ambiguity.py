from rule_engine import Measurement, is_threshold_ambiguous


def test_is_threshold_ambiguous() -> None:
    # Threshold = 3.0, Error Margin = 1.5
    # Range is [1.5, 4.5]
    m_within = Measurement(
        name="fin_angle_deviation",
        value=4.2,
        unit="deg",
        threshold=3.0,
        error_margin=1.5,
    )
    assert is_threshold_ambiguous(m_within) is True

    m_outside = Measurement(
        name="fin_angle_deviation",
        value=5.0,
        unit="deg",
        threshold=3.0,
        error_margin=1.5,
    )
    assert is_threshold_ambiguous(m_outside) is False

    m_boundary = Measurement(
        name="fin_angle_deviation",
        value=4.5,
        unit="deg",
        threshold=3.0,
        error_margin=1.5,
    )
    assert is_threshold_ambiguous(m_boundary) is True

    m_no_margin = Measurement(
        name="fin_angle_deviation",
        value=3.1,
        unit="deg",
        threshold=3.0,
    )
    assert is_threshold_ambiguous(m_no_margin) is False
