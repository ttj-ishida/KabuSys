CHANGELOG
=========

すべての重要な変更をここに記録します。
このファイルは「Keep a Changelog」形式に準拠しています。
https://keepachangelog.com/ja/1.0.0/

フォーマットは意味的に安定した変更履歴を提供することを目的としています。

Unreleased
----------

（現在のところ未リリースの変更はありません）

[0.1.0] - 2026-03-15
-------------------

初回公開リリース。日本株自動売買システム「KabuSys」のパッケージ雛形を追加しました。

Added
- パッケージ基本情報
  - src/kabusys/__init__.py を追加
    - パッケージの説明ドキュストリング（"KabuSys - 日本株自動売買システム"）
    - バージョン番号を __version__ = "0.1.0" として設定
    - 公開APIのシンボルとして __all__ = ["data", "strategy", "execution", "monitoring"] を定義
- サブパッケージ（プレースホルダ）
  - src/kabusys/data/__init__.py
  - src/kabusys/strategy/__init__.py
  - src/kabusys/execution/__init__.py
  - src/kabusys/monitoring/__init__.py
  - 各サブパッケージは現時点ではモジュール構造（パッケージ階層）のみを提供し、今後の実装のための土台を構築

Changed
- なし

Fixed
- なし

Security
- なし

備考
- 本リリースは骨組み（スケルトン）段階の公開です。各サブパッケージ（data, strategy, execution, monitoring）には今後、データ取得・戦略ロジック・注文実行・監視機能などの具体的実装を追加予定です。