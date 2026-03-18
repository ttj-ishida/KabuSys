# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。J-Quants / RSS 等から市場データやニュースを収集し、DuckDB に保存・監査・品質検査を行い、戦略・実行層に渡すための基盤機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は次の領域をカバーするモジュール群で構成されています。

- データ取得（J-Quants API：日次株価、四半期財務、JPXカレンダー）
- ニュース収集（RSS → 前処理 → DuckDB へ保存、銘柄抽出）
- データスキーマ（DuckDB に格納するテーブル定義）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- カレンダー管理（営業日判定・次/前営業日取得）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- 設定管理（環境変数 / .env 読み込み）

設計上のポイント:

- J-Quants API 呼び出しはレートリミット（120 req/min）遵守、リトライ・トークン自動リフレッシュあり
- DuckDB への保存は冪等性（ON CONFLICT）を確保
- ニュース収集は SSRF / XML Bomb / 大容量応答などのセキュリティ対策を実装
- 品質チェック（欠損・スパイク・重複・日付不整合）を提供

---

## 主な機能一覧

- 環境設定管理（kabusys.config）
  - .env/.env.local の自動読み込み（プロジェクトルート判定：.git または pyproject.toml）
  - 必須環境変数の検証（例: JQUANTS_REFRESH_TOKEN）
- J-Quants クライアント（kabusys.data.jquants_client）
  - 株価日足 / 財務データ / 市場カレンダー取得（ページネーション対応）
  - レートリミット、リトライ、IDトークン自動リフレッシュ
  - DuckDB への冗長保存関数（save_*）
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、前処理（URL除去・空白正規化）、記事ID生成（正規化URL の SHA-256）
  - DuckDB へ冪等保存、銘柄コード抽出・紐付け
  - SSRF・XML脆弱性対策、受信サイズ制限
- スキーマ定義 / 初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution / Audit 各レイヤーのテーブル定義
  - init_schema(db_path) により DuckDB を初期化
- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新、バックフィル、品質チェック（kabusys.data.quality）
  - run_daily_etl() で一括実行
- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、次/前営業日取得、カレンダー夜間更新ジョブ
- 監査ログ初期化（kabusys.data.audit）
  - signal_events / order_requests / executions テーブル、インデックス管理

---

## 必要条件 / 依存関係

- Python >= 3.10（コード内で `|` 型注釈等を使用）
- 主要依存パッケージ（少なくとも次をインストールしてください）:
  - duckdb
  - defusedxml

例:
```bash
python -m pip install "duckdb" "defusedxml"
```

（プロジェクト配布時は requirements.txt / pyproject.toml に依存を書いてください）

---

## 環境変数

必須（少なくとも開発・ETL実行で想定される）:

- JQUANTS_REFRESH_TOKEN - J-Quants リフレッシュトークン
- KABU_API_PASSWORD      - kabuステーション API パスワード
- SLACK_BOT_TOKEN        - Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID       - Slack 通知先チャンネル ID

任意 / デフォルトあり:

- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化する場合に 1 を設定

自動 .env ロードの挙動:
- プロジェクトルート（.git または pyproject.toml の存在）を基準に .env を読み込みます。
- 読み込み順序: OS 環境変数 > .env.local > .env
- テストなどで自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

設定値は kabusys.config.settings 経由で参照できます。

---

## セットアップ手順（ローカル開発 / 運用準備）

1. リポジトリをクローンしてワークディレクトリへ
   (ローカルのプロジェクトルートに .git または pyproject.toml があることが自動読み込みの基準になります)

2. Python 仮想環境を作成して有効化
```bash
python -m venv .venv
source .venv/bin/activate  # macOS / Linux
# .venv\Scripts\activate    # Windows
```

3. 依存パッケージをインストール
```bash
python -m pip install --upgrade pip
python -m pip install duckdb defusedxml
# 追加の依存があればここでインストール
```

4. 必要な環境変数を設定
- 簡易的にはプロジェクトルートに `.env` として次を用意します（例）:
```
JQUANTS_REFRESH_TOKEN=あなたのリフレッシュトークン
KABU_API_PASSWORD=xxxxxxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```
- セキュリティのため `.env` を公開リポジトリに含めないでください (.gitignore に追加)。

5. DuckDB スキーマ初期化
- Python REPL またはスクリプトでスキーマを作成します:
```python
from kabusys.data.schema import init_schema
init_schema("data/kabusys.duckdb")  # ":memory:" も可能
```

6. （任意）監査ログ用 DB 初期化
```python
from kabusys.data.audit import init_audit_db
init_audit_db("data/kabusys_audit.duckdb")
```

---

## 使い方（代表的な API / 例）

以下は主要なユースケースの例です。実運用ではエラー処理・ログ出力・スケジューラ（cron / Airflow 等）を追加してください。

- DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

- 日次 ETL の実行（株価・財務・カレンダー取得 + 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定可
print(result.to_dict())
```

- ニュース収集ジョブ（RSS フィードから収集して保存、既知銘柄リストで紐付け）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")

# sources を省略するとデフォルトの RSS ソースが使用されます
known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # source 名ごとの新規保存数
```

- J-Quants から特定銘柄の日次株価を直接取得して保存
```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(code="7203", date_from=date(2024, 1, 1), date_to=date(2024, 12, 31))
saved = jq.save_daily_quotes(conn, records)
```

- カレンダー管理（次営業日・判定等）
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

---

## ディレクトリ構成

プロジェクトの主要ファイル/ディレクトリ構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                 -- 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py       -- J-Quants API クライアント（取得・保存）
      - news_collector.py       -- RSS ニュース収集・前処理・保存
      - schema.py               -- DuckDB スキーマ定義・初期化
      - pipeline.py             -- ETL パイプライン（run_daily_etl 等）
      - calendar_management.py  -- カレンダー管理・夜間更新ジョブ
      - audit.py                -- 監査ログ初期化（signal_events, order_requests, executions）
      - quality.py              -- データ品質チェック
    - strategy/                  -- 戦略関連（未実装のスタブ）
      - __init__.py
    - execution/                 -- 発注/実行関連（未実装のスタブ）
      - __init__.py
    - monitoring/                -- 監視関連（未実装のスタブ）

その他:
- .env / .env.local / .env.example （プロジェクトルートに配置）
- pyproject.toml or setup.cfg（プロジェクト配布時に追加）

---

## 運用上の注意点 / 推奨

- J-Quants の API レート制限（120 req/min）に注意してください。クライアントは固定間隔のスロットリングで制御しますが、複数プロセスで API を同時に叩くと共有レートを超える可能性があります。
- 機密情報（トークン / パスワード）は環境変数または安全なシークレットストアで管理してください。`.env` をリポジトリに含めないでください。
- 定期実行は夜間バッチ（営業日判定やカレンダー前読み込みを考慮）で行うと安定します。ETL は品質チェックでエラー検出後も処理を継続する設計になっているため、監視・アラートを別に設置してください（Slack 通知等）。
- DuckDB ファイルは定期バックアップを推奨します（監査ログは削除しない前提のため別バックアップが望ましい）。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env 読み込みを無効化できます。

---

## そのほか

- README に記載のコードサンプルは例です。エラー処理やログ設定、タイムアウト等は実運用に合わせてカスタマイズしてください。
- 戦略層（strategy）・発注実装（execution）・監視（monitoring）は拡張ポイントとして用意されています。プラグイン的に各モジュールを実装して組み合わせてください。

---

疑問点や追加したいサンプル（cron ジョブ例、Docker 化、Airflow 実装テンプレ等）があれば教えてください。必要に応じて README を拡張します。