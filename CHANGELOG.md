# CHANGELOG

すべての重要な変更は Keep a Changelog の形式で記録します。  
このファイルはコードベースの現在の状態から推測して作成しています。初期リリース相当の記録としてまとめています。

フォーマットおよび意味:
- Added: 新機能
- Changed: 既存機能の変更（互換性に注意）
- Fixed: 修正（バグ修正）
- Security: セキュリティ関連

なお現行バージョンはパッケージの __version__ に基づき v0.1.0 としています。

Unreleased
----------


0.1.0 - 2026-03-16
------------------

Added
- パッケージ初期構成
  - パッケージ名: kabusys、バージョン: 0.1.0
  - モジュール分割: data, strategy, execution, monitoring（strategy/execution/monitoring は初期のパッケージ入口ファイルを用意）

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは OS 環境変数から設定を自動読込
    - プロジェクトルート検出ロジック: .git もしくは pyproject.toml を起点に探索（CWD に依存しない）
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能
  - .env パーサ実装の強化:
    - 空行・コメント行のスキップ
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応
    - クォート無しの値に対するインラインコメント認識（直前に空白/タブがある場合のみ）
  - Settings クラスを公開 (settings):
    - J-Quants, kabuステーション, Slack, データベースパス等のプロパティ
    - 必須項目未設定時は ValueError を送出する _require 関数
    - KABUSYS_ENV (development/paper_trading/live) と LOG_LEVEL のバリデーション
    - デフォルトの DB パス: DuckDB = data/kabusys.duckdb、SQLite = data/monitoring.db

- データ (kabusys.data)
  - J-Quants API クライアント (jquants_client.py)
    - API 通信機能: prices（日次OHLCV）、fins（四半期財務）、markets/trading_calendar を取得する fetch_* 関数群
    - レート制御: 120 req/min に合わせた固定間隔スロットリング（_RateLimiter）
    - リトライ戦略:
      - 最大 3 回の指数バックオフリトライ（ネットワーク系および 408/429/5xx を対象）
      - 429 の場合は Retry-After ヘッダ優先
      - 401 受信時はリフレッシュトークンで自動リフレッシュを行い 1 回リトライ（無限再帰防止フラグあり）
    - トークン管理: モジュールレベルの ID トークンキャッシュ（ページネーション間で共有）
    - ページネーション対応 (pagination_key) を考慮した fetch 実装
    - DuckDB への保存関数 (save_daily_quotes, save_financial_statements, save_market_calendar):
      - 挿入は冪等（ON CONFLICT DO UPDATE）で重複を排除
      - fetched_at に UTC タイムスタンプを記録（Look-ahead Bias 対策）
      - PK 欠損行はスキップして警告ログ出力
    - 型変換ユーティリティ (_to_float, _to_int) による堅牢な変換と不正値ハンドリング

  - DuckDB スキーマ定義と初期化 (schema.py)
    - 3 層データモデル（Raw / Processed / Feature）および Execution 層を反映した DDL を提供
    - raw_prices, raw_financials, raw_news, raw_executions 等の Raw テーブル
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブル
    - features, ai_scores 等の Feature テーブル
    - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution テーブル
    - 運用を考慮したチェック制約、DEFAULT、PRIMARY KEY、FOREIGN KEY の定義
    - 利用頻度に基づくインデックス作成（銘柄×日付スキャン、ステータス検索、外部参照列等）
    - init_schema(db_path) によりディレクトリ作成→テーブル/インデックス作成を行い DuckDB 接続を返す
    - get_connection(db_path) により既存 DB への接続を返す（初期化は行わない）

  - ETL パイプライン (pipeline.py)
    - 日次の差分 ETL 実装:
      - run_daily_etl: 市場カレンダー → 株価日足 → 財務データ → 品質チェック の順で実行
      - 各ステップは独立してエラーハンドリング（1 ステップ失敗でも他は継続）
    - 差分計算ロジック:
      - raw_* テーブルの最終取得日を参照し未取得範囲のみ取得
      - デフォルトのバックフィル: 最終取得日の n 日前（デフォルト 3 日）から再取得して API の後出し修正を吸収
      - 市場カレンダーは先読み（デフォルト 90 日）して営業日判定に使用
      - target_date が非営業日の場合は直近営業日に調整
    - 結果を ETLResult dataclass で集約（取得数・保存数・品質問題・エラー一覧を保持）
    - テスト容易性のため id_token を注入可能

  - 監査ログ（audit.py）
    - シグナル→発注→約定の完全トレースを目的とした監査テーブル定義
      - signal_events, order_requests (冪等キー order_request_id), executions
    - トレーサビリティ設計（business_date, strategy_id, signal_id, order_request_id, broker_order_id の階層）
    - すべての TIMESTAMP は UTC 保存を前提（init_audit_schema は SET TimeZone='UTC' を実行）
    - order_requests に対する注文種別・価格チェック（limit/stop/market の制約）を実装
    - init_audit_schema(conn) と init_audit_db(db_path) を提供

  - 品質チェックモジュール (quality.py)
    - DataQuality の主要チェックを実装:
      - 欠損データ検出 (OHLC 欠損) → check_missing_data
      - スパイク検出（前日比絶対値 > threshold、デフォルト 50%）→ check_spike
      - （重複チェック、日付不整合等も想定。少なくとも主要チェックのデータクラス QualityIssue を定義）
    - QualityIssue dataclass による問題の構造化（check_name, table, severity, detail, rows）
    - 各チェックは問題を全件収集して返す設計（Fail-Fast ではない）
    - DuckDB 上で SQL を実行して効率的に検査（パラメータバインディングを使用）

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- 環境変数の自動ロードを無効化するフラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を提供し、テストや CI での誤読込を防止

Notes / 開発者向け補足
- 初期化:
  - データベースは schema.init_schema() を呼び出して初期化すること。監査用テーブルは init_audit_schema() で追加可能。
- ETL 実行:
  - run_daily_etl(conn, target_date) を呼ぶことで差分 ETL と品質チェックが実行される。
- 設定:
  - 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（未設定時は起動時/呼び出し時に例外）
- 未実装 / 今後の拡張候補:
  - strategy / execution / monitoring モジュールの実装（現在はパッケージ入口のみ）
  - 追加の品質チェック（重複・将来日付・日付不整合）の SQL 実装
  - テストカバレッジ、CI ワークフロー、型チェッカーの統合

--- 

この CHANGELOG はコードベースの内容を解析して推測して作成したため、実際のリリースノートと差異がある可能性があります。必要であれば実際のコミット履歴やリポジトリメタデータに合わせて日付・内容を微調整します。