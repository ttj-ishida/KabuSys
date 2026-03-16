# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

<!-- v0.1.0 を最初のリリースとして作成しています。 -->

## [0.1.0] - 2026-03-16

初回リリース。日本株自動売買システムのコア基盤を実装しました。主に以下の機能を含みます。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py
    - パッケージ名とバージョン（0.1.0）、公開モジュール一覧を定義。

- 環境設定管理
  - src/kabusys/config.py
    - .env / .env.local の自動読み込み機能（プロジェクトルートは .git または pyproject.toml を基準に探索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
    - .env パーサ（export 形式、シングル/ダブルクォート、エスケープ、インラインコメント対応）。
    - 読み込み時の上書き挙動（OS 環境変数を保護する protected 機構）。
    - Settings クラスで主要な設定値をプロパティとして公開（J-Quants トークン、kabu API パスワード・ベースURL、Slack トークン・チャンネル、DuckDB/SQLite パス、環境・ログレベル検証など）。
    - KABUSYS_ENV と LOG_LEVEL に対する入力検証（許容値チェック）。

- J-Quants API クライアント
  - src/kabusys/data/jquants_client.py
    - 日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーを取得する fetch_* 関数を実装（ページネーション対応）。
    - API レート制御（固定間隔スロットリング）を実装して 120 req/min を尊重する RateLimiter。
    - リトライロジック（指数バックオフ、最大 3 回。408/429/5xx を対象）。429 の場合 Retry-After を考慮。
    - 401 受信時はリフレッシュトークンを用いて id_token を自動更新して 1 回リトライ（再帰を防ぐ allow_refresh フラグ）。
    - id_token のモジュールレベルキャッシュ（ページネーション間で共有）。
    - JSON デコード失敗時の明示的エラー。
    - DuckDB に保存する save_* 関数（raw_prices, raw_financials, market_calendar）を実装。ON CONFLICT DO UPDATE による冪等保存と PK 欠損行のスキップ、fetched_at に UTC タイムスタンプを記録。
    - 値変換ユーティリティ (_to_float/_to_int) により不正値に寛容な変換を実施（不適切な形式は None）。

- DuckDB スキーマ定義・初期化
  - src/kabusys/data/schema.py
    - Raw / Processed / Feature / Execution 層を想定した DDL を定義。
    - raw_prices, raw_financials, raw_news, raw_executions 等の Raw テーブル。
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブル。
    - features, ai_scores 等の Feature テーブル。
    - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution テーブル。
    - 利用想定クエリに基づくインデックス群。
    - init_schema(db_path) でディレクトリ作成、DDL とインデックスを冪等に実行して接続を返す。
    - get_connection(db_path) を提供（初期化済み接続を得るための補助）。

- ETL パイプライン
  - src/kabusys/data/pipeline.py
    - 日次 ETL のエントリ run_daily_etl を実装（順序: カレンダー → 株価 → 財務 → 品質チェック）。
    - 差分更新ロジック（DB の最終取得日からの差分と backfill 日数）、デフォルトバックフィル 3 日。
    - カレンダー先読み（デフォルト 90 日）による営業日調整ロジック。
    - 個別 ETL ジョブ run_prices_etl, run_financials_etl, run_calendar_etl を実装（差分取得・保存・ログ）。
    - ETLResult データクラスにより取得件数、保存件数、品質問題、エラーを集約。品質チェック結果を辞書化可能。
    - 各ステップは独立して例外をハンドリングし、1 ステップ失敗でも他を継続する設計（全件収集型のエラー処理）。

- 監査ログ（トレーサビリティ）
  - src/kabusys/data/audit.py
    - 戦略 → シグナル → 発注要求 → 約定 のトレーサビリティを記録するテーブル群を実装（signal_events, order_requests, executions）。
    - order_request_id を冪等キーとする設計、timestamps は UTC に固定（init で TimeZone='UTC' を実行）。
    - 各種制約（CHECK、外部キー）を厳格に定義。発注タイプ別のチェック制約（limit/stop/market の価格要否）を実装。
    - init_audit_schema(conn) / init_audit_db(db_path) により監査スキーマを冪等に初期化する。

- データ品質チェック
  - src/kabusys/data/quality.py
    - QualityIssue データクラスを定義（check_name, table, severity, detail, rows）。
    - 欠損データ検出（check_missing_data）：raw_prices の OHLC 欠損を検出（volume は許容）。
    - スパイク検出（check_spike）：前日比の変動率が閾値（デフォルト 50%）を超えるレコードを検出。LAG ウィンドウを利用。
    - 各チェックは問題のサンプル行（最大 10 件）と件数を返し、呼び出し元が重大度に応じて処理を決定可能。

- パッケージ構造（空モジュールのプレースホルダ）
  - src/kabusys/execution/__init__.py（存在）
  - src/kabusys/strategy/__init__.py（存在）
  - src/kabusys/data/__init__.py（存在）
  - 上記は将来の拡張のためのプレースホルダとして用意。

### Changed
- 初回リリースのためなし（新規実装中心）。

### Fixed
- 初回リリースのためなし。

### Notes / TODO
- monitoring モジュールが __all__ に含まれているが、ソース内に未実装（将来的に監視・アラート機能を追加予定）。
- 実際の運用では J-Quants の API レート制限や kabu API の認証情報管理（ファイル権限やシークレット管理）に注意すること。
- テストコードは本リポジトリ内に含まれていないため、ユニットテスト / 結合テストの追加を推奨。
- DuckDB の UNIQUE / NULL の扱いや、外部システム（Slack/kabu/kabu station）のエラーケースに対する運用方針は実運用に合わせて調整が必要。

---

(補足) 本 CHANGELOG は提供されたソースコードからの推測に基づいて作成しています。実際のリリースノートとして利用する場合は、開発履歴やコミットログと照合して調整してください。