Keep a Changelog
=================

すべての重要な変更をこのファイルに記録します。フォーマットは Keep a Changelog に準拠します。
リリースは日付順（新しいものが上）に並びます。

v0.1.0 - 2026-03-16
-------------------

初回リリース。日本株自動売買システム「KabuSys」のコア基盤を提供します。
主な追加点は以下の通りです。

Added
- パッケージ基盤
  - パッケージバージョンを設定（kabusys.__version__ = "0.1.0"）。
  - パブリック API として data, strategy, execution, monitoring モジュールを公開。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび OS 環境変数から設定を自動読み込みする仕組みを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルートの探索は __file__ を起点に .git または pyproject.toml を探すため、CWD に依存しない。
    - プロジェクトルートが見つからない場合は自動読み込みをスキップ。
    - 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト等で利用）。
  - .env パーサ実装:
    - 空行・コメント（行頭#）を無視。
    - export KEY=val 形式に対応。
    - シングル／ダブルクォートの内部でのバックスラッシュエスケープに対応。
    - quote無しの場合、# の直前が空白/タブのとき以降をコメントとして扱う。
  - .env 読み込み時の上書きロジック:
    - override=False: 未定義のキーのみセット。
    - override=True: protected（既存 OS 環境変数）以外は上書き。
  - Settings クラス
    - J-Quants, kabuステーション, Slack, DB パスなど主要設定をプロパティで提供。
    - 必須設定取得時は未設定で ValueError を送出する _require を採用（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）。
    - デフォルト値:
      - KABU_API_BASE_URL: "http://localhost:18080/kabusapi"
      - DUCKDB_PATH: "data/kabusys.duckdb"
      - SQLITE_PATH: "data/monitoring.db"
      - KABUSYS_ENV: "development"（有効値: development, paper_trading, live）
      - LOG_LEVEL: "INFO"（有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL）
    - env に基づくユーティリティプロパティ: is_live, is_paper, is_dev

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 取得対象: 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダー。
  - レート制御: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter を実装（最小間隔 60/120 秒）。
  - リトライロジック:
    - 指数バックオフ（base=2.0 秒）、最大リトライ回数 3 回。
    - リトライ対象ステータス: 408, 429, 5xx。
    - 429 の場合は Retry-After ヘッダを優先して待機時間を決定。
    - ネットワークエラー（URLError, OSError）もリトライ対象。
  - 認証トークン管理:
    - refresh_token から id_token を取得する get_id_token を提供。
    - 401 受信時は id_token を自動リフレッシュして 1 回だけリトライ（無限再帰を防ぐため allow_refresh フラグを使用）。
    - モジュールレベルで id_token をキャッシュし、ページネーション間で共有。
  - JSON デコード失敗時の明確なエラーメッセージ。
  - ページネーション対応の取得関数:
    - fetch_daily_quotes, fetch_financial_statements: pagination_key を使って自動的に全件取得。
    - fetch_market_calendar: 単一呼び出しで取得。
  - DuckDB への保存関数（冪等性を担保）:
    - save_daily_quotes, save_financial_statements, save_market_calendar を実装。
    - 取得時刻（fetched_at）は UTC ISO8601（Z）で記録し、Look-ahead Bias 防止のため「いつデータを取得したか」をトレース可能に。
    - INSERT ... ON CONFLICT DO UPDATE を使用して重複を排除・更新（冪等）。
    - PK 欠損行はスキップし、その件数はログに警告出力。

  - データ変換ユーティリティ:
    - _to_float: None/空/変換失敗で None を返す。
    - _to_int: "1.0" のようなケースは float 経由で変換し、小数部が 0 でない場合は None を返す（意図しない切捨て防止）。

- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - 3層データモデルを想定:
    - Raw Layer（raw_prices, raw_financials, raw_news, raw_executions）
    - Processed Layer（prices_daily, market_calendar, fundamentals, news_articles, news_symbols）
    - Feature Layer（features, ai_scores）
    - Execution Layer（signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）
  - DDL によるカラム型・制約（CHECK/PRIMARY KEY/FOREIGN KEY）を詳細に定義。
  - インデックス定義: 銘柄×日付検索やステータス検索、外部キー結合のためのインデックスを作成。
  - init_schema(db_path) を提供:
    - db_path の親ディレクトリを自動作成。
    - 全テーブル・インデックスを作成（冪等）。
    - ":memory:" をサポート。
  - get_connection(db_path) を提供（スキーマ初期化は行わない）。

- 監査ログ（kabusys.data.audit）
  - シグナル→発注→約定フローを UUID 連鎖でトレースする監査テーブルを定義:
    - signal_events（戦略が生成したシグナルの記録。棄却も含む）
    - order_requests（発注要求。order_request_id を冪等キーとして採用）
    - executions（証券会社からの約定情報）
  - 制約とチェックを多用してデータ整合性を担保（order_type のチェック、limit/stop の必須条件等）。
  - すべての TIMESTAMP は UTC で保存するよう SET TimeZone='UTC' を実行。
  - init_audit_schema(conn) / init_audit_db(db_path) を提供（既存 DB に追記できる初期化）。
  - 監査用インデックスを実装（signal_events の戦略別検索、order_requests のステータス検索、broker_order_id による一意制約など）。
  - 設計方針: 監査ログは削除しない（ON DELETE RESTRICT）、updated_at はアプリ側で更新、エラーや棄却も必ず永続化。

- データ品質チェック（kabusys.data.quality）
  - DataPlatform 指針に基づく主要チェックを提供:
    - check_missing_data: raw_prices の OHLC 欄の欠損検出（volume は対象外）。
    - check_spike: 前日比スパイク検出（デフォルト閾値 50%）。
    - check_duplicates: raw_prices の主キー重複検出（念のため）。
    - check_date_consistency: 将来日付の検出と market_calendar と照合して非営業日のデータ検出（market_calendar が存在しない場合はスキップ）。
    - run_all_checks: 上記すべてを実行し、QualityIssue のリストを返す。
  - QualityIssue データクラスでチェック名、テーブル、重大度（error/warning）、詳細、サンプル行（最大 10 件）を返す設計。
  - 各チェックは全問題を収集して返す（Fail-Fast ではない）。呼び出し元が重大度に応じて ETL 停止や警告処理を実施可能。
  - SQL はパラメータバインド（?）を使用し、効率的な DuckDB クエリで実装。

Security
- 認証トークンや必須シークレットは Settings 経由で取得し、未設定時は明示的にエラーを出すことで誤った運用を防止。

Notes / Implementation details
- 多くの処理で冪等性（ON CONFLICT DO UPDATE や order_request_id の冪等キー等）を念頭に設計しており、本番運用での二重挿入や二重発注を防ぐ構成になっています。
- fetched_at や監査ログの timestamp は UTC に統一して保存し、データの取得タイミングを明確にトレース可能にしています。
- J-Quants API クライアントは厳格なレート制御・リトライ・トークンリフレッシュロジックを持ち、実際の API 利用に耐えうる耐障害性を備えています。

Fixed
- (該当なし: 初回リリース)

Changed
- (該当なし: 初回リリース)

Removed
- (該当なし: 初回リリース)

Security
- (重要) J-Quants の refresh token 等はコードにハードコーディングせず、環境変数で供給すること。Settings._require により未設定時は起動時にエラーとなります。

今後の予定（例）
- strategy / execution 層の具体的なアルゴリズム実装と単体テストの追加
- ETL バッチやスケジューラとの統合サンプル
- モニタリング・アラート（Slack 連携）の実装例追加
- より詳細なドキュメント（DataSchema.md, DataPlatform.md 参照）と使用例

以上。