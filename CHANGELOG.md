# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

現在のリリース方針: 初回パブリックリリースとして v0.1.0 を作成しています。

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-03-17

初回リリース。日本株自動売買基盤のコアモジュールを追加しました。主な追加点は以下のとおりです。

### Added
- パッケージ全体
  - パッケージ名: kabusys
  - バージョン: 0.1.0（src/kabusys/__init__.py）

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルート自動検出（.git または pyproject.toml を探索）。
    - 読み込み順序: OS 環境 > .env.local > .env（.env.local は上書き）。  
    - 自動ロードを無効にする環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - 高機能な .env パーサー:
    - export KEY=val 形式対応、クォート／エスケープ処理、行内コメント処理。
  - Settings クラスで主要な設定値をプロパティとして提供:
    - J-Quants / kabuステーション / Slack / DB パス（DuckDB/SQLite）/ 環境（development/paper_trading/live）/ログレベル等
    - 値の検証（不正な KABUSYS_ENV や LOG_LEVEL は ValueError を送出）
    - デフォルトの DB パス（例: data/kabusys.duckdb）

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API 呼び出しユーティリティ:
    - レート制限（固定間隔スロットリング）を実装（120 req/min 相当）。
    - リトライ戦略（指数バックオフ、最大 3 回、408/429/5xx をリトライ対象）。
    - 401 応答時はリフレッシュトークンから id_token を自動で更新して 1 回リトライ。
    - JSON デコードのエラーハンドリング、ログ出力。
    - ページネーション対応（pagination_key を用いた反復取得）。
    - id_token のモジュールレベルキャッシュ（ページネーション間で共有）。
  - データ取得関数:
    - fetch_daily_quotes（株価日足: OHLCV）
    - fetch_financial_statements（四半期財務データ）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB への保存関数（冪等: ON CONFLICT DO UPDATE）:
    - save_daily_quotes（raw_prices テーブルへ）
    - save_financial_statements（raw_financials テーブルへ）
    - save_market_calendar（market_calendar テーブルへ）
  - 型変換ユーティリティ: _to_float, _to_int（不正値安全化）

- ニュース収集（RSS）モジュール (src/kabusys/data/news_collector.py)
  - RSS フィード取得と記事整形パイプラインを実装。
    - defusedxml を使った安全な XML パース（XML Bomb 対策）。
    - HTTP レスポンスのサイズ上限チェック（MAX_RESPONSE_BYTES = 10MB）、gzip 解凍および解凍後サイズ検査。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - リダイレクト時もスキームとホストの検証を行うカスタム RedirectHandler。
      - ホストがプライベート/ループバック/リンクローカルである場合は拒否。
    - URL 正規化とトラッキングパラメータ削除（utm_* 等）。
    - 記事ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を担保。
    - テキスト前処理（URL 除去、空白正規化）。
  - DB 保存ロジック（DuckDB を想定）:
    - save_raw_news: チャンク化して INSERT ... ON CONFLICT DO NOTHING RETURNING id を使い、実際に挿入された記事IDを返す。トランザクションでまとめて処理。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをバルク挿入。ON CONFLICT を使って重複をスキップし、実際に保存された件数を返す。
  - 銘柄コード抽出ユーティリティ:
    - extract_stock_codes: 4桁数字の候補を抽出し、known_codes のセットでフィルタリングして返す。
  - デフォルト RSS ソース定義（例: Yahoo Finance のビジネスカテゴリ）

- DuckDB スキーマ定義・初期化 (src/kabusys/data/schema.py)
  - DataSchema.md に基づく 3 層構造スキーマを実装（Raw / Processed / Feature / Execution）。
  - 主なテーブルを定義（例）:
    - raw_prices / raw_financials / raw_news / raw_executions
    - prices_daily / market_calendar / fundamentals / news_articles / news_symbols
    - features / ai_scores
    - signals / signal_queue / portfolio_targets / orders / trades / positions / portfolio_performance
  - 制約（PRIMARY KEY, CHECK, FOREIGN KEY）を適用。
  - 頻出クエリ用のインデックスを作成。
  - init_schema(db_path) によりディレクトリ生成 → DuckDB 接続 → テーブル・インデックス作成を行う（冪等）。
  - get_connection(db_path) で既存 DB への接続を提供（初期化は行わない点に注意）。

- ETL パイプライン基盤 (src/kabusys/data/pipeline.py)
  - ETLResult dataclass: ETL 実行結果（取得数、保存数、品質問題、エラー等）を表現。品質問題は辞書化可能。
  - テーブル存在チェック、最大日付取得ユーティリティ（_table_exists, _get_max_date）を提供。
  - market_calendar を用いた営業日調整ヘルパー（_adjust_to_trading_day）。
  - 差分更新ヘルパー（get_last_price_date 等）。
  - run_prices_etl: 株価日足の差分 ETL 実装（差分算出、backfill_days による遡り再取得、取得→保存の実行）。J-Quants クライアントを用いて取得し、保存は jquants_client.save_daily_quotes を使用。
  - 設計方針を反映（差分更新、backfill による後出し修正吸収、品質チェックは続行といった振る舞いを想定）。

### Security
- ニュース収集モジュールにて SSRF 対策と XML パース対策を実装（上記参照）。
- .env 読み込みで OS 環境変数の上書きを制御（protected set による保護）。

### Notes / Usage
- DB 初回セットアップ:
  - from kabusys.data.schema import init_schema
  - conn = init_schema(settings.duckdb_path)
- ニュース収集実行例:
  - run_news_collection(conn, sources=None, known_codes=set([...]))
- J-Quants API を利用するには環境変数 JQUANTS_REFRESH_TOKEN を設定する必要があります（settings.jquants_refresh_token が参照）。
- 自動 .env ロードはデフォルトで有効。テストなどで無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

### Known limitations / TODO
- quality モジュールは参照されているが（pipeline で利用）、この差分に含まれるコードでは定義が確認できません（別途実装済みである想定、または今後追加）。
- run_prices_etl の戻り値がソースコード断片の末尾で切れている（コードの完全な実装に応じて戻り値説明を確認してください）。実装方針としては (fetched_count, saved_count) を返すことを想定しています。
- 一部の外部 API 呼び出しはネットワーク依存のため、実運用では十分な監視・リトライ設定確認を推奨します。

---

以上が v0.1.0 の主な変更点・追加機能です。今後のリリースでは品質チェック（quality モジュール）、ストラテジー層、実行（kabu ステーション統合）の強化、モニタリング／アラート機能などを追加予定です。