# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
このプロジェクトの起点バージョンを 0.1.0 として記載しています。

[Unreleased]
- 開発中の変更はここに記載します。

[0.1.0] - 2026-03-18
====================

Added
-----
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0"、公開サブパッケージ一覧を定義。

- 環境・設定管理
  - 環境変数自動ロード機能を実装（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml から検出して .env / .env.local を自動読み込み（優先順位: OS 環境 > .env.local > .env）。
    - 自動ロードを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env パーサは export プレフィックス、引用符（シングル/ダブル）、インラインコメント、エスケープを考慮してパース。
    - protected 引数による OS 環境変数の上書き防止機能を実装。
  - Settings クラスを提供し、主要設定をプロパティ経由で取得する API を提供:
    - J-Quants, kabuAPI, Slack, DB パス (DuckDB/SQLite), 環境種別（development/paper_trading/live）やログレベルの検証など。
    - env/log_level は許容値チェックを行い、不正な値は ValueError を発生させる。

- J-Quants API クライアント
  - src/kabusys/data/jquants_client.py を実装。
    - API 呼び出しの共通ユーティリティ (_request) を提供。
    - レート制限（120 req/min）を遵守する固定間隔スロットリング実装（_RateLimiter）。
    - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx をリトライ対象）、429 の場合は Retry-After を優先。
    - 401 受信時の自動トークンリフレッシュを 1 回許可（無限再帰を防止）。
    - ページネーション対応（pagination_key を追跡）。
    - get_id_token（refresh_token から idToken を取得）を実装。
    - データ取得関数: fetch_daily_quotes、fetch_financial_statements、fetch_market_calendar。
    - DuckDB へ冪等に保存する save_daily_quotes、save_financial_statements、save_market_calendar を実装（ON CONFLICT DO UPDATE）。
    - 各保存処理は fetched_at を UTC ISO8601 形式で記録。
    - 型変換ユーティリティ (_to_float, _to_int) を実装し、安全に数値変換を行う。

- ニュース収集モジュール
  - src/kabusys/data/news_collector.py を実装。
    - RSS フィード取得 (fetch_rss) と記事整形（preprocess_text）機能を提供。
    - セキュリティ重視の設計:
      - defusedxml を用いた XML パース（XML Bomb 等の対策）。
      - SSRF 対策: HTTP リダイレクト先のスキームとホスト検査、プライベート IP の判定（DNS 解決含む）、リダイレクトハンドラ実装。
      - URL スキーム検証（http/https のみ許可）。
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の再チェックを実施（Gzip bomb 対策）。
    - 記事ID を URL 正規化後の SHA-256 の先頭 32 文字で生成し冪等性を確保（utm_* などのトラッキングパラメータを除去）。
    - fetch_rss は content:encoded を優先、pubDate のパース（タイムゾーンを UTC に正規化）を行う。
    - DB 保存関数:
      - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING を用い、チャンク単位（1000 件）でトランザクション内に保存し、新規挿入された記事IDリストを返す。
      - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの記事と銘柄コードの紐付けを一括挿入（ON CONFLICT DO NOTHING + RETURNING）し、正確な挿入件数を返す。
    - 銘柄コード抽出機能（extract_stock_codes）: 正規表現で 4 桁数字を検出し、known_codes に照合して一意に返す。
    - 統合収集ジョブ run_news_collection を実装（複数ソースを独立して処理し、既存エラーがあっても他ソースは継続）。

- DuckDB スキーマ管理
  - src/kabusys/data/schema.py を実装。
    - Raw / Processed / Feature / Execution の 3 層（＋Execution）スキーマを DDL で定義。
    - 主要テーブル:
      - raw_prices, raw_financials, raw_news, raw_executions
      - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
      - features, ai_scores
      - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
    - 適切なデータ型、チェック制約（CHECK）、外部キー、PRIMARY KEY を設定。
    - よく使うクエリ向けのインデックスを作成（例: idx_prices_daily_code_date 等）。
    - init_schema(db_path) でデータベースファイルの親ディレクトリ自動作成およびテーブル/インデックス作成を行う（冪等）。
    - get_connection(db_path) を提供（スキーマ初期化は行わない）。

- ETL パイプライン
  - src/kabusys/data/pipeline.py を実装（ETL の運用ロジック）。
    - ETLResult データクラスを導入し、取得・保存数、品質問題、エラーを収集・表現する API を提供。
    - DB の最終取得日を確認するユーティリティ（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
    - 営業日調整ヘルパー (_adjust_to_trading_day) を実装（market_calendar を参照して直近の営業日に補正）。
    - 差分更新ロジック: run_prices_etl にて最終取得日の backfill（デフォルト 3 日）を考慮し差分取得を行う。取得範囲の自動算出、J-Quants からの取得・DuckDB への保存を行う。
    - 品質チェックモジュール（quality）と連携する設計（品質問題は収集し ETLResult に格納、致命的でも全件収集を優先する方針）。

Changed
-------
- （初出）初版のため過去の変更なし。

Fixed
-----
- （初出）初版のため修正履歴なし。

Security
--------
- ニュース収集モジュールで SSRF 対策、defusedxml の採用、レスポンスサイズ制限、gzip 解凍後の再チェックを実装。
- J-Quants クライアントではトークンの安全なリフレッシュ（無限ループ防止）とタイムアウトを設定。

Notes / Implementation details
------------------------------
- .env のパースは shell スタイルに近い挙動を再現しており、引用符・エスケープ・コメント処理を考慮していますが、すべてのケースを網羅するわけではありません。複雑な .env を使用する場合は注意してください。
- jquants_client._request は urllib を直接利用する同期実装です。大量並列での呼び出しはレート制御やスレッド同期等に注意が必要です（現状はモジュールレベルの単純スロットリング）。
- DuckDB への大量 INSERT はチャンク化して実行していますが、大規模データを扱う際は I/O チューニングや VACUUM / コンパクション等の運用検討が推奨されます。
- run_prices_etl 等の ETL 関数はテスト容易性のため id_token 注入をサポートしています。

Acknowledgements
----------------
- RSS XML の安全なパースに defusedxml を利用。
- 内部設計は DataPlatform.md / DataSchema.md 相当の設計方針に基づいています（コード内コメント参照）。

----

リリースに関する追加のご希望（例: 変更点の粒度を細かく分ける、英語版 CHANGELOG の作成、各モジュールごとのリリースノート生成など）があればお知らせください。