# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-03-17

初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。

### Added
- パッケージ基礎
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - パッケージ公開モジュール一覧: data, strategy, execution, monitoring（各パッケージのエントリポイントを確立）。

- 設定 / 環境変数管理（kabusys.config）
  - .env / .env.local ファイルと OS 環境変数を統合して設定を読み込む自動ロード機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - プロジェクトルートは .git または pyproject.toml から探索（__file__ を起点に親ディレクトリ走査）。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト用途）。
  - .env ファイルの行パーサを実装（export KEY=val 形式、クォート対応、インラインコメント処理）。
  - .env 読み込み時に OS 環境変数を保護する protected セットを導入し、.env.local による上書きや保護対象の扱いを制御。
  - 必須設定取得ヘルパー `_require()` を実装（未設定時は ValueError を送出）。
  - Settings クラスを追加し、J-Quants / kabuステーション / Slack / DB パス / システム設定をプロパティで露出。
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の値検証を実装。
    - duckdb/sqlite の既定パスを提供（expanduser 対応）。
    - is_live / is_paper / is_dev のユーティリティプロパティを追加。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - ベース実装を追加。以下の特徴を実装:
    - レート制御: 固定間隔スロットリングで 120 req/min（_RateLimiter）。
    - 再試行ロジック: 指数バックオフ／最大 3 回、408/429/5xx をリトライ対象。429 の場合は Retry-After ヘッダを優先。
    - 401 受信時の自動トークンリフレッシュを1回だけ行い再試行（再帰を防止する allow_refresh フラグ）。
    - id_token のモジュールレベルキャッシュを導入し、ページネーション間で共有。
    - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar のページネーション対応取得関数を実装。
    - save_daily_quotes / save_financial_statements / save_market_calendar による DuckDB への冪等保存（ON CONFLICT DO UPDATE）を実装。
      - 各保存は fetched_at を UTC ISO 形式で記録。
      - PK 欠損行はスキップして警告を出力。
    - JSON デコードエラーやネットワークエラー時の明確なエラーメッセージとログ出力を実装。
    - 型変換ユーティリティ `_to_float` / `_to_int` を実装（空値・変換失敗時は None）。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからニュース記事を取得して raw_news に保存する収集パイプラインを実装。
    - デフォルト RSS ソース（Yahoo Finance のビジネスカテゴリ）を定義。
    - URL 正規化: スキーム/ホスト小文字化、トラッキングパラメータ（utm_* 等）除去、フラグメント削除、クエリパラメータソートを実装。
    - 記事 ID は正規化後の URL を SHA-256 でハッシュし先頭32文字を利用（冪等性確保）。
    - defusedxml を使用して XML 関連の脅威を軽減。
    - SSRF 対策:
      - 非 http/https スキーム拒否。
      - リダイレクト先のスキームとホストを検査するカスタムリダイレクトハンドラ（_SSRFBlockRedirectHandler）。
      - ホストがプライベート/ループバック/リンクローカル/マルチキャストかを判定してブロック（_is_private_host）。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の再チェック（Gzip bomb 対策）。
    - RSS の pubDate パースを UTC naive datetime に正規化（失敗時は警告ログと現在時刻で代替）。
    - preprocess_text：URL 除去・空白正規化を実装。
    - fetch_rss：XML パース失敗時は警告ログを出力して空リストを返すなど堅牢なエラーハンドリング。
    - DB 保存:
      - save_raw_news：チャンク単位で INSERT ... ON CONFLICT DO NOTHING RETURNING id を使い、新規挿入 ID リストを返却。トランザクションでまとめて実行。
      - save_news_symbols / _save_news_symbols_bulk：記事と銘柄コードの紐付けを一括挿入（重複排除、チャンク処理、トランザクション、INSERT ... RETURNING ベースで実挿入数を正確に返す）。
    - 銘柄コード抽出（extract_stock_codes）：4桁数字パターンを候補とし、known_codes に含まれるもののみを返す（重複除去）。

- DuckDB スキーマ定義（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層にわたる包括的な DDL を追加。
    - raw_prices, raw_financials, raw_news, raw_executions などの Raw テーブル。
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols などの Processed テーブル。
    - features, ai_scores などの Feature テーブル。
    - signals, signal_queue, orders, trades, positions, portfolio_targets, portfolio_performance などの Execution テーブル。
  - 各テーブルに対する適切な制約（PRIMARY KEY / CHECK / FOREIGN KEY）を定義。
  - 頻出クエリ向けのインデックス群を追加（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
  - init_schema(db_path)：親ディレクトリ自動作成、全DDLとインデックスを実行して接続を返す（冪等）。
  - get_connection(db_path)：既存 DB への接続取得ヘルパー。

- ETL パイプライン（kabusys.data.pipeline）
  - ETL の基本フレームワークを実装:
    - ETLResult dataclass：ETL結果のサマリ（取得数/保存数/品質問題/エラーリストなど）を格納、辞書化メソッドを提供。
    - 差分更新のための補助関数：
      - _table_exists / _get_max_date を実装。
      - get_last_price_date / get_last_financial_date / get_last_calendar_date を実装。
      - _adjust_to_trading_day：非営業日の場合、最大30日遡って直近の営業日に調整する処理を実装（market_calendar を利用）。
    - run_prices_etl を実装（差分更新、バックフィル機構、_MIN_DATA_DATE フォールバック、J-Quants から取得して保存）。
  - 設計指針として、品質チェック（kabusys.data.quality）連携、backfill_days デフォルト 3 日、calendar の先読み等を想定。

### Security
- news_collector において SSRF 対策、defusedxml の利用、レスポンスサイズ制限（DoS 対策）を追加。
- .env の読み込みで OS 環境変数を保護する仕組みを導入（protected set）。

### Performance
- J-Quants クライアント側でレート制御と再試行を実装し、API 呼び出しの安定性を確保。
- news_collector / DB 保存処理でチャンク/トランザクションを利用し、大量レコードの挿入オーバーヘッドを低減。
- id_token をモジュールキャッシュしてページネーション間での冗長なトークン取得を回避。

### Notes
- 本リリースでは core の機能実装に注力しており、strategy / execution / monitoring の具体的なアルゴリズムや監視実装は今後追加予定です。
- ETL / パイプラインは品質チェックモジュール（kabusys.data.quality）との統合を想定した設計になっていますが、quality モジュール自体の実装状況に応じて挙動が変わります。
- 一部のロジック（例: run_prices_etl の振る舞い）は将来的に拡張・調整される可能性があります。

以上が 0.1.0 の主要な変更点です。今後のリリースでは、戦略ロジック、注文実行・監視機能、テスト補強、ドキュメントの拡充を予定しています。