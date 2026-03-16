# CHANGELOG

すべての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

全般表記規則:
- 日付はリリース日を示します。
- 各項目は影響範囲（モジュール/機能）と挙動の要点を記載しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-16
初回公開リリース

### 追加 (Added)
- パッケージ基礎
  - パッケージ初期化とバージョン: kabusys v0.1.0 を追加（src/kabusys/__init__.py）。
  - サブパッケージのプレースホルダ: data, strategy, execution, monitoring をエクスポート。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを追加（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサを実装:
    - export KEY=val 形式をサポート。
    - シングル/ダブルクォートとバックスラッシュエスケープに対応。
    - コメントルール（クォートなしで '#' の直前が空白/タブの場合にコメントと扱う）を実装。
  - Settings クラスを導入し、アプリ設定をプロパティ（J-Quants トークン、kabu API 先、Slack トークン/チャンネル、DB パス、環境種別、ログレベルなど）として取得可能に。
  - KABUSYS_ENV と LOG_LEVEL の値検証を追加（許容値のチェック）。env 判定用のユーティリティプロパティ is_live / is_paper / is_dev を追加。

- J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装:
    - 株価日足（OHLCV）、財務諸表（四半期 BS/PL）、JPX マーケットカレンダーを取得する fetch_* 関数を提供。
    - ページネーション対応（pagination_key を扱うループ）。
    - API レート制御: 固定間隔スロットリングの RateLimiter 実装（デフォルト 120 req/min を厳守）。
    - 再試行ロジック: 指数バックオフ、最大 3 回、対象ステータス 408/429/5xx。
    - 401 に対する自動トークンリフレッシュ: 受信時は id_token を 1 回だけリフレッシュして再試行（無限再帰防止の allow_refresh フラグ）。
    - get_id_token: リフレッシュトークンから ID トークンを取得する POST 実装。
    - レスポンスの JSON デコード失敗時に明示的なエラーを投げる。
  - データ永続化ユーティリティ（DuckDB 用）を追加:
    - save_daily_quotes / save_financial_statements / save_market_calendar: ON CONFLICT DO UPDATE を用いた冪等保存を実装。
    - 取得時刻（fetched_at）は UTC（ISO 8601、末尾 Z）で記録して Look‑ahead bias のトレーサビリティを確保。
  - 値変換ユーティリティ _to_float / _to_int を実装（空値と不正値を安全に None にするロジック、"1.0" のような文字列変換を考慮）。

- DuckDB スキーマ定義 (src/kabusys/data/schema.py)
  - DataPlatform 設計に基づく 3 層（Raw / Processed / Feature）＋ Execution 層のテーブル定義を追加。
  - 主なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - インデックスの定義（頻出クエリパターンに基づく複数の CREATE INDEX 文）。
  - init_schema(db_path) により DB ファイルの親ディレクトリを自動作成し、全テーブルとインデックスを作成する初期化関数を提供（冪等）。
  - get_connection(db_path) で既存 DB への接続を取得するヘルパーを追加。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - 日次 ETL の主要フローを実装:
    - run_daily_etl: 市場カレンダー取得 → 株価差分取得（backfill を考慮）→ 財務差分取得 → 品質チェック（オプション）の順で実行。
    - 個別ジョブ: run_calendar_etl / run_prices_etl / run_financials_etl を提供。
  - 差分更新ロジック:
    - DB 側の最終取得日を参照して未取得分のみ取得。date_from を省略した場合は last_date - backfill_days + 1 を採用（デフォルト backfill_days = 3）。
    - 市場カレンダーは先読み（デフォルト lookahead_days = 90）して営業日調整に使用。
  - エラーハンドリング方針:
    - 各ステップは独立して例外を捕捉し、1 ステップの失敗が他ステップの実行を阻害しない（全件収集型）。
  - 実行結果の ETLResult データクラス:
    - 取得数・保存数・品質問題一覧・エラー一覧を保持。品質問題はシリアライズ可能な辞書へ変換可能。

- 監査ログ（トレーサビリティ） (src/kabusys/data/audit.py)
  - シグナル→発注→約定に至る監査テーブルを追加:
    - signal_events（戦略が出したシグナル）
    - order_requests（冪等キー order_request_id を持つ発注要求）
    - executions（証券会社の約定ログ、broker_execution_id をユニークキーとして冪等性を確保）
  - すべての TIMESTAMP は UTC を前提に保存（init_audit_schema は SET TimeZone='UTC' を実行）。
  - 発注・約定に関するステータス列・チェック制約・インデックスを定義。
  - init_audit_schema(conn) / init_audit_db(db_path) を提供。

- データ品質チェック (src/kabusys/data/quality.py)
  - 品質チェックフレームワークを追加（QualityIssue データクラスを含む）。
  - 実装済みチェック:
    - check_missing_data: raw_prices の OHLC 欠損（open/high/low/close）を検出（欠損は error）。
    - check_spike: 前日比スパイク（デフォルト閾値 50%）を検出。LAG ウィンドウを用いた SQL 実装。
  - 各チェックは問題リスト（QualityIssue）を返し、呼び出し元で重大度に応じた対応ができる設計。
  - SQL はパラメータバインドで実行し、効率的にサンプル行と件数を取得。

- その他
  - data パッケージ初期化ファイル（src/kabusys/data/__init__.py）と strategy/execution パッケージ初期化ファイルを追加（将来的な拡張ポイント）。
  - ロギングメッセージを各所に追加し、処理状況や警告を記録。

### 変更 (Changed)
- 初リリースのため該当なし。

### 修正 (Fixed)
- 初リリースのため該当なし。

### 削除 (Removed)
- 初リリースのため該当なし。

### セキュリティ (Security)
- 初リリースのため該当なし。
- 注意: 環境変数/トークンを扱うため、運用時は .env の取り扱いに注意してください。

### マイグレーション / 運用上の注意
- DuckDB 初期化:
  - 初回は data.schema.init_schema(db_path) を実行してスキーマを作成してください。既存 DB に対しては冪等に実行されます。
  - 監査ログテーブルを別に初期化する場合は data.audit.init_audit_db() / init_audit_schema() を使用。
- .env 自動読み込み:
  - パッケージインポート時にプロジェクトルートが検出できる場合、自動で .env/.env.local を読み込みます。テスト等で自動読み込みを抑止したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- タイムゾーン:
  - 取得時刻（fetched_at）および監査ログの TIMESTAMP は UTC を用いるため、出力や表示時は適切に変換してください。
- API レートリミット:
  - J-Quants API はデフォルトで 120 req/min を想定しています。レート制御は固定間隔スロットリングで実装されていますが、運用上の負荷や別制約がある場合は間隔の調整を検討してください。

---

今後の予定（短期ロードマップ）
- strategy / execution 層の具体実装（シグナル生成→発注の統合）
- 追加の品質チェック（重複・将来日付・日付不整合の積極的検出）
- テストカバレッジ強化と CI の追加
- J-Quants クライアントのより細かな rate/backoff 設定の外部化

もし CHANGELOG の表現や項目の粒度で調整したい点があれば指示してください。