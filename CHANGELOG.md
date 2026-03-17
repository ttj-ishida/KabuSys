CHANGELOG
=========

すべての注目すべき変更はこのファイルに記載します。フォーマットは Keep a Changelog に準拠しています。
タグ付けと日付はソースコードから推測した初期リリース情報に基づきます。

Unreleased
----------

（未リリースの変更はここに記載します）

[0.1.0] - 2026-03-17
-------------------

Added
- 初期リリース: KabuSys — 日本株自動売買システムのコア実装を追加。
  - パッケージバージョン: 0.1.0 (src/kabusys/__init__.py)
  - パッケージ公開 API: data, strategy, execution, monitoring をエクスポート。

- 環境・設定管理 (src/kabusys/config.py)
  - .env / .env.local および OS 環境変数からの自動読み込みを実装。
  - プロジェクトルート検出: .git または pyproject.toml を基準にルートを特定（パッケージ配布後の動作を考慮）。
  - 自動ロードの無効化オプション: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサを強化:
    - export KEY=val 形式対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理。
    - 無効行（コメントや不正フォーマット）の無視。
  - Settings クラスを追加し、J-Quants / kabu / Slack / DB / システム設定をプロパティとして取得・検証。
    - 環境変数必須チェック（_require）
    - KABUSYS_ENV / LOG_LEVEL の検証（許可値を限定）
    - duckdb/sqlite パスの Path 返却、is_live / is_paper / is_dev の便宜メソッド。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得 API 実装。
  - レート制限管理: 固定間隔スロットリングで 120 req/min を厳守する RateLimiter を実装。
  - リトライ戦略: 指数バックオフ、最大 3 回、408/429/5xx を対象。429 の Retry-After を尊重。
  - 認証トークン自動リフレッシュ: 401 受信時に refresh を行い 1 回だけリトライ。ID トークンのモジュールキャッシュを導入（ページネーション間で共有）。
  - ページネーション対応の fetch_* 関数 (fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar)。
  - DuckDB への保存関数 (save_daily_quotes, save_financial_statements, save_market_calendar) は冪等性を確保（ON CONFLICT DO UPDATE）。
  - fetched_at を UTC で記録し、Look-ahead Bias を防止する設計。
  - 型変換ユーティリティ (_to_float, _to_int) を追加し、安全な数値変換を実現。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィード取得と raw_news への保存機能を実装。デフォルト RSS ソースに Yahoo Finance を設定。
  - セキュリティ・堅牢性:
    - defusedxml による XML パース（XML Bomb 等の対策）。
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、ホストのプライベートアドレス検査、リダイレクト時の事前検証用 RedirectHandler。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）、gzip 解凍後のサイズチェック（Gzip bomb 対策）。
    - トラッキングパラメータ（utm_*, fbclid 等）の除去、URL 正規化。
    - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を担保。
  - テキスト前処理（URL 除去、空白正規化）、RSS pubDate の安全なパース（UTC に正規化）を実装。
  - DB 保存:
    - save_raw_news: チャンク化して INSERT ... ON CONFLICT DO NOTHING RETURNING id を使用し、新規挿入 ID を返却。トランザクションでまとめて実行。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄の紐付けを一括保存（ON CONFLICT で重複を無視）。トランザクション処理およびチャンク分割を実装。
  - 銘柄コード抽出: 4桁数字パターンを使い、known_codes と照合して重複を除去して返す extract_stock_codes を提供。
  - run_news_collection: 複数 RSS ソースを処理し、失敗しても他ソースに影響させず結果を集約するジョブ実装。

- DuckDB スキーマ定義 (src/kabusys/data/schema.py)
  - Raw / Processed / Feature / Execution の 3 層に対応するテーブル群を定義。
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な制約（PRIMARY KEY / CHECK / FOREIGN KEY）を設定。
  - 頻出クエリ向けのインデックスを定義（code/date、status 等）。
  - init_schema(db_path) でディレクトリ作成 → テーブル・インデックス作成（冪等）、get_connection を提供。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - ETLResult dataclass により ETL 実行結果（取得数・保存数・品質問題・エラー）を集約。
  - 差分更新ロジック:
    - get_last_price_date/get_last_financial_date/get_last_calendar_date などの補助。
    - 市場カレンダーを用いた非営業日の調整（_adjust_to_trading_day）。
    - run_prices_etl: 差分更新、バックフィル（デフォルト 3 日）、最小データ日（2017-01-01）を考慮した取得と保存の実装。
  - 品質チェックのフック（quality モジュールとの連携を想定）と、ETL の継続方針（Fail-Fast ではなく呼び出し元に判断を委ねる設計）。

Security
- RSS/HTTP 周りに対する複数のセキュリティ対策を導入:
  - defusedxml による安全な XML パース
  - URL スキーム検証（http/https のみ）
  - プライベートアドレス（ループバック・リンクローカル等）へのアクセス拒否
  - リダイレクト時の事前検証ハンドラ
  - レスポンスサイズ上限と Gzip 解凍後の再チェック（Dos/Gzip bomb 対策）

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Notes / Implementation details
- 各種保存処理は DuckDB の SQL（ON CONFLICT / RETURNING）を利用して冪等性と正確な差分検出を実現。
- J-Quants API クライアントはネットワーク・HTTP エラーや 401 リフレッシュのケースを考慮した頑健な実装になっているため、長時間のバッチ実行に適している。
- コードコメント・ドキュメント文字列で設計意図（Look-ahead Bias 回避、トランザクションまとめ、チャンク処理など）が明示されている。

Authors
- ソースコード内の実装に基づき作成（リポジトリのコントリビュータ情報はソースに含まれていません）。

ライセンスやリポジトリ管理（タグ付け、リリース手順など）は別途ドキュメント化してください。