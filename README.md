# KabuSys

日本株向け自動売買プラットフォーム用ライブラリセット（KabuSys）。  
データ取得・ETL、ニュース収集、マーケットカレンダー管理、データ品質チェック、監査ログなどの基盤機能を提供します。

---

## 概要

KabuSys は J-Quants API や RSS フィード、kabuステーション（発注系はインターフェース想定）等からデータを取り込み、DuckDB に保存・整備することを目的としたモジュール群です。  
設計上のポイント：

- データ取得はレート制限・リトライ・トークン自動更新に対応
- ETL は差分更新・バックフィルを行い冪等に保存（ON CONFLICT）
- ニュース収集では SSRF や XML Bomb に配慮した安全な実装
- 品質チェック（欠損・スパイク・重複・日付不整合）を実施
- 監査ログ（シグナル→発注→約定のトレーサビリティ）を DuckDB に保持

---

## 主な機能一覧

- data.jquants_client
  - J-Quants API から日足、四半期財務、マーケットカレンダーを取得・保存
  - レートリミット／リトライ／トークン自動更新対応
- data.pipeline
  - 日次 ETL（run_daily_etl）：カレンダー取得 → 株価 → 財務 → 品質チェック
  - 差分更新・バックフィル・営業日調整
- data.news_collector
  - RSS フィードの収集、前処理、DuckDB への冪等保存（raw_news）
  - 記事 ID は正規化 URL の SHA-256（先頭32文字）
  - SSRF/サイズ制限/defusedxml による安全対策
- data.calendar_management
  - 市場カレンダーの管理（営業日判定、前後営業日の取得、夜間カレンダー更新）
- data.quality
  - 欠損、スパイク、重複、日付不整合のチェック（QualityIssue を返す）
- data.schema / data.audit
  - DuckDB のスキーマ定義と初期化（Raw / Processed / Feature / Execution / Audit）
  - 監査ログ用スキーマの初期化（UTC 固定、トレーサビリティ確保）
- 設定管理（kabusys.config）
  - 環境変数 / .env 自動読み込み（プロジェクトルート検出）、必須チェック、環境モード判定

---

## 前提（依存関係）

最低限必要なライブラリ（抜粋）：

- Python 3.10+
- duckdb
- defusedxml

その他、標準ライブラリの urllib 等を使用しています。実際のプロジェクトでは pyproject.toml / requirements.txt を参照してインストールしてください。

例（pip）:
```
pip install duckdb defusedxml
```

---

## セットアップ手順

1. リポジトリをクローン / パッケージを入手

2. 仮想環境を作成（推奨）
```
python -m venv .venv
source .venv/bin/activate  # Unix/macOS
.venv\Scripts\activate     # Windows
```

3. 依存パッケージをインストール
```
pip install -r requirements.txt
# または最低限:
pip install duckdb defusedxml
```

4. 環境変数の設定
- プロジェクトルートに `.env` または `.env.local` を配置することで自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化）。
- 主な環境変数（例）:
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
  - KABU_API_PASSWORD: kabu API のパスワード（必須）
  - KABU_API_BASE_URL: kabu API のベース URL（省略可）
  - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
  - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: SQLite（モニタリング用）パス（デフォルト: data/monitoring.db）
  - KABUSYS_ENV: 実行環境 (development | paper_trading | live)（デフォルト: development）
  - LOG_LEVEL: ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)

例 .env（テンプレート）
```
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

5. DuckDB スキーマの初期化
- data.schema.init_schema(db_path) を呼ぶことで必要なテーブル・インデックスを作成します。
- 監査ログ専用 DB が必要な場合は data.audit.init_audit_db(db_path) を使用します。

---

## 使い方（簡易例）

以下はいくつかの基本的な利用例です。実際は適切なログ設定や例外処理を付与してください。

- DuckDB スキーマ初期化
```python
from kabusys.data import schema

conn = schema.init_schema("data/kabusys.duckdb")
# またはインメモリ
# conn = schema.init_schema(":memory:")
```

- 監査ログ DB 初期化（別 DB にする場合）
```python
from kabusys.data import audit

audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

- 日次 ETL 実行（run_daily_etl）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース収集ジョブ（RSS 収集→保存→銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes は銘柄コード集合（例: {"7203", "6758", ...}）
res = run_news_collection(conn, sources=None, known_codes=set(["7203", "6758"]))
print(res)  # {source_name: saved_count}
```

- カレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved:", saved)
```

- 品質チェックを個別に実行
```python
from kabusys.data import quality
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
issues = quality.run_all_checks(conn, target_date=date.today(), reference_date=date.today())
for iss in issues:
    print(iss)
```

---

## 設定と挙動の補足

- .env 自動読み込み
  - kabusys.config モジュールはパッケージファイル位置からプロジェクトルート（.git または pyproject.toml）を探索し、.env/.env.local を自動読み込みします。
  - テスト等で自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
  - 読み込み順: OS 環境変数 > .env.local > .env（.env.local は上書き可）

- 環境モード
  - KABUSYS_ENV は development / paper_trading / live のいずれか。live の場合は本番挙動にするフラグ（is_live 等）があります。

- ログ
  - LOG_LEVEL によりログレベルを制御します。デフォルトは INFO。

---

## ディレクトリ構成

リポジトリの主要なディレクトリ／ファイル（src 以下を抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数・設定管理（.env 自動読み込み、必須チェック）
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py            — RSS ニュース収集・前処理・保存・銘柄抽出
    - schema.py                    — DuckDB スキーマ定義と初期化（Raw/Processed/Feature/Execution）
    - pipeline.py                  — ETL パイプライン（差分取得・保存・品質チェック）
    - calendar_management.py       — カレンダー管理・夜間更新・営業日判定ユーティリティ
    - audit.py                     — 監査ログ用スキーマ（signal/order/execution トレーサビリティ）
    - quality.py                   — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - strategy/
    - __init__.py                  — 戦略関連（拡張ポイント、実装はここに置く）
  - execution/
    - __init__.py                  — 発注実行関連（kabuステーション等との接続を実装）
  - monitoring/
    - __init__.py                  — 監視・メトリクス（サンプル用の名前空間）

---

## 開発・運用における注意点

- セキュリティ
  - news_collector は SSRF・XML 攻撃・巨大レスポンスに対策していますが、運用時も信頼できる RSS ソースを管理してください。
  - トークン・パスワードは .env に保存する場合、アクセス制御を行い漏洩に注意してください。

- 冪等性
  - ETL・保存関数は ON CONFLICT を用いて冪等に設計されていますが、DDL やスキーマ変更時の互換性に注意してください。

- テスト容易性
  - jquants_client などは id_token 注入や _urlopen のモックが可能な設計です。ユニットテスト・統合テストを用意してから運用してください。

---

必要に応じて README にサンプル CLI、Dockerfile、CI ワークフロー、より詳細な .env.example を追加できます。もし追加してほしい項目（例: 実運用でのデプロイ手順、cron / GitHub Actions サンプル）があれば教えてください。