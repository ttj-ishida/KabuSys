CHANGELOG
=========

すべての重要な変更点を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。

フォーマット:
- 重大な変更は各リリース見出しの下にカテゴリ（Added, Changed, Fixed, Security 等）で整理しています。
- 日付はリリース日を示します。

Unreleased
----------

（現在未リリースの変更はありません）

[0.1.0] - 2026-03-18
-------------------

Added
- 初回リリース: KabuSys — 日本株自動売買システムの基礎機能を実装。
  - パッケージ構成
    - kabusys パッケージを追加。公開モジュール: data, strategy, execution, monitoring。
    - バージョン定義: __version__ = "0.1.0"（src/kabusys/__init__.py）。
  - 環境設定管理（src/kabusys/config.py）
    - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートの .git / pyproject.toml を基準に探索）。
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - .env/.env.local のロード順序と override/protected の仕組みを実装。
    - 必須設定取得ヘルパー _require と Settings クラス（J-Quants, kabu API, Slack, DB パス, 環境判定、ログレベル検証等）。
    - KABUSYS_ENV と LOG_LEVEL の入力検証（許容値チェック）。
  - J-Quants API クライアント（src/kabusys/data/jquants_client.py）
    - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得関数を実装。
    - レート制限対応: 固定間隔スロットリング（120 req/min）を実装する RateLimiter。
    - リトライ戦略: 指数バックオフ／最大3回、408/429/5xx を対象。429 の Retry-After を優先。
    - 401 発生時はリフレッシュトークンから自動で id_token を再取得して 1 回リトライする仕組み。
    - ページネーション対応（pagination_key を使ったループ）を実装。
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）は冪等性を確保（ON CONFLICT DO UPDATE）。
    - データ変換ユーティリティ（_to_float, _to_int）を追加し、型安全に変換。
    - fetched_at に UTC タイムスタンプを格納し Look-ahead Bias のトレースを可能に。
  - ニュース収集モジュール（src/kabusys/data/news_collector.py）
    - RSS フィードから記事を取得して raw_news に保存するパイプラインを実装。
    - 設計上の安全・堅牢機能:
      - defusedxml を使用した XML パースで XML Bomb 等の攻撃に対処。
      - SSRF 対策: URL スキーム検証（http/https のみ許可）、ホストのプライベートアドレス判定、リダイレクト検査用ハンドラ実装（_SSRFBlockRedirectHandler）。
      - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10 MB）および gzip 解凍後の検査（Gzip bomb 対策）。
      - トラッキングパラメータ（utm_*, fbclid 等）を削除する URL 正規化および記事ID の SHA-256（先頭32文字）生成による冪等化。
      - テキスト前処理（URL 除去・空白正規化）。
      - DuckDB へのバルク挿入はチャンク化・トランザクションで安全に処理、INSERT ... RETURNING を用いて実際に挿入された件数を返却。
    - 銘柄コード抽出機能（4桁数字・known_codes フィルタ）。
    - run_news_collection により複数 RSS ソースの収集を統合。ソース単位で個別にエラーハンドリング（1ソース失敗でも他は継続）。
  - DuckDB スキーマ定義（src/kabusys/data/schema.py）
    - DataPlatform 設計に基づく 3 層（Raw / Processed / Feature）＋ Execution 層のテーブル群を定義する DDL を実装。
    - 主なテーブル: raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等。
    - 各種 CHECK 制約、PRIMARY/FOREIGN KEY、インデックス定義を追加。
    - init_schema(db_path) による初期化ユーティリティ、get_connection() を提供。
  - ETL パイプライン基礎（src/kabusys/data/pipeline.py）
    - 差分更新の概念を導入（最終取得日から backfill_days を遡って再取得）。
    - 市場カレンダーの先読み（デフォルト lookahead 値）。
    - ETLResult データクラスにより ETL 実行結果（取得数、保存数、品質問題、エラー）を集約。
    - テーブル存在チェック、最大日付取得ユーティリティ（_table_exists, _get_max_date）を実装。
    - run_prices_etl の骨格を実装（差分計算、fetch → save の流れ）。
  - その他
    - モジュールのロギング（logger）を適所に配置して実行状況・警告を記録。

Security
- ニュース収集に関する複数のセキュリティ対策を導入:
  - defusedxml による安全な XML パース。
  - SSRF 防止のためスキーム検証、プライベートアドレス検査、リダイレクト時の検査を実装。
  - レスポンスサイズ制限と gzip 解凍後再チェックによるメモリ DoS / Gzip bomb 対策。
- J-Quants クライアントでは認証トークン管理と自動リフレッシュ（401 ハンドリング）を実装。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Notes / Usage
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等は Settings 経由で取得され、未設定時は ValueError を送出します。
- DuckDB のスキーマ初期化は init_schema(db_path) を使用してください（初回のみ実行）。
- ニュース収集で抽出する銘柄コードは known_codes に有効なコードセットを渡すことで絞り込み可能です。
- 自動 .env ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

今後の予定
- ETL の完全実装（品質チェックモジュールとの連携、run_prices_etl の最終戻り値整備など）。
- strategy / execution / monitoring 各モジュールの実装拡張（現状はパッケージプレースホルダ）。
- 単体テスト・統合テストの追加（ネットワーク/外部APIのモックを含む）。