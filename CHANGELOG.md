Keep a Changelog
=================

すべての重要な変更をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

[Unreleased]
------------

（なし）

[0.1.0] - 2026-03-17
-------------------

Added
- 初回リリース (パッケージ: kabusys)
  - パッケージバージョンを設定（src/kabusys/__init__.py: __version__ = "0.1.0"）。
  - パッケージ公開 API を定義（data, strategy, execution, monitoring を export）。

- 環境・設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む機能を実装。
  - プロジェクトルート検出ロジックを導入（.git または pyproject.toml を基準、CWD非依存）。
  - .env のパース処理を強化（コメント、export プレフィックス、クォート内エスケープ、インラインコメント等に対応）。
  - 自動ロードの優先順位を採用: OS環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
  - 必須環境変数チェック（_require）と Settings クラスによるプロパティ型/妥当性チェック（env, log_level 等）。
  - デフォルト値と Path 型変換を提供（duckdb/sqlite パス等）。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - API 呼び出しユーティリティを実装（_request）。
    - レート制限 (120 req/min) を守る固定間隔スロットリング実装（_RateLimiter）。
    - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx をリトライ対象）。
    - 429 の場合は Retry-After ヘッダ優先。
    - 401 受信時はトークン自動リフレッシュを 1 回行って再試行（無限再帰防止）。
    - JSON デコードエラーハンドリング、タイムアウト等。
  - id_token 取得関数（get_id_token）とモジュールレベルのトークンキャッシュを実装（ページネーション間で共有）。
  - データ取得関数を実装（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - ページネーション対応と pagination_key 重複防止。
    - 取得ログ（取得件数記録、fetched_at の考慮は保存関数側で行う旨設計）。
  - DuckDB への冪等保存関数を実装（save_daily_quotes, save_financial_statements, save_market_calendar）。
    - ON CONFLICT DO UPDATE を用いた冪等挿入。
    - PK 欠損行のスキップおよびログ出力。
    - fetched_at を UTC ISO 形式で記録。
  - ユーティリティ関数 (_to_float, _to_int) により安全な型変換を提供（空値・不正値を None に変換、"1.0" などの float 文字列を正しく扱う等）。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードからの記事収集・前処理・保存のワークフローを実装。
  - セキュリティ対策と堅牢性:
    - defusedxml による XML パースで XML Bomb 等を防止。
    - SSRF 防止: リダイレクト時にスキーム検証とプライベートIP/ループバック判定を行うハンドラ（_SSRFBlockRedirectHandler）を実装。
    - 初期ホスト検査（_is_private_host）で private/loopback/link-local/multicast を拒否。
    - スキーム検証（http/https のみ許可）。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
  - URL 正規化とトラッキングパラメータ削除（utm_* 等）、ハッシュによる記事ID生成（SHA-256 の先頭32文字）を導入して冪等性を確保。
  - テキスト前処理（URL 削除、空白正規化）。
  - RSS のパースとフォールバック実装（channel/item の探索、content:encoded 優先）。
  - DuckDB への保存処理:
    - バルク INSERT をチャンク化してトランザクションで実行、INSERT ... RETURNING を使って実際に挿入された記事IDを返す（save_raw_news）。
    - news_symbols の一括保存ロジック（_save_news_symbols_bulk）と個別保存（save_news_symbols）、ON CONFLICT DO NOTHING を使用して重複を排除。
  - 銘柄コード抽出ロジック（4桁数字の候補 -> known_codes と照合して重複除去）（extract_stock_codes）。
  - 全体ジョブ run_news_collection を実装（複数ソース独立エラーハンドリング、既知銘柄紐付け、結果集計）。

- スキーマ定義と初期化（src/kabusys/data/schema.py）
  - DuckDB 用のスキーマを DataSchema.md に基づき実装。
    - Raw 層: raw_prices, raw_financials, raw_news, raw_executions 等。
    - Processed 層: prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等。
    - Feature 層: features, ai_scores。
    - Execution 層: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等。
  - 各テーブルに制約（PRIMARY KEY, CHECK, FOREIGN KEY 等）を付与。
  - 頻出クエリ用のインデックスを定義（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
  - init_schema(db_path) によりディレクトリ自動作成→DDL 実行→接続返却。get_connection は既存 DB への接続のみ提供。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - ETLResult dataclass を導入し、ETL 実行結果・品質問題・エラーを集約して保持・辞書化可能に実装。
  - 差分更新を支えるユーティリティを実装:
    - テーブル存在チェック (_table_exists)、最大日付取得 (_get_max_date)。
    - 営業日補正ロジック (_adjust_to_trading_day)。
    - 最終取得日取得関数（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
  - run_prices_etl の差分更新ロジック（date_from 自動決定、backfill_days デフォルト 3 日）を実装（fetch→save の流れ）。品質チェックは別モジュール quality を利用する設計（品質チェックはエラー重大度に応じて ETL 継続を許容する方針）。

Security
- RSS および外部 HTTP 取得周りで SSRF 対策、XML の安全パース、レスポンスサイズ制限などを導入（news_collector）。
- API 呼び出しで認証トークンの安全な自動リフレッシュと再試行設計を実装（jquants_client）。

Performance
- レート制限遵守のためのスロットリング（_RateLimiter）を導入し、API レート制限順守を保証。
- ニュース保存でチャンク化したバルク INSERT を採用して DB オーバーヘッドを低減。
- トークンキャッシュによりページネーション間の無駄な再認証を回避。

Notes / Design
- 各保存関数は冪等性（ON CONFLICT DO UPDATE / DO NOTHING）を重視して設計。
- ETL は Fail-Fast を取らず、品質チェックは検出結果を集約して呼び出し元に判断を委ねる方針。
- 外部依存（DuckDB、defusedxml 等）を使い、セキュリティと性能のバランスを考慮。

Fixed
- （初回リリースのため該当なし）

Changed
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- （上記 Security セクション参照）

---

注記:
- 本 CHANGELOG はソースコード（src/ 以下）から推測して作成しています。実際のリリースノートとして使用する場合は、対象リリースでの追加・変更点・既知の制約をプロジェクトの実施チームで確認のうえ確定してください。