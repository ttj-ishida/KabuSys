"""param_extractor 単体テスト（Issue #279）"""

from __future__ import annotations

from kabusys.ai.param_extractor import extract_params


class TestExtractParams:
    def test_valid_json_block_returns_dict(self):
        text = 'おすすめです。\n```json\n{"threshold": 0.65}\n```'
        result = extract_params(text)
        assert result == {"threshold": 0.65}

    def test_no_json_block_returns_none(self):
        assert extract_params("パラメータは据え置きで良いです。") is None

    def test_invalid_json_returns_none(self):
        text = "```json\n{invalid}\n```"
        assert extract_params(text) is None

    def test_whitelist_only_violation_returns_none(self):
        text = '```json\n{"db_path": "/data/db"}\n```'
        assert extract_params(text) is None

    def test_mixed_keys_removes_violation_keeps_valid(self):
        text = '```json\n{"threshold": 0.65, "db_path": "/data/db"}\n```'
        result = extract_params(text)
        assert result == {"threshold": 0.65}
        assert "db_path" not in result

    def test_unknown_weight_key_excluded(self):
        text = '```json\n{"weights": {"unknown_factor": 0.5, "momentum": 0.45}}\n```'
        result = extract_params(text)
        assert result == {"weights": {"momentum": 0.45}}

    def test_value_out_of_range_excluded(self):
        # threshold must be 0.0〜1.0; 1.5 is out of range
        text = '```json\n{"threshold": 1.5, "sector_boost": 0.03}\n```'
        result = extract_params(text)
        assert result == {"sector_boost": 0.03}
        assert "threshold" not in result

    def test_last_block_used_when_multiple_blocks(self):
        text = (
            '```json\n{"threshold": 0.55}\n```\n'
            "詳細は以下の通りです。\n"
            '```json\n{"threshold": 0.65}\n```'
        )
        result = extract_params(text)
        assert result == {"threshold": 0.65}

    def test_negative_stop_loss_rate_valid(self):
        text = '```json\n{"stop_loss_rate": -0.08}\n```'
        result = extract_params(text)
        assert result == {"stop_loss_rate": -0.08}

    def test_positive_stop_loss_rate_excluded(self):
        text = '```json\n{"stop_loss_rate": 0.08}\n```'
        assert extract_params(text) is None

    def test_weights_dict_parsed_correctly(self):
        text = '```json\n{"weights": {"momentum": 0.45, "value": 0.25}}\n```'
        result = extract_params(text)
        assert result == {"weights": {"momentum": 0.45, "value": 0.25}}

    def test_empty_weights_dict_excluded(self):
        text = '```json\n{"weights": {}}\n```'
        assert extract_params(text) is None

    def test_int_values_for_holding_days(self):
        text = '```json\n{"min_holding_days": 3, "max_holding_days": 30}\n```'
        result = extract_params(text)
        assert result == {"min_holding_days": 3, "max_holding_days": 30}
        assert isinstance(result["min_holding_days"], int)

    def test_bool_weight_value_excluded(self):
        # bool は int のサブクラスだが weight 値として許可しない
        text = '```json\n{"weights": {"momentum": true, "value": 0.25}}\n```'
        result = extract_params(text)
        assert result == {"weights": {"value": 0.25}}
        assert "momentum" not in result["weights"]

    def test_float_holding_days_excluded(self):
        # min_holding_days は整数のみ許可; 小数点以下がある float は除外
        text = '```json\n{"min_holding_days": 3.7, "max_holding_days": 30}\n```'
        result = extract_params(text)
        assert result == {"max_holding_days": 30}
        assert "min_holding_days" not in result

    def test_whole_float_holding_days_accepted(self):
        # 小数点以下が 0 の float (例: 3.0) は整数として許可
        text = '```json\n{"min_holding_days": 3.0}\n```'
        result = extract_params(text)
        assert result == {"min_holding_days": 3}
        assert isinstance(result["min_holding_days"], int)
