# KabuSys — 日本株自動売買システム

軽量なデータプラットフォームとETL、監査ログを備えた日本株向け自動売買基盤のプロトタイプ実装です。  
J-Quants API から株価・財務・市場カレンダーを取得して DuckDB に格納し、品質チェック・監査ログ・ETL パイプラインを提供します。発注・戦略・モニタリング層は拡張可能な構成になっています。

---

## 主な機能

- J-Quants API クライアント
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得
  - レート制限（120 req/min）対応のスロットリング
  - リトライ（指数バックオフ）・401 → リフレッシュトークン自動再取得対応
  - 取得時刻を UTC で記録（look-ahead bias 対策）
- DuckDB ベースのスキーマ管理
  - Raw / Processed / Feature / Execution の多層スキーマ定義と初期化
  - 冪等な INSERT（ON CONFLICT DO UPDATE）設計
- ETL パイプライン
  - 差分取得（最終取得日ベース）＋ backfill 対応
  - 市場カレンダーの先読み（lookahead）
  - 品質チェック（欠損・重複・スパイク・日付不整合）
  - ETL 結果を ETLResult で集約
- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定 のトレーサビリティテーブル
  - 発注要求の冪等キー（order_request_id）をサポート
- データ品質チェックモジュール
  - QualityIssue 型で問題を集計・返却（error / warning）

---

## 要件

- Python 3.10 以上（型注釈に PEP 604 等を使用）
- pip パッケージ:
  - duckdb
- ネットワークアクセス（J-Quants API / Slack / kabuステーション 等、必要に応じて）

（実行環境に応じて追加の依存やラッパーが必要になることがあります）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone ...（プロジェクトルートに .git があることを想定）

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb
   - （将来、requirements.txt を用意したら pip install -r requirements.txt）

4. 環境変数設定
   - プロジェクトルートに .env または .env.local を用意します。
   - 自動ロードはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD : kabuステーション API のパスワード
     - SLACK_BOT_TOKEN : Slack Bot トークン
     - SLACK_CHANNEL_ID : 通知先 Slack チャンネル ID
   - 任意／デフォルト:
     - KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH : 監視用 SQLite パス（デフォルト: data/monitoring.db）

   ※ .env のパースは shell 風のクォートやコメントに対応します（config._parse_env_line）。

5. スキーマ初期化
   - Python REPL やスクリプトから duckdb データベースを作成・初期化します。

     例:
     - from kabusys.data.schema import init_schema
       conn = init_schema("data/kabusys.duckdb")

---

## 使い方（主な API/例）

以下はライブラリを直接呼び出す最小の例です。適宜ログ設定やエラーハンドリングを追加してください。

- DuckDB スキーマの初期化
  - from kabusys.data.schema import init_schema
    conn = init_schema(settings.duckdb_path)  # settings は kabusys.config.settings

- 監査テーブルの初期化（既に init_schema で作成した conn に追加可能）
  - from kabusys.data.audit import init_audit_schema
    init_audit_schema(conn)

- J-Quants API でデータ取得（直接）
  - from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
    token = get_id_token()  # settings の refresh token を使用
    records = fetch_daily_quotes(id_token=token, date_from=date(2023,1,1), date_to=date(2023,1,31))

- ETL（日次パイプライン）
  - from kabusys.data.pipeline import run_daily_etl
    result = run_daily_etl(conn, target_date=None)  # target_date を指定しなければ今日を使用
    print(result.to_dict())

- データ品質チェックを個別に実行
  - from kabusys.data.quality import run_all_checks
    issues = run_all_checks(conn, target_date=None)
    for i in issues: print(i)

ポイント:
- ETL は差分更新を行い、既存データは ON CONFLICT で上書きするため基本的に冪等です。
- J-Quants へのリクエストは内部でレート制限とリトライを制御します。
- 401 応答時は自動で get_id_token により一回だけトークンリフレッシュを試行します。

---

## 簡単な実行サンプル

1. スキーマ作成 & ETL 実行

   - python -c "from kabusys.config import settings; from kabusys.data.schema import init_schema; from kabusys.data.pipeline import run_daily_etl; conn = init_schema(settings.duckdb_path); res = run_daily_etl(conn); print(res.to_dict())"

2. 品質チェックのみ

   - python -c "from kabusys.config import settings; from kabusys.data.schema import get_connection; from kabusys.data.quality import run_all_checks; conn = get_connection(settings.duckdb_path); print([i.__dict__ for i in run_all_checks(conn)])"

---

## 設計上の注意点 / 動作ポリシー

- レート制限: J-Quants は 120 req/min を想定しており、クライアントは固定間隔スロットリングで遵守します。
- リトライ: ネットワークエラー・一部ステータスコード（408, 429, 5xx）は最大 3 回の指数バックオフでリトライします。401 はトークン自動刷新を一度行います。
- 取得時刻（fetched_at）は UTC で保存し、データが「いつ取得されたか」を追跡可能にします（Look-ahead Bias 対策）。
- ETL は Fail-Fast ではなく、各ステップのエラーを集約して呼び出し元が判断できるようになっています（ETLResult.errors / quality issues）。

---

## ディレクトリ構成

（リポジトリの src/kabusys 以下を抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                      — 環境変数/設定読み込みロジック
    - data/
      - __init__.py
      - jquants_client.py            — J-Quants API クライアント（取得・保存ロジック）
      - schema.py                    — DuckDB スキーマ定義と init_schema / get_connection
      - pipeline.py                  — ETL パイプライン（差分取得・保存・品質チェック）
      - quality.py                   — データ品質チェック群
      - audit.py                     — 監査ログ（signal / order_request / execution）
    - strategy/
      - __init__.py                   — 戦略層（拡張用）
    - execution/
      - __init__.py                   — 発注/約定 / ブローカー連携（拡張用）
    - monitoring/
      - __init__.py                   — 監視/アラート（拡張用）

---

## 開発・拡張のヒント

- strategy/, execution/, monitoring/ はプレースホルダです。具体的な売買戦略やブローカー接続はここに実装してください。
- DuckDB のスキーマは data/schema.py に集約されています。追加のテーブルはここへ追記し、init_schema を通じて配布するのが推奨です。
- 品質チェックは SQL ベースで実装されているため、大量データでも比較的高速に実行できます。チェック結果を Slack へ通知するなどの連携は monitoring 層で実装してください。
- 自動環境変数読み込みは .git または pyproject.toml をプロジェクトルート検出の基準とします。テスト時に自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ライセンス / 貢献

この README はコードベースの概要を示すためのものであり、実運用にあたっては追加の安全対策（例: 発注の二重防止、詳細なエラーハンドリング、テスト、監査運用手順など）が必要です。貢献や提案は Pull Request / Issue を通じて行ってください。

---

必要であれば、README にサンプル .env.example、CLI スクリプト例、デプロイ手順（systemd / cron / Airflow 連携）などの追記も作成します。どの項目を優先して詳述しますか？