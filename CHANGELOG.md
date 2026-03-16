CHANGELOG
=========
All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and uses Semantic Versioning.

Unreleased
----------
- （今後のリリース候補）小さな改善や追加機能、バグ修正はここに記載します。

[0.1.0] - 2026-03-16
--------------------
Added
- 初回リリース。日本株自動売買システムのコアモジュールを追加。
- パッケージ構成
  - kabusys: パッケージトップ（__version__ = 0.1.0）
  - サブパッケージ: data, strategy, execution, monitoring（出口を定義）
- 環境設定管理（kabusys.config）
  - .env および環境変数から設定を自動読み込み（優先順位: OS 環境 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト向け）。
  - .env パーサは export 構文、シングル／ダブルクォート、エスケープ、インラインコメント処理に対応。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / システム設定をプロパティで取得。
  - KABUSYS_ENV と LOG_LEVEL のバリデーションを実装（有効値チェック）。
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得機能を実装。
  - API レート制御: 固定間隔スロットリング（120 req/min 相当の最小間隔）を導入。
  - 再試行ロジック: 指数バックオフを用いた最大 3 回のリトライ（対象: 408, 429, 5xx、ネットワークエラー等）。
  - 401 Unauthorized 受信時はリフレッシュトークンで id_token を自動更新して 1 回再試行（無限再帰対策あり）。
  - ページネーション対応（pagination_key の処理）とモジュールレベルでの id_token キャッシュ。
  - データ取得時の fetched_at を UTC 形式で記録し、Look-ahead Bias を防止できる設計。
  - DuckDB への保存時は冪等性を担保（ON CONFLICT DO UPDATE）し、PK 欠損行はスキップして警告を出力。
  - 型変換ユーティリティ (_to_float, _to_int) を実装して入力ノイズに耐性を持たせる。
- データスキーマ（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の 3 層（＋監査）に基づく DuckDB スキーマ定義を追加。
  - 各テーブルに適切な型、制約（CHECK、PRIMARY/FOREIGN KEY）を付与。
  - 検索頻度を考慮したインデックスを作成（銘柄×日付、ステータス検索など）。
  - init_schema(db_path) によりディレクトリ作成→DDL実行→インデックス作成を行い、冪等に初期化。
  - get_connection(db_path) を提供（スキーマ初期化は行わない）。
- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL の実装: 市場カレンダー -> 株価日足 -> 財務データ -> 品質チェック のフローを提供。
  - 差分更新のサポート: DB の最終取得日を参照して未取得分のみを取得、デフォルトで過去 N 日分を backfill（デフォルト 3 日）して API 後出し修正を吸収。
  - カレンダーは lookahead（デフォルト 90 日）を指定して先読み取得し営業日調整に利用。
  - run_daily_etl は各ステップを独立してエラーハンドリングし、1 ステップ失敗でも他を継続（失敗は ETLResult に集約）。
  - id_token を注入可能にしてテスト容易性を確保。
  - ETLResult データクラスに取得件数、保存件数、品質問題、エラー要約を含める。
- データ品質チェック（kabusys.data.quality）
  - 標準的な品質チェックを実装:
    - 欠損データ検出（OHLC 欄の必須欠損を error として検出）
    - 異常値検出（前日比スパイク、デフォルト閾値 50%）
    - 重複チェック、日付不整合（将来日付・非営業日データ）等の設計に対応
  - QualityIssue データクラスで問題を抽象化（check_name, table, severity, detail, sample rows）。
  - 複数の問題を収集して返す（Fail-Fast ではなく集計方式）。
- 監査ログ（kabusys.data.audit）
  - シグナル → 発注要求 → 約定のチェーンをトレース可能な監査テーブルを追加（signal_events, order_requests, executions）。
  - order_request_id を冪等キーとして扱い二重発注防止を想定。
  - すべての TIMESTAMP は UTC で保存する運用方針（init_audit_schema で SET TimeZone='UTC' を実行）。
  - 発注種別ごとのチェック制約（limit/stop/market の価格制約）、ステータス遷移を想定した列定義を含む。
  - 関連検索用インデックスも提供。
- 一貫したログ出力
  - 各主要処理で logger を利用して情報・警告・エラーを出力する設計。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Notes / Implementation details
- DuckDB を利用したローカル DB を前提とし、":memory:" を用いたインメモリ接続にも対応。
- SQL 実行時はプレースホルダ（?）を用いる設計思想（インジェクションリスク軽減）。
- 設計ドキュメント（DataPlatform.md, DataSchema.md 等）に基づいた実装注釈がソース内に含まれている（実行・拡張のための設計指針を明示）。
- 将来の改善候補としては、より細かなテストカバレッジ、外部 API のモック化ヘルパー、非同期版の API クライアントなどを想定。

----- 
（補足）
この CHANGELOG はリポジトリ内のコード実装と docstring から推測して作成しています。実際の開発履歴やコミット履歴がある場合はそちらに基づいて更新してください。