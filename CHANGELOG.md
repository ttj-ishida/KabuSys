# CHANGELOG

すべての重要な変更をこのファイルに記録します。
形式は「Keep a Changelog」（https://keepachangelog.com/ja/1.0.0/）準拠です。
このプロジェクトはセマンティックバージョニングを使用します。

## [Unreleased]
- 開発中の変更や機能追加はここに記載してください。

## [0.1.0] - 2026-03-15
最初の公開リリース。

### 追加
- 新規パッケージ "kabusys" を追加。
  - パッケージ説明: "KabuSys - 日本株自動売買システム"（src/kabusys/__init__.py のモジュールドキュメンテーション文字列）。
  - パッケージバージョンを定義: `__version__ = "0.1.0"`。
  - パッケージの公開 API を定義: `__all__ = ["data", "strategy", "execution", "monitoring"]`。
- 基本モジュール構成を追加（いずれも初期プレースホルダファイルとして作成）。
  - src/kabusys/data/__init__.py
  - src/kabusys/strategy/__init__.py
  - src/kabusys/execution/__init__.py
  - src/kabusys/monitoring/__init__.py

### 変更
- 該当なし（新規作成のため）。

### 修正
- 該当なし。

### 非推奨
- 該当なし。

### 削除
- 該当なし。

### セキュリティ
- 該当なし。

---

備考:
- 現状の各サブパッケージ（data、strategy、execution、monitoring）は初期プレースホルダで、今後具体的な機能（データ取得／前処理、売買戦略、注文実行、監視・ロギング等）を実装していく予定です。
- 次回リリースでは各サブパッケージの実装詳細・APIをCHANGELOGの「Added」や「Changed」に追記してください。