Keep a Changelog
================

すべての重要な変更はこのファイルに記録します。このプロジェクトは Keep a Changelog の形式に従い、セマンティックバージョニングを採用します。  
詳細: https://keepachangelog.com/ja/1.0.0/ 、セマンティックバージョニング: https://semver.org/lang/ja/

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 2026-03-15

初期リリース

追加
- 新規パッケージ "KabuSys" を追加
  - top-level: src/kabusys/__init__.py
    - パッケージのドキュメンテーション文字列を追加 ("KabuSys - 日本株自動売買システム")
    - パッケージバージョンを定義: __version__ = "0.1.0"
    - 外部公開モジュール一覧を定義: __all__ = ["data", "strategy", "execution", "monitoring"]
  - サブパッケージのプレースホルダを追加（空の __init__.py を含む）
    - src/kabusys/data/__init__.py
    - src/kabusys/strategy/__init__.py
    - src/kabusys/execution/__init__.py
    - src/kabusys/monitoring/__init__.py
  - パッケージ構成を src/ 配下に配置（将来的な開発・ビルドを想定）

ドキュメント
- パッケージの簡易説明を __init__.py に追加（上記ドキュメント文字列）

破壊的変更
- なし

修正
- なし

削除
- なし

注記（移行・利用ガイド）
- インポート例:
  - import kabusys
  - from kabusys import data, strategy, execution, monitoring
  - kabusys.__version__ でバージョン確認可能
- 現状、サブパッケージはプレースホルダであり実際の機能実装は含まれていません。今後のリリースで各モジュールに機能（データ取得、戦略、注文実行、監視など）を追加予定です。

今後の予定
- 各サブパッケージに具体的な実装（API クライアント、戦略フレームワーク、注文実行ラッパー、監視・ロギング機能）を追加
- 単体テスト、ドキュメント、CI/CD を整備
- 公開パッケージ配布（PyPI 等）に向けたセットアップファイルの追加