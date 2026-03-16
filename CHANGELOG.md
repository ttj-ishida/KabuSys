KEEP A CHANGELOGの形式に準拠した CHANGELOG.md を以下に作成しました（日本語）。リポジトリ内のコードから推測できる変更点・初回リリース内容を記載しています。必要なら日付や細部を調整してください。

CHANGELOG.md
-------------

全体方針: 保守的な差分履歴管理を想定し、初回リリースとして機能セットとアーキテクチャ上の重要な設計判断を記録しています。

Unreleased
----------

- （今後の変更をここに記載）

0.1.0 - 2026-03-16
-----------------

Added
- 初回リリース。日本株自動売買システム "KabuSys" のコアモジュールを追加。
  - パッケージメタ情報
    - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として定義。
    - パッケージの公開モジュール一覧を __all__ に設定。

- 環境設定 / config
  - .env ファイルまたは環境変数から設定値を読み込む Settings クラスを実装。
  - プロジェクトルート判定: __file__ を起点に .git または pyproject.toml を探索して自動的にプロジェクトルートを特定するロジックを追加。配布後も CWD に依存しない読み込みを実現。
  - .env ローダー:
    - ".env" と ".env.local" の二段階読み込み（OS 環境変数 > .env.local > .env の優先度）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理、クォートなしのコメント処理などをサポートする堅牢な行パーサーを実装。
    - 読込失敗時は警告を発行（warnings.warn）。
    - OS環境変数を保護する protected セット機構を実装（.env.local での上書きを制御）。
  - Settings による必須項目チェック（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。未設定時は ValueError を送出。
  - 環境種別（KABUSYS_ENV）の検証（development / paper_trading / live）とログレベル（LOG_LEVEL）の検証。
  - データベースのデフォルトパス設定（DuckDB: data/kabusys.duckdb、SQLite: data/monitoring.db）。

- データアクセス: J-Quants クライアント（data/jquants_client.py）
  - J-Quants API から以下の取得関数を実装:
    - fetch_daily_quotes (株価日足: OHLCV) — ページネーション対応
    - fetch_financial_statements (財務データ: 四半期 BS/PL) — ページネーション対応
    - fetch_market_calendar (JPX マーケットカレンダー)
  - 認証:
    - refresh_token から id_token を取得する get_id_token を実装。
    - id_token のモジュールレベルキャッシュを実装し、ページネーション間でトークンを共有。
    - 401 受信時は自動で id_token を一度だけリフレッシュして再試行するロジック。
  - HTTP ユーティリティ:
    - 固定間隔スロットリングによるレート制御（120 req/min、_RateLimiter を実装）。
    - 再試行（最大 3 回）、指数バックオフ、HTTP 408/429/5xx に対するリトライ、および 429 の Retry-After ヘッダ優先処理。
    - JSON デコードエラーやネットワークエラーに対するハンドリングとログ出力。
    - fetch_* 関数は取得件数のログを出力。
  - DuckDB への保存関数（冪等性）:
    - save_daily_quotes, save_financial_statements, save_market_calendar を実装。
    - 各 save_* は ON CONFLICT DO UPDATE を用いて重複を排除し、fetched_at（UTC ISO8601）を保存。
    - PK 欠損行はスキップし、スキップ件数は警告ログへ。
  - ユーティリティ変換関数:
    - _to_float / _to_int: 入力値の安全な数値変換（空値・不正値を None にする。_to_int は小数部が非ゼロの float 文字列を変換しない等の保護）。

- データベーススキーマ（data/schema.py）
  - DuckDB 用のスキーマ定義を実装（Raw / Processed / Feature / Execution 層の区別）。
  - Raw レイヤー: raw_prices, raw_financials, raw_news, raw_executions。
  - Processed レイヤー: prices_daily, market_calendar, fundamentals, news_articles, news_symbols。
  - Feature レイヤー: features, ai_scores。
  - Execution レイヤー: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance。
  - 各テーブルの制約（PRIMARY KEY, CHECK, FOREIGN KEY）を定義してデータ整合性を担保。
  - 頻出クエリに備えたインデックス群を追加（コード×日付スキャン、ステータス検索など）。
  - init_schema(db_path) により DB ファイル（あるいは ":memory:"）に対して idempotent にテーブルを作成し接続を返す。親ディレクトリがなければ自動作成。
  - get_connection(db_path) で既存 DB へ接続可能（スキーマ初期化は行わないことを明記）。

- ETL パイプライン（data/pipeline.py）
  - 差分更新型 ETL を実装:
    - run_prices_etl, run_financials_etl, run_calendar_etl: 各種差分ETL（date_from 自動算出、backfill、lookahead など）。
    - run_daily_etl: 日次 ETL の総合エントリポイント（市場カレンダー → 株価 → 財務 → 品質チェックの順）。
  - 差分更新ロジック:
    - DB の最終取得日を基に date_from を自動算出し、既取得分はスキップ。
    - デフォルトのバックフィル日数を 3 日に設定し、後出し修正を吸収。
    - 市場カレンダーは基準日から 90 日の先読み（デフォルト）を行い営業日調整に利用。
  - ETLResult データクラス:
    - 実行結果（取得数、保存数、品質問題一覧、エラー一覧）を集約し、to_dict でシリアライズ可能。
    - 個々のステップは独立して例外処理され、1 ステップの失敗が他を止めない設計（Fail-Fast ではない）。
  - 品質チェック統合:
    - ETL 後に quality モジュールを呼び出して欠損・スパイクなどの品質チェックを実行（run_quality_checks オプションで有効/無効）。

- 品質チェック（data/quality.py）
  - データ品質チェック用モジュールを実装（欠損・スパイク・重複・日付不整合を想定）。主な機能:
    - QualityIssue データクラス（check_name, table, severity, detail, rows）。
    - check_missing_data: raw_prices の OHLC 欠損検出（サンプル最大 10 行を返す）。欠損は severity="error" として扱いログ出力。
    - check_spike: LAG を用いた前日比スパイク検出（デフォルト閾値 0.5 = 50%）。
    - （設計上）各チェックは全件収集してリストを返す方式で、呼び出し元で重大度に応じた判断を行う。

- 監査ログ / トレーサビリティ（data/audit.py）
  - 戦略→シグナル→発注→約定の一連を UUID 連鎖で完全にトレース可能にする監査スキーマを実装。
  - テーブル:
    - signal_events: 戦略が出した全シグナル（棄却やエラーを含む）を記録。decision と reason フィールドあり。
    - order_requests: 発注要求（order_request_id を冪等キーとして使用）。limit/stop の価格整合性を CHECK 制約で保証。
    - executions: 証券会社からの約定情報を記録（broker_execution_id をユニークな冪等キーとして保存）。
  - init_audit_schema(conn) / init_audit_db(db_path) を用いた idempotent な監査テーブル初期化。
  - 全 TIMESTAMP を UTC に保存するために接続時に SET TimeZone='UTC' を実行。
  - インデックス群を定義し、日付/銘柄検索や pending キュー検索を効率化。

Logging / Observability
- 各主要処理（fetch/save/etl/quality）で info/warning/error を適切に出力。例外時は logger.exception を用いてスタックトレースを記録。

Design notes / Implementation details
- 冪等性を重視: API 取得後の DB 保存は ON CONFLICT DO UPDATE を基本とし、複数実行に耐える設計。
- Look-ahead bias 防止のため fetched_at を UTC で記録し「データをいつ知り得たか」をトレース可能に。
- API レート制限を厳守（120 req/min）する RateLimiter を実装。
- HTTP リトライは指数バックオフ、429 時は Retry-After を尊重、401 はトークンリフレッシュで一度のみ対応。
- データ変換ユーティリティは入力の雑多な値に対して安全な None 化を行い上流の不整合を低減。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- （初回リリースのため該当なし）

注記（今後の検討点）
- quality モジュールの全チェック（例えば重複チェック、日付不整合チェック）や pipeline 側の run_all_checks の具体実装、及びテストケースの充実化を推奨。
- DB マイグレーション・バージョニング（例: Flyway 相当）やスキーマ変更手順の整備を今後検討することを推奨。
- 大量データ取得時のパフォーマンス（ページネーション戦略、並列取得、DuckDB の VACUUM 等）や長期運用の監視（Prometheus / メトリクス）を追加検討。

もし CHANGELOG の日付や文言、あるいは「Unreleased」に含める予定の変更候補などを合わせて記載したい場合は、その内容を教えてください。必要に応じて英語版やリリースノート短縮版（リリース向け要約）も作成します。