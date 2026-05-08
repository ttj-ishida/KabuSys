"""tests/test_regime_provider.py — RegimeProvider 実装の単体テスト"""

from datetime import date

import pytest

from kabusys.core.interfaces import build_regime_provider
from kabusys.core.interfaces.regime import DatabaseRegimeProvider, NullRegimeProvider


@pytest.fixture
def duck_conn():
    from kabusys.data.schema import init_schema

    conn = init_schema(":memory:")
    yield conn
    conn.close()


def test_null_regime_provider_always_bull():
    p = NullRegimeProvider()
    assert p.get_regime(date.today()) == "bull"


def test_null_regime_provider_any_date():
    p = NullRegimeProvider()
    assert p.get_regime(date(2020, 1, 1)) == "bull"


def test_db_regime_provider_empty_table_returns_bull(duck_conn):
    p = DatabaseRegimeProvider(duck_conn)
    assert p.get_regime(date.today()) == "bull"


def test_db_regime_provider_returns_stored_label(duck_conn):
    duck_conn.execute(
        "INSERT INTO market_regime (date, regime_score, regime_label, ma200_ratio, macro_sentiment)"
        " VALUES ('2024-09-01', 0.8, 'neutral', 1.05, 0.1)"
    )
    p = DatabaseRegimeProvider(duck_conn)
    assert p.get_regime(date(2024, 9, 1)) == "neutral"


def test_db_regime_provider_bear(duck_conn):
    duck_conn.execute(
        "INSERT INTO market_regime (date, regime_score, regime_label, ma200_ratio, macro_sentiment)"
        " VALUES ('2024-09-02', -0.5, 'bear', 0.88, -0.4)"
    )
    p = DatabaseRegimeProvider(duck_conn)
    assert p.get_regime(date(2024, 9, 2)) == "bear"


def test_build_regime_provider_disabled_returns_null(duck_conn):
    p = build_regime_provider(duck_conn, enabled=False)
    assert isinstance(p, NullRegimeProvider)


def test_build_regime_provider_enabled_returns_db(duck_conn):
    p = build_regime_provider(duck_conn, enabled=True)
    assert isinstance(p, DatabaseRegimeProvider)


def test_build_regime_provider_enabled_true_conn_none_raises_value_error():
    with pytest.raises(ValueError):
        build_regime_provider(None, enabled=True)


def test_regime_provider_isinstance_check(duck_conn):
    from kabusys.core.interfaces.regime import RegimeProvider

    p_null = NullRegimeProvider()
    p_db = DatabaseRegimeProvider(duck_conn)
    assert isinstance(p_null, RegimeProvider)
    assert isinstance(p_db, RegimeProvider)
