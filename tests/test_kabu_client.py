"""KabuStationClient のユニットテスト。httpx をモックして kabu station 不要で実行可能。"""

from __future__ import annotations

from unittest.mock import MagicMock

from kabusys.execution.kabu_client import KabuStationClient


def _make_client(token_json: dict, cash_json: dict) -> KabuStationClient:
    """httpx.Client をモックした KabuStationClient を返す。"""
    mock_token_resp = MagicMock()
    mock_token_resp.status_code = 200
    mock_token_resp.json.return_value = token_json

    mock_cash_resp = MagicMock()
    mock_cash_resp.status_code = 200
    mock_cash_resp.json.return_value = cash_json

    mock_http = MagicMock()
    mock_http.post.return_value = mock_token_resp
    mock_http.get.return_value = mock_cash_resp

    client = KabuStationClient.__new__(KabuStationClient)
    client._api_password = "test_pass"
    client._trade_password = "test_pass"
    client._base_url = "http://localhost:18081/kabusapi"
    client._timeout = 10.0
    client._token = None
    client._client = mock_http

    return client


def test_get_available_cash_returns_zero_when_stock_account_wallet_is_null():
    """検証環境で StockAccountWallet が null のとき 0.0 を返す（TypeError を raise しない）。"""
    client = _make_client(
        {"Token": "test_token"},
        {
            "StockAccountWallet": None,
            "AuKCStockAccountWallet": None,
            "AuJbnStockAccountWallet": None,
        },
    )

    assert client.get_available_cash() == 0.0


def test_get_available_cash_returns_value_when_stock_account_wallet_is_set():
    """本番環境で StockAccountWallet が数値のとき、その値を返す。"""
    client = _make_client(
        {"Token": "test_token"},
        {
            "StockAccountWallet": 1_000_000.0,
            "AuKCStockAccountWallet": 1_000_000.0,
            "AuJbnStockAccountWallet": 0.0,
        },
    )

    assert client.get_available_cash() == 1_000_000.0


def test_get_available_cash_returns_zero_when_stock_account_wallet_key_missing():
    """StockAccountWallet キー自体が存在しないとき 0.0 を返す。"""
    client = _make_client(
        {"Token": "test_token"},
        {"AuKCStockAccountWallet": None, "AuJbnStockAccountWallet": None},
    )

    assert client.get_available_cash() == 0.0
