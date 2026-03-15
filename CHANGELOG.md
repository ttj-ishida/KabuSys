# Keep a Changelog

すべての注目すべき変更点をこのファイルで記録します。  
このプロジェクトは Keep a Changelog の規約に従って変更履歴を記載します。

## [0.1.0] - 2026-03-15

初回リリース。日本株自動売買システムのコア基盤を追加しました。

### 追加
- パッケージ基礎
  - パッケージ名: kabusys、バージョン 0.1.0 を設定（src/kabusys/__init__.py）。
  - モジュール構成の骨格を追加（data, strategy, execution, monitoring を公開）。

- 環境変数 / 設定管理（src/kabusys/config.py）
  - .env ファイルおよび OS 環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルートの検出ロジックを実装（.git または pyproject.toml を起点に上位ディレクトリを探索）。これにより CWD に依存しない自動読み込みを実現。
  - .env / .env.local の読み込み順（OS 環境 > .env.local > .env）を実装。`.env.local` は `.env` を上書きする。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能（テスト用途）。
  - .env ファイルパーサを実装:
    - 空行・コメント行を無視。
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープに対応して正しく値を復元。
    - クォートなし値についてはインラインコメント（#）を適切に扱う（直前がスペース/タブの場合のみコメントと認識）。
  - 環境変数の取得ヘルパー _require を実装（未設定時は ValueError を送出）。
  - 設定オブジェクト Settings を提供（settings = Settings()）:
    - J-Quants / kabuステーション / Slack / DB パス等のプロパティを定義。
    - 必須環境変数を明示: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID。
    - デフォルト値: KABUSYS_API_BASE_URL のデフォルトは "http://localhost:18080/kabusapi"、データベースパスのデフォルトは duckdb: "data/kabusys.duckdb"、sqlite: "data/monitoring.db"。
    - 環境（KABUSYS_ENV）は development, paper_trading, live のいずれかに制限（妥当性チェック）。
    - LOG_LEVEL の妥当性チェック（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - is_live / is_paper / is_dev のユーティリティプロパティを提供。

- データベーススキーマ（DuckDB）と初期化 API（src/kabusys/data/schema.py）
  - 3〜4 層構造のスキーマ定義を追加（Raw / Processed / Feature / Execution 層）:
    - Raw 層: raw_prices, raw_financials, raw_news, raw_executions
    - Processed 層: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature 層: features, ai_scores
    - Execution 層: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに主キー、CHECK 制約、外部キー（必要に応じて ON DELETE 挙動）を定義し、データ整合性を強化。
  - 頻出クエリを想定したインデックス群を定義（例: 銘柄×日付、ステータス検索、signal_id→orders 等）。
  - init_schema(db_path) を実装:
    - DuckDB ファイルを初期化し、すべてのテーブルとインデックスを作成（冪等性あり）。
    - db_path の親ディレクトリを自動作成。
    - ":memory:" によるインメモリ DB をサポート。
    - 初回接続後に DDL を逐次実行して schema を構築。
  - get_connection(db_path) を実装:
    - 既存 DuckDB へ接続を返す（スキーマ初期化は行わない: 初回は init_schema を使用すること）。

- 監査ログ（トレーサビリティ）モジュール（src/kabusys/data/audit.py）
  - signal → order_request → execution のフローを UUID 連鎖で完全トレース可能にする監査テーブル群を実装。
  - 主要テーブル:
    - signal_events: 戦略が生成したすべてのシグナルを記録（rejected や error 含む）。
    - order_requests: 発注要求（order_request_id を冪等キーとして採用）。limit/stop/market のチェック制約を実装。
    - executions: 証券会社からの約定ログ（broker_execution_id をユニークな冪等キーとして保存）。
  - 監査設計上の方針をドキュメント化:
    - 監査ログは削除しない想定（FK は ON DELETE RESTRICT）。
    - すべての TIMESTAMP を UTC で保存（初期化時に SET TimeZone='UTC' を実行）。
    - created_at / updated_at の運用方針（アプリ側が更新時に updated_at を current_timestamp で更新）。
  - init_audit_schema(conn) を実装:
    - 既存の DuckDB 接続に監査テーブルと関連インデックスを追加（冪等）。
  - init_audit_db(db_path) を実装:
    - 監査専用 DB を初期化して接続を返す。親ディレクトリの自動作成、UTC タイムゾーン設定を行う。

- その他
  - データディレクトリや DB ファイルのデフォルトパスを設定（data/kabusys.duckdb, data/monitoring.db）。
  - 各所にドキュメント文字列（docstring）を充実させ、設計意図や使用法を明確化。

### 変更
- （初回リリースのため変更履歴なし）

### 修正
- （初回リリースのため修正履歴なし）

### 既知の注意点 / 今後の TODO（メモ）
- strategy、execution、monitoring パッケージは骨格のみで、個別のアルゴリズム・実行ロジックは今後実装予定。
- audit の updated_at フィールドはアプリ側で明示的に更新する運用を想定しているため、利用側の実装で current_timestamp を設定すること。
- DuckDB の制限（例: UNIQUE と NULL の扱い）を踏まえたインデックス設計を行っているが、実運用での検証が必要。
- .env パーサは一般的なフォーマットを広くサポートするが、特殊ケースは今後の拡張対象。

---

（このファイルはプロジェクトの初期リリースに合わせて自動生成した CHANGELOG です。必要に応じて後続リリースで追記してください。）