# Changelog

すべての注目すべき変更点をここに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。

現在のパッケージバージョン: 0.1.0

## [Unreleased]


## [0.1.0] - 2026-03-16
初回リリース

### 追加 (Added)
- パッケージ骨子を実装
  - パッケージ名: kabusys
  - エクスポート: data, strategy, execution, monitoring

- 設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込み
    - プロジェクトルートを .git または pyproject.toml から探索して .env / .env.local を読み込む実装
    - 読み込みは OS 環境変数を優先し、.env.local が .env を上書きする
    - 自動読み込みを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - .env パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープに対応）
  - 環境変数保護: OS 環境変数は protected として上書きを防止
  - Settings クラスを提供し、アプリで必要な設定をプロパティとして取得
    - 必須設定 (未設定時は ValueError): JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DB パスのデフォルト: DuckDB -> data/kabusys.duckdb、SQLite -> data/monitoring.db
    - 環境モード検証: KABUSYS_ENV (development | paper_trading | live)
    - ログレベル検証: LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)

- J-Quants API クライアント (kabusys.data.jquants_client)
  - データ取得機能:
    - 株価日足（OHLCV）取得（fetch_daily_quotes） — ページネーション対応
    - 財務データ（四半期 BS/PL）取得（fetch_financial_statements） — ページネーション対応
    - JPX マーケットカレンダー取得（fetch_market_calendar）
  - 認証: refresh_token から id_token を取得する get_id_token（POST）
  - HTTP レイヤーの堅牢化:
    - レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）
    - リトライロジック（指数バックオフ、最大 3 回）。対象ステータス: 408/429/5xx
    - 401 レスポンス受信時は自動トークンリフレッシュを 1 回試行
    - ページネーション間で id_token を共有するモジュールキャッシュを実装
  - データ保存（DuckDB 連携）:
    - save_daily_quotes, save_financial_statements, save_market_calendar を提供
    - 挿入は冪等（ON CONFLICT DO UPDATE）で実装
    - fetched_at を UTC ISO フォーマットで記録してトレーサビリティを保持
  - 型変換ユーティリティ: _to_float / _to_int（安全な変換ロジック）

- DuckDB スキーマ管理 (kabusys.data.schema)
  - DataPlatform に基づく多層スキーマ定義を実装
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに必要な制約（PRIMARY KEY / CHECK / FOREIGN KEY）を付与
  - パフォーマンス用インデックス群を定義
  - init_schema(db_path) でデータベース初期化（ディレクトリ自動作成、冪等でテーブル作成）
  - get_connection(db_path) を提供（初期化は行わない）

- ETL パイプライン (kabusys.data.pipeline)
  - 日次 ETL のエントリポイント run_daily_etl を実装
    - 処理順: 市場カレンダー ETL → 株価日足 ETL → 財務データ ETL → 品質チェック
    - 差分更新ロジック: DB の最終取得日から backfill 日数分を遡って再取得（デフォルト backfill_days=3）
    - 市場カレンダーは先読み（デフォルト 90 日）で取得し、営業日調整に利用
    - ページネーションと id_token 注入に対応（テスト容易性考慮）
  - 個別ジョブ: run_prices_etl, run_financials_etl, run_calendar_etl を実装（取得数・保存数を返す）
  - ETL 結果を格納する ETLResult dataclass を提供（品質問題やエラーを収集）
  - 各ステップは独立してエラーハンドリング（1 ステップ失敗でも他は継続）

- 監査ログ（トレーサビリティ） (kabusys.data.audit)
  - トレース用テーブル群を追加
    - signal_events（戦略が生成したシグナルを全て記録）
    - order_requests（冪等キー付きの発注要求ログ）
    - executions（証券会社から返る約定ログ）
  - 監査の設計方針を実装（UUID 連鎖、UTC タイムスタンプ、ON DELETE RESTRICT、created_at/updated_at）
  - init_audit_schema(conn) / init_audit_db(db_path) を提供（UTC タイムゾーンを設定）
  - 監査用インデックス群を定義（status / date / broker_order_id 等の高速検索を想定）

- データ品質チェック (kabusys.data.quality)
  - チェック項目を実装
    - 欠損データ検出（raw_prices の OHLC 欄）
    - スパイク検出（前日比の絶対変動 > threshold; デフォルト 50%）
    - （将来的に重複・日付不整合チェックを追加しやすい構成）
  - QualityIssue dataclass を導入し、各チェックは QualityIssue のリストを返す
  - DuckDB 上で効率的にクエリ実行（パラメータバインド使用）
  - run_all_checks 相当の呼び出し箇所を ETL に組み込み（ETL 側で結果を集約）

### 変更 (Changed)
- （初版のため該当なし）

### 修正 (Fixed)
- （初版のため該当なし）

### セキュリティ (Security)
- 環境変数読み込みの設計により、OS 環境変数が意図せず上書きされないよう保護（protected set）
- トークンやシークレットは Settings 経由で必須項目として扱う（未設定時は明確にエラー）

### 既知の制約 / 注意点 (Notes)
- strategy と execution, monitoring パッケージの __init__ は存在するが、個別の戦略・発注実装はこのリリースでは含まれていない（骨子のみ）。
- API のレート制御は固定間隔スロットリングで実装しているため、極端なスパイクや分散実行時の調整が必要な場合がある。
- DuckDB を利用しているため、並列アクセスや永続化の要件に応じて運用設定を検討すること（ファイルロック等）。
- quality モジュールは主要チェックを実装しているが、必要に応じて追加チェック（重複・未来日付など）を拡張することを想定。
- テストコード・CI 設定はこのリリースに含まれていない。

### マイグレーション / 初期化手順
- DuckDB スキーマ初期化:
  - from kabusys.data.schema import init_schema
  - conn = init_schema(settings.duckdb_path)
- 監査ログ初期化（既存接続に追加）:
  - from kabusys.data.audit import init_audit_schema
  - init_audit_schema(conn)
- 日次 ETL 実行例:
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn)
- 必要な環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - オプション: KABUSYS_ENV, LOG_LEVEL, DUCKDB_PATH, SQLITE_PATH, KABUSYS_DISABLE_AUTO_ENV_LOAD

---

今後の予定（例）
- strategy / execution 層の具体的実装（注文送信、約定処理、ポジション管理）
- 追加の品質チェック（重複検出、日付不整合、ニュース整合性等）
- 単体テスト・統合テストの整備、CI ワークフロー
- モニタリング（Slack 通知等）の実装拡充

--- 

（注）この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノート作成時はリリース担当者による確認・補足を推奨します。