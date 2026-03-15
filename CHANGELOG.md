# Changelog

すべての重要な変更はこのファイルに記録します。本ファイルは「Keep a Changelog」仕様に準拠しています。
このプロジェクトはセマンティック バージョニングを使用します。詳細は https://semver.org/ を参照してください。

## [Unreleased]

## [0.1.0] - 2026-03-15
初回リリース。日本株自動売買システム「KabuSys」の基本パッケージ構成を追加しました。

### 追加
- パッケージ初期化ファイルを追加
  - src/kabusys/__init__.py
    - パッケージドキュメンテーション文字列 ("KabuSys - 日本株自動売買システム") を設定。
    - バージョン情報 `__version__ = "0.1.0"` を定義。
    - 外部公開モジュールとして `__all__ = ["data", "strategy", "execution", "monitoring"]` を定義。
- サブパッケージのスケルトンを追加（空の初期化ファイル）
  - src/kabusys/data/__init__.py
  - src/kabusys/strategy/__init__.py
  - src/kabusys/execution/__init__.py
  - src/kabusys/monitoring/__init__.py

### 変更
- 該当なし

### 修正
- 該当なし

### 非推奨
- 該当なし

### 削除
- 該当なし

---

このリリースはプロジェクトの骨組み（パッケージ構成と公開APIのエントリポイント）を提供します。今後のリリースで各サブパッケージ（データ取得/管理、ストラテジー実装、注文実行、監視/ログ等）の具体的実装を追加していきます。