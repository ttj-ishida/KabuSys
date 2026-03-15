# Changelog

すべての重要な変更はこのファイルに記録されます。

このプロジェクトは Keep a Changelog の形式に従い、セマンティックバージョニングを採用しています。

## [Unreleased]

### 追加
- ここには次回リリースでの変更を記載します。

## [0.1.0] - 2026-03-15

### 追加
- 初回リリース（パッケージ骨組みを追加）
  - パッケージ名: `kabusys`（説明: "KabuSys - 日本株自動売買システム"）
  - バージョン: `0.1.0`（src/kabusys/__init__.py 内の `__version__` を設定）
  - エクスポート: `__all__ = ["data", "strategy", "execution", "monitoring"]`
  - 以下のサブパッケージ（プレースホルダ）を追加:
    - src/kabusys/data/__init__.py
    - src/kabusys/strategy/__init__.py
    - src/kabusys/execution/__init__.py
    - src/kabusys/monitoring/__init__.py
  - 基本的なパッケージ構造とモジュール公開インタフェースを整備し、今後の実装（データ取得、売買戦略、注文実行、監視機能など）に備える

### 注意事項
- 現在各サブパッケージは空の初期化ファイルのみで構成されており、機能実装は今後追加予定です。