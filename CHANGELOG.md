# CHANGELOG

すべての注記は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠します。  
このプロジェクトはセマンティックバージョニングに従います。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-18
初回リリース。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py によりパッケージ名と公開サブパッケージ（data, strategy, execution, monitoring）を定義。
  - バージョン情報 __version__ = "0.1.0" を追加。

- 設定・環境変数管理
  - src/kabusys/config.py を追加。
    - .env / .env.local の自動ロード機能（プロジェクトルートは .git または pyproject.toml で検出）。
    - .env ファイルの行パーサ実装（export 構文、クォートのエスケープ、インラインコメントの扱い等に対応）。
    - OS 環境変数を保護する protected パラメータと override 振る舞いの実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート（テスト用）。
    - Settings クラスにより、J-Quants / kabu / Slack / DB パス / 環境 (development/paper_trading/live) / ログレベルなどの設定取得を提供。値検証（許容値チェック）を行うプロパティ群を追加。

- J-Quants API クライアント
  - src/kabusys/data/jquants_client.py を追加。
    - 日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダー取得関数を実装（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - API レート制御（120 req/min 固定インターバルの RateLimiter）を実装してレート制限を順守。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を再試行対象）。
    - 401 Unauthorized 受信時の自動トークンリフレッシュを 1 回まで行う仕組み（get_id_token とキャッシュ）。
    - JSON デコード失敗やネットワークエラーを明示的に扱うエラーハンドリング。
    - DuckDB に対する冪等（idempotent）保存関数を提供（save_daily_quotes, save_financial_statements, save_market_calendar）。INSERT ... ON CONFLICT DO UPDATE により重複を排除。
    - レコード保存時に fetched_at を UTC ISO 形式で付与して Look-ahead bias を追跡可能に。

- ニュース収集モジュール
  - src/kabusys/data/news_collector.py を追加。
    - RSS フィード取得（fetch_rss）、前処理、記事ID生成、DuckDB 保存ロジック（save_raw_news, save_news_symbols, _save_news_symbols_bulk）を実装。
    - 記事IDは URL 正規化後の SHA-256 の先頭32文字を使用して冪等性を確保（utm_* 等のトラッキングパラメータ除去）。
    - defusedxml を用いた XML パース（XML Bomb 等への対策）。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - リダイレクト毎にスキームとホスト/IP の事前検証を行うカスタムリダイレクトハンドラ（_SSRFBlockRedirectHandler）。
      - ホストがプライベート/ループバック/リンクローカル/マルチキャストかの検査（DNS 解決と IP 判定）。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10 MB）および gzip 解凍後のサイズ検査でメモリ DoS を緩和。
    - Gzip 解凍失敗時、XML パース失敗時は安全にスキップして警告ログを出力。
    - DB への挿入はトランザクションでまとめ、INSERT ... RETURNING を利用して実際に挿入されたレコードを返す（チャンク処理により SQL 長制限を回避）。
    - テキスト前処理（URL 除去、空白正規化）、および本文から銘柄コード（4桁）を抽出する関数 extract_stock_codes を実装。
    - デフォルト RSS ソース（Yahoo Finance の business カテゴリ）を定義。

- DuckDB スキーマ
  - src/kabusys/data/schema.py を追加。
    - Raw / Processed / Feature / Execution 層のテーブル定義を網羅的に実装（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等）。
    - 各カラムの制約（PRIMARY KEY、CHECK、FOREIGN KEY）や適切な型を設定。
    - 検索パフォーマンスを考慮したインデックス群を追加。
    - init_schema(db_path) によりディレクトリ自動作成とテーブル/インデックスの冪等的作成を提供。get_connection() も提供。

- ETL パイプライン
  - src/kabusys/data/pipeline.py を追加（ETL の骨組み）。
    - 差分更新ロジック（最終取得日からの差分取得、backfill_days による後出し修正吸収）。
    - 市場カレンダーの先読み（日数指定可能）。
    - ETL 実行結果を表す ETLResult dataclass（品質チェック結果、エラー一覧、判定プロパティを含む）。
    - テーブル存在チェック、最大日付取得ヘルパー、営業日調整ロジックなどを実装。
    - run_prices_etl の骨組みを実装（fetch → save の流れ）。品質チェックモジュール（quality）との連携を想定。

### Security
- ニュース収集における SSRF 対策と XML パーサの安全化（defusedxml）を導入。
- RSS の受信サイズ制限と gzip 解凍後サイズチェックによりメモリ消費攻撃を軽減。
- URL 正規化・トラッキングパラメータ除去により、冪等性を高めつつ外部サービスへの無駄なリクエストを削減。

### Performance & Reliability
- J-Quants API クライアントで固定間隔のレートリミッタを導入し、API レート超過のリスクを低減。
- 再試行 (retry) と指数バックオフの実装により一時的なネットワーク/サーバ問題に対する堅牢性を向上。
- DuckDB へのバルク/チャンク挿入、トランザクション集約、ON CONFLICT による冪等保存で ETL の効率化を図る。

### Notes / Migration
- 初期リリースのため互換性破壊は発生していません。
- .env 自動読み込みはプロジェクトルートの検出に依存します。必要に応じて環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます（テスト用途を想定）。
- DuckDB スキーマは init_schema() で初期化してください。既存 DB を使用する場合は get_connection() を使用し、schema 初期化は行われません。

### Known limitations
- pipeline.run_prices_etl の戻り値タプル定義が未完（ファイル末尾で切れているように見える箇所があり、完全な戻り値や他の ETL ジョブ（財務・カレンダー）の run 関数は実装の継続が必要）。
- quality モジュールの具体的実装は本差分に含まれていないため、品質チェックの詳細な判定は別実装を参照する必要があります。
- strategy / execution / monitoring パッケージ本体は初期化ファイルのみで、中身は今後追加予定。

---

（今後のリリースでは各リファクタ・バグフィックス・機能追加ごとにこの CHANGELOG を更新してください。）