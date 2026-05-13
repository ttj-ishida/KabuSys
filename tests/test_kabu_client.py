"""KabuStationClient のユニットテスト。httpx をモックして kabu station 不要で実行可能。"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from kabusys.execution.kabu_client import KabuStationClient


def _make_client(token_json: dict, cash_json: dict) -> KabuStationClient:
    """httpx.Client をモックした KabuStationClient を返す。"""
    mock_token_resp = MagicMock()
    mock_token_resp.status_code = 200
    mock_token_resp.json.return_value = token_json

    mock_cash_resp = MagicMock()
    mock_cash_resp.status_code = 200
    mock_cash_resp.json.return_value = cash_json

    with patch("kabusys.execution.kabu_client.httpx.Client") as mock_cls:
        mock_http = MagicMock()
        mock_cls.return_value = mock_http
        mock_http.post.return_value = mock_token_resp
        mock_http.get.return_value = mock_cash_resp
        client = KabuStationClient.__new__(KabuStationClient)
        client._api_password = "test_pass"
        client._trade_password = "test_pass"
        client._base_url = "http://localhost:18081/kabusapi"
        client._timeout = 10.0
        client._token = None
        client._client = mock_http

    return client, mock_http, mock_token_resp, mock_cash_resp


def test_get_available_cash_returns_zero_when_stock_account_wallet_is_null():
    """検証環境で StockAccountWallet が null のとき 0.0 を返す（TypeError を raise しない）。"""
    token_json = {"Token": "test_token"}
    cash_json = {
        "StockAccountWallet": None,
        "AuKCStockAccountWallet": None,
        "AuJbnStockAccountWallet": None,
    }
    client, _, _, _ = _make_client(token_json, cash_json)

    result = client.get_available_cash()

    assert result == 0.0


def test_get_available_cash_returns_value_when_stock_account_wallet_is_set():
    """本番環境で StockAccountWallet が数値のとき、その値を返す。"""
    token_json = {"Token": "test_token"}
    cash_json = {
        "StockAccountWallet": 1_000_000.0,
        "AuKCStockAccountWallet": 1_000_000.0,
        "AuJbnStockAccountWallet": 0.0,
    }
    client, _, _, _ = _make_client(token_json, cash_json)

    result = client.get_available_cash()

    assert result == 1_000_000.0
