# Changelog

すべての重要な変更はこのファイルに記録します。本ファイルは Keep a Changelog の慣習に準拠します。

## [0.1.0] - 2026-03-16

初回リリース

### 追加 (Added)
- パッケージ基本構成
  - パッケージエントリポイントを追加（kabusys.__version__ = 0.1.0、__all__ の公開モジュール指定）。
- 環境設定管理 (`kabusys.config`)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - 読み込み順序: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能（テスト用途）。
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索し、CWD に依存しない方式を採用。
  - .env 行パーサー実装（export プレフィックス、クォート、エスケープ、インラインコメント対応）。
  - 環境変数保護機能: OS 環境変数は protected として上書きを防止（.env.local は上書き可能だが OS 環境は保護）。
  - 必須環境変数取得ヘルパー `_require()` と Settings クラスを提供。
    - Settings では J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パス、実行環境（development/paper_trading/live）やログレベルの検証などのプロパティを公開。
    - env / log_level に対する入力検証を実装し、不正値は ValueError を送出。
- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - API 呼び出しの共通ユーティリティと堅牢な HTTP リトライ・レート制御を実装。
    - 固定間隔スロットリングで 120 req/min を遵守する RateLimiter を実装。
    - 指数バックオフによるリトライ（最大 3 回）、対象ステータス: 408/429/5xx。
    - 429 の場合は Retry-After ヘッダを優先して待機。
    - 401 受信時はリフレッシュトークンを自動で使用して id_token をリフレッシュし 1 回だけ再試行（再帰を避けるため allow_refresh フラグ制御）。
    - ページネーション（pagination_key）対応。
    - モジュールレベルの id_token キャッシュ（ページネーション間で共有）。
  - データ取得関数を実装:
    - fetch_daily_quotes: 株価日足（OHLCV）をページネーション対応で取得。
    - fetch_financial_statements: 四半期財務データをページネーション対応で取得。
    - fetch_market_calendar: JPX マーケットカレンダーを取得（祝日/半日/SQ 情報含む）。
  - DuckDB 保存関数（冪等）を実装:
    - save_daily_quotes: raw_prices テーブルへ ON CONFLICT DO UPDATE による冪等保存。
    - save_financial_statements: raw_financials テーブルへ冪等保存。
    - save_market_calendar: market_calendar テーブルへ冪等保存（HolidayDivision の意味付けを変換して保存）。
    - 各保存関数は取得時刻 fetched_at を UTC ISO8601 形式で記録。
  - ユーティリティ関数:
    - _to_float / _to_int: 型変換を安全に行うユーティリティ（空値や不正な値は None を返す、_to_int は小数部が非ゼロのケースを排除）。
- DuckDB スキーマ定義 (`kabusys.data.schema`)
  - DataSchema に基づく多層テーブル定義を追加:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに整合性チェック（CHECK 制約）、主キー、外部キーを定義。
  - 頻出クエリのためのインデックスを複数定義。
  - init_schema(db_path) によりディレクトリ作成 → テーブル/インデックス作成（冪等）を実行し、接続を返す。
  - get_connection(db_path) で既存 DB への接続を返す（スキーマ初期化は行わない）。
- ETL パイプライン (`kabusys.data.pipeline`)
  - 日次 ETL の実装（差分更新・バックフィル・品質チェック）。
    - run_daily_etl: カレンダー取得 → 営業日に調整 → 株価 ETL → 財務 ETL → 品質チェック の一連処理を実行。
    - run_calendar_etl / run_prices_etl / run_financials_etl: 個別ジョブ実装。差分取得ロジックとデフォルトのバックフィル（3 日）を搭載。
    - 差分更新支援: DB 側の最終取得日を取得して自動的に date_from を算出（初回は J-Quants の最小日付を使用）。
    - calendar はデフォルトで先読み（lookahead）90 日分を取得し、営業日判定に使用。
  - ETLResult データクラスを導入し、各 ETL 実行結果（取得数、保存数、品質問題、エラー）を集約。品質問題はシリアライズ可能な辞書へ変換可能。
  - ETL 各ステップは独立してエラーハンドリングされ、1 ステップ失敗でも他ステップは継続（Fail-Fast しない設計）。
  - id_token を引数注入可能にしてテスト容易性を確保。
- 監査ログ・トレーサビリティ (`kabusys.data.audit`)
  - シグナル→発注→約定のトレーサビリティを保証する監査テーブル群を追加。
    - signal_events, order_requests, executions テーブルを定義（UUID/冪等キー/ステータス/履歴用タイムスタンプ等）。
    - order_requests に対する複数のチェック制約（limit/stop/market の価格必須条件）を実装。
    - すべての TIMESTAMP を UTC で保存（init_audit_schema は SET TimeZone='UTC' を実行）。
    - init_audit_schema(conn) と init_audit_db(db_path) を提供（冪等）。
    - 監査用インデックスを複数作成（ステータススキャン、signal_id / broker_order_id 紐付け等）。
- データ品質チェック (`kabusys.data.quality`)
  - QualityIssue データクラスを導入（check_name, table, severity, detail, sample rows）。
  - チェック実装:
    - check_missing_data: raw_prices の OHLC 欠損検出（volume は対象外）。検出時は severity="error"。
    - check_spike: 前日比でのスパイク（デフォルト 50%）検出。LAG ウィンドウで効率的に算出。サンプル/総数を返す。
  - DuckDB への SQL 実行はパラメータバインド（?）を使用し、安全に実行。
- ロギング／監査の考慮
  - 重要イベント（取得件数、保存件数、リトライ、401 リフレッシュ、PK 欠損によるスキップなど）に対して logger を使用して情報・警告・エラーを出力。
- テスト性向上のための設計配慮
  - id_token の注入や allow_refresh フラグ、キャッシュ制御（force_refresh）によりユニットテストでの動作制御が容易。

### 変更 (Changed)
- （初版リリースのため該当なし）

### 修正 (Fixed)
- （初版リリースのため該当なし）

### セキュリティ (Security)
- HTTP リトライで 401 を受けた場合に自動でトークンをリフレッシュする処理を実装。ただし無限再帰にならないよう allow_refresh フラグで制御。

---

注:
- 本 CHANGELOG はソースコードの実装から推測して作成したものであり、リリースノートの文章は実装上の設計・挙動を要約したものです。具体的な API 利用法やマイグレーション手順は別途ドキュメント（DataSchema.md, DataPlatform.md 等）を参照してください。