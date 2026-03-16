CHANGELOG
=========

すべての重要な変更はここに記録します。  
このファイルは Keep a Changelog の慣習に従っています。  
詳細は https://keepachangelog.com/ja/ を参照してください。

[Unreleased]
-------------

- （現在なし）

0.1.0 - 2026-03-16
------------------

Added
- 初回リリース。日本株自動売買プラットフォームの基本コンポーネントを追加。
  - パッケージメタ:
    - kabusys パッケージ初期化（__version__ = 0.1.0, export モジュール群）。
  - 設定／環境変数管理（kabusys.config）:
    - .env ファイルおよび環境変数から設定を自動読み込み（.env, .env.local、OS 環境変数優先）。
    - 自動ロードを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - プロジェクトルート検出ロジック: 親ディレクトリに .git または pyproject.toml がある場所を基準に探索。
    - .env パーサ: export 形式、シングル/ダブルクォート、エスケープ、行内コメントの取り扱いに対応。
    - Settings クラスを提供（J-Quants リフレッシュトークン、kabu API 設定、Slack トークン/チャンネル、DB パス等）。
    - 入力検証: KABUSYS_ENV は development/paper_trading/live、LOG_LEVEL は標準ログレベルのみ許可。
    - デフォルトの DB パス: DuckDB -> data/kabusys.duckdb、SQLite -> data/monitoring.db。
  - J-Quants API クライアント（kabusys.data.jquants_client）:
    - データ取得: 日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーを取得する fetch_* 関数群。
    - ページネーション対応（pagination_key を追跡）。
    - レート制限: 固定間隔スロットリングで 120 req/min を遵守（_RateLimiter）。
    - 再試行ロジック: 指数バックオフで最大 3 回リトライ、HTTP 408/429/5xx を再試行対象に含む。
    - 429 時は Retry-After ヘッダを優先して待機。
    - 401 受信時は自動でリフレッシュトークンから id_token を再取得して 1 回だけリトライ（無限再帰回避）。
    - id_token キャッシュによりページネーション間でトークンを共有。
    - DuckDB へ冪等に保存する save_* 関数（ON CONFLICT DO UPDATE を利用）。
    - データ取得時刻（fetched_at）を UTC で記録し、Look‑ahead bias を防止可能にする設計。
    - 型変換ユーティリティ（_to_float, _to_int）を実装し、不正値や空値を安全に扱う。
  - DuckDB スキーマ定義と初期化（kabusys.data.schema）:
    - Raw / Processed / Feature / Execution の多層スキーマを定義。
    - raw_prices, raw_financials, raw_news, raw_executions 等の Raw テーブル。
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブル。
    - features, ai_scores 等の Feature テーブル。
    - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution テーブル。
    - 頻出クエリのためのインデックスを複数定義。
    - init_schema(db_path) による自動ディレクトリ作成と冪等的テーブル作成。
    - get_connection(db_path) による既存 DB 接続取得（初期化は行わない点に注意）。
  - ETL パイプライン（kabusys.data.pipeline）:
    - 日次 ETL 処理 run_daily_etl を実装（カレンダー→株価→財務→品質チェックの順）。
    - 差分更新ロジック: DB の最終取得日から差分のみを取得し、backfill_days による再取得で API の後出し修正を吸収。
    - カレンダーは lookahead_days（デフォルト 90 日）先まで先読み。
    - 各ステップは独立してエラーハンドリングし、1 ステップ失敗でも他は継続（Fail‑Fast ではなく集約型エラー収集）。
    - ETLResult データクラスで結果／品質問題／エラーを集約。品質問題は詳細を含む辞書化が可能。
    - 営業日調整ヘルパー: market_calendar に基づき target_date を直近の営業日に調整（最大 30 日遡り）。
  - 品質チェック（kabusys.data.quality）:
    - QualityIssue データクラスを実装（check_name, table, severity, detail, rows）。
    - 欠損データ検出（OHLC の欠損チェック、デフォルトでエラー扱い）。
    - スパイク検出（前日比の絶対変動率が閾値を超える場合を検出、デフォルト閾値 50%）。
    - 重複チェック、日付不整合チェックなどに対応する設計（SQL ベース、パラメータバインドで安全）。
    - 各チェックは全件収集し、呼び出し側が重大度に応じて対処を決定可能。
  - 監査ログ（kabusys.data.audit）:
    - シグナル→発注要求→約定を UUID 連鎖でトレースする監査スキーマを追加。
    - signal_events（戦略が生成したすべてのシグナルを記録）、order_requests（冪等キー order_request_id を持つ発注要求）、executions（証券会社からの約定ログ）を定義。
    - order_requests のステータス遷移や価格チェック（limit/stop の必須チェック等）を DDL レベルで制約。
    - init_audit_schema(conn) / init_audit_db(db_path) による初期化関数を提供。すべての TIMESTAMP を UTC で保存するために SET TimeZone='UTC' を実行。
  - その他:
    - data および strategy / execution / monitoring のパッケージ構成を用意（__init__.py を配置）。
    - ログ出力箇所により ETL や API 呼び出し等の状態を追跡可能。

Changed
- 初版のため既存からの移行なし。

Fixed
- 初版のため既存バグ修正なし。

Security
- セキュリティ関連:
  - 秘密情報（J-Quants のリフレッシュトークン等）は環境変数経由で取得。自動 .env ロードはテスト時に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

Notes / Developer guidance
- 必須環境変数（例）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - 設定が不足すると Settings のプロパティ取得で ValueError を送出。
- DuckDB 初期化:
  - 初回は data.schema.init_schema(db_path) を呼び出してテーブルを作成してください。
  - 監査ログのみ別 DB に分離したい場合は init_audit_db() を利用できます。
- ETL 実行:
  - run_daily_etl(conn, target_date=None) を利用し、戻り値の ETLResult により保存件数・品質問題・エラーを確認してください。
- 既知の制約:
  - 現時点で strategy・execution の具象実装は含まれておらず、パッケージ骨組みのみ提供しています。

今後の予定（未実装 / 検討中）
- strategy・execution 層の具体的な戦略実装、ブローカ統合（kabu ステーションとの発注フロー）、
  モニタリング／アラート機能の追加（Slack 通知連携の実装など）。
- 単体テスト・統合テストの整備、CI/CD の導入。
- performance 最適化や大量データ処理時のチューニング。

--- 

この CHANGELOG はリポジトリの初期コードベースから推測して作成しています。実際のリリースノートには運用やドキュメント情報を反映してください。