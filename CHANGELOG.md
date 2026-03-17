CHANGELOG
=========

All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠しています。
リリースはセマンティックバージョニングに従います。

v0.1.0 - 2026-03-17
-------------------

Added
- 初期リリース: KabuSys 日本株自動売買システムのコア機能を実装。
- パッケージ情報:
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として公開。
  - パッケージ外部公開モジュール: data, strategy, execution, monitoring（__all__ 指定）。

- 環境設定 / config:
  - .env ファイルまたは環境変数から設定を読み込む自動ローダ実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - プロジェクトルートは __file__ を基点に `.git` または `pyproject.toml` を探索して特定。
  - .env パーサの実装:
    - `export KEY=val` 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理等をサポート。
    - 無効行（空行・コメント・不正フォーマット）はスキップ。
    - OS の既存環境変数を保護する protected オプション。
  - Settings クラスに主要設定をプロパティとして提供:
    - J-Quants: `jquants_refresh_token`（必須）
    - kabuステーション: `kabu_api_password`, `kabu_api_base_url`（デフォルト値あり）
    - Slack: `slack_bot_token`, `slack_channel_id`（必須）
    - DB パス: `duckdb_path`（デフォルト `data/kabusys.duckdb`）、`sqlite_path`
    - システム設定の検証: `KABUSYS_ENV`（development/paper_trading/live の検証）と `LOG_LEVEL`（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - 環境判定ヘルパ: `is_live`, `is_paper`, `is_dev`

- データ取得クライアント / data.jquants_client:
  - J-Quants API クライアントを実装。
    - レート制限厳守: 固定間隔スロットリングによる 120 req/min 制御（_RateLimiter）。
    - リトライ戦略: 指数バックオフ、最大 3 回リトライ。HTTP 408/429 と 5xx を再試行対象。
    - 認証トークン自動処理: 401 受信時にリフレッシュして 1 回再試行（トークンキャッシュを共用）。
    - ページネーション対応のフェッチ関数:
      - fetch_daily_quotes (株価日足/OHLCV)
      - fetch_financial_statements (四半期財務データ)
      - fetch_market_calendar (JPX カレンダー)
    - レスポンス JSON デコードエラーを検出して明確な例外メッセージを返す。
    - 取得時刻（fetched_at）を UTC ISO8601 形式で付与（Look-ahead bias トレース用）。
  - DuckDB への保存（冪等）関数:
    - save_daily_quotes: raw_prices に ON CONFLICT DO UPDATE で保存（PK: date, code）。
    - save_financial_statements: raw_financials に ON CONFLICT DO UPDATE（PK: code, report_date, period_type）。
    - save_market_calendar: market_calendar に ON CONFLICT DO UPDATE（PK: date）。
    - 型変換ユーティリティ `_to_float`/`_to_int` により不整合値に柔軟に対応。

- ニュース収集 / data.news_collector:
  - RSS フィードからニュース記事を安全に収集して DuckDB に保存する機能を実装。
    - デフォルト RSS ソースに Yahoo Finance（business）を含む。
    - セキュリティ対策:
      - defusedxml を使用した XML パース（XML Bomb 等対策）。
      - SSRF 対策: URL スキーム検証（http/https のみ）、ホスト/IP のプライベートアドレス検出、リダイレクト検査（_SSRFBlockRedirectHandler）。
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）によるメモリ DoS 対策。gzip 解凍後のサイズチェックも実施（Gzip bomb 対策）。
    - URL 正規化と記事 ID 生成:
      - トラッキングパラメータ（utm_*, fbclid, gclid など）を除去し、スキーム/ホスト小文字化・フラグメント削除・クエリソートを実行。
      - 正規化後の SHA-256 ハッシュの先頭32文字を記事 ID として冪等性を保証。
    - テキスト前処理: URL 除去、空白正規化。
    - RSS パースの堅牢性: content:encoded を優先、description フォールバック、guid の URL 代替対応。
  - DuckDB への保存:
    - save_raw_news: チャンク単位で INSERT ... ON CONFLICT DO NOTHING RETURNING id を利用し、新規挿入された記事 ID リストを返す。トランザクションでまとめて処理。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを ON CONFLICT DO NOTHING RETURNING で保存し、実際に挿入された件数を正確に返す。
  - 銘柄コード抽出:
    - 4桁数字のパターンから候補抽出し、known_codes セットでフィルタして重複除去して返す。

- スキーマ / data.schema:
  - DuckDB 用のスキーマ初期化モジュールを実装（init_schema, get_connection）。
  - 3 層設計を反映したテーブル群を定義:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルの制約（PRIMARY KEY、CHECK、FOREIGN KEY）を設置し、データ整合性を確保。
  - 頻出クエリ向けのインデックスを作成（コード/日付検索、ステータス検索など）。

- ETL パイプライン / data.pipeline:
  - ETLResult dataclass を実装して ETL 実行結果（取得数、保存数、品質問題、エラー等）を集約。
  - 差分取得ユーティリティ:
    - テーブルの最終取得日取得関数: get_last_price_date, get_last_financial_date, get_last_calendar_date。
    - 非営業日調整: _adjust_to_trading_day（market_calendar を参照して最も近い過去営業日に調整）。
  - run_prices_etl の一部実装:
    - 差分更新ロジック（最終取得日から backfill_days 前を date_from とする）と J-Quants からの取得→保存の流れを実装。
    - 既定値: _MIN_DATA_DATE = 2017-01-01、_DEFAULT_BACKFILL_DAYS = 3、カレンダー先読みなど。

- テスト支援:
  - news_collector._urlopen をモック差替え可能にしてテストしやすく設計。
  - config の自動ロードは環境変数で無効化可能（テストでの分離容易化）。

Changed
- N/A（初期リリースのため変更履歴はありません）

Fixed
- N/A（初期リリース）

Security
- RSS パースに defusedxml を使用、SSRF / Gzip bomb / 大容量レスポンス対策等のセキュリティ強化を組み込み。

Known issues / 注意事項
- run_prices_etl の戻り値:
  - 現状の実装ファイルは run_prices_etl の末尾が "return len(records)," のように途中で途切れており、(fetched_count, saved_count) の完全なタプルを返していない箇所が存在します。実行時にタプル不整合の例外が発生する可能性があるため、修正が必要です。
- schema と実装の整合性:
  - news_articles テーブルと raw_news の二重管理（raw と processed）の同期や、外部キーの依存関係に基づく運用フローは使用方法に依存します。マイグレーションや ETL ワークフロー設計時に運用ルールを定義してください。
- 未実装 / スタブ:
  - package 内の execution/strategy ディレクトリは __init__.py のみで、各戦略や実行ロジックは今後の実装対象です。
- 例外ハンドリング方針:
  - 一部の ETL や集約処理は「ソース単位でエラーを隔離して継続する」設計になっており（run_news_collection 等）、重大エラーが発見されても処理を続行する振る舞いです。呼び出し側で ETLResult の内容をチェックして対応してください。

リリースノートに関する補足
- 本 CHANGELOG はコードベースから推測して作成しています。今後の実装追加（戦略モジュール、発注実行の実装、品質チェックモジュールの詳細等）に合わせて項目を追加していきます。