# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]
- 次回リリースに向けた変更はここに記載します。

## [0.1.0] - 2026-03-17
初回公開リリース。日本株自動売買プラットフォームのコアライブラリを提供します。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = 0.1.0, エクスポート: data, strategy, execution, monitoring）。
- 設定管理
  - 環境変数／.env 読み込みモジュール（kabusys.config）。
  - プロジェクトルート自動検出ロジック（.git または pyproject.toml を基準）により、CWD に依存しない .env 自動読み込みを実装。
  - 読み込み優先順位: OS 環境 > .env.local > .env。自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサの実装（export プレフィックス対応、クォート/エスケープ、インラインコメント処理）。
  - アプリケーション設定ラッパー Settings を提供（必須キー取得用の _require、各種プロパティ: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL）。値検証（有効な env 値／ログレベルチェック）と is_live/is_paper/is_dev ヘルパーを含む。
- J-Quants クライアント（kabusys.data.jquants_client）
  - 日次株価（OHLCV）、四半期財務データ、マーケットカレンダーを取得する API クライアントを実装。
  - レート制御（固定間隔スロットリング）でデフォルト 120 req/min を順守する RateLimiter を実装。
  - 冪等保存用の save_* 関数（DuckDB への ON CONFLICT … DO UPDATE を使用）を実装（save_daily_quotes, save_financial_statements, save_market_calendar）。
  - リトライ処理（指数バックオフ、最大 3 回、HTTP 408/429/5xx の再試行）を実装。
  - 401 応答時のトークン自動リフレッシュ（1 回のみ）およびモジュール内トークンキャッシュを実装。get_id_token 関数を提供。
  - ページネーション対応（pagination_key を使用）で fetch_* 関数が全データを取得。
  - 取得時刻（fetched_at）を UTC で記録し、Look-ahead Bias対策を考慮。
  - データ型変換ユーティリティ（_to_float, _to_int）を実装し、厳格な型変換ルールを適用。
- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからニュースを収集して raw_news テーブルへ保存する一連のモジュールを追加（fetch_rss, save_raw_news, save_news_symbols, run_news_collection）。
  - セキュリティ対策:
    - defusedxml による XML パース（XML Bomb 等対策）。
    - SSRF 対策: URL スキーム検証（http/https のみ）、リダイレクト先の事前検証、プライベート IP/ループバック/リンクローカルの拒否。
    - 受信バイト上限（MAX_RESPONSE_BYTES = 10MB）によるメモリ DoS 軸の防止。gzip 解凍後サイズチェックも実施（Gzip bomb 対策）。
    - トラッキングパラメータ（utm_* 等）の除去と URL 正規化、記事ID は正規化 URL の SHA-256（先頭32文字）で生成して冪等性を担保。
  - DB 側の挿入はチャンク処理とトランザクションで行い、INSERT ... RETURNING を用いて実際に挿入された件数を返す。
  - 銘柄コード抽出ユーティリティ（4桁数字パターン + known_codes フィルタ）を提供。
  - _urlopen を抽象化してテスト時に差し替え可能に（モック容易性）。
- スキーマ定義（kabusys.data.schema）
  - DuckDB 向けデータモデルと初期化処理を実装（init_schema, get_connection）。
  - 3 層（Raw / Processed / Feature / Execution）を意識したテーブル群を定義:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型・制約（CHECK／PRIMARY KEY／FOREIGN KEY）を付与。頻出クエリ向けのインデックスも定義。
  - init_schema は親ディレクトリ自動作成や :memory: オプションに対応。
- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新を行う ETL 用ユーティリティを実装（run_prices_etl 等の下地）。
  - 差分計算ロジック: DB の最終取得日から backfill_days（デフォルト 3 日）前を再取得して後出し修正を吸収。
  - 市場カレンダーの先読み（デフォルト 90 日）と初回ロードの開始日を定義（J-Quants のデータ開始日 2017-01-01）。
  - ETL 結果を表現する ETLResult データクラスを提供（品質問題・エラーの集約、has_errors/has_quality_errors プロパティ、辞書化メソッド）。
  - DB 存在チェックや最大日付取得のユーティリティを提供（_table_exists, _get_max_date, get_last_price_date 等）。
  - run_prices_etl は差分取得→保存の基本フローを実装し、jq.fetch_daily_quotes / jq.save_daily_quotes を利用（id_token 注入可能でテスト容易）。

### Changed
- 初回リリースのため該当なし（今後のリリースでの差分に記載）。

### Fixed
- 初回リリースのため該当なし（今後のリリースでの差分に記載）。

### Security
- news_collector に多層的な SSRF 対策と XML パース硬化、レスポンスサイズ制限、gzip 解凍後チェックなどを実装。
- 環境変数による認証情報の取り扱い（.env 自動読み込み）で OS 環境変数が保護されるよう設計（.env の上書き制御、protected set）。

### Notes / Migration
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings で必須となる（未設定時は ValueError を送出）。
- データベース:
  - 初回使用時は必ず init_schema(settings.duckdb_path) を実行してテーブルを作成してください。既存テーブルは無害な形でスキップ（冪等）。
- 自動 .env 読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（ユニットテスト等で便利です）。
- jquants_client は API レート制限やリトライを内包するため、外部からは id_token を注入してテスト可能です。news_collector の _urlopen もモック差し替え可能です。

---

この CHANGELOG はコードベースの実装内容から推測して作成しています。実際のリリースノートでは変更の意図や既知の制限、互換性に関する詳細を追記してください。