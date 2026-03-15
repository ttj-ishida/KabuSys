# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣例に従って管理しています。  
安定版リリースのみをここに記載します。

## [Unreleased]

## [0.1.0] - 2026-03-15
### 追加
- 初期リリースを追加。
- パッケージ `kabusys` を作成（概要: "KabuSys - 日本株自動売買システム"）。
- パッケージのバージョン情報を設定: `__version__ = "0.1.0"`。
- パッケージ外部公開 API を定義: `__all__ = ["data", "strategy", "execution", "monitoring"]`。
- サブパッケージの雛形を追加:
  - `src/kabusys/__init__.py`
  - `src/kabusys/data/__init__.py`
  - `src/kabusys/strategy/__init__.py`
  - `src/kabusys/execution/__init__.py`
  - `src/kabusys/monitoring/__init__.py`
- 上記のサブパッケージは現時点で実装の雛形（空の __init__）となっており、今後それぞれにデータ取得、戦略ロジック、注文執行、監視・ログ等の実装を追加予定。

### 備考
- 初期セットアップ（パッケージ構造と公開 API の定義）に重点を置いたリリースです。今後のリリースで各モジュールの具体的な機能実装、テスト、ドキュメントを順次追加していきます。

[Unreleased]: #  
[0.1.0]: #