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
