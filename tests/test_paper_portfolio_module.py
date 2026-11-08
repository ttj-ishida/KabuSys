"""paper 資産算出の共用モジュール（Issue #427）。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


def test_script_alias_points_to_shared_function():
    import run_portfolio_construction

    from kabusys.operations.paper_portfolio import calc_paper_portfolio_value

    assert run_portfolio_construction._calc_paper_portfolio_value is calc_paper_portfolio_value
