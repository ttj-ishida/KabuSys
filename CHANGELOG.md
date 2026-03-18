CHANGELOG
=========

すべての注目すべき変更を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  
安定したバージョンはセマンティックバージョニングに従います。

[0.1.0] - 2026-03-18
-------------------

Added
- 初期リリース: KabuSys - 日本株自動売買システムの骨組みを実装。
  - パッケージ構成:
    - kabusys: パッケージ本体（__version__ = 0.1.0）。
    - サブパッケージ: data, strategy, execution, monitoring（strategy/execution は初期は空のパッケージ）。
- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込み（プロジェクトルートを .git または pyproject.toml で探索）。
  - 読み込み優先順位: OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能。
  - .env パーサは export KEY=val 形式、クォート・エスケープ、インラインコメント処理をサポート。
  - protected 引数による OS 環境変数の上書き防止ロジック。
  - Settings クラスを提供（J-Quants/ Kabu API / Slack / DB パス / 環境種別 / ログレベル等のプロパティ）。
  - env/log_level の妥当性チェックを実装（許容値セット検査）。
- J-Quants API クライアント (kabusys.data.jquants_client)
  - API 呼び出しユーティリティ:
    - 固定間隔スロットリングによるレート制限（120 req/min）。
    - 冪等性／ページネーション対応（pagination_key を利用して全件取得）。
    - 汎用的なリトライロジック（指数バックオフ、最大3回、HTTP 408/429/5xx 等を対象）。
    - 401 受信時の自動トークンリフレッシュ（1 回のみ再試行）およびモジュールレベルの ID トークンキャッシュ。
    - JSON デコード失敗検出とエラーメッセージ向上。
  - データ取得関数:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（四半期財務データ）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB への保存関数（冪等）:
    - save_daily_quotes / save_financial_statements / save_market_calendar
    - 全て ON CONFLICT DO UPDATE を使い、fetched_at を UTC で記録して Look-ahead Bias を防止。
  - 値変換ユーティリティ (_to_float / _to_int) による堅牢な型変換（不正値は None）。
- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィード取得器:
    - defusedxml を用いた安全な XML パース（XML Bomb などの脅威に対策）。
    - HTTP/HTTPS スキームのみ許可し、SSRF 攻撃防止のためにプライベートアドレスへ接続しない事前検証とリダイレクト検査。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）および gzip 解凍後のサイズ検査（Gzip bomb 対策）。
    - User-Agent / Accept-Encoding を設定してリクエスト。
    - URL 正規化（トラッキングパラメータ除去、クエリのソート、フラグメント除去）。
    - 記事 ID は正規化 URL の SHA-256（先頭32文字）を採用して冪等性を確保。
    - コンテンツ前処理（URL 除去、空白正規化）。
  - DB 保存:
    - save_raw_news: chunked バルク INSERT（チャンクサイズ制限）を行い、INSERT ... RETURNING id で新規挿入分のみを返す。トランザクション管理（commit/rollback）。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを冪等に保存（ON CONFLICT DO NOTHING、RETURNING で実挿入数を取得）。
  - 銘柄コード抽出:
    - 4桁数字パターンから known_codes に基づき有効コードのみ抽出、重複除去。
  - run_news_collection:
    - 複数 RSS ソースを順次処理（ソース毎に独立したエラーハンドリング）。新規挿入件数を集計し、既存記事には紐付けを行わない。
    - デフォルト RSS ソースとして Yahoo Finance のカテゴリフィードを登録。
- DuckDB スキーマ定義と初期化 (kabusys.data.schema)
  - DataPlatform 設計に基づく多層スキーマを実装:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに NOT NULL / CHECK / PRIMARY KEY / FOREIGN KEY 制約を付与（データ整合性重視）。
  - よく使うクエリ向けのインデックスを作成（code/date, status, signal_id など）。
  - init_schema(db_path) によりディレクトリ自動作成・DDL 実行を行い、接続を返す（冪等）。
  - get_connection(db_path) で既存 DB への接続を取得（初期化は行わない）。
- ETL パイプライン (kabusys.data.pipeline)
  - ETLResult dataclass により ETL の実行結果・品質問題・エラー情報を構造化。
  - 差分更新ヘルパー:
    - テーブル存在チェック、最大日付取得ユーティリティ（get_last_price_date / get_last_financial_date / get_last_calendar_date）。
    - 取引日調整補助（_adjust_to_trading_day）。
  - run_prices_etl（株価日足の差分 ETL）の骨組みを実装:
    - 最終取得日からの差分取得および backfill_days による再取得（デフォルト 3 日）で API 後出し修正を吸収。
    - jquants_client の fetch/save を利用した取得・保存処理（ロギング付き）。
  - 品質チェックとの連携を想定（quality モジュールと協調する設計）。
- ロギング:
  - 各モジュールで logger を使用し、重要イベント（取得件数、保存件数、警告、例外）を記録。

Security
- セキュリティに関する複数の対策を初期実装:
  - news_collector: defusedxml による XML パース、SSRF 対策（ホスト/IP のプライベート判定、リダイレクト検査）、最大レスポンスバイト制限、gzip 解凍後のサイズ検査。
  - .env ロード時に OS 環境変数が protected として上書きされないよう保護。
  - 外部 URL についてスキーム検証（http/https のみ）を徹底。

Notes
- public API（主要関数／オブジェクト）:
  - kabusys.__version__, kabusys.__all__
  - kabusys.config.settings（Settings インスタンス）
  - kabusys.data.jquants_client: get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar, save_daily_quotes, save_financial_statements, save_market_calendar
  - kabusys.data.news_collector: fetch_rss, save_raw_news, save_news_symbols, run_news_collection, extract_stock_codes 等
  - kabusys.data.schema: init_schema, get_connection
  - kabusys.data.pipeline: ETLResult, get_last_price_date, get_last_financial_date, get_last_calendar_date, run_prices_etl（その他補助関数）
- strategy / execution パッケージは初期はプレースホルダ。今後戦略実装や発注ロジックを追加予定。
- このリリースは初期実装のため、API の拡張や関数シグネチャの変更が将来発生する可能性があります。特にパイプラインの振る舞い（バックフィル方針・品質チェックの処理方針など）は今後調整される見込みです。

未解決 / TODO（今後の改善候補）
- quality モジュール（品質チェック）の実装・統合（pipeline は品質チェックを利用する設計になっている）。
- run_prices_etl の更なる機能追加（並列化、より細かい差分計算、ログ/監査の強化）。
- strategy / execution 層の具体実装（シグナル生成、注文発行・リトライ、ポジション管理）。
- 単体テスト／統合テストの充実（ネットワーク依存部のモック化や fixture 整備）。
- ドキュメント（DataPlatform.md, API 使用例、運用ガイド）の整備。