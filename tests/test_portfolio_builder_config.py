"""tests/test_portfolio_builder_config.py — load_portfolio_config() のテスト"""

from __future__ import annotations


class TestLoadPortfolioConfig:
    def test_returns_default_when_no_file(self, tmp_path, monkeypatch):
        """strategy_config.yaml が存在しない場合はデフォルト値を返す。"""
        from kabusys.portfolio import portfolio_builder

        monkeypatch.setattr(portfolio_builder, "_PORTFOLIO_CONFIG_PATH", tmp_path / "no_such.yaml")
        result = portfolio_builder.load_portfolio_config()
        assert result["max_positions"] == 10

    def test_reads_max_positions_from_yaml(self, tmp_path, monkeypatch):
        """portfolio.max_positions を yaml から読み込む。"""
        import yaml

        from kabusys.portfolio import portfolio_builder

        cfg_file = tmp_path / "strategy_config.yaml"
        cfg_file.write_text(yaml.dump({"portfolio": {"max_positions": 15}}), encoding="utf-8")
        monkeypatch.setattr(portfolio_builder, "_PORTFOLIO_CONFIG_PATH", cfg_file)
        result = portfolio_builder.load_portfolio_config()
        assert result["max_positions"] == 15

    def test_falls_back_on_invalid_type(self, tmp_path, monkeypatch):
        """max_positions が文字列の場合はデフォルト 10 にフォールバックする。"""
        import yaml

        from kabusys.portfolio import portfolio_builder

        cfg_file = tmp_path / "strategy_config.yaml"
        cfg_file.write_text(yaml.dump({"portfolio": {"max_positions": "ten"}}), encoding="utf-8")
        monkeypatch.setattr(portfolio_builder, "_PORTFOLIO_CONFIG_PATH", cfg_file)
        result = portfolio_builder.load_portfolio_config()
        assert result["max_positions"] == 10

    def test_falls_back_when_max_positions_below_minimum(self, tmp_path, monkeypatch):
        """max_positions が 1 未満（0 以下）の場合はデフォルト 10 にフォールバックする。"""
        import yaml

        from kabusys.portfolio import portfolio_builder

        cfg_file = tmp_path / "strategy_config.yaml"
        cfg_file.write_text(yaml.dump({"portfolio": {"max_positions": 0}}), encoding="utf-8")
        monkeypatch.setattr(portfolio_builder, "_PORTFOLIO_CONFIG_PATH", cfg_file)
        result = portfolio_builder.load_portfolio_config()
        assert result["max_positions"] == 10

    def test_falls_back_when_portfolio_section_missing(self, tmp_path, monkeypatch):
        """portfolio セクションが存在しない場合はデフォルト 10 を返す。"""
        import yaml

        from kabusys.portfolio import portfolio_builder

        cfg_file = tmp_path / "strategy_config.yaml"
        cfg_file.write_text(yaml.dump({"strategy": {"threshold": 0.6}}), encoding="utf-8")
        monkeypatch.setattr(portfolio_builder, "_PORTFOLIO_CONFIG_PATH", cfg_file)
        result = portfolio_builder.load_portfolio_config()
        assert result["max_positions"] == 10

    def test_max_positions_one_is_valid(self, tmp_path, monkeypatch):
        """max_positions = 1 は有効な最小値として受け入れられる。"""
        import yaml

        from kabusys.portfolio import portfolio_builder

        cfg_file = tmp_path / "strategy_config.yaml"
        cfg_file.write_text(yaml.dump({"portfolio": {"max_positions": 1}}), encoding="utf-8")
        monkeypatch.setattr(portfolio_builder, "_PORTFOLIO_CONFIG_PATH", cfg_file)
        result = portfolio_builder.load_portfolio_config()
        assert result["max_positions"] == 1

    def test_returns_dict(self, tmp_path, monkeypatch):
        """戻り値は dict である。"""
        from kabusys.portfolio import portfolio_builder

        monkeypatch.setattr(portfolio_builder, "_PORTFOLIO_CONFIG_PATH", tmp_path / "no_such.yaml")
        result = portfolio_builder.load_portfolio_config()
        assert isinstance(result, dict)
        assert "max_positions" in result

    def test_integer_valued_float_is_accepted(self, tmp_path, monkeypatch):
        """max_positions = 10.0（整数値の float）は有効として受け入れる。"""
        import yaml

        from kabusys.portfolio import portfolio_builder

        cfg_file = tmp_path / "strategy_config.yaml"
        cfg_file.write_text(yaml.dump({"portfolio": {"max_positions": 10.0}}), encoding="utf-8")
        monkeypatch.setattr(portfolio_builder, "_PORTFOLIO_CONFIG_PATH", cfg_file)
        result = portfolio_builder.load_portfolio_config()
        assert result["max_positions"] == 10

    def test_non_integer_float_falls_back(self, tmp_path, monkeypatch):
        """max_positions = 10.5（非整数 float）はデフォルト 10 にフォールバックする。"""
        import yaml

        from kabusys.portfolio import portfolio_builder

        cfg_file = tmp_path / "strategy_config.yaml"
        cfg_file.write_text(yaml.dump({"portfolio": {"max_positions": 10.5}}), encoding="utf-8")
        monkeypatch.setattr(portfolio_builder, "_PORTFOLIO_CONFIG_PATH", cfg_file)
        result = portfolio_builder.load_portfolio_config()
        assert result["max_positions"] == 10

    def test_falls_back_when_portfolio_is_list(self, tmp_path, monkeypatch):
        """portfolio セクションが list の場合はデフォルト 10 にフォールバックする。"""
        import yaml

        from kabusys.portfolio import portfolio_builder

        cfg_file = tmp_path / "strategy_config.yaml"
        cfg_file.write_text(yaml.dump({"portfolio": [10]}), encoding="utf-8")
        monkeypatch.setattr(portfolio_builder, "_PORTFOLIO_CONFIG_PATH", cfg_file)
        result = portfolio_builder.load_portfolio_config()
        assert result["max_positions"] == 10

    def test_falls_back_when_max_positions_is_bool(self, tmp_path, monkeypatch):
        """max_positions が bool の場合はデフォルト 10 にフォールバックする。"""
        import yaml

        from kabusys.portfolio import portfolio_builder

        cfg_file = tmp_path / "strategy_config.yaml"
        cfg_file.write_text(yaml.dump({"portfolio": {"max_positions": True}}), encoding="utf-8")
        monkeypatch.setattr(portfolio_builder, "_PORTFOLIO_CONFIG_PATH", cfg_file)
        result = portfolio_builder.load_portfolio_config()
        assert result["max_positions"] == 10

    def test_falls_back_when_yaml_root_is_not_dict(self, tmp_path, monkeypatch):
        """YAML ルートが dict でない場合（例: リスト）はデフォルト 10 にフォールバックする。"""
        from kabusys.portfolio import portfolio_builder

        cfg_file = tmp_path / "strategy_config.yaml"
        cfg_file.write_text("- item1\n- item2\n", encoding="utf-8")
        monkeypatch.setattr(portfolio_builder, "_PORTFOLIO_CONFIG_PATH", cfg_file)
        result = portfolio_builder.load_portfolio_config()
        assert result["max_positions"] == 10


class TestLoadPortfolioSizingConfig:
    """Issue #437: 資金配分（配分方式・1 銘柄上限・投資割合の上限）も設定ファイルから読む。"""

    def _load(self, tmp_path, portfolio):
        import yaml

        from kabusys.portfolio import portfolio_builder

        cfg_file = tmp_path / "strategy_config.yaml"
        cfg_file.write_text(yaml.dump({"portfolio": portfolio}), encoding="utf-8")
        return portfolio_builder.load_portfolio_config(cfg_file)

    def test_reads_all_keys(self, tmp_path):
        r = self._load(
            tmp_path,
            {
                "allocation_method": "equal",
                "max_positions": 3,
                "max_position_pct": 0.34,
                "max_utilization": 0.5,
                "risk_pct": 0.01,
            },
        )
        assert r == {
            "allocation_method": "equal",
            "max_positions": 3,
            "max_position_pct": 0.34,
            "max_utilization": 0.5,
            "risk_pct": 0.01,
        }

    def test_invalid_values_fall_back_per_key(self, tmp_path):
        from kabusys.portfolio.portfolio_builder import DEFAULT_PORTFOLIO_CONFIG

        r = self._load(
            tmp_path,
            {
                "allocation_method": "magic",
                "max_positions": 3,
                "max_position_pct": 1.5,
                "max_utilization": 0,
                "risk_pct": True,
            },
        )
        assert r["max_positions"] == 3
        for key in ("allocation_method", "max_position_pct", "max_utilization", "risk_pct"):
            assert r[key] == DEFAULT_PORTFOLIO_CONFIG[key]

    def test_repo_config_is_valid(self):
        """リポジトリの strategy_config.yaml は案 A（均等・7 銘柄・10%・70%、Issue #430）。"""
        from kabusys.portfolio.portfolio_builder import load_portfolio_config

        r = load_portfolio_config()
        assert r["allocation_method"] == "equal"
        assert r["max_positions"] == 7
        assert r["max_position_pct"] == 0.10
        assert r["max_utilization"] == 0.70


class TestApplyHoldingLimits:
    """Issue #437: 保有銘柄数・投資割合の上限を保有全体にかける。"""

    @staticmethod
    def _c(*codes):
        return [
            {"code": c, "score": 1.0 - i * 0.1, "signal_rank": i + 1} for i, c in enumerate(codes)
        ]

    def test_new_slots_reduced_by_holdings(self):
        from kabusys.portfolio.portfolio_builder import apply_holding_limits

        cands, cash = apply_holding_limits(
            self._c("A", "B", "C"),
            {"X": 100, "Y": 100},
            {"X": 1000.0, "Y": 1000.0},
            portfolio_value=1_000_000,
            available_cash=800_000,
            max_positions=3,
            max_utilization=0.5,
        )
        assert [c["code"] for c in cands] == ["A"]
        # 50 万円 − 保有 20 万円 = 30 万円
        assert cash == 300_000

    def test_full_holdings_leave_no_new_candidates(self):
        from kabusys.portfolio.portfolio_builder import apply_holding_limits

        cands, _ = apply_holding_limits(
            self._c("A", "X"),
            {"X": 100, "Y": 100, "Z": 100},
            {"X": 100.0, "Y": 100.0, "Z": 100.0},
            portfolio_value=1_000_000,
            available_cash=900_000,
            max_positions=3,
            max_utilization=0.5,
        )
        # 保有中の X（買い増し）は枠を使わないので残る
        assert [c["code"] for c in cands] == ["X"]

    def test_cash_capped_by_utilization_room_and_never_negative(self):
        from kabusys.portfolio.portfolio_builder import apply_holding_limits

        _, cash = apply_holding_limits(
            self._c("A"),
            {"X": 600},
            {"X": 1000.0},
            portfolio_value=1_000_000,
            available_cash=400_000,
            max_positions=3,
            max_utilization=0.5,
        )
        assert cash == 0.0

    def test_sell_codes_free_slots_and_are_not_candidates(self):
        from kabusys.portfolio.portfolio_builder import apply_holding_limits

        cands, cash = apply_holding_limits(
            self._c("X", "A", "B"),
            {"X": 300, "Y": 100},
            {"X": 1000.0, "Y": 1000.0},
            portfolio_value=1_000_000,
            available_cash=900_000,
            max_positions=3,
            max_utilization=0.5,
            sell_codes={"X"},
        )
        assert [c["code"] for c in cands] == ["A", "B"]
        assert cash == 400_000

    def test_missing_price_of_holding_blocks_new_buys(self):
        from kabusys.portfolio.portfolio_builder import apply_holding_limits

        cands, cash = apply_holding_limits(
            self._c("A"),
            {"X": 100},
            {},
            portfolio_value=1_000_000,
            available_cash=900_000,
            max_positions=3,
            max_utilization=0.5,
        )
        assert cands == [] and cash == 0.0
