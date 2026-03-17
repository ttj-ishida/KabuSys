# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣例に従います。  

## [0.1.0] - 2026-03-17

初回公開リリース。日本株自動売買・データ基盤のコア機能を実装しています。

### Added
- パッケージ基盤
  - kabusys パッケージを追加。主要サブパッケージ: data, strategy, execution, monitoring（空の __init__ を用意）。
  - バージョン情報: `__version__ = "0.1.0"` を設定。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
  - ルート検出ロジック: `.git` または `pyproject.toml` を基準にプロジェクトルートを探索（CWD 非依存）。
  - .env 読み込み: `.env` → `.env.local` の優先順、OS 環境変数は保護（上書き防止）。
  - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを抑止可能。
  - 設定クラス `Settings` を実装。主なプロパティ:
    - J-Quants: `jquants_refresh_token`
    - kabuステーション: `kabu_api_password`, `kabu_api_base_url`
    - Slack: `slack_bot_token`, `slack_channel_id`
    - DB パス: `duckdb_path`（デフォルト `data/kabusys.duckdb`）、`sqlite_path`
    - 環境種別/ログレベルの検証: `env`, `log_level`（入力検証あり）
    - 環境判定ヘルパー: `is_live`, `is_paper`, `is_dev`

- J-Quants クライアント (kabusys.data.jquants_client)
  - API ベース機能: ID トークン取得（リフレッシュ）、株価日足・財務データ・マーケットカレンダーの取得関数を実装。
  - レート制御: 固定間隔スロットリングで J-Quants のレート制限 (120 req/min) を遵守する `_RateLimiter` を実装。
  - 再試行/リトライ: 指数バックオフによるリトライ（最大 3 回）、HTTP 408/429/5xx に対応。429 の場合は Retry-After ヘッダを優先。
  - 401 ハンドリング: 401 を受けた場合に自動で ID トークンを刷新して一度だけ再試行。
  - ページネーション対応: `pagination_key` を追跡してページ取り込みを行う実装。
  - DuckDB への冪等保存関数: `save_daily_quotes`, `save_financial_statements`, `save_market_calendar`（各関数は ON CONFLICT 句で重複更新を行い冪等性を確保）。
  - データ整形ユーティリティ: 安全な数値パース関数 `_to_float`, `_to_int`。
  - 取得時刻の記録 (`fetched_at`) により Look-ahead Bias のトレースが可能。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードから記事を収集して raw_news に保存する一連の処理を実装。
  - 記事ID: URL 正規化後の SHA-256（先頭32文字）で生成し冪等性を担保（utm_* 等のトラッキングパラメータを除去して正規化）。
  - デフォルト RSS ソース: Yahoo Finance（business カテゴリ）。
  - セキュリティ対策:
    - defusedxml を利用して XML Bomb 等を防止。
    - URL スキーム検証（http/https のみ許可）とプライベートアドレス拒否（SSRF 対策）。
    - リダイレクト時にもスキーム/ホスト検証を行うカスタムリダイレクトハンドラ。
    - レスポンス受信サイズ上限（10 MB）と gzip 解凍後の再チェック（Gzip Bomb 対策）。
    - 受信サイズや不正レスポンスはログ出力して安全にスキップ。
  - 前処理: URL 除去、空白正規化の `preprocess_text`、RSS pubDate の安全なパース。
  - DB 保存:
    - `save_raw_news`: チャンク化して INSERT ... ON CONFLICT DO NOTHING RETURNING id を用い、新規挿入IDのみを返す。
    - `save_news_symbols` / `_save_news_symbols_bulk`: 記事と銘柄コードの紐付けをチャンク挿入で保存（ON CONFLICT DO NOTHING、トランザクションで正確な挿入数を返す）。
  - 銘柄コード抽出: 正規表現で 4 桁数字候補を抽出し、既知銘柄セットでフィルタする `extract_stock_codes`。
  - 統合収集ジョブ `run_news_collection` を実装（各ソースは独立してエラーハンドリング、既知銘柄の紐付けを実行）。

- スキーマ管理 (kabusys.data.schema)
  - DuckDB 用のスキーマ定義を追加（Raw / Processed / Feature / Execution の各レイヤー）。
  - 主なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 適切な型・制約・CHECK・PRIMARY KEY・FOREIGN KEY を定義。
  - インデックス定義を追加（頻出クエリに備えた複数インデックス）。
  - `init_schema(db_path)` 関数で DB ファイルの親ディレクトリ自動作成 → 接続 → 全DDL/インデックス実行（冪等）。
  - `get_connection(db_path)` で既存 DB への接続を取得（初期化は行わない）。

- ETL パイプライン基礎 (kabusys.data.pipeline)
  - ETL の設計方針と差分更新ロジックを実装。
  - ETL 結果を表すデータクラス `ETLResult`（品質問題、エラー集計、シリアライズ機能含む）。
  - 差分取得ヘルパー: テーブル存在確認、最大日付取得関数 `_get_max_date` / get_last_price_date / get_last_financial_date / get_last_calendar_date。
  - 取引日調整ヘルパー `_adjust_to_trading_day`（market_calendar を参照して非営業日→直近営業日に調整）。
  - 株価差分ETL `run_prices_etl` の骨格を実装（差分計算、バックフィル日数、取得→保存の流れ）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- ニュース収集における SSRF と XML 関連攻撃への対策を実装:
  - URL スキーム検証（http/https のみ）。
  - ホスト/リダイレクト先がプライベートIPである場合は拒否。
  - defusedxml による XML パース保護。
  - レスポンスサイズ上限と gzip 解凍後のサイズチェックによる DoS 緩和。
- .env ファイル読み込みはデフォルトで OS 環境変数を保護（上書きされない）する挙動。

### Notes
- J-Quants API のレート制限・トークンリフレッシュ・再試行挙動は実運用向けに丁寧に実装済みだが、実際の運用では API キー管理やネットワークエラーに対する監視を併用してください。
- DuckDB を想定したスキーマ設計のため、運用前に init_schema() でスキーマ初期化を行ってください。
- news_collector の挙動（RSS 元や known_codes）や pipeline のパラメータ（backfill_days 等）は運用環境に合わせて調整してください。

## Unreleased
- 今後の予定:
  - complete ETL の各ジョブ（financials / calendar）の run_* 実装と品質チェックの統合。
  - execution（発注）周りの実装（kabu ステーション連携、注文送信/約定処理）。
  - monitoring / Slack 通知等の運用監視機能追加。
  - テストカバレッジと CI ワークフローの整備。