# KabuSys

日本株向けの自動売買プラットフォーム向けライブラリ（ライブラリ群）。  
データ収集（J-Quants / RSS）、ETL、データ品質チェック、DuckDB スキーマ定義、監査ログ（発注→約定のトレース）などを提供します。

---

## 概要

KabuSys は日本株のデータプラットフォームを構成するためのモジュール群です。主に以下を目的としています。

- J-Quants API からの株価・財務・カレンダー取得（レート制御・再試行・トークン自動更新を備える）
- RSS フィードからのニュース収集と記事→銘柄紐付け（SSRF/圧縮/XML攻撃対策あり）
- DuckDB ベースのスキーマ定義・初期化（Raw / Processed / Feature / Execution / Audit 層）
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- データ品質チェック（欠損・スパイク・重複・日付不整合検出）
- 監査テーブル（シグナル→発注→約定の完全トレース）

設計上の特徴：
- API レート制御・指数バックオフリトライ・トークン自動リフレッシュ
- データ保存は冪等性を重視（ON CONFLICT / DO UPDATE / DO NOTHING）
- セキュリティ考慮（RSS収集時のSSRF対策、defusedxml の利用、受信サイズ制限 等）
- DuckDB を用いた軽量かつ自己完結型のデータストア

---

## 機能一覧

- 環境変数管理（.env/.env.local を自動ロード（OS環境変数優先））
- J-Quants クライアント
  - 日足（OHLCV）取得（ページネーション対応）
  - 財務諸表（四半期）取得
  - 市場カレンダー取得
  - トークン取得/更新ロジック
- ニュース収集（RSS）モジュール
  - URL 正規化、トラッキングパラメータ削除、記事ID生成（SHA-256）
  - SSRF 対策、gzip チェック、XML パース防御
  - raw_news / news_symbols への冪等保存
- DuckDB スキーマ定義・初期化
  - Raw / Processed / Feature / Execution / Audit 層
  - インデックス定義
- ETL パイプライン
  - 差分更新（最終取得日からの差分取得）
  - バックフィル（API の後出し修正吸収）
  - 品質チェック呼び出しの統合
- データ品質チェック
  - 欠損データ、スパイク（急騰・急落）、重複、日付不整合の検出
- 監査ログ（audit）
  - signal_events / order_requests / executions のテーブルとインデックス
  - 発注の冪等性（order_request_id）と UTC タイムゾーンの運用

---

## 前提 / 必要環境

- Python 3.10 以上（PEP 604 の union 型表記 等を使用）
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API / RSS フィード）

（実際のパッケージ要件は setup / pyproject.toml に従ってください）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動

   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成して有効化（例: venv）

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール（例）

   ```bash
   pip install duckdb defusedxml
   # またはプロジェクトにパッケージ定義があれば
   # pip install -e .
   ```

4. 環境変数の準備
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（OS環境変数が優先）。
   - 自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   最低限設定が必要な環境変数（コード上で必須とされているもの）：
   - JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD      — kabuステーション API のパスワード
   - SLACK_BOT_TOKEN        — Slack 通知用ボットトークン
   - SLACK_CHANNEL_ID       — Slack チャンネル ID

   その他の設定：
   - KABUSYS_ENV (development|paper_trading|live) — デフォルト: development
   - LOG_LEVEL (DEBUG|INFO|...) — ログレベル、デフォルト INFO
   - KABU_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
   - DUCKDB_PATH / SQLITE_PATH — データベースファイルパス（デフォルト: data/kabusys.duckdb, data/monitoring.db）

5. データベーススキーマの初期化（DuckDB）

   Python REPL やスクリプトで:

   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ファイルを作成・テーブル作成
   ```

   監査ログ（audit）テーブルを別 DB または同一接続へ追加する場合:

   ```python
   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn)  # conn は init_schema の返り値 など
   ```

---

## 使い方（簡単な例）

- 日次 ETL を実行する（株価・財務・カレンダー取得 + 品質チェック）:

  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- J-Quants から日足データを直接取得して保存する:

  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data import jquants_client as jq
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, records)
  print("saved:", saved)
  ```

- RSS からニュースを収集して保存（銘柄抽出あり）:

  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.news_collector import run_news_collection

  conn = init_schema("data/kabusys.duckdb")
  # known_codes は有効な銘柄コードのセット（例: {"7203","6758",...}）
  res = run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
  print(res)  # {source_name: 新規保存件数}
  ```

- 品質チェックを単体で実行する:

  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.quality import run_all_checks
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  issues = run_all_checks(conn, target_date=date.today(), reference_date=date.today())
  for i in issues:
      print(i)
  ```

---

## 設定 / 環境変数の詳細

主な環境変数（必須・任意）：

- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID

- 任意 / デフォルト:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
  - KABU_API_BASE_URL: デフォルト http://localhost:18080/kabusapi
  - DUCKDB_PATH: デフォルト data/kabusys.duckdb
  - SQLITE_PATH: デフォルト data/monitoring.db
  - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動ロードを無効化

.env ファイルのロード順序（優先度）:
1. OS 環境変数（最優先）
2. .env.local（存在すれば上書き）
3. .env（存在すれば読み込み）

---

## セキュリティ・運用に関する注意点

- RSS 取得時は SSRF/内部アドレスアクセスを排除するため、リダイレクト先のスキームやホスト/IP を検査します。
- XML 解析には defusedxml を使用し、XML Bomb 等への対策を行っています。
- J-Quants API へのアクセスはレート制御（120 req/min）と再試行戦略（指数バックオフ）を備えています。
- DuckDB 内のタイムスタンプは監査モジュールでは UTC を前提にしています（init_audit_schema で SET TimeZone='UTC' を実行）。

---

## ディレクトリ構成

リポジトリ内の主なファイル・モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理（.env 自動ロード）
  - data/
    - __init__.py
    - jquants_client.py           — J-Quants API クライアント（取得・保存）
    - news_collector.py           — RSS ニュース収集・保存・銘柄抽出
    - schema.py                   — DuckDB スキーマ定義・初期化
    - pipeline.py                 — ETL パイプライン（差分更新・品質チェック）
    - calendar_management.py      — 市場カレンダー管理／営業日判定
    - audit.py                    — 監査ログ（signal / order_request / executions）
    - quality.py                  — データ品質チェック
  - strategy/
    - __init__.py                 — 戦略のエントリポイント（将来的に実装）
  - execution/
    - __init__.py                 — 発注・約定処理（将来的に実装）
  - monitoring/
    - __init__.py                 — 監視用モジュール（将来的に実装）

（README に載せたものは主要ファイルの要約です。プロジェクト内にさらに補助スクリプトやドキュメントが存在する可能性があります。）

---

## 開発・貢献

- コードは種類ごとにモジュール化されています（data, strategy, execution, monitoring）。新しい機能は該当モジュールに追加してください。
- 単体テストやCI整備を行う場合、KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動 .env ロードを無効化するとテストの安定化に役立ちます。
- 重要な DB 操作はトランザクションで保護されています。外部 API 呼び出し周辺は適切にモック可能に実装されています（例: news_collector._urlopen の差し替え）。

---

必要であれば README にサンプル .env.example、より詳細な API 使用例、CI / デプロイ手順、依存バージョンの厳密な指定などを追記できます。どの情報を追加したいか教えてください。