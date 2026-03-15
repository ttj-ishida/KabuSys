# Changelog

すべての注目すべき変更はこのファイルに記録しています。  
このプロジェクトは Keep a Changelog に準拠しています。  
<https://keepachangelog.com/ja/1.0.0/>

## [Unreleased]

## [0.1.0] - 2026-03-15
初回リリース

### 追加
- パッケージ初期スケルトンを追加
  - src/kabusys パッケージを作成
  - パッケージドキュメンテーション（モジュールレベルの docstring）を追加: "KabuSys - 日本株自動売買システム"
  - バージョン情報を追加: `__version__ = "0.1.0"`
  - パブリック API を定義: `__all__ = ["data", "strategy", "execution", "monitoring"]`
- サブパッケージ（プレースホルダ）を追加
  - src/kabusys/data/
  - src/kabusys/strategy/
  - src/kabusys/execution/
  - src/kabusys/monitoring/
  - いずれのサブパッケージも現状は初期化ファイルのみ（実装は未追加）

### 仕様・備考
- ソースは src/ 配下に配置されるレイアウトを採用
- 現時点ではフレームワークの骨組み（モジュール構成と公開 API）のみを提供。各サブパッケージの具体的な機能（データ取得、戦略ロジック、注文実行、監視）は未実装。
- 今後の予定（例）
  - data: 市場データの収集と整形
  - strategy: 売買戦略の実装とバックテスト用インターフェイス
  - execution: 注文送信・約定管理の実装
  - monitoring: ログ・アラート・稼働監視の実装

### 既知の制限
- 実行可能な機能は存在しません（API スケルトンのみ）。ドキュメントに基づく実装追加が必要です。