# Changelog

すべての重要な変更をここに記録します。本ファイルは「Keep a Changelog」の形式に従い、セマンティックバージョニングを採用します。  
詳細: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-03-15
### 追加
- 初期リリース: KabuSys — 日本株自動売買システムの骨組みを作成。
- パッケージメタ情報を追加（src/kabusys/__init__.py）
  - __version__ = "0.1.0" を設定。
  - __all__ に公開するサブパッケージ ["data", "strategy", "execution", "monitoring"] を定義。
  - モジュールの簡単なモジュールドキュメント文字列を追加。
- サブパッケージを作成（プレースホルダとしての __init__.py を配置）
  - src/kabusys/data/__init__.py
  - src/kabusys/strategy/__init__.py
  - src/kabusys/execution/__init__.py
  - src/kabusys/monitoring/__init__.py
- リポジトリ構造の初期整備（パッケージの骨格のみ。各サブパッケージは現時点で実装未着手でプレースホルダファイルのみ存在）。

### 変更
- なし

### 修正
- なし

### セキュリティ
- なし

## 注記
- 本バージョンはパッケージ構造と公開インターフェースの初期定義に重点を置いており、実際のデータ取得、売買戦略、注文実行、監視ロジックは未実装です。今後のリリースで各サブパッケージに機能を追加していきます。