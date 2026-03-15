Keep a Changelog
=================

すべての注目すべき変更をバージョンごとに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（現在未リリースの変更はここに記載します）

0.1.0 - 2026-03-15
-----------------

Added
- 初回リリース: Python パッケージ "kabusys" を公開。
  - パッケージのトップレベル docstring を追加（"KabuSys - 日本株自動売買システム"）。
  - バージョン情報を定義: `__version__ = "0.1.0"`。
  - 外部公開 API を定義: `__all__ = ["data", "strategy", "execution", "monitoring"]`。
- プロジェクト構成（src/kabusys）を作成し、以下のサブパッケージ骨組みを準備:
  - data: 市場データの取得・管理に関する処理を実装するためのプレースホルダ（`src/kabusys/data/__init__.py`）。
  - strategy: 売買ロジック（アルゴリズム・シグナル生成）を実装するためのプレースホルダ（`src/kabusys/strategy/__init__.py`）。
  - execution: 注文送信やブローカーAPI連携を行うためのプレースホルダ（`src/kabusys/execution/__init__.py`）。
  - monitoring: システム状態・ポジション・ログ等の監視用処理を実装するためのプレースホルダ（`src/kabusys/monitoring/__init__.py`）。
- ソース配置ポリシー: パッケージは src/ 配下に配置。

Changed
- 該当なし（初版のため）

Fixed
- 該当なし（初版のため）

Removed
- 該当なし（初版のため）

Deprecated
- 該当なし（初版のため）

Security
- 該当なし（初版のため）

注記
- 本リリースは主にプロジェクトの骨組み（スケルトン）を整える目的です。各サブパッケージは今後のリリースで具体的な機能（データ取得、戦略実装、注文実行、監視・アラート等）を追加していきます。