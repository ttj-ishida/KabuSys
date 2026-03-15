# Changelog

すべての重要な変更はこのファイルに記録します。  
このプロジェクトはセマンティックバージョニングを採用しています。

フォーマットは Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠しています。

## [Unreleased]

## [0.1.0] - 2026-03-15
### 追加
- 初回リリース: KabuSys — 日本株自動売買システムの骨組みを追加。
- パッケージ構成を追加（src レイアウト）:
  - パッケージルート: `kabusys` (`src/kabusys/__init__.py`)
  - サブパッケージ（空の初期モジュールを含む）:
    - `kabusys.data` (`src/kabusys/data/__init__.py`)
    - `kabusys.strategy` (`src/kabusys/strategy/__init__.py`)
    - `kabusys.execution` (`src/kabusys/execution/__init__.py`)
    - `kabusys.monitoring` (`src/kabusys/monitoring/__init__.py`)
- パッケージメタ情報を追加:
  - `__version__ = "0.1.0"`
  - `__all__ = ["data", "strategy", "execution", "monitoring"]`
- モジュールトップに短いドキュメンテーション文字列（パッケージ説明）を追加。

### 備考
- 各サブパッケージは現時点でプレースホルダ（初期化ファイルのみ）です。今後、データ取得、戦略定義、注文実行、監視機能などを実装予定です。