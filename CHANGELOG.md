# Changelog

すべての注目すべき変更点はこのファイルに記録します。
このプロジェクトは [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に準拠しています。
セマンティックバージョニングを採用します。

## [Unreleased]

## [0.1.0] - 2026-03-15
初回リリース。プロジェクトの骨組み（パッケージスケルトン）を追加しました。

### 追加
- パッケージの初期構成を追加
  - パッケージ名: `kabusys`
  - バージョン: `0.1.0`（`src/kabusys/__init__.py` の `__version__` にて設定）
  - モジュール説明（docstring）: "KabuSys - 日本株自動売買システム"
- サブパッケージ（プレースホルダ）を追加
  - `kabusys.data`（`src/kabusys/data/__init__.py`）
  - `kabusys.strategy`（`src/kabusys/strategy/__init__.py`）
  - `kabusys.execution`（`src/kabusys/execution/__init__.py`）
  - `kabusys.monitoring`（`src/kabusys/monitoring/__init__.py`）
- パッケージ外部公開 API を定義
  - `__all__ = ["data", "strategy", "execution", "monitoring"]` により上記サブパッケージを公開

### 変更
- なし

### 修正
- なし

### 削除
- なし

### セキュリティ
- なし

---

備考:
- 現時点では各サブパッケージは初期ファイル（空の `__init__.py`）のみで、実装は含まれていません。今後、データ取得/管理（data）、取引戦略（strategy）、注文実行（execution）、監視/ロギング（monitoring）などの機能を順次実装する予定です。