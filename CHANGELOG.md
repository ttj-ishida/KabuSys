# Changelog

すべての注目すべき変更を記録します。本ファイルは Keep a Changelog の形式に準拠しています。  
安定版の互換性は SemVer に従います。

## [0.1.0] - 2026-03-17

初回リリース。日本株自動売買プラットフォームの基盤機能を実装しました。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ基礎
  - kabusys パッケージ作成、バージョンを 0.1.0 に設定。
  - サブパッケージのプレースホルダ: data, strategy, execution, monitoring。

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機能（プロジェクトルート判定は .git または pyproject.toml を使用）。
  - 環境変数自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサ実装:
    - export KEY=val 形式対応、クォート処理、インラインコメント処理。
    - 読み込み時の上書き制御（override）と OS 環境変数保護（protected）。
  - Settings クラスを提供（プロパティ経由でトークン・パス・環境等を取得）。
    - 必須環境変数取得時は未設定で ValueError を送出。
    - KABUSYS_ENV、LOG_LEVEL の検証ロジック。
    - duckdb/sqlite パスのデフォルト設定や is_live/is_paper/is_dev ヘルパー。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API 呼び出しユーティリティ（_request）実装:
    - レート制限（120 req/min）を守る固定間隔スロットリング（_RateLimiter）。
    - リトライロジック（指数バックオフ、最大 3 回）。408/429/5xx を再試行対象に。
    - 429 の場合は Retry-After ヘッダの優先利用。
    - 401 (Unauthorized) を受信した場合、自動でリフレッシュして1回だけ再試行。
    - JSON デコードエラーハンドリング。
  - id_token 取得ロジック（get_id_token）とモジュールレベルのトークンキャッシュ。
  - データ取得関数:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（財務データ、ページネーション対応）
    - fetch_market_calendar（JPX カレンダー）
    - 取得時に fetched_at を記録する設計指針を反映（保存側）。
  - DuckDB へ冪等保存するヘルパー:
    - save_daily_quotes / save_financial_statements / save_market_calendar（ON CONFLICT ... DO UPDATE を使用）。
    - PK 欠損行のスキップ、保存件数のログ出力。
  - 型変換ユーティリティ: _to_float / _to_int（堅牢な変換・不正値処理）。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィード収集・前処理・DB 保存ワークフロー実装。
  - セキュリティ／堅牢性機能:
    - defusedxml による XML パース（XML Bomb 対策）。
    - SSRF 対策: リダイレクト時のスキーム検査 & ホストがプライベート/ループバックかをチェックする _SSRFBlockRedirectHandler と _is_private_host。
    - URL スキーム検証（http/https のみ許可）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MB）と読み取り後のチェック、gzip 解凍後のサイズ検証（Gzip bomb 対策）。
    - User-Agent/Accept-Encoding の利用、最終 URL の再検証。
  - 記事 ID の生成:
    - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリパラメータソート）を行い、その SHA-256 の先頭32文字を記事IDとして使用（冪等性確保）。
    - _normalize_url / _make_article_id 実装。
  - テキスト前処理（preprocess_text）: URL 除去、空白正規化。
  - RSS パース（fetch_rss）:
    - content:encoded を優先、description フォールバック。
    - pubDate の RFC 2822 パース（UTC に正規化、失敗時は現在時刻で代替）。
    - 不正な要素をスキップしつつログ出力。
  - DuckDB 保存:
    - save_raw_news: チャンク分割挿入、トランザクション管理、INSERT ... ON CONFLICT DO NOTHING RETURNING で新規挿入 ID を返却。
    - save_news_symbols / _save_news_symbols_bulk: 記事-銘柄紐付けの一括保存（重複除去、チャンク・トランザクション）。
  - 銘柄コード抽出ユーティリティ:
    - 4桁数字パターンに基づく抽出（extract_stock_codes）、known_codes フィルタ付き。
  - 統合ジョブ run_news_collection:
    - デフォルトソース辞書、ソース毎に独立したエラーハンドリング、known_codes に基づく銘柄紐付け。

- データベーススキーマ（kabusys.data.schema）
  - DuckDB 用スキーマ定義を追加（DataSchema.md に準拠）:
    - Raw / Processed / Feature / Execution レイヤーのテーブル定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等）。
    - 各テーブルに適切な型・制約（CHECK、PRIMARY KEY、FOREIGN KEY）を設定。
    - 頻出クエリ向けのインデックス定義を追加。
  - init_schema(db_path) によりディレクトリ自動作成→スキーマ作成（冪等）して接続を返す。
  - get_connection(db_path) で既存 DB に接続可能（初期化は行わない）。

- ETL パイプライン（kabusys.data.pipeline）
  - ETL の設計・ヘルパー実装:
    - ETLResult データクラス（品質問題・エラーの集約、to_dict）。
    - 差分更新のためのヘルパー: _table_exists, _get_max_date, get_last_price_date, get_last_financial_date, get_last_calendar_date。
    - 取引日調整ヘルパー: _adjust_to_trading_day（market_calendar を参照して非営業日時の調整）。
    - run_prices_etl 実装（差分更新ロジック、backfill_days デフォルト 3、_MIN_DATA_DATE の扱い、jq.fetch_daily_quotes と jq.save_daily_quotes 呼び出し）。
  - 設計方針の反映:
    - 差分更新・バックフィル、品質チェックの継続実行（Fail-Fast にならない）を想定。

### 修正 (Fixed)
- （初回実装のため特定の「修正」は無し。堅牢性向上のための防御的実装を多数追加：XML/DOS/SSRF/サイズ上限/トークンリフレッシュ等）

### セキュリティ (Security)
- RSS パーサに defusedxml を採用し XML 関連攻撃に対処。
- SSRF 対策: 外部接続やリダイレクト先がプライベートアドレスに到達することを防止するチェックを追加。
- 外部 URL のスキーム制限（http/https のみ）。
- レスポンスサイズの上限と gzip 解凍後チェックによりメモリ DoS を緩和。

### テスト支援 (Testing)
- news_collector._urlopen を差し替え（モック）可能に設計してテスト容易性を確保。
- 環境自動ロードを環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能（テスト時に便利）。

### 既知の制約 / TODO
- pipeline.run_prices_etl 以外の ETL ジョブ（財務・カレンダーの差分ETLや品質チェックの実装呼び出しルーチン）は今後実装予定。
- strategy / execution / monitoring モジュールはプレースホルダ（実装継続予定）。

----------

注: 本 CHANGELOG はソースコードから推測して作成しています。実際のリリースノートとして公開する際は必要に応じて文言や日付を調整してください。