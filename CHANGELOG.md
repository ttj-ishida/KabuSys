# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に合わせています。

## [Unreleased]
（今後の変更をここに記載）

## [0.1.0] - 2026-03-17

初期リリース。日本株自動売買システム「KabuSys」の基盤機能を提供します。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - パッケージエントリポイントを追加（kabusys.__version__ = "0.1.0"）。
  - public API として data, strategy, execution, monitoring を __all__ に公開。

- 環境設定管理（kabusys.config）
  - .env/.env.local ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルートの検出ロジック（.git または pyproject.toml を探索）を導入し、CWD に依存しない読み込みを実現。
  - .env パーサを実装: export プレフィックス対応、シングル/ダブルクォート対応、インラインコメントの扱い、コメント行スキップ等。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用途）。
  - Settings クラスを実装し、以下の設定プロパティを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH (デフォルト: data/kabusys.duckdb), SQLITE_PATH (デフォルト: data/monitoring.db)
    - KABUSYS_ENV (development / paper_trading / live), LOG_LEVEL の検証ロジック
    - is_live / is_paper / is_dev ヘルパー

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API 呼び出しユーティリティを実装（_request）。
    - レート制限を遵守する固定間隔スロットリング（120 req/min）。
    - 再試行ロジック（指数バックオフ、最大 3 回、対象ステータス 408/429/5xx）。
    - 401 受信時に自動的にリフレッシュトークンで id_token を取得して 1 回だけ再試行。
    - JSON デコードエラーに対する適切なエラー報告。
    - ページネーション対応の fetch_ 関数（pagination_key を利用）。
  - データ取得関数:
    - fetch_daily_quotes（OHLCV 日足、ページネーション対応）
    - fetch_financial_statements（四半期 BS/PL、ページネーション対応）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への保存関数（冪等: ON CONFLICT DO UPDATE）
    - save_daily_quotes（raw_prices）
    - save_financial_statements（raw_financials）
    - save_market_calendar（market_calendar）
  - ユーティリティ: _to_float/_to_int（堅牢な型変換）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集処理を実装（DEFAULT_RSS_SOURCES に Yahoo Finance を含む）。
  - 安全対策:
    - defusedxml による XML パース（XML Bomb 等の防御）。
    - SSRF 対策: URL スキーム検証 (http/https のみ)、リダイレクト先のスキーム/ホスト事前検証、プライベート IP 検出によるブロック。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）でメモリ DoS を防止。gzip 解凍後の検証も実施。
  - コンテンツ処理:
    - URL 正規化（スキーム/ホスト小文字化、トラッキングクエリ削除、フラグメント除去、クエリのソート）
    - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成し、冪等性を確保。
    - テキスト前処理（URL 除去・空白正規化）。
    - pubDate のパース（RFC 2822->UTC へ変換。失敗時は現在時刻を代替）。
  - DB 保存:
    - save_raw_news：チャンク（_INSERT_CHUNK_SIZE）で INSERT ... ON CONFLICT DO NOTHING RETURNING id を用いて新規挿入IDのみを返す。トランザクションでまとめて実行。
    - save_news_symbols / _save_news_symbols_bulk：記事と銘柄コードの紐付けをチャンク挿入で保存。重複除去および挿入数を正確に返却。
  - 銘柄コード抽出: 4桁数字の正規表現による抽出と known_codes によるフィルタリング（重複除去）。

- DuckDB スキーマ定義と初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の 3 層（+ Execution Layer）構造に基づくテーブル群を DDL で定義。
  - 主要テーブル（例: raw_prices, raw_financials, raw_news, prices_daily, market_calendar, fundamentals, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance など）を作成。
  - インデックスを多数定義し、頻出クエリのパフォーマンスを考慮。
  - init_schema(db_path) でディレクトリ自動作成と全テーブル・インデックスの冪等作成を実装。
  - get_connection(db_path) で既存 DB への接続を取得（初期化は行わない）。

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新を行う ETL の骨格を実装。
    - 差分判断用の get_last_price_date / get_last_financial_date / get_last_calendar_date を追加。
    - 日付調整ヘルパー（_adjust_to_trading_day）を追加: 非営業日の調整ロジック。
    - run_prices_etl の差分ロジックを実装（最終取得日の backfill を考慮した再取得、jquants_client.fetch & save の呼び出し）。
  - ETLResult データクラスを追加し、ETL 結果・品質問題・エラー情報を集約できる設計。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- ニュース収集で SSRF 対策を導入（スキーム検証、プライベートアドレス検出、リダイレクト時の検査）。
- XML パースに defusedxml を採用し、外部攻撃ベクトルを軽減。
- .env 読み込み時に OS 環境変数を protected として扱うことで意図しない上書きを防止。

### Notes / Migration
- 初回使用時は DuckDB のスキーマ初期化が必要です。init_schema(settings.duckdb_path) を呼び出してください。
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD
  - これらが未設定の場合は Settings のプロパティアクセスで ValueError が発生します。
- 自動 .env 読み込みはデフォルトで有効です。テスト等で無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API のレート制限は 120 req/min に固定しています。大量バッチ処理を行う際はこの制限を考慮してください。

### Known issues / TODO
- strategy および execution パッケージはエントリポイントのみで具体的な戦略・発注ロジックは未実装（今後の機能追加予定）。
- pipeline.run_prices_etl を含む ETL のさらに詳細な品質チェック（quality モジュール）や監査ログの統合は別途実装予定。
- 大量データ運用時のパフォーマンスチューニング（DuckDB の VACUUM/統計など）は今後の課題。

---

Authors: KabuSys 開発チーム

（変更履歴は今後のリリースで逐次追記します）