# Changelog

すべての重要な変更履歴をここに記録します。本ファイルは Keep a Changelog の方針に準拠します。

## [0.1.0] - 2026-03-18
初回リリース。日本株自動売買システム「KabuSys」のコア基盤を追加。

### 追加
- パッケージ公開情報
  - パッケージのバージョンを `__version__ = "0.1.0"` として設定。
  - パッケージの公開モジュールを `__all__ = ["data", "strategy", "execution", "monitoring"]` として定義。

- 環境設定管理 (kabusys.config)
  - .env / .env.local ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - プロジェクトルート検出: `.git` または `pyproject.toml` を基準に __file__ から親ディレクトリを探索。
    - 自動ロードを無効化するためのフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を提供（テスト用途）。
  - .env パーサ: export プレフィックス、クォート／エスケープ、インラインコメントの扱いに対応した堅牢なパーサを実装。
  - 必須環境変数取得ヘルパー `_require()` と Settings クラスを提供。以下の主要設定プロパティを公開:
    - J-Quants: `jquants_refresh_token`
    - kabuAPI: `kabu_api_password`, `kabu_api_base_url`（デフォルト: http://localhost:18080/kabusapi）
    - Slack: `slack_bot_token`, `slack_channel_id`
    - DBパス: `duckdb_path`（デフォルト: data/kabusys.duckdb）, `sqlite_path`（デフォルト: data/monitoring.db）
    - 実行環境: `env`（検証: development|paper_trading|live）、`log_level`（検証: DEBUG|INFO|...）
    - 環境種別判定: `is_live`, `is_paper`, `is_dev`

- J-Quants API クライアント (kabusys.data.jquants_client)
  - J-Quants API から株価日足、財務データ、マーケットカレンダーを取得するクライアントを実装。
  - レート制御: 固定間隔スロットリングで 120 req/min 制限を守る RateLimiter 実装。
  - 再試行（リトライ）ロジック:
    - 最大リトライ回数 3 回、指数バックオフを採用（対象: 408, 429, 5xx, ネットワークエラー）。
    - 429 時は Retry-After ヘッダを尊重。
    - 401（Unauthorized）受信時はリフレッシュトークンから自動で id_token を更新して 1 回だけリトライ。
  - ページネーション対応のデータ取得関数:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
    - 取得時に取得レコード数のログ出力。
  - DuckDB へ冪等的に保存する保存関数:
    - save_daily_quotes: raw_prices テーブルへ ON CONFLICT DO UPDATE を使って保存。
    - save_financial_statements: raw_financials テーブルへ ON CONFLICT DO UPDATE。
    - save_market_calendar: market_calendar テーブルへ ON CONFLICT DO UPDATE。
    - 保存時に fetched_at（UTC）を記録し、Look-ahead バイアス防止とトレーサビリティを確保。
  - 型変換ユーティリティ `_to_float`, `_to_int`（不正値や小数部非ゼロの int 変換を安全に扱う）。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードからのニュース収集と DuckDB への保存機能を実装。デフォルトソースに Yahoo Finance のビジネス RSS を設定。
  - セキュリティ対策:
    - defusedxml を使用し XML Bomb 等から保護。
    - SSRF 対策: リダイレクト時にスキームとホスト/IP の検証を行うカスタム RedirectHandler を実装。
    - URL スキーム検証（http/https のみ許容）、ホストがプライベート/ループバックであれば拒否。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後の再チェックを行うことでメモリDoSを防止。
    - 受信ヘッダ Content-Length の事前チェックと実際の読み込み上限の両方を実施。
  - フィード処理:
    - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ削除、フラグメント除去、クエリソート）。
    - 記事IDは正規化 URL の SHA-256（先頭32文字）で生成し冪等性を保証。
    - タイトル/本文の前処理（URL 除去、空白正規化）。
    - pubDate のパースを行い UTC naive datetime へ変換（パース失敗時は現在時刻で代替）。
    - XML 解析エラーや不正なレスポンスは警告ログを出して安全にスキップ。
  - DB 保存:
    - save_raw_news: INSERT ... RETURNING を使い、新規挿入された記事IDのみを返す。チャンク (>1000) 分割と1トランザクションでの挿入に対応。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを冪等的に保存（ON CONFLICT DO NOTHING、RETURNING により実挿入数を取得）。
  - 銘柄抽出:
    - extract_stock_codes: 正規表現で4桁の候補を抽出し、既知銘柄リストでフィルタして重複を除去。

- DuckDB スキーマ定義 (kabusys.data.schema)
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature）＋Execution 層のテーブル DDL を追加。
  - 主なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルの制約（NOT NULL / CHECK / PRIMARY KEY / FOREIGN KEY）を定義。
  - 検索効率のためのインデックスも定義（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
  - 初期化ユーティリティ:
    - init_schema(db_path): DB ファイルの親ディレクトリを自動作成し、全テーブルとインデックスを冪等的に作成して接続を返す（:memory: 対応）。
    - get_connection(db_path): 既存 DB への接続を返す（スキーマ初期化は行わない）。

- ETL パイプライン (kabusys.data.pipeline)
  - 差分更新（incremental）を想定した ETL ヘルパーを実装。
    - 差分更新のデフォルト単位は営業日 1 日。
    - バックフィル（backfill_days）により最終取得日の数日前から再取得し、API 後出し修正を吸収。
    - 市場カレンダーの先読み日数設定（デフォルト 90 日）。
    - ETLResult データクラスを導入し、取得件数、保存件数、品質問題、エラーの集約・シリアライズをサポート。
  - DB ヘルパー:
    - テーブル存在チェック、テーブルの最大日付取得（汎用 _get_max_date）。
    - 市場カレンダーを参照して非営業日を直近の営業日に調整する _adjust_to_trading_day。
    - get_last_price_date, get_last_financial_date, get_last_calendar_date を公開。
  - 個別ジョブ:
    - run_prices_etl: 差分ロジックでの株価日足取得と保存（fetch -> save の流れ）。取得範囲算出、ログ出力、保存件数の返却。設計上 backfill_days デフォルト 3 日。

### 変更
- なし（初回リリース）

### 修正
- なし（初回リリース）

### 脆弱性
- なし（リリース時点で既知の重大な脆弱性はなし）。  
  - ただし外部ネットワーク/API 連係部分は環境依存のため、運用時には API キー管理・ネットワーク制御・監視を推奨。

### 既知の制限・注意点
- DuckDB スキーマの整合性や外部キーは定義済みだが、アプリケーション側でのトランザクション設計やマイグレーション管理は今後の課題。
- run_prices_etl の実行は jquants API の提供データ範囲やレート制限により時間を要する場合がある。
- news_collector の URL 検証はホスト名の DNS 解決失敗時に「安全側で通過」とする設計（可用性重視）。環境によっては追加のネットワークポリシーが必要。

---

開発に関する詳細な設計ドキュメント（DataPlatform.md, DataSchema.md 等）はリポジトリ内の該当ドキュメントを参照してください。今後のリリースでは監視・実行戦略・バックテストモジュールなどを追加予定です。