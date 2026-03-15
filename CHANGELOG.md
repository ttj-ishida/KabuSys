# Changelog

すべての重要な変更をここに記録します。本ドキュメントは「Keep a Changelog」の形式に準拠し、セマンティック バージョニングを使用します。

フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-03-15
初回リリース。以下を追加しました。

### 追加
- パッケージ基盤を作成
  - パッケージ名: `kabusys`
  - src レイアウトでの配置（`src/kabusys`）
  - パッケージ説明のトップレベル docstring: "KabuSys - 日本株自動売買システム"
- バージョン情報の追加
  - `src/kabusys/__init__.py` に `__version__ = "0.1.0"` を定義
- サブパッケージ（モジュール）を追加
  - `data`：データ取得・管理用のサブパッケージ（`src/kabusys/data/__init__.py` を作成）
  - `strategy`：売買戦略を実装するためのサブパッケージ（`src/kabusys/strategy/__init__.py` を作成）
  - `execution`：注文発行・約定処理のためのサブパッケージ（`src/kabusys/execution/__init__.py` を作成）
  - `monitoring`：監視・ログ・ステータス管理用のサブパッケージ（`src/kabusys/monitoring/__init__.py` を作成）
- 公開 API の定義
  - `__all__ = ["data", "strategy", "execution", "monitoring"]` を `src/kabusys/__init__.py` に追加し、上記サブパッケージをパッケージ外部に公開

### 注記
- 各サブパッケージの `__init__.py` は作成済みですが、個々の機能実装（クラス・関数・細部のロジック）は含まれていません。今後のリリースで機能追加・実装を行う予定です。