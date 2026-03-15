# Keep a Changelog
すべての重要な変更はこのファイルに記録します。
このプロジェクトは [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の原則に従います。
Semantic Versioning を採用しています（https://semver.org/）。

## 変更履歴

### 未リリース
- （現在のところ未公開の変更はありません）

### 0.1.0 - 2026-03-15
初回リリース。パッケージの骨組み（スケルトン）を追加しました。

追加 (Added)
- パッケージ "kabusys" を新規作成
  - 概要: "KabuSys - 日本株自動売買システム"（パッケージのトップレベル docstring）
  - バージョン情報を持つ: `__version__ = "0.1.0"`
  - 公開 API を定義: `__all__ = ["data", "strategy", "execution", "monitoring"]`
- サブパッケージ（空の初期化ファイルを含む）を追加
  - `kabusys.data` - データ取得/管理用モジュール（将来的に株価・板情報・指標の取得処理を想定）
  - `kabusys.strategy` - 売買戦略定義用モジュール（戦略の実装・評価を想定）
  - `kabusys.execution` - 注文執行/API連携用モジュール（発注・約定管理を想定）
  - `kabusys.monitoring` - 監視/ログ・メトリクス用モジュール（稼働監視やアラートを想定）
- プロジェクトの最小構成（パッケージ初期化のみ）をコミット
  - ファイル構成（主なファイル）
    - src/kabusys/__init__.py
    - src/kabusys/data/__init__.py
    - src/kabusys/strategy/__init__.py
    - src/kabusys/execution/__init__.py
    - src/kabusys/monitoring/__init__.py

変更 (Changed)
- なし（初回リリースのため）

修正 (Fixed)
- なし

削除 (Removed)
- なし

セキュリティ (Security)
- なし

備考 / 開発者向けメモ
- 現時点では各サブパッケージは初期化ファイルのみで実装は未着手です。今後、次のような機能実装を予定しています:
  - data: 市場データ取得、キャッシュ、前処理
  - strategy: 戦略インターフェース、バックテスト用ユーティリティ
  - execution: 証券会社/取引APIとの接続、注文管理、例外ハンドリング
  - monitoring: ロギング、メトリクス収集、アラート送信
- バージョンはパッケージ内部の `__version__` で管理しています。API互換性や機能追加に応じてセマンティックバージョニングに従って更新してください。