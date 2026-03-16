# CHANGELOG

すべての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

全てのバージョンはセマンティックバージョニングに従います。

## [Unreleased]

- 小さな改善やドキュメントの追加はここに記載します。

## [0.1.0] - 2026-03-16
初回リリース。

### Added
- パッケージ初期化
  - パッケージルート: kabusys パッケージを追加。バージョンは `0.1.0` に設定（src/kabusys/__init__.py）。
  - パッケージ公開モジュール: data, strategy, execution, monitoring を __all__ に登録。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルまたは OS 環境変数から設定を自動読み込みする仕組みを導入。
    - プロジェクトルートは `.git` または `pyproject.toml` を起点に探索（CWD 非依存）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
    - .env のパースは `export KEY=val`、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント等に対応。
    - ファイル読み込み失敗時は警告を発行して継続。
  - Settings クラスを公開（settings インスタンス）。
    - J-Quants、kabuステーション、Slack、データベースパス等のプロパティ（必須変数は未設定時に ValueError）。
    - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の入力検証（許容値を限定）。
    - 便利なフラグ: is_live / is_paper / is_dev。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - API から次のデータを取得する機能を追加:
    - 株価日足（OHLCV）取得（fetch_daily_quotes）: ページネーション対応。
    - 財務データ（四半期 BS/PL）取得（fetch_financial_statements）: ページネーション対応。
    - JPX マーケットカレンダー取得（fetch_market_calendar）。
  - 認証:
    - リフレッシュトークンから ID トークンを取得する get_id_token を実装。
    - モジュールレベルで ID トークンをキャッシュ（ページネーション間で共有）。
    - 401 受信時は自動でトークンをリフレッシュして最大1回リトライ。
  - リクエストの堅牢化:
    - 固定間隔スロットリングによるレート制御（120 req/min）を実装（_RateLimiter）。
    - 冪等的なリトライロジック（指数バックオフ、最大 3 回、対象: 408/429/5xx）。
    - 429 の場合は Retry-After ヘッダを優先して待機。
    - JSON デコード失敗時は明確なエラーを発生させる。
  - DuckDB への保存ユーティリティ:
    - save_daily_quotes / save_financial_statements / save_market_calendar を提供。
    - INSERT ... ON CONFLICT DO UPDATE による冪等保存。
    - PK 欠損行はスキップして警告出力。
    - 保存時に fetched_at を UTC タイムスタンプで記録（Look-ahead bias 対策）。
  - データ型変換ヘルパー: _to_float, _to_int（不正値に対する安全な変換ロジック）。
  - ロギングを適切に出力（取得件数、保存件数、リトライ状況等）。

- DuckDB スキーマ定義と初期化（src/kabusys/data/schema.py）
  - DataPlatform 設計に基づく 3 層（Raw / Processed / Feature）＋ Execution 層のテーブル定義を追加。
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - インデックス定義（検索パターンに基づく）を追加。
  - init_schema(db_path) により DuckDB を初期化して全テーブル・インデックスを作成（冪等）。
    - db_path の親ディレクトリが存在しない場合は自動作成。
    - ":memory:" によるインメモリ DB に対応。
  - get_connection(db_path) を提供（初期化済み接続の取得用、スキーマは作らない旨を明記）。

- 監査（Audit）スキーマ（src/kabusys/data/audit.py）
  - シグナル→発注→約定のトレーサビリティを担保する監査テーブルを実装。
    - signal_events（戦略が生成したシグナルすべてを記録）
    - order_requests（冪等キー order_request_id を持つ発注要求ログ）
    - executions（証券会社からの約定ログ、broker_execution_id を冪等キーとして扱う）
  - ステータス列、制約、外部キー（ON DELETE RESTRICT）等を厳格に定義。
  - init_audit_schema(conn) / init_audit_db(db_path) で初期化可能。
  - すべての TIMESTAMP を UTC に固定（init で SET TimeZone='UTC' を実行）。
  - 監査用のインデックスを追加（検索効率向上）。

- データ品質チェックモジュール（src/kabusys/data/quality.py）
  - DataPlatform に基づく品質チェックを実装:
    - 欠損データ検出（check_missing_data）: raw_prices の OHLC 欠損を検出（severity = error）。
    - 異常値（スパイク）検出（check_spike）: 前日比の変動率でスパイク検出（デフォルト閾値 50%、severity = warning）。
    - 重複チェック（check_duplicates）: raw_prices の主キー重複検出（severity = error）。
    - 日付不整合チェック（check_date_consistency）: 将来日付、market_calendar と矛盾する非営業日データの検出（severity = error / warning）。
    - run_all_checks で一括実行し、すべての QualityIssue を返す（Fail-Fast ではなく全件収集）。
  - 各チェックは QualityIssue データクラスを返す（サンプル行を最大 10 件返す）。
  - SQL はパラメタライズされ、安全性と効率を確保。
  - market_calendar 未存在時のチェックは例外を捕捉してスキップ。

### Changed
- 初版なので該当なし。

### Fixed
- 初版なので該当なし。

### Notes / Migration
- 初回リリースのため、DB 初期化は必須です。初回起動時に必ず data.schema.init_schema()（あるいは init_audit_db/ init_audit_schema）を呼んでください。
- 必須の環境変数（例: JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID）は Settings 経由で参照すると未設定時に ValueError が発生します。.env.example を参考に .env を用意してください。
- DuckDB のスキーマ変更や手動データ投入がある場合、ON CONFLICT 句や UNIQUE 制約の挙動に注意してください（ETL の冪等性を前提として実装されています）。

---

（この CHANGELOG はコードベースから推測して作成しています。実際の変更履歴やリリースノートはプロジェクト運用に合わせて適宜更新してください。）