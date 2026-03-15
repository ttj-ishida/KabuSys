# Changelog

All notable changes to this project will be documented in this file.

このプロジェクトのすべての重要な変更はこのファイルに記録されます。  
このファイルは "Keep a Changelog" の形式に準拠し、セマンティックバージョニングを採用しています。

## [Unreleased]

（現在未リリースの変更はここに記載します）

## [0.1.0] - 2026-03-15

### Added
- 初回公開（ベース実装）
  - パッケージメタ情報を追加
    - `src/kabusys/__init__.py` にパッケージドキュメント文字列とバージョン定義 `__version__ = "0.1.0"` を追加。
    - `__all__ = ["data", "strategy", "execution", "monitoring"]` を定義し、公開APIとして主要サブパッケージを明示。
  - 基本的なパッケージ構成を作成
    - サブパッケージのプレースホルダを追加：
      - `src/kabusys/data/__init__.py`（データ取得・管理用）
      - `src/kabusys/strategy/__init__.py`（売買戦略用）
      - `src/kabusys/execution/__init__.py`（注文実行用）
      - `src/kabusys/monitoring/__init__.py`（モニタリング・ロギング用）
  - 日本株自動売買システム（KabuSys）の初期骨格を整備し、今後の実装拡張の土台を準備。

### Changed
- なし

### Deprecated
- なし

### Removed
- なし

### Fixed
- なし

### Security
- なし

---

注意・補足
- 現在のリポジトリは基本的なパッケージ構造（モジュールのプレースホルダ）を整えた段階です。各サブパッケージ内に具体的な機能（API呼び出し、注文ロジック、データ取得、監視機能など）を実装することで機能が追加されます。
- パッケージの利用例（インポート）：
  - from kabusys import data, strategy, execution, monitoring
- バージョニングはセマンティックバージョニングに従います。将来的に機能追加はマイナーバージョン、破壊的変更はメジャーバージョンの更新として扱います。