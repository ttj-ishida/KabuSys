Keep a Changelog 準拠 — 変更履歴 (日本語)
====================================

すべての変更は意図的にコードベースから推測して記載しています。  
バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に基づきます。

[0.1.0] - 2026-03-17
-------------------

Added
- 初回リリース: KabuSys 日本株自動売買プラットフォームの基礎機能群を追加。
  - パッケージ構成:
    - kabusys.config: 環境変数・設定管理（.env/.env.local 自動ロード + Settings クラス）
    - kabusys.data: データ取得・保存・スキーマ定義・ETLパイプライン
    - kabusys.strategy: 戦略モジュール用パッケージ（空イニシャライザ）
    - kabusys.execution: 発注/実行モジュール用パッケージ（空イニシャライザ）
  - バージョン: 0.1.0

- 環境設定（src/kabusys/config.py）
  - プロジェクトルート探索: .git または pyproject.toml を基準に自動検出するため、CWD に依存しない自動 .env 読み込みを実現。
  - .env パーサ実装: export 形式やシングル/ダブルクォート、エスケープ、インラインコメントの扱いを考慮した堅牢なパーサを実装。
  - 自動ロード優先順位: OS 環境変数 > .env.local > .env。テストなどで自動ロードを無効にする KABUSYS_DISABLE_AUTO_ENV_LOAD を提供。
  - Settings クラス: 必須設定を取得するヘルパー（_require）を実装。主なキー:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）

- J-Quants クライアント（src/kabusys/data/jquants_client.py）
  - API 呼び出しの共通処理を実装:
    - レート制限 (120 req/min) を守る固定間隔スロットリング実装 (_RateLimiter)
    - 再試行（最大 3 回）＋指数バックオフ。HTTP 408/429/5xx をリトライ対象に指定
    - 429 の場合は Retry-After ヘッダを優先
    - 401 受信時は refresh token から id_token を自動リフレッシュして 1 回だけリトライ（無限再帰防止）
    - id_token のモジュールレベルキャッシュを共有してページネーション間で利用
    - レスポンスの JSON デコード失敗時に詳細なエラーメッセージを出力
  - fetch_* 系関数（ページネーション対応）:
    - fetch_daily_quotes: 株価日足（OHLCV）
    - fetch_financial_statements: 財務（四半期 BS/PL）
    - fetch_market_calendar: JPX マーケットカレンダー
  - 保存関数（DuckDB へ冪等保存）:
    - save_daily_quotes, save_financial_statements, save_market_calendar: ON CONFLICT DO UPDATE を利用し冪等性を確保
    - fetched_at を UTC ISO8601（Z）で記録し、いつデータを取得したかを追跡可能に
  - ユーティリティ: 安全な数値変換関数 _to_float / _to_int（不正な小数切捨ての回避等）

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィード収集フローの実装:
    - RSS 取得（fetch_rss）、テキスト前処理（URL 除去・空白正規化）、記事ID生成、DuckDB への冪等保存、銘柄紐付け
  - セキュリティ対策:
    - defusedxml を使った XML パース（XML Bomb 等への対策）
    - SSRF 対策: リダイレクト先のスキーム検証とプライベートホスト拒否用ハンドラ (_SSRFBlockRedirectHandler)
    - 初期 URL と最終 URL 双方についてスキームとプライベートホスト判定
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MB）を導入しメモリ DoS を防止。gzip 解凍後も再チェック
    - 許可スキームは http/https のみ
  - 記事 ID と正規化:
    - _normalize_url でトラッキングパラメータ（utm_*, fbclid, gclid 等）を削除・ソートして標準化
    - _make_article_id は正規化 URL の SHA-256 ハッシュ先頭32文字を使用（冪等性確保）
  - DB 保存・パフォーマンス:
    - INSERT ... RETURNING を用いて実際に挿入された記事 ID を返す
    - チャンクサイズと単一トランザクションでの一括挿入によりオーバーヘッドを低減
    - save_news_symbols / _save_news_symbols_bulk で銘柄紐付けをバルク保存
  - 銘柄抽出:
    - 正規表現による 4 桁数字抽出（_CODE_PATTERN = r"\b(\d{4})\b"）と known_codes フィルタにより有効銘柄のみ抽出

- DuckDB スキーマ定義（src/kabusys/data/schema.py）
  - DataSchema.md に基づく多層スキーマを実装（Raw / Processed / Feature / Execution）
  - 主なテーブル（抜粋）:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切なデータ型・CHECK 制約・PRIMARY KEY を設定
  - インデックス定義（頻出クエリ向け）
  - init_schema(db_path) で親ディレクトリ作成＋全 DDL 実行（冪等）。get_connection は既存 DB 接続を返す

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - ETLResult dataclass により ETL 実行結果を集約（品質問題やエラー一覧を含む）
  - 差分更新ロジック:
    - DB の最終取得日を元に差分（およびデフォルトで backfill_days=3 を適用）を自動算出
    - run_prices_etl: date_from 指定がない場合に最終取得日 - backfill_days + 1 を開始日として再取得
    - 市場カレンダー先読み（_CALENDAR_LOOKAHEAD_DAYS = 90）等を想定した設計
  - 品質チェック統合ポイント（quality モジュール呼び出しを想定）。品質エラーは収集を続行し、呼び出し元で判断可能

Security
- ニュース収集での SSRF 対策、XML パースにおける defusedxml 利用、レスポンスサイズ制限など、外部入力・ネットワークを扱う箇所に対する複数の安全対策を導入。

Notes / Migration
- .env の自動読み込みは既定で有効。自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に有用）。
- 必須環境変数（JQUANTS_REFRESH_TOKEN、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID、KABU_API_PASSWORD）は Settings を通じて取得され、未設定時は ValueError が発生します。
- DuckDB のデフォルトパスは data/kabusys.duckdb（相対パス）です。init_schema を初回実行してスキーマを作成してください。
- J-Quants API は rate-limit（120 req/min）を厳守するためのスロットリングが入っています。大量一括リクエスト時はこの制限を考慮してください。
- news_collector の既存実装は HTTP レスポンスの Content-Length が異常な値のときや gzip 解凍失敗時に安全にスキップします。RSS ソース追加時は source 名と URL を DEFAULT_RSS_SOURCES に追加してください。

Unreleased
- （現時点では未定義）

参考
- パッケージバージョン: 0.1.0 (src/kabusys/__init__.py)
- 実装ファイル: src/kabusys/config.py, src/kabusys/data/jquants_client.py, src/kabusys/data/news_collector.py, src/kabusys/data/schema.py, src/kabusys/data/pipeline.py

もし特定の変更点（例えばリリース日を別にしたい、あるいは追加で「Fixed」「Changed」等の区分を分けたい場合）はお知らせください。コードの実際の履歴（コミット差分）があれば、より正確な CHANGELOG を作成できます。