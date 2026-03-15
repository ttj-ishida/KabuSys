# Changelog

すべての変更は Keep a Changelog の慣習に従って記録されています。  
このプロジェクトはセマンティックバージョニング (https://semver.org/) を使用します。

## [Unreleased]

特になし

## [0.1.0] - 2026-03-15

### Added
- 初期リリース（スケルトン実装）。
- パッケージ名: `kabusys`。パッケージ docstring に「KabuSys - 日本株自動売買システム」と記載。
- バージョン情報を定義: `__version__ = "0.1.0"`.
- 明示的な公開対象を定義: `__all__ = ["data", "strategy", "execution", "monitoring"]`。
- パッケージ構成（src ディレクトリ内）:
  - `src/kabusys/__init__.py`（パッケージのエントリポイント）
  - サブパッケージのプレースホルダ（各々空の __init__.py を含む）:
    - `src/kabusys/data/__init__.py`
    - `src/kabusys/strategy/__init__.py`
    - `src/kabusys/execution/__init__.py`
    - `src/kabusys/monitoring/__init__.py`
- 全体として、システムは日本株の自動売買を想定したモジュール分割（データ取得、戦略、注文実行、監視）でスケルトンが構成されている。

### Changed
- なし

### Fixed
- なし

### Removed
- なし

---

注意:
- 現リリースはプロジェクトの骨組み（パッケージとモジュールの雛形）に留まります。各サブパッケージ（data, strategy, execution, monitoring）には実装が含まれておらず、今後のリリースで具体的な機能（データ収集、売買戦略、取引実行、監視/ロギングなど）が追加される予定です。