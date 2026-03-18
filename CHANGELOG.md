Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

[Unreleased]
-----------

- なし

[0.1.0] - 2026-03-18
--------------------

Added
- パッケージ初期リリース (kabusys v0.1.0)
  - パッケージ公開情報:
    - src/kabusys/__init__.py にて __version__ = "0.1.0"、モジュール公開 __all__ = ["data", "strategy", "execution", "monitoring"] を定義。
  - 環境設定モジュール（kabusys.config）
    - .env ファイル／環境変数の読み込み機能を実装。
    - プロジェクトルート自動検出: .git または pyproject.toml を基準に探索（CWD に依存しない実装）。
    - .env パーサーの改良:
      - export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理、コメント判定などに対応。
    - 自動ロードの優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
    - 設定アクセス用 Settings クラスを提供（J-Quants トークン、kabu API、Slack、DB パス、環境・ログレベル判定等）。入力検証（有効な env 値 / log level のチェック）を実装。
  - J-Quants API クライアント（kabusys.data.jquants_client）
    - 日足（OHLCV）、財務（四半期 BS/PL）、JPX カレンダー取得機能を実装（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
    - HTTP レート制御: 固定間隔スロットリング実装（120 req/min を想定）。
    - リトライロジック: 指数バックオフ、最大試行回数、408/429/5xx に対する再試行、429 の Retry-After 優先等。
    - 401 Unauthorized 受信時は ID トークンを自動リフレッシュして 1 回だけ再試行する仕組み。
    - ページネーション対応（pagination_key を利用し重複防止）。
    - DuckDB への冪等保存（save_daily_quotes / save_financial_statements / save_market_calendar）:
      - ON CONFLICT DO UPDATE を用いた更新、PK 欠損行のスキップログ出力、挿入件数のログ出力。
    - モジュールレベルのトークンキャッシュと id_token 注入可能性によりテスト容易性を考慮。
    - JSON デコードエラーやネットワーク例外に対する明確なエラーハンドリング。
    - 型変換ユーティリティ (_to_float / _to_int) を実装し入力の堅牢性を確保。
  - ニュース収集モジュール（kabusys.data.news_collector）
    - RSS フィードの取得、前処理、DuckDB への保存、銘柄紐付けを担う一連の処理を実装。
    - セキュリティ対策:
      - defusedxml を利用した XML パース（XML Bomb 等の対策）。
      - SSRF 対策: URL スキーム検証（http/https のみ許可）、ホストのプライベートアドレス判定（IP 直接判定および DNS 解決）、リダイレクト先の検査（カスタム RedirectHandler）。
      - レスポンス受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後サイズ検査（Gzip bomb 対策）。
      - URL 正規化でトラッキングパラメータ（utm_* 等）を除去して記事ID生成（SHA-256 の先頭32文字）に利用し冪等性を確保。
    - テキスト前処理機能（URL 除去・空白正規化）。
    - RSS パースのフォールバック（名前空間付きや非標準レイアウトに対応）。
    - DuckDB への保存:
      - save_raw_news: チャンク化（_INSERT_CHUNK_SIZE）してトランザクション内で INSERT ... ON CONFLICT DO NOTHING RETURNING id を利用し、新規挿入 ID を正確に取得。
      - save_news_symbols / _save_news_symbols_bulk: (news_id, code) ペアを一括保存、重複除去、トランザクション処理、INSERT ... RETURNING による実挿入数算出。
    - 銘柄抽出ロジック: 正規表現による 4 桁数字候補から既知銘柄セットに照合して抽出（重複排除）。
    - fetch_rss / run_news_collection でエラー隔離（1 ソース失敗でも他ソース継続）とログ出力を実装。
    - デフォルト RSS ソースに Yahoo Finance のビジネスカテゴリを登録。
    - テスト容易性: HTTP オープン処理を抽象化して _urlopen をモック可能に設計。
  - DuckDB スキーマ定義と初期化（kabusys.data.schema）
    - Raw / Processed / Feature / Execution 層を含む包括的な DDL を実装。
    - テーブル群:
      - raw_prices, raw_financials, raw_news, raw_executions
      - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
      - features, ai_scores
      - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
    - 制約・チェック・外部キーを積極採用（NOT NULL、PRIMARY KEY、CHECK、FOREIGN KEY）。
    - インデックス定義（頻出クエリ向け）を実装。
    - init_schema(db_path) で親ディレクトリ自動作成、すべての DDL/インデックスを実行して接続を返す（冪等）。
    - get_connection(db_path) により既存 DB へ接続（初期化は行わない旨を明記）。
  - ETL パイプライン（kabusys.data.pipeline）
    - 差分更新を念頭においた ETL 処理設計。
    - ETLResult データクラスを実装（取得数・保存数・品質問題・エラー等を格納、辞書化ユーティリティ付き）。
    - 差分判定ユーティリティ（テーブル存在チェック、最大日付取得）を実装。
    - 市場カレンダーに基づく非営業日調整（直近の営業日に丸めるロジック）。
    - run_prices_etl の雛形を実装（差分取得、バックフィル日数、取得 → 保存のフロー）。設計として id_token 注入可能。
    - ETL の設計方針として「Fail-Fast を避ける」「品質チェックで発見した問題は収集して報告する」を採用。
  - 汎用ユーティリティ
    - URL 正規化、記事 ID 生成、RSS 日時パース（RFC 2822 → UTC naive）、テキスト前処理、銘柄コード抽出、変換ユーティリティなどを提供。
    - ロギングを各所に適切に配置し実行状況を可視化。

Security
- ニュース収集における SSRF、XML 脆弱性、Gzip Bomb、巨大レスポンスに対する防御を実装。
- 環境読み込み時に OS 環境変数を保護する設計（protected set）。

Notes / Design
- 多くの保存処理は冪等性を重視（ON CONFLICT DO UPDATE / DO NOTHING）。
- テストしやすさを考慮し、外部依存（HTTP オープン、id_token 取得など）は注入／モック可能に設計。
- 日付/時間は UTC を基準に扱い、データ取得時刻（fetched_at）を記録して Look-ahead Bias を抑制する意図を明記。
- strategy/execution/monitoring のパッケージ構成は確立しているが、一部 __init__ はプレースホルダ（将来的な機能追加を想定）。

Breaking Changes
- 初期リリースのためなし。

Acknowledgements
- ソースコードの実装から推測して記載しました。実際の使用・運用に際しては README や DataPlatform.md / DataSchema.md 等の公式ドキュメントと合わせて確認してください。