CHANGELOG
=========

すべての注目すべき変更点をこのファイルに記録します。
このプロジェクトは Keep a Changelog の慣習に従います。
変更履歴は互換性に関するセマンティックバージョニングを前提とします。

[0.1.0] - 2026-03-17
--------------------

Added
- 初期リリース: パッケージ kabusys (バージョン 0.1.0) を追加。
  - src/kabusys/__init__.py に __version__="0.1.0" を定義し公開モジュールを設定。

- 設定/環境変数管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を追加。
    - プロジェクトルート検出: .git または pyproject.toml を起点にルートを特定する _find_project_root() を実装。CWD に依存しない挙動。
    - .env / .env.local の優先順制御: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パーサ実装: export プレフィックス、クォート付き値、インラインコメント、エスケープ処理に対応する _parse_env_line()。
    - 上書き制御と protected キー（OS 環境変数保護）に対応した _load_env_file()。
  - Settings クラスを導入し、必要な環境変数をプロパティとして提供（必須項目は _require() による検査）。
    - J-Quants / kabuステーション / Slack / DB パス等の設定項目を定義。
    - KABUSYS_ENV と LOG_LEVEL の厳密検証（許容値チェック）と convenience プロパティ（is_live 等）。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 基本設計: レート制限遵守、リトライ（指数バックオフ）、401 時のトークン自動リフレッシュ、取得時刻（fetched_at）UTC 記録、DuckDB への冪等保存を実現。
  - レート制限: 固定間隔スロットリング _RateLimiter（120 req/min 相当）。
  - HTTP ユーティリティ _request():
    - GET/POST, JSON ボディサポート。
    - 408/429/5xx に対する再試行、429 の Retry-After ヘッダ優先、最大リトライ回数の設定。
    - 401 発生時は get_id_token によるトークンリフレッシュを一度だけ試行（無限再帰防止）。
  - 認証補助: get_id_token()（refresh token から idToken を取得）。
  - データ取得関数:
    - fetch_daily_quotes(), fetch_financial_statements(), fetch_market_calendar()（ページネーション対応、pagination_key 管理）。
    - 取得ログ出力（取得件数）。
  - DuckDB 保存関数（冪等）:
    - save_daily_quotes(), save_financial_statements(), save_market_calendar() — ON CONFLICT DO UPDATE を使った更新対応と PK 欠損行のスキップ。
    - fetched_at を UTC ISO フォーマットで記録。
  - ユーティリティ: _to_float(), _to_int()（安全な変換ロジック）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS 取得から DuckDB への保存までの一連機能を提供。
  - セキュリティ設計:
    - defusedxml を使用して XML Bomb 等の攻撃を防御。
    - HTTP リダイレクト先のスキーム検証およびプライベートアドレス検査（SSRF 対策）を行う _SSRFBlockRedirectHandler と _is_private_host()。
    - URL スキーム検証 (http/https のみ) と受信サイズ上限（MAX_RESPONSE_BYTES=10MB）の厳格チェック。gzip 解凍後のサイズ再確認。
    - URL 正規化時にトラッキングパラメータ除去（utm_* 等）を行う _normalize_url()。
  - 記事ID生成: 正規化 URL の SHA-256（先頭32文字）を記事IDとして冪等性保証。
  - RSS パース: fetch_rss()（content:encoded 優先、pubDate のパースとフォールバック、記事前処理 preprocess_text）。
  - DB 保存:
    - save_raw_news(): INSERT ... RETURNING を使い、実際に新規挿入された記事IDのリストを返却。チャンク分割およびトランザクション管理。
    - save_news_symbols() / _save_news_symbols_bulk(): news_symbols への銘柄紐付け（ON CONFLICT DO NOTHING と RETURNING で実際の挿入数を返す）。
  - 銘柄コード抽出: 正規表現による4桁コード抽出 extract_stock_codes()（known_codes フィルタと重複除去）。
  - 統合収集ジョブ: run_news_collection() — 複数ソースの独立処理、エラー隔離、銘柄紐付けの一括保存。

- DuckDB スキーマ定義 (src/kabusys/data/schema.py)
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature / Execution）をカバーする DDL を定義。
  - raw_prices, raw_financials, raw_news, raw_executions など Raw レイヤー。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed レイヤー。
  - features, ai_scores 等の Feature レイヤー。
  - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution レイヤー。
  - 制約と CHECK（数値非負・サイド列の列挙等）を設置。
  - インデックス定義（典型的な銘柄×日付検索やステータス検索向け）。
  - init_schema(db_path) による初期化（親ディレクトリ自動作成、冪等作成）、get_connection() を提供。

- ETL パイプライン基盤 (src/kabusys/data/pipeline.py)
  - ETL の設計方針と処理フローを実装:
    - 差分更新ロジック（DB の最終取得日を参照して再取得範囲を算出）。
    - backfill_days による後出し修正吸収。
    - 品質チェックとエラーの収集（quality モジュールとの連携想定）。
  - ETLResult dataclass を追加（結果メタ情報、品質問題リスト、エラー一覧を保持、シリアライズ用 to_dict()）。
  - テーブル存在確認、最大日付取得、営業日調整（market_calendar を参照）などの内部ユーティリティを実装。
  - run_prices_etl() を追加（差分計算 → jq.fetch_daily_quotes → jq.save_daily_quotes）。戻り値として取得件数と保存件数を返す設計（実装は部分的に含まれる）。

- パッケージ構成
  - data, strategy, execution, monitoring を公開（strategy/, execution/, monitoring/ は空の __init__.py でプレースホルダ）。

Security
- RSS パーシングで defusedxml を採用、SSRF 対策、受信サイズ制限、Gzip 解凍後のサイズチェックを導入。
- J-Quants API クライアントでトークン管理（自動リフレッシュ）と厳格なリトライポリシーを実装。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Notes / Known limitations / TODO
- strategy/, execution/, monitoring/ モジュールはプレースホルダで、本リリースでは実装がない。今後のリリースで戦略、注文実行、監視ロジックを追加予定。
- pipeline.run_prices_etl() 等は実装中/部分的（ファイル末尾が途中で切れていることから追加実装が必要）で、完全な ETL ワークフロー（品質チェック integration、その他の ETL ジョブ）は今後整備予定。
- quality モジュールの詳細な実装は本リリースに含まれていない想定（pipeline から参照されるが実体は別実装を想定）。
- 単体テストや CI の記述はソースからは確認できないため、テストの整備が推奨される。

ライセンス、貢献方法、リポジトリ URL 等はこの CHANGELOG に含めていません。必要であれば追記してください。