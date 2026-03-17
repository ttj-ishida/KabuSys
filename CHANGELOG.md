# Changelog

すべての注目に値する変更はここに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

※この CHANGELOG は、提示されたコードベースの内容から推測して作成しています。

## [0.1.0] - 2026-03-17

初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__init__ に __version__ = "0.1.0"）。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ に定義。

- 設定 / 環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機能:
    - プロジェクトルートを .git または pyproject.toml から探索して検出。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト向け）。
  - .env パーサー実装（export プレフィックス、クォート、インラインコメント等に対応）。
  - 必須設定取得ヘルパー (_require) と、いくつかの設定プロパティを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）。
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH 等のデフォルト値。
    - KABUSYS_ENV（development / paper_trading / live の検証）と LOG_LEVEL の検証。
    - is_live / is_paper / is_dev のユーティリティ。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 基本機能:
    - ID トークン取得 (get_id_token)。
    - 株価日足(fetch_daily_quotes)、財務データ(fetch_financial_statements)、市場カレンダー(fetch_market_calendar) の取得。
    - ページネーション対応。
  - レート制御:
    - 固定間隔スロットリング (_RateLimiter) による 120 req/min の制限実装（デフォルト）。
  - リトライ/エラーハンドリング:
    - 指数バックオフで最大 3 回リトライ(_MAX_RETRIES)。
    - 401 受信時はトークンを自動リフレッシュして 1 回だけリトライ。
    - 408/429/5xx の場合はリトライを行う（429 の Retry-After を尊重）。
  - DuckDB への保存関数（冪等）:
    - save_daily_quotes, save_financial_statements, save_market_calendar:
      - ON CONFLICT DO UPDATE を使って冪等性を保証。
      - fetched_at を UTC で記録し、データ取得時刻のトレースを可能に。
    - 型変換ユーティリティ (_to_float, _to_int) を実装。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィード収集・前処理・保存パイプライン実装。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 対策）。
    - SSRF 対策: URL スキーム検証、ホストがプライベートアドレスかの検査、リダイレクト時の検査用ハンドラ(_SSRFBlockRedirectHandler)。
    - 受信サイズ上限(MAX_RESPONSE_BYTES=10MB)、gzip 解凍後のサイズ検査。
  - 記事ID生成:
    - URL を正規化（トラッキングパラメータ除去・ソート・小文字化・フラグメント除去）し、その SHA-256 の先頭32文字を記事IDとして利用（冪等性保証）。
  - テキスト前処理(preprocess_text): URL 除去、空白正規化。
  - DB 保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING id により、実際に挿入された記事IDを返す（チャンク挿入、トランザクションまとめ）。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括挿入（重複排除、ON CONFLICT でスキップ、RETURNING で挿入数を取得）。
  - 銘柄コード抽出:
    - 4桁数字パターンから候補を抽出し、known_codes に含まれるもののみを返す extract_stock_codes。

- データベーススキーマ（kabusys.data.schema）
  - DuckDB 用 DDL を実装:
    - Raw / Processed / Feature / Execution 層のテーブル定義を網羅（raw_prices, raw_financials, raw_news, prices_daily, market_calendar, fundamentals, features, ai_scores, signals, signal_queue, orders, trades, positions など）。
    - 各種制約（PRIMARY KEY、CHECK、FOREIGN KEY）を含む設計。
    - よく使うクエリ向けのインデックス定義を複数追加。
  - init_schema(db_path) によりディレクトリ自動作成とテーブル初期化を行う（冪等）。
  - get_connection(db_path) で既存 DB に接続可能。

- ETL パイプライン（kabusys.data.pipeline）
  - ETLResult データクラスを実装（取得数、保存数、品質チェック結果、エラー一覧を保持）。
  - 差分更新ロジックのヘルパー:
    - 最終取得日取得関数: get_last_price_date, get_last_financial_date, get_last_calendar_date。
    - 営業日に調整する _adjust_to_trading_day。
  - run_prices_etl: 差分更新を行う株価 ETL ジョブの最初の実装（差分算出、backfill_days による後出し修正吸収、jq.fetch_daily_quotes / jq.save_daily_quotes の呼び出し）。
  - ETL 設計方針:
    - 差分更新（既存最大日付からの再取得）、デフォルトバックフィル 3 日、品質チェックは fail-fast せず報告する設計方針を反映。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- XML パースに defusedxml を採用して XML 関連の脅威を軽減。
- RSS 取得の際に SSRF 対策を導入（ホストのプライベート判定、リダイレクト先検査、スキーム検証）。
- HTTP レスポンスサイズ制限と gzip 解凍後サイズ検査によりリソース攻撃を緩和。

### 既知の問題 (Known issues / Notes)
- run_prices_etl の実装がファイル末尾で途切れており、戻り値が不完全（len(records) のみを返すなどの不整合が見られます）。実際のリリースでは (fetched_count, saved_count) のタプルが期待されます。お使いの環境ではこの関数の戻り値を確認してください。
- strategy, execution, monitoring パッケージは __init__.py が空であり、各モジュールの実装は今後追加が必要です。
- quality モジュールは参照（import）されているものの、このスナップショット内での品質チェック実装の全容は未提示です。ETL の品質チェック連携は追加実装が必要です。
- get_id_token は settings.jquants_refresh_token が未設定だと ValueError を送出します。環境変数の設定を忘れないでください。

### 必要な環境変数
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
- 任意／デフォルトあり:
  - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - KABUSYS_ENV (development|paper_trading|live、デフォルト: development)
  - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL、デフォルト: INFO)

### マイグレーション / 利用開始ガイド
- データベースの初期化: kabusys.data.schema.init_schema(db_path) を呼び出して DuckDB スキーマを作成してください。
- ニュース収集: kabusys.data.news_collector.run_news_collection を使用して RSS 収集と銘柄紐付けを実行できます。
- J-Quants データ取得: kabusys.data.jquants_client.fetch_* 系と save_* 系を組み合わせて ETL を実行してください。
- テストや CI で自動 .env ロードを無効にする場合は、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

今後のリリースでは以下を予定しています（例）:
- pipeline の完全実装と品質チェックの統合。
- strategy/execution/monitoring の具体的実装（売買戦略、発注・約定処理、監視アラート）。
- テストカバレッジ整備と CI 設定。