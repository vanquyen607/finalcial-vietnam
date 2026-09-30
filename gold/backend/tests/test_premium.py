from __future__ import annotations

from app.services.premium import OZ_PER_TAEL, SJC_CODE, compute_premium


def test_oz_per_tael_constant():
    assert abs(OZ_PER_TAEL - 37.5 / 31.1034768) < 1e-9
    assert SJC_CODE == "SJL1L10"


def test_compute_premium_math():
    # spot 4180 USD/oz, tỷ giá 26270 -> TG ~132.4 triệu/lượng
    gap = compute_premium(140_500_000, 4180.0, 26_270.0)
    assert gap is not None
    expected_world = 4180.0 * 26_270.0 * OZ_PER_TAEL
    assert gap["world_vnd_luong"] == round(expected_world)
    assert gap["gap_abs"] == round(140_500_000 - expected_world)
    assert gap["gap_pct"] == round((140_500_000 - expected_world) / expected_world * 100, 2)
    assert gap["gap_abs"] > 0  # SJC luôn cao hơn TG


def test_compute_premium_rejects_bad_input():
    assert compute_premium(0, 4180.0, 26_270.0) is None
    assert compute_premium(140_500_000, 0, 26_270.0) is None
    assert compute_premium(140_500_000, 4180.0, 0) is None
    assert compute_premium(140_500_000, -5, 26_270.0) is None
