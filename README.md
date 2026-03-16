# KabuSys — 日本株自動売買システム

短い概要
- KabuSys は日本株の自動売買プラットフォーム向けに設計された Python パッケージ群です。
- データ取得（J-Quants）、データベーススキーマ（DuckDB）、監査ログ、データ品質チェックなど、自動売買システムの基盤となる共通機能を提供します。
- 戦略（strategy）、発注実行（execution）、監視（monitoring）用のパッケージを想定した構成になっており、実際の戦略やブローカー接続は各プロジェクトで実装します。

主な特徴
- J-Quants API クライアント
  - 日足（OHLCV）、財務諸表、マーケットカレンダーを取得
  - API レート制限 (120 req/min) を守る内部レートリミッタ
  - 401 時の自動トークン刷新、リトライ（指数バックオフ）実装
  - ページネーション対応、取得時刻（UTC）を記録して Look‑ahead Bias を防止
- DuckDB スキーマ
  - Raw / Processed / Feature / Execution の多層スキーマを定義
  - 冪等性を考慮した INSERT ... ON CONFLICT DO UPDATE を利用する設計
  - パフォーマンスを考慮したインデックス定義
- 監査ログ（audit）
  - シグナル→発注要求→約定までを UUID 連鎖でトレース可能
  - 冪等キー、ステータス遷移、UTC タイムスタンプ運用
- データ品質チェック（quality）
  - 欠損、重複、スパイク（急騰・急落）、日付整合性などのチェックを提供
  - 各チェックは QualityIssue のリストを返し、呼び出し元で扱える設計
- 設定管理（config）
  - .env ファイルや OS 環境変数から自動読込（プロジェクトルートを基準に .env/.env.local を読み込み）
  - 必須設定の取得ラッパー（Settings クラス）
  - 自動読込を無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD フラグあり

セットアップ手順（開発環境向け）
1. 前提
   - Python 3.10 以上（コード内での型注釈に Python 3.10 の構文（| 型）が使われています）
   - pip と仮想環境（venv / virtualenv 等）
   - DuckDB を利用するため pip install duckdb が必要
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）
3. パッケージのインストール
   - プロジェクトルートで:
     - pip install -e . もしくは requirements.txt がある場合は pip install -r requirements.txt
   - 必要な主要依存:
     - duckdb
4. 環境変数設定
   - プロジェクトルート（.git や pyproject.toml があるディレクトリ）に .env または .env.local を置くと自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主要な環境変数（必須は明記）:
     - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD (必須) — kabuステーション API パスワード
     - SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
     - SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
     - KABUSYS_ENV (任意) — one of: development, paper_trading, live（デフォルト: development）
     - LOG_LEVEL (任意) — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD (任意) — 自動 .env 読込を無効化するフラグ（"1"）
     - KABU_API_BASE_URL (任意) — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
     - DUCKDB_PATH (任意) — デフォルト data/kabusys.duckdb
     - SQLITE_PATH (任意) — デフォルト data/monitoring.db
   - .env の簡易例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxx
     KABU_API_PASSWORD=yyyyy
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     ```
5. データベース初期化（DuckDB）
   - Python REPL またはスクリプトで:
     ```python
     from kabusys.config import settings
     from kabusys.data.schema import init_schema

     conn = init_schema(settings.duckdb_path)
     ```
   - 監査ログ用スキーマを別 DB に用意したい場合:
     ```python
     from kabusys.data.audit import init_audit_db
     conn_audit = init_audit_db("data/kabusys_audit.duckdb")
     ```
   - 既存接続に監査テーブルを追加する場合:
     ```python
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn)  # conn: duckdb connection from init_schema
     ```

基本的な使い方（例）
- 設定値の参照:
  ```python
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  db_path = settings.duckdb_path
  if settings.is_live:
      # 本番向け処理
      pass
  ```
- J-Quants から日足を取得して DuckDB に保存:
  ```python
  from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes, save_daily_quotes
  from kabusys.data.schema import init_schema
  from kabusys.config import settings
  from datetime import date

  conn = init_schema(settings.duckdb_path)
  token = get_id_token()  # settings.jquants_refresh_token を使って ID トークンを取得
  records = fetch_daily_quotes(id_token=token, code="7203", date_from=date(2023,1,1), date_to=date(2023,12,31))
  saved = save_daily_quotes(conn, records)
  print(f"保存件数: {saved}")
  ```
  - fetch_* 系関数はページネーションとレート制御、リトライを内包しています。
  - save_* 系関数は冪等性を保つ INSERT ... ON CONFLICT を利用します。
- データ品質チェック:
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)  # 全チェックを実行
  for i in issues:
      print(i.check_name, i.severity, i.detail)
  ```
- 監査ログ関連の利用例（シンプルな初期化）:
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn)
  # 以後、アプリ側で signal_events / order_requests / executions テーブルに INSERT を行う
  ```

設計上のポイント・注意事項
- 自動 .env 読み込みはパッケージ import 時点で行われます（プロジェクトルートの .env/.env.local）。テストや特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットして読み込みを無効にできます。
- J-Quants クライアントは以下のポリシーに従います:
  - 120 req/min のレート制限を固定間隔スロットリングで制御
  - 指数バックオフによる最大 3 回のリトライ（408/429/5xx を対象）
  - 401 を受けたらリフレッシュトークンで自動取得を試み 1 回のみリトライ
- DuckDB の初期化関数は冪等（既存テーブルがあればスキップ）です。初回実行時は親ディレクトリが自動作成されます。
- すべての監査系 TIMESTAMP は UTC で保存する運用を前提としています（init_audit_schema は TimeZone を UTC に設定します）。
- quality モジュールは fail-fast ではなく検出された全件（サンプル）を返すため、呼び出し元で重大度に応じた処理（ETL 停止や警告）を実装してください。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py (パッケージ初期化・バージョン)
  - config.py (環境変数・設定管理、.env 自動読み込み、Settings クラス)
  - data/
    - __init__.py
    - jquants_client.py (J-Quants API クライアント: 取得 + DuckDB への保存)
    - schema.py (DuckDB スキーマ定義と初期化)
    - audit.py (監査ログスキーマと初期化)
    - quality.py (データ品質チェック)
  - strategy/
    - __init__.py (戦略実装用プレースホルダ)
  - execution/
    - __init__.py (発注実装用プレースホルダ)
  - monitoring/
    - __init__.py (監視実装用プレースホルダ)

（ファイルツリーの抜粋）
- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/data/jquants_client.py
- src/kabusys/data/schema.py
- src/kabusys/data/audit.py
- src/kabusys/data/quality.py
- src/kabusys/strategy/__init__.py
- src/kabusys/execution/__init__.py
- src/kabusys/monitoring/__init__.py

開発・運用上の推奨
- 本番運用（KABUSYS_ENV=live）の際はログレベルや Slack 通知、監査ログの運用ポリシーを明確にしてください。
- DB（DuckDB）ファイルは定期的にバックアップを取ることを推奨します（特に監査ログは削除しない前提）。
- J-Quants の呼び出しや長時間の ETL はレート制限・例外ハンドリングに注意して運用してください。

貢献・問い合わせ
- この README はコードベースの説明に焦点を当てています。戦略や実行ポリシーはプロジェクト固有の要件に従って実装してください。
- バグレポートや改善提案は Issue を通じてお願いします（リポジトリの運用ルールに従ってください）。

以上。必要ならば README をさらに拡張して、
- API リファレンス（各関数のパラメータ・戻り値の詳細）
- よくある質問（FAQ）
- デプロイ手順（systemd / Docker / CI）
なども追記します。どの内容を追加したいか教えてください。