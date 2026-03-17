CHANGELOG
=========

すべての重要な変更をこのファイルに記録します。
フォーマットは「Keep a Changelog」に従っています。  

[0.1.0] - 2026-03-17
-------------------

Added
- 初期リリース。パッケージ名: kabusys、バージョン 0.1.0。
- 基本パッケージ構成を追加:
  - モジュール群: data, strategy, execution, monitoring をエクスポート。
- 設定・環境変数管理 (kabusys.config):
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml 検出）から自動読み込み。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサを実装（コメント行、export プレフィックス、クォート内エスケープ、インラインコメント処理等をサポート）。
  - 必須キー取得メソッド _require と Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB 等の設定プロパティを定義。
  - KABUSYS_ENV / LOG_LEVEL の値検証（許容値チェック）や .duckdb/.sqlite パス扱いをサポート。
  - is_live / is_paper / is_dev の便利プロパティを提供。

- J-Quants API クライアント (kabusys.data.jquants_client):
  - 株価日足、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得する API クライアントを実装。
  - レート制限対応: 固定間隔スロットリングで 120 req/min を尊重（内部 RateLimiter 実装）。
  - リトライロジック: 指数バックオフ、最大 3 回、HTTP 408/429/5xx を再試行対象に含める。
  - 401 応答時はリフレッシュトークンを用いて id_token を自動更新し 1 回だけリトライ。
  - id_token のモジュールレベルキャッシュ（ページネーション間で共有）を実装。
  - ページネーション対応（pagination_key の追跡と重複防止）。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）:
    - 挿入は冪等（ON CONFLICT DO UPDATE）で実装。
    - PK 欠損行はスキップしログ出力。
  - 型変換ユーティリティ (_to_float, _to_int) を実装し、無効値や小数切り捨ての誤適用を防止。

- ニュース収集モジュール (kabusys.data.news_collector):
  - RSS フィード取得・前処理・保存の一連処理を実装。
  - セキュアな XML パーシングに defusedxml を利用。
  - SSRF 対策:
    - URL スキーム検証（http/https のみ許可）。
    - リダイレクト先スキーム・ホストの事前検証（プライベート/ループバック/リンクローカル/マルチキャストは拒否）。
    - _SSRFBlockRedirectHandler によるリダイレクト時検査。
    - DNS 解決失敗時は安全側の挙動（通過）を採用。
  - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10 MB）および gzip 解凍後の再検査（Gzip bomb 対策）。
  - URL 正規化とトラッキングパラメータ除去（utm_* 等）、記事 ID を正規化後の URL の SHA-256（先頭32文字）で生成し冪等性を担保。
  - テキスト前処理（URL除去、空白正規化）。
  - DuckDB への保存:
    - raw_news へチャンク単位で INSERT ... ON CONFLICT DO NOTHING RETURNING id により実際に挿入された記事IDを返す。
    - news_symbols への記事-銘柄紐付けもチャンク挿入・ON CONFLICT DO NOTHING + RETURNING を利用し挿入件数を正確に返す。
  - 銘柄コード抽出ロジック（4桁数字候補を known_codes と突合して重複排除して返す）。
  - デフォルト RSS ソースに Yahoo 経済カテゴリを登録。

- DuckDB スキーマ定義・初期化 (kabusys.data.schema):
  - Raw / Processed / Feature / Execution の多層スキーマを定義し、init_schema(db_path) で初期化可能。
  - 主なテーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 適切な型チェック、NOT NULL 制約、PRIMARY KEY、FOREIGN KEY を定義。
  - 頻出クエリ向けのインデックス群を作成（例: code/date の組合せ、orders/status 等）。
  - get_connection(db_path) を提供（init_schema は別途呼び出し推奨）。

- ETL パイプライン (kabusys.data.pipeline):
  - 差分更新を行う ETL の基本設計を実装（差分算出、バックフィル、品質チェック連携のためのフック設計）。
  - ETLResult データクラスを導入し、取得件数・保存件数・品質問題・エラーを集約。品質問題は辞書化してログ/監査に出力可能。
  - DuckDB の最終取得日取得ユーティリティ（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
  - 市場カレンダーを参照して非営業日を直近営業日に調整するヘルパー (_adjust_to_trading_day)。
  - 個別 ETL ジョブの一部実装: run_prices_etl（差分算出、backfill_days 設定、jq.fetch_daily_quotes → jq.save_daily_quotes の呼び出し）を実装。初回ロードの開始日 _MIN_DATA_DATE = 2017-01-01 を使用。
  - 市場カレンダーは先読み（_CALENDAR_LOOKAHEAD_DAYS = 90 日）を考慮する設計。

Security
- defusedxml の採用、SSRF 対策、レスポンスサイズ制限、URL スキーム検証などにより外部入力処理のセキュリティを強化。
- .env 自動ロード時に既存 OS 環境変数を保護する仕組み（protected set）を導入。

Notes / Migration
- 初回利用時は schema.init_schema(db_path) を実行して DuckDB のテーブルを作成してください。
- 環境変数の設定例は .env.example を参照すること（Settings._require は未設定時に ValueError を投げます）。
- J-Quants API 利用時は JQUANTS_REFRESH_TOKEN が必要です。kabusys.data.jquants_client は自動で id_token を取得・更新しますが、テスト時は id_token を注入して挙動を安定化できます。
- RSS 収集ではデフォルトで Yahoo のビジネス RSS を利用しますが、run_news_collection の sources 引数で任意のソース辞書を指定できます。
- ログやエラー情報は各モジュールで logger を利用して出力されます。LOG_LEVEL 環境変数でログレベルを制御してください。

Acknowledgements
- 本実装では外部ライブラリ defusedxml、duckdb を利用しています。

（以降のバージョンでは、ETL の品質チェックモジュール quality の統合、strategy / execution / monitoring の具体実装、run_prices_etl の他ジョブ（財務・カレンダー・ニュース収集）との統合処理の追加が期待されます。）