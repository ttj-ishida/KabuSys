# Changelog

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の原則に従います。  
セマンティック バージョニングを使用します。

## Unreleased
（現在未リリースの変更はありません）

## [0.1.0] - 2026-03-15
初回リリース。プロジェクトの骨組み（スケルトン）を追加。

### Added
- パッケージ `kabusys` を追加。
  - ファイル: `src/kabusys/__init__.py`
  - パッケージ説明（docstring）: "KabuSys - 日本株自動売買システム"
  - バージョン定義: `__version__ = "0.1.0"`
  - 公開インターフェース定義: `__all__ = ["data", "strategy", "execution", "monitoring"]`
- サブパッケージのスケルトンを追加（プレースホルダとして空の `__init__.py` を配置）。
  - `src/kabusys/data/__init__.py`
  - `src/kabusys/strategy/__init__.py`
  - `src/kabusys/execution/__init__.py`
  - `src/kabusys/monitoring/__init__.py`
- パッケージの基本的なディレクトリ構成を確立し、以降の機能実装（データ取得、戦略、約定、監視など）の基盤を提供。

### Changed
- なし

### Fixed
- なし

### Removed
- なし

### Deprecated
- なし

### Security
- なし

注記:
- 現在は骨組みのみであり、各サブパッケージは将来的に機能を追加するためのプレースホルダです。APIはまだ安定していないため、今後のリリースで変更される可能性があります。