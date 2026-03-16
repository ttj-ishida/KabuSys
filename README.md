# KabuSys — 日本株自動売買プラットフォーム (README)

概要
----
KabuSys は日本株の自動売買プラットフォーム向けのコアライブラリです。  
主にデータ収集（J-Quants API）、データベース管理（DuckDB スキーマ）、ETL パイプライン、品質チェック、監査ログ（発注→約定のトレーサビリティ）を提供します。  
戦略層・実行層・監視層は拡張可能な設計になっており、バックエンドのデータ基盤と発注監査を安定的に構築できます。

主な特徴
--------
- J-Quants API クライアント
  - 株価日足（OHLCV）、四半期決算（BS/PL）、JPX マーケットカレンダーを取得
  - レートリミット（120 req/min）・リトライ・トークン自動リフレッシュを実装
  - 取得時刻（fetched_at）を UTC で記録して look-ahead bias を防止
- DuckDB スキーマ
  - Raw / Processed / Feature / Execution の多層スキーマを定義
  - 冪等な保存（ON CONFLICT DO UPDATE）、インデックス定義
- ETL パイプライン
  - 差分更新（最終取得日ベース）とバックフィル機能
  - 市場カレンダーの先読み、品質チェック統合
- データ品質チェック
  - 欠損・重複・スパイク（急騰/急落）・日付不整合（未来日・非営業日）検出
  - QualityIssue を集約して呼び出し元に返す（Fail-Fast ではなく全件収集）
- 監査ログ（audit）
  - シグナル→発注要求→約定を UUID 連鎖でトレース
  - 発注の冪等キー、ステータス管理、UTC タイムスタンプ設計

要件（推奨）
------------
- Python 3.10+
  - 型注釈に Python 3.10 の union 型表現（A | B）を使用
- duckdb
- （利用する機能によって）インターネット接続、J-Quants のリフレッシュトークン、kabuステーション API、Slack トークンなど

セットアップ手順
----------------
1. リポジトリをクローン / コピー
   - 例: git clone <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージのインストール
   - duckdb をインストール（最低限）:
     - pip install duckdb
   - プロジェクトをローカル開発インストール（プロジェクトルートに pyproject.toml/setup がある想定）:
     - pip install -e .

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを使用してください）

4. 環境変数設定
   - プロジェクトルートに .env または .env.local を置くと、自動的に読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード
     - SLACK_BOT_TOKEN — Slack ボットトークン（通知用）
     - SLACK_CHANNEL_ID — Slack チャネル ID
   - 任意:
     - KABUSYS_ENV — (development | paper_trading | live), default: development
     - LOG_LEVEL — (DEBUG | INFO | WARNING | ERROR | CRITICAL), default: INFO
     - DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite パス（default: data/monitoring.db）

.env.example（参考）
-------------------
以下は .env ファイルの例です（実際のトークンは秘匿してください）。

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

使い方（基本例）
----------------

1) DuckDB スキーマ初期化
- Python REPL / スクリプトから:
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

  - ":memory:" を渡すとインメモリ DB が使用できます:
    conn = init_schema(":memory:")

2) 監査ログ（audit）テーブルの初期化（既存 conn に追加）
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn)

  または、監査専用 DB を初期化:
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")

3) 日次 ETL 実行
- 日次 ETL は市場カレンダー → 株価 → 財務 → 品質チェック の順に実行します。

  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # target_date を指定しないと今日が対象
  print(result.to_dict())

  - 戻り値は ETLResult オブジェクト。fetched/saved/quality_issues/errors を確認できます。

4) 個別データ取得（テスト・開発向け）
- J-Quants から直接データを取得する際（トークンは settings から自動取得）:

  from kabusys.data import jquants_client as jq
  records = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
  # DuckDB に保存する場合:
  saved = jq.save_daily_quotes(conn, records)

5) 品質チェックの単体実行
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2023,1,31))
  for i in issues:
      print(i)

設定管理の注意点
-----------------
- .env の自動読み込み
  - パッケージ import 時にプロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を自動ロードします。
  - テストや CI で自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- 必須環境変数が未設定の場合、settings のプロパティ呼び出しで ValueError が発生します。早期に .env を準備してください。

API の設計上のポイント（実装上の注記）
-------------------------------------
- J-Quants クライアントはレート制限（120 req/min）を守るために固定間隔スロットリングを使用します。
- HTTP エラー時はリトライ（最大 3 回、指数バックオフ）を行います。401 は自動的にリフレッシュして一回のみリトライします。
- ETL の保存は冪等（ON CONFLICT DO UPDATE）で設計されています。
- 取得時刻（fetched_at）は UTC の ISO 8601 で記録されます。
- 品質チェックは Fail-Fast ではなく全検査を行い、問題の一覧を返します。呼び出し元で停止・アラート処理を行ってください。

ディレクトリ構成（主要ファイル）
-----------------------------
以下はパッケージ内の主要ファイル（抜粋）です:

src/kabusys/
- __init__.py
- config.py                (環境変数・設定管理)
- data/
  - __init__.py
  - jquants_client.py      (J-Quants API クライアント + 保存ロジック)
  - schema.py              (DuckDB スキーマ定義・初期化)
  - pipeline.py            (ETL パイプライン)
  - quality.py             (データ品質チェック)
  - audit.py               (監査ログ用テーブル定義/初期化)
  - audit.py               (監査ログ)
- strategy/
  - __init__.py            (戦略モジュール用プレースホルダ)
- execution/
  - __init__.py            (発注実行モジュール用プレースホルダ)
- monitoring/
  - __init__.py            (監視用プレースホルダ)

よくある運用フロー（例）
-----------------------
- 初期化:
  - init_schema() で DB を作成
  - run_daily_etl() を cron/スケジューラで日次実行
- 戦略バッチ:
  - features テーブルを作成し戦略ロジックで signals を生成
  - signal_queue / orders / trades を通じて実際の発注管理を行う
- 監査:
  - audit テーブル（signal_events, order_requests, executions）で全履歴を格納
- 監視:
  - 品質チェック結果や ETLResult を Slack に通知して運用アラートを行う

開発・寄稿
----------
- 新しい機能（戦略・実行・監視）を追加する場合は、data レイヤーのスキーマ拡張と互換性を確認してください（DDL は冪等であることが前提）。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して環境の独立性を確保してください。
- DuckDB のインメモリ DB(":memory:") を利用すると単体テストが簡単になります。

サポート / 注意事項
------------------
- 実運用でライブ発注を行う場合は、KABUSYS_ENV を必ず適切に設定し（paper_trading / live）、発注前に十分な検証を行ってください。
- API キーやトークンは漏えいしないよう管理してください。
- J-Quants の利用制限・利用規約に従ってください。

以上が README のサンプルです。必要に応じて CI の設定、Docker 利用例、具体的な戦略テンプレートや Slack 通知ハンドラのサンプルも追加可能です。必要な項目があれば教えてください。