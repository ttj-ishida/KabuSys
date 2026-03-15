# Changelog

すべての注目すべき変更履歴を記録します。本ファイルは Keep a Changelog の形式に準拠しています。  
安定版のみをここに記載し、日付はリリース日を示します。

※このプロジェクトはバージョン管理下の初期状態に基づく推定的な記載です。コードから推測した内容を反映しています。

## [Unreleased]
（未リリースの変更はここに記載）

## [0.1.0] - 2026-03-15
初回公開

### Added
- パッケージの初期実装を追加
  - src/kabusys/__init__.py
    - パッケージ説明ドキュストリングを追加（"KabuSys - 日本株自動売買システム"）。
    - バージョン番号を設定: `__version__ = "0.1.0"`。
    - 外部公開モジュール一覧を定義: `__all__ = ["data", "strategy", "execution", "monitoring"]`。
  - パッケージ内部の基本モジュール用のパッケージディレクトリを追加（プレースホルダ）
    - src/kabusys/data/__init__.py
    - src/kabusys/strategy/__init__.py
    - src/kabusys/execution/__init__.py
    - src/kabusys/monitoring/__init__.py
  - 以下の責務に対応するモジュール構成を設計・確立
    - data: 市場データや取得・管理ロジック（プレースホルダ）
    - strategy: 売買戦略の実装・管理（プレースホルダ）
    - execution: 注文発行・約定管理（プレースホルダ）
    - monitoring: 稼働監視・ログ・アラート（プレースホルダ）

### Changed
- なし

### Fixed
- なし

### Removed
- なし

---

参照: 初期コミット相当（ファイル構成と最小限のモジュールエクスポートのみ）