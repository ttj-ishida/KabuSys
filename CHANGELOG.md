# Changelog

すべての重要な変更履歴をこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]
（今後の変更をここに記載します）

## [0.1.0] - 2026-03-17
初回リリース

### Added
- パッケージ初期構成
  - パッケージメタ情報: kabusys.__version__ = 0.1.0、公開モジュール一覧を __all__ に定義。

- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込みする機構を実装。
    - プロジェクトルートの検出は __file__ を基点に .git または pyproject.toml を探索するため、CWD に依存しない。
    - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env のパースは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントなどに対応。
    - ファイル読み込み失敗時は警告を出力してスキップ。
  - Settings クラスを提供（settings インスタンス経由で利用）。
    - J-Quants / kabuステーション / Slack / DB パス 等の設定プロパティを用意。
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）。
    - duckdb/sqlite パスのデフォルトと expanduser 対応。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 基本機能
    - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得する関数を実装（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
    - 認証トークン取得関数 get_id_token を実装（リフレッシュトークンから ID トークンを取得）。
  - 信頼性・スロットリング設計
    - 固定間隔スロットリングによるレート制限（120 req/min）を実装する _RateLimiter を導入。
    - リトライロジック（最大 3 回、指数バックオフ）を実装。対象ステータスコードやネットワークエラーに対してリトライ。
    - 429 の場合は Retry-After ヘッダを優先して待機。
    - 401 受信時はトークンを自動リフレッシュして 1 回だけリトライ（allow_refresh フラグで再帰を防止）。
    - ページネーション対応（pagination_key を追跡し重複防止）。
  - データ保存
    - DuckDB へ冪等保存する save_daily_quotes / save_financial_statements / save_market_calendar を実装（INSERT ... ON CONFLICT DO UPDATE）。
    - レコードごとの PK 欠損はスキップし、スキップ件数はログ出力。
    - 取得タイミング（fetched_at）は UTC ISO8601 形式で記録（Look-ahead Bias のトレーサビリティ確保）。
  - ユーティリティ
    - _to_float / _to_int による堅牢な型変換（空値や不正値は None、"1.0" 等の扱いを考慮）。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS 収集、前処理、DB 保存、銘柄紐付けを行う一連処理を実装。
  - セキュリティ・堅牢性
    - defusedxml を使用して XML Bomb 等の攻撃を防御。
    - リダイレクト検査と SSRF 対策を含むカスタム HTTPRedirectHandler（_SSRFBlockRedirectHandler）を実装。リダイレクト先のスキームとプライベートアドレスを事前検証。
    - 初期 URL および最終 URL のスキーム検証（http/https のみ許可）、ホストのプライベートアドレスチェック。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）を設け、Content-Length および実際の読み込みで上限超過を検出。gzip 解凍後も上限を再検証（Gzip bomb 対策）。
    - URL スキーム検証で http/https 以外を拒否して SSRF や file: などを排除。
  - 機能
    - URL 正規化（クエリのトラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリソート）。
    - 記事 ID は正規化 URL の SHA-256 ハッシュ先頭32文字で生成し冪等性を保証。
    - テキスト前処理（URL 削除、空白正規化）。
    - デフォルトの RSS ソースを設定（例: Yahoo Finance のビジネスカテゴリ）。
    - fetch_rss: RSS 取得→XMLパース→記事リスト生成（content:encoded を優先して description を利用）。
    - DuckDB への保存:
      - save_raw_news はチャンク分割・トランザクション・INSERT ... ON CONFLICT DO NOTHING RETURNING を使用して実際に挿入された記事 ID を返却。
      - save_news_symbols / _save_news_symbols_bulk による (news_id, code) 紐付けをチャンク化して一括挿入（RETURNING で実挿入件数を取得）。
    - 銘柄コード抽出: 正規表現で 4 桁数字を抽出し、known_codes に存在するもののみを返す。

- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の 3 層（＋実行層）に対応したテーブル DDL を定義。
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約（PRIMARY KEY, FOREIGN KEY, CHECK 等）を追加してデータ整合性を確保。
  - 頻出クエリ用のインデックス定義を追加。
  - init_schema(db_path) で必要な親ディレクトリの自動作成、全テーブル・インデックスの冪等作成を行い DuckDB 接続を返却。
  - get_connection(db_path) で既存 DB への接続を取得（スキーマ初期化は行わない旨を明示）。

- ETL パイプラインの基礎（kabusys.data.pipeline）
  - ETLResult データクラスを導入し、ETL のメタ情報（取得件数、保存件数、品質問題、エラー等）を集約。
    - to_dict で品質問題をシリアライズ可能に変換。
  - 差分更新のためのヘルパーを実装
    - テーブル存在チェック、最大日付取得用ユーティリティ（_table_exists / _get_max_date）。
    - 市場カレンダーがある場合に非営業日を直近の営業日に調整する _adjust_to_trading_day。
    - get_last_price_date / get_last_financial_date / get_last_calendar_date を提供。
  - run_prices_etl を実装（差分取得・バックフィル機能を内包）
    - デフォルトバックフィル日数は 3 日（後出し修正の吸収）。
    - 初回ロード向けの最小日付 _MIN_DATA_DATE = 2017-01-01。
    - 実際の API 呼び出しは jquants_client を利用し、save_* で冪等保存。

### Security
- セキュリティ強化点の明記
  - defusedxml による XML パースの堅牢化。
  - SSRF 対策（スキーム/リダイレクト/プライベートホスト検査）。
  - .env ロード時に OS 環境変数を保護するための protected キー機構。
  - DuckDB に対する INSERT 文は可能な限り ON CONFLICT 句を使用し不整合な再挿入を回避。

### Notes / Design Decisions
- 多くの処理で「冪等性」を重視（ON CONFLICT / INSERT ... DO UPDATE / DO NOTHING）。
- API 呼び出しの信頼性向上のためにレート制限・リトライ・トークン自動リフレッシュを採用。
- ETL は「Fail-Fast」ではなく、品質チェックの問題を収集して呼び出し元で判断できる型に設計。
- テスト容易性のため、いくつかの低レイヤ関数（例: _urlopen や id_token の注入）を差し替え可能にしている。

### Removed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

---

注: 各モジュールの詳細な挙動や API はソースコードの docstring に記載されています。将来的なリリースでは各機能ごとに分割して変更点を記載します。