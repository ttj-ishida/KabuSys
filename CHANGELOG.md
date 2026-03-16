# Changelog

すべての変更は Keep a Changelog の形式に従い、重要度ごとに分類しています。  
このファイルはコードベースからの実装内容を元に推測して作成した初期の変更履歴です。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-16

### Added
- パッケージ初期リリース: kabusys 0.1.0
  - モジュール構造:
    - kabusys (パッケージ初期化: __version__ = "0.1.0")
    - data: データ取得・スキーマ・ETL・品質・監査関連
    - strategy: 戦略用パッケージ（初期プレースホルダ）
    - execution: 発注/実行関連パッケージ（初期プレースホルダ）
    - monitoring: 監視用（エクスポートは __all__ に含む）

- 環境設定管理 (`kabusys.config`)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダー実装
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - プロジェクトルート検出: .git または pyproject.toml を起点に検索（__file__ ベース）
    - 自動ロードの無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能
  - .env パーサーの実装（`_parse_env_line`）
    - export プレフィックス対応（export KEY=val）
    - シングル/ダブルクォートのエスケープ対応
    - インラインコメント処理（クォートあり/なしの違いを考慮）
  - .env 読み込みの上書き制御（override / protected）
  - Settings クラスを公開 (`settings`)。主要設定プロパティを提供:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - ヘルパー: is_live / is_paper / is_dev

- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - 基本設計: レート制限、リトライ、トークン自動リフレッシュ、ページネーション、取得時刻（fetched_at）保存、DuckDB への冪等保存を考慮
  - レート制限: 固定間隔スロットリング実装（120 req/min → min_interval = 60/120 = 0.5s）
  - リトライポリシー:
    - 最大試行回数: 3 回
    - 指数バックオフ（base 2.0 秒）
    - HTTP ステータス 408/429 および 5xx を再試行対象
    - 429 の場合は Retry-After ヘッダを尊重
  - 401 (Unauthorized) を受けた場合、自動でリフレッシュトークンを使って id_token を再取得し 1 回リトライ（無限再帰防止）
  - トークンキャッシュ（モジュールレベル）を実装し、ページネーション呼び出し間で共有
  - API 呼び出しユーティリティ `_request` 実装（GET/POST、JSON body、デコード検査）
  - データ取得関数（ページネーション対応）:
    - fetch_daily_quotes: 株価日足（OHLCV）
    - fetch_financial_statements: 四半期財務データ
    - fetch_market_calendar: JPX マーケットカレンダー
  - DuckDB へ保存する冪等的関数:
    - save_daily_quotes: raw_prices に INSERT ... ON CONFLICT DO UPDATE
      - fetched_at を UTC ISO 形式で記録（末尾は "Z"）
      - PK（date, code）欠損行はスキップしログ出力
    - save_financial_statements: raw_financials に保存（ON CONFLICT DO UPDATE）
    - save_market_calendar: market_calendar に保存（ON CONFLICT DO UPDATE）
  - 値変換ユーティリティ:
    - _to_float / _to_int（空値・不正値を None に落とす、安全な int 変換）

- DuckDB スキーマ定義と初期化 (`kabusys.data.schema`)
  - DataPlatform 構造に基づく多層スキーマを定義:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに制約（NOT NULL / CHECK / PRIMARY KEY / FOREIGN KEY）を定義
  - 頻出クエリ向けインデックス群を定義（例: code×date、status 検索など）
  - init_schema(db_path) を提供:
    - 指定パスの親ディレクトリを自動作成（":memory:" を許容）
    - 全テーブルとインデックスを作成（冪等）
  - get_connection(db_path) を提供（既存 DB への接続、初期化は行わない）

- ETL パイプライン (`kabusys.data.pipeline`)
  - ETL の設計方針とワークフローを実装:
    - 差分更新: DB の最終取得日を基に再取得範囲を計算（バックフィルで後出し修正を吸収）
    - 保存: jquants_client の save_* 関数を利用して冪等保存
    - 品質チェック: quality モジュールを呼び出し、問題は収集して返す（Fail-Fast ではない）
  - 定数:
    - 最小データ日: 2017-01-01
    - カレンダー先読み: デフォルト 90 日
    - バックフィル日数: デフォルト 3 日
  - ETLResult データクラスを追加（取得数/保存数/品質問題/エラー一覧を保持）
  - 差分取得ユーティリティ:
    - get_last_price_date / get_last_financial_date / get_last_calendar_date
  - 個別 ETL ジョブ:
    - run_prices_etl: 株価差分 ETL（date_from 自動算出、backfill 対応）
    - run_financials_etl: 財務差分 ETL（同上）
    - run_calendar_etl: 市場カレンダー ETL（最終日翌日〜target + lookahead まで）
  - run_daily_etl: 日次 ETL の統合実行
    - 処理順: カレンダー ETL → 株価 ETL → 財務 ETL → 品質チェック
    - 各ステップは独立して例外処理され、1 ステップ失敗でも他は継続（エラーは ETLResult に蓄積）
    - 品質チェックはオプション（run_quality_checks=True）
    - デバッグ/監査のために詳細ログを出力

- 監査ログ（トレーサビリティ）テーブル (`kabusys.data.audit`)
  - 監査テーブル群を定義:
    - signal_events: シグナル生成ログ（戦略ID・決定・理由・ステータス等）
    - order_requests: 発注要求ログ（order_request_id を冪等キーとして利用、各種チェック制約）
    - executions: 証券会社からの約定ログ（broker_execution_id をユニーク冪等キー）
  - ステータス遷移や設計原則（UTC タイムスタンプ、削除禁止、created_at/updated_at の取り扱い）を文書化して実装
  - init_audit_schema(conn) を提供: 既存 DuckDB 接続に監査テーブルを追加（SET TimeZone='UTC' 実行）
  - init_audit_db(db_path) を提供: 監査専用 DB を初期化して返す
  - 監査用インデックス群を定義（signal 日付・戦略検索、status ベースのキュー検索、broker_id による紐付け等）

- データ品質チェック (`kabusys.data.quality`)
  - 品質チェック設計と実装（DuckDB 上の SQL ベース）
  - QualityIssue データクラスを導入（check_name, table, severity, detail, rows）
  - 実装済みチェック（少なくとも以下を含む）
    - check_missing_data: raw_prices の OHLC 欄の欠損検出（必須カラムが NULL のレコードを検出、重大度 = error）
    - check_spike: 前日比スパイク検出（LAG を用いた window 関数、閾値デフォルト 50%）
    - （設計書に並ぶ）重複チェック・将来日付/営業日外検出などの実装方針を反映
  - 各チェックは問題を収集して QualityIssue のリストで返す（Fail-Fast ではない）
  - SQL はパラメータバインド（?）を使用し、インジェクションを低減

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Deprecated
- （初期リリースのため該当なし）

### Removed
- （初期リリースのため該当なし）

### Security
- （初期リリースのため該当なし）

補足
- 多くの実装はデータ整合性（CHECK/PK/FK）と冪等性（ON CONFLICT）を重視しているため、外部システムとの連携や再実行に備えた設計になっています。
- J-Quants クライアントはネットワーク障害・レート制限・トークン有効期限切れを考慮した堅牢なリトライロジックを備えています。
- ETL と品質チェックは分離されており、品質問題の検出後の運用判断（ETL 停止／通知）は呼び出し側に委ねられます。

もしリリース日や追加の実装履歴（コミットごとの細かな変更）を反映したい場合は、対象コミットや実際のリリース日を教えてください。追記して更新します。