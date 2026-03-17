CHANGELOG
=========

すべての重要な変更点を記録します。本ファイルは Keep a Changelog の形式に準拠します。
リリースはセマンティックバージョニングに従います。

[Unreleased]
-------------

- （なし）

[0.1.0] - 2026-03-17
--------------------

Added
- パッケージ初期リリース: kabusys v0.1.0 を追加。
  - パッケージ構成:
    - kabusys (トップレベル)
      - data: データ取得・保存・ETL関連モジュール
      - strategy: 戦略モジュール（初期プレースホルダ）
      - execution: 発注/実行周り（初期プレースホルダ）
      - monitoring: 監視関連（エクスポート先として想定）
  - 公開 API:
    - kabusys.__version__ = "0.1.0"
    - kabusys.config.settings: 環境変数ベースの設定取得クラス

- 環境設定管理（src/kabusys/config.py）
  - .env/.env.local の自動ロード機能を実装（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - プロジェクトルート検出ロジックを導入（.git または pyproject.toml を基準、__file__ 起点で親ディレクトリを探索）。
  - .env パーサを実装（export プレフィックス対応、クォート内エスケープ・インラインコメント処理、トラッキングコメントの取り扱い等）。
  - 環境値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）、必須キー取得時の例外通知。
  - 標準的な設定項目を提供（J-Quants / kabuステーション / Slack / DB パス等）。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - API 呼び出しユーティリティを実装:
    - API ベース URL、レートリミット（120 req/min）に基づく固定間隔スロットリングを実装（_RateLimiter）。
    - 再試行ロジック（指数バックオフ、最大 3 回、HTTP 408/429/5xx を対象）。
    - 401 受信時の ID トークン自動リフレッシュ機構（リフレッシュは 1 回のみ）。
    - ページネーション対応（pagination_key を用いた全ページ取得）。
    - JSON デコードエラーを検出して分かりやすいエラーメッセージを出力。
    - モジュールレベルの ID トークンキャッシュを導入し、ページネーション間でトークンを共有。
  - データ取得関数:
    - fetch_daily_quotes: 株価日足（OHLCV）をページネーション対応で取得。
    - fetch_financial_statements: 財務（四半期 BS/PL）をページネーション対応で取得。
    - fetch_market_calendar: JPX マーケットカレンダーを取得。
  - DuckDB へ保存する冪等関数:
    - save_daily_quotes / save_financial_statements / save_market_calendar
    - ON CONFLICT DO UPDATE による冪等性、PK 欠損行のスキップと警告。
  - データ型変換ユーティリティ: _to_float, _to_int（"1.0" などの文字列処理や小数切捨て回避の仕様を明示）。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィード取得と記事保存パイプラインを実装:
    - fetch_rss: RSS の取得・XML パース・記事抽出（title, content, link, pubDate 等）。
    - save_raw_news: raw_news テーブルへ INSERT ... RETURNING を用いたチャンク挿入（トランザクションまとめ）。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄の紐付けを一括保存（ON CONFLICT DO NOTHING、INSERT RETURNING を使用）。
    - run_news_collection: 複数ソースの統合収集ジョブ（ソース単位で独立したエラーハンドリング）。
  - セキュリティ／堅牢性機能:
    - defusedxml を用いた XML パースで XML Bomb 等の攻撃を緩和。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - リダイレクト時にスキーム/ホストを検査するカスタムハンドラ (_SSRFBlockRedirectHandler) を利用。
      - ホスト名を DNS 解決してプライベート/ループバック/リンクローカル/マルチキャストを拒否。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES=10MB）および gzip 解凍後のサイズ検査（Gzip bomb 対策）。
    - 記事 ID の冪等性: 正規化 URL の SHA-256 の先頭 32 文字を記事 ID として採用（utm_* 等のトラッキングパラメータを除去して正規化）。
    - 受信バッファ制限、User-Agent の設定、gzip Accept-Encoding 対応。
  - テキスト前処理と抽出:
    - URL 除去・空白正規化を行う preprocess_text。
    - RFC2822 形式の pubDate パース（失敗時は警告ログと現時刻代替）。
    - 銘柄コード抽出機能 extract_stock_codes（4桁数字、known_codes によるフィルタ、重複排除）。

- DuckDB スキーマ定義（src/kabusys/data/schema.py）
  - DataSchema.md に基づく多層テーブル定義を実装:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルの制約（PRIMARY KEY、CHECK 制約、外部キー）を定義。
  - クエリ性能向上のためのインデックス定義を追加（例: idx_prices_daily_code_date 等）。
  - init_schema(db_path) により親ディレクトリ自動作成・DDL 実行・インデックス作成を行う冪等初期化 API を提供。
  - get_connection(db_path) で既存 DB へ接続可能（初回は init_schema 推奨）。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 差分更新を前提とした ETL 実装（差分取得、backfill 日数、品質チェックフックを想定）。
  - ETLResult データクラスを導入し、取得件数・保存件数・品質問題・エラーを集約。
  - 市場カレンダーを利用した営業日調整ヘルパー（_adjust_to_trading_day）。
  - get_last_price_date / get_last_financial_date / get_last_calendar_date のヘルパー関数を提供。
  - run_prices_etl の骨格（差分算出、最小データ開始日 _MIN_DATA_DATE=2017-01-01、backfill のデフォルト 3 日）を実装（fetch→save の呼び出しまでを含む）。
  - 品質チェックは別モジュール quality として分離する設計（ETL は重大エラーを検出しても収集を続行する方針）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- ニュース収集で SSRF を防ぐための複数レイヤの検査（スキーム検証、プライベートアドレス検知、リダイレクト時の検証）。
- XML パーサに defusedxml を使用して unsafe な XML を検出・防御。
- .env 読み込み時に OS 環境変数を保護する protected パラメータを導入（.env.local が OS 環境変数を上書きしないよう保護可能）。

Notes / Requirements
- 環境変数例（必須）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- デフォルト DB パス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- J-Quants API レート制限を遵守する実装（120 req/min）。
- ETL の完全実行や品質チェック連携は quality モジュールの実装が前提。

今後の予定（想定）
- strategy / execution / monitoring の具体実装（現在はパッケージ構造上のプレースホルダ）。
- quality モジュールの実実装と ETL との統合強化（エラーレポーティング・自動修復方針）。
- 単体テスト／統合テストの追加（network/mocking の整備）。
- CLI やスケジューラ連携（Cron / Airflow 等）による定期収集ジョブの提供。

-----
この CHANGELOG はコード内の実装と設計注釈（docstring、コメント）から推測して作成しています。実際のリリースノート作成時はコミット履歴・PR コメントを参照して適宜調整してください。