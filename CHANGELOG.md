# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

なお、本リリースはパッケージの初回公開（v0.1.0）相当の内容をコードベースから推測して記載しています。

## [Unreleased]

## [0.1.0] - 2026-03-16

### Added
- パッケージ基盤
  - パッケージ初期化とバージョン定義を追加（kabusys.__version__ = "0.1.0"）。
  - パッケージ公開モジュール一覧を __all__ に設定（data, strategy, execution, monitoring）。

- 環境設定 / 設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを導入。
  - 自動 .env ロード機能:
    - プロジェクトルートを .git または pyproject.toml を起点に探索して .env / .env.local を自動読み込み。
    - OS 環境変数を保護する仕組み（.env の上書き制御）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用途）。
  - .env パーサの強化:
    - export KEY=val 形式、シングル/ダブルクォート、バックスラッシュによるエスケープ、インラインコメントの扱い等に対応。
    - 無効行（空行・コメント行・= を含まない行）を適切に無視。
  - 必須設定取得ヘルパー (_require) と主なプロパティを実装:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須設定。
    - データベースパスのデフォルト（DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"）。
    - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の検証ロジック。
    - env に基づく is_live / is_paper / is_dev 判定プロパティ。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - J-Quants から株価日足、財務データ、マーケットカレンダーを取得する fetch_* 関数を実装。
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar はページネーション対応。
  - 認証サポート:
    - リフレッシュトークンから ID トークンを取得する get_id_token を実装。
    - モジュールレベルの ID トークンキャッシュを導入（ページネーション間で共有）。
    - 401 受信時の自動リフレッシュ（1回のみ）と再試行を実装。
  - HTTP リクエスト基盤:
    - 固定間隔スロットリングによるレート制御（デフォルト 120 req/min）。
    - リトライ（指数バックオフ、最大 3 回、408/429/5xx を対象）、429 の Retry-After ヘッダ優先対応。
    - タイムアウト設定・JSON デコードエラーの扱い。
    - fetched_at を UTC ISO8601 で記録する設計（Look-ahead Bias 防止のため）。
  - DuckDB への保存処理（冪等）:
    - save_daily_quotes, save_financial_statements, save_market_calendar を実装。
    - 各関数は ON CONFLICT DO UPDATE を用いて重複を排除。
    - PK 欠損行はスキップし、スキップ件数をログ出力。
  - 型変換ユーティリティ:
    - _to_float / _to_int：安全な float/int 変換（空値・不正値は None、"1.0" のような文字列 float を int に変換等の挙動を明示）。

- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - データレイヤー設計（三層：Raw / Processed / Feature + Execution）に基づく DDL を実装。
  - テーブル群（raw_prices, raw_financials, raw_news, raw_executions,
    prices_daily, market_calendar, fundamentals, news_articles, news_symbols,
    features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）を定義。
  - 監査用 DDL を想定した外部キー/制約と、頻出クエリ用のインデックスを定義。
  - init_schema(db_path) による初期化（親ディレクトリ自動作成、:memory: 対応）、get_connection を提供。

- 監査ログ（audit）スキーマ（src/kabusys/data/audit.py）
  - シグナル→発注→約定までのトレーサビリティを確保する監査テーブルを実装。
    - signal_events（戦略が生成したシグナルのログ）
    - order_requests（発注要求。order_request_id を冪等キーとして扱う、価格チェック等の制約あり）
    - executions（証券会社からの約定情報）
  - 監査用インデックスを多数定義（status 検索・signal_id 結合・broker_order_id 紐付け等）。
  - init_audit_schema(conn) / init_audit_db(db_path) を提供。タイムゾーンを UTC に固定。

- データ品質チェック（src/kabusys/data/quality.py）
  - QualityIssue データクラスを導入し、各チェックの検出結果を統一フォーマットで返却。
  - 実装されたチェック:
    - check_missing_data: raw_prices の OHLC 欠損検出（volume は対象外）。
    - check_spike: 前日比スパイク検出（デフォルト閾値 50%）。
    - check_duplicates: raw_prices の主キー重複検出。
    - check_date_consistency: 将来日付検出、および market_calendar との整合性チェック（非営業日のデータ検出）。
    - run_all_checks: 上記全チェックを実行して結果を集約。
  - 各チェックはサンプル行（最大 10 件）を返し、全件収集する設計（Fail-Fast ではない）。

- その他
  - data, strategy, execution, monitoring パッケージのプレースホルダを追加（__init__.py ファイルを配置）。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- 認証トークンの取り扱いについて注意を注記:
  - J-Quants のリフレッシュトークン / Slack トークン等は必須設定であり、.env に平文で置く場合の運用上の注意が必要。

### Notes / Known limitations
- strategy、execution、monitoring パッケージはプレースホルダ（内部実体は未実装／最小構成）となっているため、実際の売買ロジック・注文送信・監視ワークフローは別途実装が必要。
- DuckDB の制約・インデックスは設計に基づくが、実運用でのパフォーマンスチューニングは実データに合わせて調整が必要。
- J-Quants API 呼び出しは urllib をベースに実装しているため、高度な HTTP クライアント（セッション管理やコネクションプール）が必要な場合は拡張を検討。
- .env の自動ロードはプロジェクトルートの検出に .git / pyproject.toml を用いるため、配布後や特殊な配置では期待通りに動作しない可能性がある。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して明示的にロードする運用を推奨。

---

開発・運用にあたって不明点や追加で CHANGELOG に含めたい変更（例：リリース日付の確定、追加のマイグレーション手順など）があればお知らせください。