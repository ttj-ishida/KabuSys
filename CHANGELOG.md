# CHANGELOG

すべての注目すべき変更点を記録します。This project adheres to "Keep a Changelog" と Semantic Versioning に従います。

## [0.1.0] - 2026-03-17

初回リリース — 日本株自動売買システム「KabuSys」の基盤機能を追加。

### 追加 (Added)
- パッケージ初期化
  - src/kabusys/__init__.py: パッケージ名、バージョン（0.1.0）と公開サブパッケージ（data, strategy, execution, monitoring）を定義。

- 環境設定管理
  - src/kabusys/config.py:
    - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装（プロジェクトルートは .git または pyproject.toml を探索して決定）。
    - .env/.env.local の読み込み順（OS 環境 > .env.local > .env）に対応。テスト等で自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - export KEY=val 形式、クォート・エスケープ、インラインコメント処理に対応する .env パーサを実装。
    - Settings クラスを公開（jquants_refresh_token, kabu_api_password, slack_bot_token, slack_channel_id, duckdb_path, sqlite_path, kabu_api_base_url 等のプロパティを提供）。
    - KABUSYS_ENV / LOG_LEVEL の値検証（許容値チェック）と is_live / is_paper / is_dev のユーティリティプロパティを実装。
    - 必須環境変数未設定時に ValueError を投げる _require ヘルパ。

- J-Quants API クライアント
  - src/kabusys/data/jquants_client.py:
    - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得関数を実装（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - 認証トークン取得・キャッシュ（get_id_token, モジュールレベルキャッシュ）と自動リフレッシュ機構を実装。
    - レートリミッタ（固定間隔スロットリング）を実装して API レート制限（120 req/min）を順守。
    - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）および 429 の Retry-After 処理。
    - DuckDB へ冪等に保存する save_* 関数（save_daily_quotes, save_financial_statements, save_market_calendar）を追加（ON CONFLICT DO UPDATE）。
    - 取得時刻（fetched_at）は UTC ISO 形式で記録し、Look-ahead バイアスの説明トレースを可能に。
    - データ変換ユーティリティ（_to_float, _to_int）を追加し、NULL/空文字や不正フォーマットを安全に扱う。

- ニュース収集モジュール（RSS）
  - src/kabusys/data/news_collector.py:
    - RSS フィード取得・パース・前処理・DB 保存のフローを実装（fetch_rss, save_raw_news, save_news_symbols, run_news_collection など）。
    - 安全性対策：
      - defusedxml を用いた XML パース（XML Bomb 等の防御）。
      - SSRF 対策（HTTP リダイレクト検査、ホストがプライベートアドレスかの検出、許可スキームは http/https のみ）。
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）チェックと gzip 解凍後のサイズ検査（Gzip bomb 対策）。
      - URL 正規化とトラッキングパラメータ除去（_normalize_url, _TRACKING_PARAM_PREFIXES）。
    - 記事ID生成: 正規化 URL の SHA-256（先頭32文字）を使用し冪等性を担保。
    - 文章前処理（URL 除去・空白正規化）を実装（preprocess_text）。
    - 銘柄コード抽出ユーティリティ（extract_stock_codes）を実装（4桁数字と既知コードセットでフィルタ）。
    - DuckDB への保存はトランザクション・チャンク処理（INSERT ... RETURNING を使用）で実装し、実際に挿入された件数を返却。

- DuckDB スキーマ管理
  - src/kabusys/data/schema.py:
    - Raw / Processed / Feature / Execution の 3 層に対応したテーブル群の DDL を定義。
    - raw_prices / raw_financials / raw_news / raw_executions、prices_daily / market_calendar / fundamentals / news_articles / news_symbols、features / ai_scores、signals / signal_queue / orders / trades / positions / portfolio_performance 等を作成。
    - 適切なチェック制約（NOT NULL, CHECK 等）、主キー、外部キーを設定。
    - 頻出クエリ向けのインデックスを定義。
    - init_schema(db_path) でファイル作成を含む初期化処理を実装（冪等）。get_connection を提供。

- ETL パイプライン基盤
  - src/kabusys/data/pipeline.py:
    - ETL の基本設計を実装（差分更新、バックフィル、品質チェックの連携）。
    - ETLResult dataclass を追加し、結果の構造（取得件数、保存件数、品質問題、エラー等）を統一。
    - 差分更新ヘルパ（get_last_price_date / get_last_financial_date / get_last_calendar_date）を実装。
    - 市場カレンダーを参照して営業日に調整するヘルパ（_adjust_to_trading_day）。
    - run_prices_etl（株価差分 ETL）の基本処理を実装（差分算出 → jq.fetch_daily_quotes → jq.save_daily_quotes）。バックフィル日数や id_token 注入に対応。

### 変更 (Changed)
- 初期リリースのため該当なし。

### 修正 (Fixed)
- 初期リリースのため該当なし。

### セキュリティ (Security)
- ニュース収集で以下の対策を実装：
  - defusedxml による安全な XML パース（XML パーサ攻撃への耐性）。
  - SSRF を防ぐためのリダイレクト時スキームチェックとプライベートアドレス検出（_SSRFBlockRedirectHandler, _is_private_host）。
  - レスポンスサイズ制限、gzip 解凍後のサイズチェックによりメモリ DoS / Gzip bomb を防止。
  - URL スキーム検証により file:, javascript:, mailto: 等の不正スキームを拒否。

### 注意 (Notes)
- 設定は環境変数依存の部分が多いため、本番運用前に .env.example を参考に必要な環境変数を設定してください（JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD 等）。
- DuckDB スキーマ初期化（init_schema）を最初に実行してから ETL / ニュース収集等を動作させてください。
- ETL モジュールは品質チェックモジュール（kabusys.data.quality）との連携を想定しており、品質チェック結果を ETLResult に格納します（quality モジュールは別実装）。

-----

今後の見通し:
- strategy / execution / monitoring パッケージの実装（トレード戦略、発注・約定処理、運用モニタリング）。
- テストカバレッジ拡充（ユニットテスト・統合テスト）。
- 更なる堅牢化（エラーハンドリング改善、スケーラビリティ向上）。