Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは「Keep a Changelog」規約に従います。  

----


Unreleased
----------

（現在のリリース履歴は下記 v0.1.0 を参照してください）




0.1.0 - 2026-03-18
------------------

Added
- 基本パッケージ初期構成を追加
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`。
  - パッケージ公開 API: data, strategy, execution, monitoring（モジュールの雛形を含む）。
- 環境設定管理モジュールを追加（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルート判定: `.git` または `pyproject.toml` を基準）。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env のパース機能を実装（export 構文、クォート、コメント処理、エスケープ対応）。
  - 設定オブジェクト `settings` を追加し、J-Quants / kabu API / Slack / DB パス / システム設定をプロパティ経由で取得可能。
  - KABUSYS_ENV, LOG_LEVEL の妥当性検証（限定値チェック）と利便性プロパティ（is_live/is_paper/is_dev）。
  - 必須環境変数未設定時にわかりやすいエラーメッセージを送出する `_require` を実装。
- J-Quants API クライアントを追加（kabusys.data.jquants_client）
  - データ取得: 日足（OHLCV）, 財務（四半期BS/PL）, JPX マーケットカレンダーを取得する関数を提供（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
  - レート制限対応: 固定間隔スロットリング（120 req/min）を守る内部 RateLimiter。
  - リトライ機構: 指数バックオフによる最大3回の再試行、408/429/5xx を再試行対象として扱う。429 の場合は Retry-After ヘッダを尊重。
  - 401 応答時の自動トークンリフレッシュを1回行い再試行（無限再帰防止のため一部呼出しではリフレッシュ無効化）。
  - ページネーション対応: pagination_key を用いたページ連結処理（ページ間でトークンを共有するキャッシュ対応）。
  - 保存機能: DuckDB に対する保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。いずれも冪等性を担保（INSERT ... ON CONFLICT DO UPDATE）。
  - データの取得時刻（fetched_at）を UTC で記録し、Look-ahead Bias を防止するトレーサビリティを提供。
  - 数値変換ユーティリティ（_to_float / _to_int）で不正値に耐性を持たせる。
- ニュース収集モジュールを追加（kabusys.data.news_collector）
  - RSS フィードから記事を収集して raw_news に保存する一連の処理を実装（fetch_rss / save_raw_news / save_news_symbols / run_news_collection 等）。
  - セキュリティ対策:
    - defusedxml を用いた安全な XML パース（XML Bomb 等の防御）。
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、ホストがプライベート/ループバック/リンクローカルでないことを検査（DNS 解決・IP 判定）、リダイレクト先の事前検証（カスタム RedirectHandler）。
    - レスポンス読み込みサイズ上限（MAX_RESPONSE_BYTES = 10MB）を設け、Gzip 解凍後もサイズチェックを行う（Gzip bomb 対策）。
  - 記事ID の決定方法: URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）後に SHA-256 の先頭32文字を採用し冪等性を確保。
  - テキスト前処理: URL 除去・空白正規化を実装（preprocess_text）。
  - 銘柄コード抽出: 正規表現による 4 桁数字抽出と known_codes によるフィルタ（extract_stock_codes）。
  - DB 保存のバルク処理: チャンク分割・トランザクション管理・INSERT ... RETURNING を使用して実際に挿入された ID や件数を正確に取得。
  - 既定 RSS ソースを提供（例: Yahoo Finance カテゴリ RSS）。
- DuckDB スキーマ管理モジュールを追加（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の各レイヤに対応するテーブル定義を追加（raw_prices, raw_financials, raw_news, market_calendar, prices_daily, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance など多数）。
  - 各テーブルに適切な型・チェック制約・プライマリキー・外部キーを定義。
  - インデックス定義（頻出クエリ向け）を用意。
  - スキーマ初期化関数 init_schema(db_path) を提供（親ディレクトリ自動作成、":memory:" 対応、冪等でテーブル作成）。
  - 既存 DB へ接続する get_connection(db_path) を提供（スキーマ初期化は行わない）。
- ETL パイプライン基盤を追加（kabusys.data.pipeline）
  - ETL の設計に基づく差分更新・保存・品質チェックの骨格を実装。
  - ETLResult dataclass を導入し、処理結果・品質問題・エラーを集約して返却可能（to_dict によるシリアライズ対応）。
  - 差分更新補助: DB の最終取得日を調べるユーティリティ（get_last_price_date / get_last_financial_date / get_last_calendar_date）。
  - 市場カレンダー補正ヘルパー（_adjust_to_trading_day）を実装。
  - run_prices_etl を含む個別 ETL ジョブの骨格（差分算出、バックフィル日数 _DEFAULT_BACKFILL_DAYS）を実装。J-Quants クライアントの fetch_* / save_* を利用して取得・保存を実施し、取得件数／保存件数を返す設計。
  - 品質チェック連携ポイント（quality モジュール）を想定し、品質問題を記録する仕組み（パイプライン単位で継続実行する方針）。
- その他ユーティリティ
  - URL 正規化、トラッキングパラメータ除去、RSS pubDate の堅牢なパース（タイムゾーン処理）等のユーティリティを実装。

Security
- RSS/HTTP 関連で SSRF と XML 攻撃に対する多重防御を実装（スキーム検証、プライベート IP 判定、リダイレクト検査、defusedxml 使用、サイズ上限）。
- J-Quants クライアントではトークンの安全なリフレッシュと再試行方針を導入。

Changed
- 初期リリースのため変更履歴はありません（今後のバージョンで記録します）。

Fixed
- 初期リリースのため修正履歴はありません。

Notes / Migration
- .env 自動ロードはパッケージ初期化時にプロジェクトルートを探索して行われます。テストや特殊環境で自動ロードを抑止するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 必須の環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）は未設定時に ValueError を送出します。`.env.example` に従って設定を行ってください。
- DuckDB スキーマの初期化は init_schema() を呼び出して行ってください。既存 DB を使う場合は get_connection() を用いて接続し、初回のみ init_schema() を実行してください。

---- 

今後の予定（例）
- ETL の品質チェック実装（quality モジュールの具体実装とルール化）
- モニタリング／通知（Slack 連携の実装）
- strategy / execution モジュールの具備（シグナル生成・注文送信ロジック）
- 単体テスト・統合テストの追加（ネットワーク依存部分のモック容易化を継続）