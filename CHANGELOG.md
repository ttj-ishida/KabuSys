# CHANGELOG

すべての変更は Keep a Changelog の形式に従い、セマンティック バージョニングを採用します。  
詳細: https://keepachangelog.com/ja/

## [0.1.0] - 2026-03-18

初回リリース。本パッケージは日本株の自動売買・データ基盤を構成するコア機能を含みます。主な追加点は以下のとおりです。

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - パッケージ API を公開するための __all__ に data/strategy/execution/monitoring を追加。

- 環境設定管理 (kabusys.config)
  - .env/.env.local を含む環境変数自動ロード機能を実装。
    - プロジェクトルートを .git または pyproject.toml で検出して読み込み（カレントワーキングディレクトリ非依存）。
    - 読み込み順序: OS 環境 > .env.local > .env。OS 環境を保護するため .env の上書き制御あり。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用途を想定）。
  - .env パーサ実装:
    - export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメントの扱いなどの堅牢なパース。
  - Settings クラス:
    - J-Quants / kabuステーション / Slack / DB パス等の必須/省略可能設定をプロパティで提供。
    - KABUSYS_ENV と LOG_LEVEL の許容値チェック（不正値は ValueError）。
    - duckdb/sqlite の既定パス、env 判定ユーティリティ(production/paper/dev)。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - データ取得:
    - 日次株価 (OHLCV)、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得する API 呼び出しを実装。
    - ページネーション対応（pagination_key による繰り返し取得）。
  - レート制御 & リトライ:
    - 固定間隔スロットリングでレート制限（120 req/min）に対応する RateLimiter 実装。
    - 再試行ロジック（指数バックオフ、最大 3 回、対象ステータス 408/429/5xx）。
    - 429 の Retry-After ヘッダ優先処理。
  - 認証:
    - リフレッシュトークンから id_token を取得する get_id_token() を実装。
    - 401 を受けた場合は id_token を自動リフレッシュして 1 回リトライ。ページネーション間でモジュールレベルのトークンキャッシュを共有。
  - データ保存:
    - DuckDB への保存関数 save_daily_quotes / save_financial_statements / save_market_calendar を実装。
    - fetched_at を UTC で記録し Look-ahead bias を防止。
    - 冪等性を考慮し ON CONFLICT DO UPDATE を使って重複/更新を処理。
  - 型安全な変換ユーティリティ (_to_float, _to_int) を提供。

- ニュース収集 (kabusys.data.news_collector)
  - RSS 取得 + 前処理 + DB 保存のフローを実装:
    - fetch_rss(): RSS を取得して NewsArticle 型のリストを返却。
    - preprocess_text(): URL 除去・空白正規化を実装。
    - _normalize_url(), _make_article_id(): URL 正規化と SHA-256 ベース（先頭32文字）での記事ID生成により冪等性を確保（utm_* 等トラッキングパラメータ除去）。
    - defusedxml を利用して XML 攻撃対策。
    - レスポンス最大サイズ制限（10 MB）と gzip 解凍後の検査による DoS 対策。
    - SSRF 対策:
      - リダイレクト時にスキーム検証と内部アドレス検査を行うカスタムリダイレクトハンドラを実装。
      - 初回および最終 URL のホストがプライベート/ループバック/リンクローカルでないかを検査。
    - save_raw_news(): DuckDB に一括挿入（チャンク単位）し、INSERT ... RETURNING で実際に挿入された記事 ID を返す（ON CONFLICT DO NOTHING）。
    - news_symbols 連携:
      - extract_stock_codes(): テキストから 4 桁銘柄コード抽出（known_codes フィルタ）。
      - save_news_symbols / _save_news_symbols_bulk(): news_id と銘柄コードの紐付けを一括かつ冪等に保存（RETURNING で挿入数取得）。
    - run_news_collection(): 複数 RSS ソースを巡回して個別にエラーハンドリングしつつ DB 保存、銘柄紐付けまで実行。

- DuckDB スキーマ定義と初期化 (kabusys.data.schema)
  - DataSchema.md に基づく多層スキーマを実装:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型・チェック制約、プライマリキー・外部キーを設定。
  - 頻出クエリ向けインデックスも定義。
  - init_schema(db_path) で DB ファイルの親ディレクトリ自動作成後に全テーブルを idempotent に作成し DuckDB 接続を返す。
  - get_connection(db_path) で既存 DB への接続を返す（初期化は行わない）。

- ETL パイプライン (kabusys.data.pipeline)
  - 差分更新型 ETL の基盤を実装:
    - ETLResult dataclass により実行結果・品質問題・エラーの集約を実現。
    - 最終取得日の判定ユーティリティ (get_last_price_date / get_last_financial_date / get_last_calendar_date) を実装。
    - 市場カレンダーに基づく営業日調整機能 (_adjust_to_trading_day) を実装。
    - run_prices_etl()（株価差分ETL）を実装（差分算出、backfill_days による後出し修正吸収、J-Quants からの取得と保存処理）。  
      ※ run_prices_etl() はコード末尾でタプルを返すところまで実装されています（fetch/save の呼び出し・ログ出力含む）。
  - 設計方針として品質チェックモジュールと連携する想定（quality モジュールを参照）。

### 変更 (Changed)
- 初回リリースにつき該当なし。

### 修正 (Fixed)
- 初回リリースにつき該当なし。

### セキュリティ (Security)
- XML パースに defusedxml を採用し XML 関連攻撃を軽減。
- RSS 取得時に SSRF を防ぐためのリダイレクト検査とプライベートアドレス検査を実装。
- レスポンスサイズ制限（MAX_RESPONSE_BYTES）と gzip 解凍後の再チェックにより、メモリ DoS や Gzip bomb を緩和。
- URL 正規化とトラッキングパラメータ除去により、冪等性・プライバシー面を改善。

### 既知の制限 / 注意点 (Notes)
- 一部のモジュール（strategy、execution、monitoring）の __init__ はプレースホルダ的に存在しますが、具体的な戦略ロジックや発注実装は別途実装が必要です。
- run_news_collection の銘柄抽出は known_codes を渡す必要があります（渡さない場合は紐付けをスキップ）。
- get_id_token は settings.jquants_refresh_token に依存するため、環境変数 JQUANTS_REFRESH_TOKEN の設定が必須です。
- DuckDB の初期化は init_schema() を推奨します。get_connection() は既存スキーマを前提とします。
- pipeline.run_prices_etl と他 ETL ジョブは品質チェックモジュール (kabusys.data.quality) と連携する設計を想定しており、quality モジュールの実装が必要です。

---

今後の予定（例）
- strategy / execution の具体的なシグナル生成・送信機能の実装
- 監視・アラート（Slack 通知等）の追加（monitoring）
- quality モジュールの実装と ETL 実行ワークフローの完全統合
- テストカバレッジの拡充および CI ワークフロー整備

もし CHANGELOG に追記したい詳細（例: 追加した RSS ソース一覧、各関数の挙動変更履歴など）があれば教えてください。必要に応じてエントリを分割してより細かく記載します。