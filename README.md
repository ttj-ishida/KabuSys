KabuSys
=======

日本株向けの自動売買プラットフォーム基盤ライブラリ（モジュール群）
このリポジトリは、J-Quants / kabuステーション 等から市場データを取得し、DuckDB に格納するためのデータ基盤（ETL）、品質チェック、監査ログ（発注→約定トレース）といった共通機能を提供します。戦略層・実行層・監視層は別モジュールとして組み合わせて利用することを想定しています。

主な目的
- J-Quants API から株価・財務・マーケットカレンダーを安全に取得・保存
- DuckDB 上に 3 層（Raw / Processed / Feature）＋ Execution / Audit を構築
- ETL の差分更新・バックフィル・品質チェックを提供
- 監査ログ（signal → order_request → executions）の一貫したトレーサビリティを確保

機能一覧
- 環境設定管理
  - .env / .env.local を自動読み込み（プロジェクトルートを .git または pyproject.toml から探索）
  - 必須環境変数の取得とバリデーション
  - 自動ロード無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）
- J-Quants クライアント（data/jquants_client.py）
  - 日足 OHLCV、四半期財務、マーケットカレンダーの取得
  - ページネーション対応、レートリミット（120 req/min）順守
  - リトライ（指数バックオフ、最大 3 回。408/429/5xx 対象）
  - 401 受信時はリフレッシュトークンで自動的に ID トークンを更新して再試行
  - 取得時刻（fetched_at）を UTC で記録（Look-ahead bias 回避）
  - DuckDB への保存は冪等（ON CONFLICT DO UPDATE）
- DuckDB スキーマ定義（data/schema.py）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - インデックス、外部キー、制約を含めた初期化関数
  - init_schema(), get_connection()
- ETL パイプライン（data/pipeline.py）
  - 差分更新（最終取得日からの差分取得 + backfill）
  - 市場カレンダーの先読み（デフォルト 90 日）
  - 日次 ETL の統合エントリ（run_daily_etl）
  - 品質チェック（quality モジュール）実行オプション
- 品質チェック（data/quality.py）
  - 欠損データ検出、スパイク検出（前日比）、重複チェック、日付不整合（未来日付 / 非営業日）
  - 問題は QualityIssue オブジェクトで集約（error / warning）
- 監査ログ（data/audit.py）
  - signal_events / order_requests / executions の DDL と初期化
  - 発注フローを UUID 連鎖でトレース（order_request_id は冪等キー）
  - init_audit_schema(), init_audit_db()

セットアップ手順（ローカル開発向け）
- 必要要件
  - Python 3.10 以上（PEP 604 の型記法（|）を使用）
  - duckdb パッケージ
- 仮想環境作成（例）
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- パッケージインストール
  - pip install duckdb
  - （開発用にパッケージ化している場合）pip install -e .
- 環境変数（.env）の用意
  - プロジェクトルートに .env または .env.local を置くと自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - 主要な環境変数（例）:
    - JQUANTS_REFRESH_TOKEN: J-Quants の refresh token（必須）
    - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
    - KABU_API_BASE_URL: kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN: Slack 通知用の Bot トークン（必須）
    - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
    - DUCKDB_PATH: DuckDB ファイルパス（省略時: data/kabusys.duckdb）
    - SQLITE_PATH: 監視 DB 等に使う SQLite パス（省略時: data/monitoring.db）
    - KABUSYS_ENV: development | paper_trading | live（省略時: development）
    - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（省略時: INFO）
  - .env の書式はシェル形式に準拠（export 付き行やクォート、コメント処理に対応）

使い方（主要ユースケース）
- DuckDB スキーマ初期化（Python スクリプト例）
  - from pathlib import Path
    from kabusys.data import schema
    db_path = Path("data/kabusys.duckdb")
    conn = schema.init_schema(db_path)
  - 監査ログを追加する場合:
    - from kabusys.data import audit
      audit.init_audit_schema(conn)
  - 監査専用 DB を別に作る場合:
    - audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")

- J-Quants トークン取得（直接呼び出し）
  - from kabusys.data.jquants_client import get_id_token
    id_token = get_id_token()  # settings.jquants_refresh_token を使用して ID トークンを取得

- 日次 ETL の実行
  - from datetime import date
    from kabusys.data import pipeline, schema
    conn = schema.get_connection("data/kabusys.duckdb")  # 事前に init_schema() を実行しておく
    result = pipeline.run_daily_etl(conn, target_date=date.today())
    print(result.to_dict())
  - run_daily_etl は以下を順に実行します:
    1. 市場カレンダー ETL（先読み）
    2. 株価日足 ETL（差分 + backfill）
    3. 財務データ ETL（差分 + backfill）
    4. 品質チェック（オプション）

- 個別 ETL を呼ぶ
  - pipeline.run_prices_etl(conn, target_date)
  - pipeline.run_financials_etl(conn, target_date)
  - pipeline.run_calendar_etl(conn, target_date)

- 品質チェック単体実行
  - from kabusys.data.quality import run_all_checks
    issues = run_all_checks(conn, target_date=date.today())
    for i in issues: print(i)

注意・運用上のポイント
- API レート制限を厳守（J-Quants: 120 req/min）。jquants_client は内部で固定間隔スロットリングを行いますが、運用時は並列実行数に注意してください。
- 401 エラー発生時に自動リフレッシュを行いますが、refresh token が無効な場合は失敗します。refresh token は適切に管理してください。
- DuckDB のファイルパスの親ディレクトリは自動作成されますが、ファイルシステム権限に注意してください。
- run_daily_etl は各ステップで例外を補足して処理を継続します。戻り値 ETLResult の errors / quality_issues を確認してアラートや停止判定を行ってください。
- 監査ログは削除しない運用を想定しています（ON DELETE RESTRICT）。大きなデータ量になる可能性があるためアーカイブ・バックアップ設計を検討してください。

ディレクトリ構成（主要ファイル）
- src/
  - kabusys/
    - __init__.py                # パッケージ定義（__version__ 等）
    - config.py                  # 環境変数・設定管理（settings オブジェクト）
    - data/
      - __init__.py
      - jquants_client.py        # J-Quants API クライアント（取得・保存・リトライ・レート制御）
      - schema.py                # DuckDB スキーマ定義と初期化
      - pipeline.py              # ETL パイプライン（差分更新・backfill・統合）
      - quality.py               # データ品質チェック
      - audit.py                 # 監査ログ（signal / order_request / executions）
      - pipeline.py              # ETL 実行ロジック（再掲）
    - strategy/
      - __init__.py              # 戦略層のエントリ（今後実装を想定）
    - execution/
      - __init__.py              # 発注実行層のエントリ（今後実装を想定）
    - monitoring/
      - __init__.py              # 監視・通知層（今後実装を想定）

付録：トラブルシューティング
- .env が読み込まれない
  - プロジェクトルート判定は __file__ の親ディレクトリを .git または pyproject.toml を基準に探索します。パッケージ配布後やインストール後に別の CWD で実行する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定し、手動で os.environ を設定するか dotenv 等を用いて読み込んでください。
- ID トークン関連のエラー
  - get_id_token() が失敗する場合は refresh token（JQUANTS_REFRESH_TOKEN）を確認してください。API 側の障害やレート制限の影響も考慮してください。
- DuckDB 操作のエラー
  - スキーマ初期化時に権限エラーが出る場合はデータディレクトリの所有者・パーミッションを確認してください。

ライセンス・貢献
- 本ドキュメントではライセンスファイルは示していません。リポジトリの LICENSE を参照してください。
- バグ修正・機能追加はプルリクエストでお寄せください。大きな設計変更は事前に Issue を出して議論してください。

この README はこのコードベースの現状実装（データ取得・スキーマ・ETL・品質・監査）に基づく概要と利用手順をまとめたものです。戦略実装やブローカ接続・監視周りは別モジュール／運用設計と組み合わせて利用してください。