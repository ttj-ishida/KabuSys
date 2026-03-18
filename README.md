# KabuSys

日本株向けの自動売買プラットフォーム向けライブラリ（KabuSys）。  
データ取得（J-Quants）、ETL／データ品質、ニュース収集、マーケットカレンダー管理、監査ログなどの基盤機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株アルゴリズム取引のための基盤ライブラリ群です。主な目的は以下です。

- J-Quants API からの市場データ（株価日足・財務情報・マーケットカレンダー）取得
- DuckDB を用いた冪等なデータ保存（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分更新・バックフィル）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- RSS ベースのニュース収集と銘柄抽出（SSRF や XML Bomb対策済み）
- マーケットカレンダー運用（営業日判定、前後営業日探索）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）

設計上のポイント：
- API レート制御・リトライ・トークン自動更新を備えた J-Quants クライアント
- DuckDB への INSERT は ON CONFLICT を使い冪等性を担保
- データ収集・保存は部分失敗を許容して他処理を継続（ログで通知）
- セキュリティ対策（RSS の SSRF 対策、defusedxml を使った XML パース等）

---

## 機能一覧

- data/:
  - jquants_client: J-Quants API クライアント（取得・保存関数、認証トークン管理、レートリミット）
  - pipeline: 日次ETL（差分取得・保存・品質チェック）の実装
  - schema: DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
  - news_collector: RSS 取得・前処理・DB 保存・銘柄抽出
  - calendar_management: カレンダー更新ジョブと営業日判定ユーティリティ
  - quality: データ品質チェック（欠損、重複、スパイク、日付不整合）
  - audit: 発注〜約定の監査ログテーブル定義と初期化
- config: 環境変数管理（.env 自動読み込み、必須値チェック、環境種別判定）
- strategy/: 戦略層（拡張用のパッケージ位置）
- execution/: 発注実行（拡張用のパッケージ位置）
- monitoring/: 監視用（拡張用のパッケージ位置）

---

## 必要環境 / 依存

最低限の依存（このリポジトリ内のコードで明示的に使われているもの）:

- Python 3.9+（typing の演算子などを使用）
- duckdb
- defusedxml

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# パッケージとして開発インストールする場合
pip install -e .
```

（プロジェクトが配布する requirements.txt や pyproject.toml があればそれに従ってください）

---

## 環境変数

config.Settings で参照する主な環境変数:

必須:
- JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD      — kabuステーション API のパスワード
- SLACK_BOT_TOKEN        — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID       — Slack 通知先チャンネル ID

任意（デフォルトあり）:
- KABU_API_BASE_URL      — kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH            — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV            — 環境 (development | paper_trading | live)。デフォルト: development
- LOG_LEVEL              — ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）

自動で .env / .env.local をプロジェクトルートから読み込みます。自動ロードを無効化する場合は環境変数:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

.example の .env 例（README 用）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意: 秘密情報は公開リポジトリに置かないでください。

---

## セットアップ手順

1. リポジトリをクローンして移動
   ```bash
   git clone <repo_url>
   cd <repo_dir>
   ```

2. 仮想環境を作成して依存をインストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -e .  # または最低限: pip install duckdb defusedxml
   ```

3. 環境変数を用意
   - プロジェクトルートに `.env` または `.env.local` を作成し、上記の必須変数を設定します。
   - または環境に直接エクスポートします。

4. DuckDB スキーマを初期化
   - Python REPL またはスクリプトで:
     ```python
     from kabusys.data import schema
     from kabusys.config import settings

     conn = schema.init_schema(settings.duckdb_path)
     ```
   - 監査ログ用 DB を別に作る場合:
     ```python
     from kabusys.data import audit
     conn = audit.init_audit_db("data/kabusys_audit.duckdb")
     ```

---

## 使い方（簡単な実行例）

以下は代表的な利用例です。運用スクリプトに組み込んで Cron / Airflow / 他のジョブスケジューラから実行することを想定しています。

- 日次 ETL を実行してデータ取得・品質チェック
  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data import schema

  conn = schema.init_schema(settings.duckdb_path)  # 既に初期化済みなら get_connection でも可
  result = run_daily_etl(conn, target_date=None)  # target_date=None で今日
  print(result.to_dict())
  ```

- 市場カレンダーの夜間更新ジョブ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data import schema
  from kabusys.config import settings

  conn = schema.get_connection(settings.duckdb_path)
  saved = calendar_update_job(conn)
  print("saved", saved)
  ```

- RSS ニュース収集ジョブ（銘柄抽出付き）
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data import schema

  conn = schema.get_connection("data/kabusys.duckdb")
  # known_codes は有効な銘柄コードのセット（例: {"7203", "6758", ...}）
  results = run_news_collection(conn, known_codes={"7203", "6758"})
  print(results)
  ```

- J-Quants のトークンを直接使ってデータを取得
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使用して ID トークン取得
  quotes = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
  print(len(quotes))
  ```

ログレベルは環境変数 LOG_LEVEL で調整してください。

---

## ディレクトリ構成

主要なファイル構成（src 配下）:

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py                — J-Quants API クライアント（取得・保存）
    - news_collector.py                — RSS ニュース収集・DB保存・銘柄抽出
    - schema.py                        — DuckDB スキーマ定義・初期化
    - pipeline.py                      — 日次 ETL パイプライン
    - calendar_management.py           — マーケットカレンダー更新・営業日判定
    - quality.py                       — データ品質チェック
    - audit.py                         — 監査ログ（シグナル→注文→約定）
    - (その他のデータ関連モジュール)
  - strategy/
    - __init__.py                      — 戦略層の拡張ポイント
  - execution/
    - __init__.py                      — 発注実行の拡張ポイント
  - monitoring/
    - __init__.py                      — 監視関連の拡張ポイント

その他:
- pyproject.toml / setup.cfg / requirements.txt（プロジェクトに応じて存在）
- .env, .env.local（プロジェクトルートで自動読み込み可能）

---

## 注意事項 / 運用上のヒント

- API レート（J-Quants: 120 req/min）を考慮して、過度な並列リクエストを避けてください。jquants_client は内部でレート制御を行いますが、外部からの大量呼び出しは制御できません。
- .env ファイルに秘密情報を置く場合はアクセス権限に注意し、公開リポジトリへ含めないでください。
- DuckDB ファイルのバックアップ/ローテーションを運用ポリシーとして検討してください（ファイル破損やディスク消費への対策）。
- news_collector は外部 URL を取得するためネットワーク接続が必要です。SSRF 対策やレスポンスサイズ上限の設定が組み込まれていますが、実運用では追加のネットワーク制御（プロキシ・FW）を検討してください。
- テスト時に自動 .env 読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 開発・拡張のポイント

- strategy/ と execution/ は戦略ロジックやブローカー接続を追加するための場所です。戦略はシグナルを生成し signals / signal_queue に格納する形で連携できます。
- audit モジュールは発注の冪等キー（order_request_id）や監査履歴を厳格に記録するための DDL を用意しています。実際のブローカー送信ロジックを実装する際はここへ情報を追記してください。
- ETL の品質チェック（quality.run_all_checks）は Fail-Fast ではなく問題を収集する設計です。上流で判定（停止／通知）を行う場合は結果を解析して制御してください。

---

この README はコードベースの主要機能・使い方・セットアップをまとめたものです。個別 API の詳細や更なる運用手順（CI、デプロイ、監視設定等）はプロジェクトのドキュメント（DataPlatform.md 等）に従ってください。