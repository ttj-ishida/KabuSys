# Changelog

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを使用します。

## [Unreleased]


## [0.1.0] - 2026-03-15
初回リリース。日本株自動売買システムの基盤となるコア機能群を追加。

### Added
- パッケージ基礎
  - パッケージ名: kabusys、バージョン 0.1.0 をパッケージ初期化で定義。
  - 下位モジュールの骨組みを追加: data, strategy, execution, monitoring（いくつかはプレースホルダとして空の __init__）。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定値を読み込む自動ローダーを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルート判定: .git または pyproject.toml を起点に探索（__file__ を基準にするため CWD に依存しない）。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用途などを想定）。
    - OS 環境変数を保護するため、.env 読み込み時に既存キーを保護（.env.local は override=True で上書き可）。
  - .env のパース機能を強化:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォートされた値のエスケープ処理を考慮した正しい取り扱い。
    - 行頭のコメント、行内コメントの取り扱い（クォート有無に応じた判定）。
    - 無効行はスキップ。
  - Settings クラスを追加（settings = Settings() で利用可能）。
    - J-Quants / kabuステーション / Slack / DB / システム関連の設定プロパティを提供：
      - jquants_refresh_token (必須: JQUANTS_REFRESH_TOKEN)
      - kabu_api_password (必須: KABU_API_PASSWORD)
      - kabu_api_base_url (デフォルト: http://localhost:18080/kabusapi)
      - slack_bot_token (必須: SLACK_BOT_TOKEN)
      - slack_channel_id (必須: SLACK_CHANNEL_ID)
      - duckdb_path (デフォルト: data/kabusys.duckdb)
      - sqlite_path (デフォルト: data/monitoring.db)
      - env: KABUSYS_ENV の検証（development / paper_trading / live）
      - log_level: LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
      - is_live / is_paper / is_dev のショートカットプロパティ
    - 必須環境変数未設定時は ValueError を送出することで早期検出を促進。

- データスキーマ (src/kabusys/data/schema.py)
  - DuckDB を用いた多層データレイヤー（Raw / Processed / Feature / Execution）の DDL を定義。
    - Raw layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature layer: features, ai_scores
    - Execution layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - テーブル制約（型・CHECK・PRIMARY KEY・FOREIGN KEY 等）を明示的に定義。
  - 頻出クエリを考慮したインデックス定義を追加（例: 銘柄×日付、ステータス検索、外部キー参照用など）。
  - 公開 API:
    - init_schema(db_path): ディレクトリ自動作成、すべてのテーブル/インデックスを冪等に作成し DuckDB 接続を返す。":memory:" に対応。
    - get_connection(db_path): 既存 DB への接続を返す（スキーマ初期化は行わない。初回は init_schema を推奨）。
  - 実運用を想定した設計メモ（DataSchema.md に準拠する想定）をコメントに記載。

- 監査ログ（トレーサビリティ） (src/kabusys/data/audit.py)
  - シグナル〜発注〜約定までをトレースする監査用テーブル群とインデックスを追加。
    - signal_events: 戦略が生成したすべてのシグナル（棄却・エラー含む）を保存。decision カラム、reason、created_at 等を持つ。
    - order_requests: 冪等キー(order_request_id) を持つ発注要求ログ。注文種別ごとのチェック制約（limit/stop/market の価格要件）を実装。status 変遷管理カラムを含む。
    - executions: 証券会社からの約定情報を保存。broker_execution_id を冪等キー（UNIQUE）として扱う。
  - 監査テーブル向けのインデックス群を定義（status スキャン、signal_id/日付/銘柄検索、broker_order_id 紐付け等）。
  - 公開 API:
    - init_audit_schema(conn): 既存 DuckDB 接続に監査テーブルを追加（SET TimeZone='UTC' を実行し UTC を採用）。
    - init_audit_db(db_path): 監査専用 DB を初期化して接続を返す（ディレクトリ自動作成、":memory:" 対応）。
  - 設計原則（コードコメントで明示）:
    - 監査ログは削除しない前提（FK は ON DELETE RESTRICT）。
    - すべての TIMESTAMP は UTC に統一。
    - order_request_id による冪等性の確保。

### Notes
- すべてのスキーマ定義・インデックス作成は冪等（CREATE IF NOT EXISTS）で実装されているため、何度実行しても上書きや重複を起こしにくい設計。
- デフォルトの DuckDB ファイルパスは data/kabusys.duckdb、監視用 SQLite は data/monitoring.db。
- DuckDB を利用（duckdb パッケージが依存関係）。
- strategy、execution、monitoring パッケージは現時点ではモジュール枠のみ用意（今後の戦略実装や実行ロジック、監視機能の追加を想定）。

### Breaking Changes
- なし（初回リリース）。

--- 

開発者向け短い利用例
- スキーマ初期化:
  - from kabusys.data.schema import init_schema
  - conn = init_schema(settings.duckdb_path)
- 監査テーブル初期化:
  - from kabusys.data.audit import init_audit_schema
  - init_audit_schema(conn)

（この CHANGELOG はソースコードの内容から推測して作成しています。実際のドキュメントや運用方針に合わせて必要に応じて編集してください。）