CHANGELOG
=========

すべての変更は Keep a Changelog の方針に従って記載しています。  
このファイルはリポジトリ内の現在のコードベースから推測して生成した初期の変更履歴です。

[0.1.0] - 2026-03-18
-------------------

Added
- パッケージ初期リリース。
  - パッケージ名: KabuSys（src/kabusys）
  - バージョン: 0.1.0（src/kabusys/__init__.py）

- 設定/環境管理モジュールを追加（src/kabusys/config.py）。
  - .env ファイルまたは OS 環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み順: OS 環境変数 > .env.local > .env
    - プロジェクトルート判定は .git または pyproject.toml を基準に行うため、CWD に依存しない。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサ: export プレフィックス、クォート、インラインコメント処理に対応。
  - 必須設定の取得関数（_require）と Settings クラスを提供。
    - 必須環境変数（例）: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DB パスのデフォルト: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"
    - KABUSYS_ENV の有効値: development / paper_trading / live
    - LOG_LEVEL の有効値: DEBUG / INFO / WARNING / ERROR / CRITICAL
    - ユーティリティプロパティ: is_live / is_paper / is_dev

- J-Quants API クライアントを追加（src/kabusys/data/jquants_client.py）。
  - 主な機能:
    - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、市場カレンダーを取得する fetch_* 関数を実装。
    - ページネーション対応（pagination_key を用いたフェッチループ）。
    - レート制限遵守用の固定間隔レートリミッタ（120 req/min）。
    - リトライロジック（指数バックオフ、最大 3 回。対象: 408, 429, 5xx およびネットワークエラー）。
    - 401 を受信した場合は ID トークンを自動リフレッシュして 1 回だけリトライ（無限再帰対策あり）。
    - ID トークンのモジュールレベルキャッシュを実装（ページネーション間で再利用）。
    - DuckDB へ保存する save_* 関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT DO UPDATE による冪等性を確保。
    - fetched_at を UTC 形式で保存し、データの取得時刻をトレース可能にする。
  - ユーティリティ:
    - _to_float / _to_int による安全な型変換（不正値は None）。

- ニュース収集モジュールを追加（src/kabusys/data/news_collector.py）。
  - RSS フィードから記事を収集して DuckDB の raw_news に保存する機能を実装。
  - 主な特徴・設計:
    - defusedxml を使用して XML Bomb 等の攻撃を防御。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - リダイレクト検査用のカスタム RedirectHandler を実装し、リダイレクト先のスキームとホストの検証を行う。
      - ホストがプライベート/ループバック/リンクローカル/マルチキャストであれば拒否。
    - 応答サイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ再検査（Gzip bomb 防止）。
    - 記事ID は URL 正規化（tracking パラメータ除去、クエリソート等）後の SHA-256（先頭32文字）で生成し冪等性を保証。
    - テキスト前処理（URL 除去・空白正規化）。
    - DB 保存はトランザクションでまとめ、チャンク INSERT（INSERT ... RETURNING）で実際に挿入された ID を返す。
    - 銘柄コード抽出（4桁数字 + known_codes フィルタ）と一括保存サポート。
  - 公開 API:
    - fetch_rss(), save_raw_news(), save_news_symbols(), run_news_collection() など。

- DuckDB スキーマ定義と初期化モジュールを追加（src/kabusys/data/schema.py）。
  - DataSchema.md に基づく 3 層構造（Raw / Processed / Feature / Execution）で多数のテーブルを定義:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切なデータ型・チェック制約・主キー・外部キーを付与。
  - 実行時に作成する索引（頻出クエリ向け）を定義。
  - init_schema(db_path) で DB ファイルの親ディレクトリ作成 → 全DDL/インデックス実行 → DuckDB 接続を返す（冪等）。
  - get_connection(db_path) で既存 DB への接続を返す（初期化は行わない）。

- ETL パイプラインモジュールを追加（src/kabusys/data/pipeline.py）。
  - 差分更新（差分取得）を行う ETL ワークフローの支援関数を実装。
    - 最終取得日判定 get_last_price_date / get_last_financial_date / get_last_calendar_date。
    - 営業日調整ヘルパー _adjust_to_trading_day（market_calendar があれば直近の営業日に調整）。
    - run_prices_etl(): 差分更新ロジック、backfill_days による再取得（デフォルト3日）、fetch -> save の流れを実装。
  - ETLResult dataclass を導入し、実行結果（取得数、保存数、品質問題、エラー等）を集約して返却可能。
  - 品質チェックモジュール（quality）との連携を想定した設計（品質チェックは重大度に応じたフラグ管理）。

- パッケージ構造・エクスポート
  - top-level __all__ に data, strategy, execution, monitoring を含める（src/kabusys/__init__.py）。
  - 空のパッケージ初期化ファイルを strategy/ と execution/ に追加。

Changed
- N/A（初期リリースのため既存機能の変更はなし）

Fixed
- N/A（初期リリースのためバグ修正履歴はなし）

Security
- ニュース収集で複数のセキュリティ対策を導入:
  - defusedxml による XML パース保護。
  - SSRF 対策（スキーム検証、プライベートアドレス検出、リダイレクト時の前検証）。
  - レスポンスサイズ上限（10MB）と Gzip 解凍後の再検査による DoS/Gzip bomb 対策。
- J-Quants クライアント: 401 自動リフレッシュ時の無限再帰防止とリトライ制御。

Notes / Migration
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings 経由で必須取得されるため、実行前に設定してください。
- 自動 .env ロードはデフォルトで有効。テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- DuckDB と defusedxml が依存パッケージとして必要です。
- init_schema() を初回実行して DB スキーマを作成してください（":memory:" もサポート）。

今後の予定（想定）
- quality モジュールの実実装（欠損・スパイク等の判定ルール）。
- strategy と execution パッケージの具体的実装（シグナル生成、発注処理）。
- モニタリング / Slack 通知等の統合（Settings に Slack 設定はあるため連携を予定）。

連絡・貢献
- これはコードから推測して生成した初期 CHANGELOG です。誤りや補足があればリポジトリの実装に合わせて更新してください。