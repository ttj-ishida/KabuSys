kabusys
=======

日本株向けのデータ基盤・自動売買フレームワーク（骨組み実装）。  
主に J-Quants API からのデータ収集、DuckDB ベースのスキーマ定義、ETL パイプライン、データ品質チェック、監査ログ（発注→約定のトレース）に重点を置いたモジュール群を提供します。

要点
- Python パッケージ名: kabusys
- 現バージョン: 0.1.0（src/kabusys/__init__.py）
- データ保存: DuckDB（ローカルファイルまたは :memory:）
- 外部 API: J-Quants（認証・レート制御・再試行・トークンリフレッシュ対応）
- 監査（発注→約定）用スキーマを別途初期化可能

主な機能
- J-Quants クライアント（デイリー株価、四半期財務、マーケットカレンダー）
  - レート制限（120 req/min）を固定間隔スロットリングで遵守
  - 再試行（指数バックオフ、最大 3 回）、401 時はトークン自動リフレッシュ
  - 取得時刻 (fetched_at) を UTC タイムスタンプで保存し、Look-ahead バイアス対策
  - DuckDB への保存は冪等（ON CONFLICT DO UPDATE）
- DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
  - run_daily_etl() により日次 ETL を実行、個別コンポーネントも呼べる
- データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 問題は QualityIssue オブジェクトで収集。致命度に応じて呼び出し元で判断
- 監査ログ（signal_events / order_requests / executions）
  - 発注フローを UUID 系列でトレース可能。監査テーブルの初期化 API あり
- 設定管理（環境変数 / .env の自動ロード、必須チェック）

セットアップ手順（開発環境）
- 前提: Python 3.9+（型アノテーションで | を使用しているため）、duckdb をインストール可能な環境

1. 仮想環境の作成・有効化
   - Unix/macOS:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows (PowerShell):
     - python -m venv .venv
     - .\.venv\Scripts\Activate.ps1

2. 依存パッケージのインストール
   - pip install duckdb
   - またはパッケージ配布がある場合: pip install -e .
   - 必要に応じて urllib 等の標準ライブラリは不要です（標準搭載）。

3. 環境変数（.env）を準備
   - プロジェクトルートに .env または .env.local を置くと、自動で読み込まれます（.git または pyproject.toml をプロジェクトルート判定基準に使用）。
   - 自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時など）。
   - 主な必須環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API のパスワード（発注機能を使う場合）
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（任意の通知連携を使う場合は必須）
     - SLACK_CHANNEL_ID: Slack チャンネル ID
   - 任意 / デフォルト値:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
     - KABU_API_BASE_URL: デフォルト http://localhost:18080/kabusapi
     - DUCKDB_PATH: デフォルト data/kabusys.duckdb
     - SQLITE_PATH: デフォルト data/monitoring.db

例 .env（サンプル）
- .env.example を参考に下記を作成してください（ファイルはリポジトリに含まれていない想定）:
  JQUANTS_REFRESH_TOKEN=your_refresh_token
  KABU_API_PASSWORD=your_kabu_password
  SLACK_BOT_TOKEN=xoxb-...
  SLACK_CHANNEL_ID=C01234567
  DUCKDB_PATH=./data/kabusys.duckdb
  KABUSYS_ENV=development
  LOG_LEVEL=INFO

使い方（主要 API の例）
- DuckDB スキーマを初期化して ETL を実行する簡単な例:

  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  # DB を初期化（ファイルがなければ作成）
  conn = init_schema(settings.duckdb_path)

  # 日次 ETL を実行（id_token は省略可能。settings のリフレッシュトークンから内部取得）
  result = run_daily_etl(conn)
  print(result.to_dict())

- 監査ログテーブル（order/exec の監査用）を既存接続に追加:

  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn)

- J-Quants の生データ取得を直接呼ぶ例:

  from kabusys.data import jquants_client as jq
  # 明示的にトークンを渡すことも可能
  records = jq.fetch_daily_quotes(date_from=date(2022,1,1), date_to=date(2022,1,31))
  # DuckDB に保存するには save_* を使用
  from kabusys.data.schema import get_connection
  conn = get_connection(settings.duckdb_path)
  jq.save_daily_quotes(conn, records)

設計上の注意点 / 実運用上のポイント
- レート制限: jquants_client は 120 req/min を守るためにスロットリングを行います。大量取得時は遅延が発生します。
- 再試行: ネットワークエラーや 408/429/5xx で最大 3 回までリトライ。429 の場合は Retry-After を尊重。
- トークン管理: 401 受信時はリフレッシュを一度だけ試みます（無限再帰対策あり）。
- ETL の冪等性: save_* 系は ON CONFLICT DO UPDATE を利用しているため、同一レコードを複数回投入しても上書きされます。
- 品質チェック: run_daily_etl は品質チェックで検出された問題を収集して返します。呼び出し側は結果の severity を見て運用判断してください。
- カレンダー: ETL は先に market_calendar を取得して「営業日」判定に使用します（lookahead を取得）。
- audit テーブルの TIMESTAMP は UTC を前提にします（init_audit_schema は接続に対して SET TimeZone='UTC' を実行します）。
- .env のパース挙動は一般的なシェル形式（export KEY=val、クォート、インラインコメントの扱い）に対応しています。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py                : パッケージ定義、__version__
  - config.py                  : 環境変数 / 設定管理（Settings）
  - data/
    - __init__.py
    - jquants_client.py        : J-Quants API クライアント（取得 + DuckDB 保存）
    - schema.py                : DuckDB スキーマ定義・初期化（Raw/Processed/Feature/Execution）
    - pipeline.py              : ETL パイプライン（差分更新・backfill・品質チェック）
    - audit.py                 : 監査ログスキーマ（signal/order_request/executions）
    - quality.py               : データ品質チェック（欠損・スパイク・重複・日付不整合）
  - strategy/
    - __init__.py              : 戦略モジュール（拡張ポイント）
  - execution/
    - __init__.py              : 発注/ブローカー連携（拡張ポイント）
  - monitoring/
    - __init__.py              : 監視関連（空のまま拡張可能）

API 要約（主要関数）
- config.Settings
  - settings.jquants_refresh_token, settings.kabu_api_password, settings.duckdb_path, settings.env, など

- data.jquants_client
  - get_id_token(refresh_token: str | None) -> str
  - fetch_daily_quotes(...), fetch_financial_statements(...), fetch_market_calendar(...)
  - save_daily_quotes(conn, records), save_financial_statements(conn, records), save_market_calendar(conn, records)

- data.schema
  - init_schema(db_path) -> DuckDB connection（全テーブルを作成）
  - get_connection(db_path) -> DuckDB connection（既存 DB への接続）

- data.pipeline
  - run_daily_etl(conn, target_date=None, ...) -> ETLResult
  - run_prices_etl / run_financials_etl / run_calendar_etl 個別実行可能

- data.quality
  - run_all_checks(conn, target_date=None, ...) -> list[QualityIssue]
  - check_missing_data / check_spike / check_duplicates / check_date_consistency

- data.audit
  - init_audit_schema(conn)  # 監査用テーブルを追加
  - init_audit_db(db_path)   # 監査専用 DB を初期化

トラブルシューティング
- .env が読み込まれない
  - プロジェクトルートは .git または pyproject.toml を基準に自動検出します。CI やテストで読み込みを制御する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API エラー（401）
  - リフレッシュトークンが無効な場合、get_id_token が失敗します。settings.jquants_refresh_token を確認してください。
- DuckDB 接続周り
  - init_schema() は親ディレクトリが存在しない場合に自動作成します。:memory: を指定すればインメモリ DB を使用できます。
- 大量データ取得が遅い
  - レート制限（120 req/min）のため意図的に遅くなる設計です。バルク取得を考える場合は API の仕様に合わせて取得ロジックを見直してください。

拡張ポイント
- strategy/ と execution/ パッケージは将来的に戦略定義（signal 生成）、リスク管理、ブローカー連携を追加することを想定しています。
- monitoring/ はメトリクス収集・アラート連携（Prometheus, Slack 通知など）で拡張可能です。

貢献 / 開発者向けメモ
- 型ヒントとドキュメント文字列を重視しています。ユニットテストや統合テストを追加すると品質が向上します。
- ETL の各ステップは例外を捕捉して続行する設計なので、呼び出し側で ETLResult を確認して適切なアラートや再試行を行ってください。

以上がこのコードベースの概要と利用ガイドです。追加したい利用例やドキュメントの要望があれば教えてください。