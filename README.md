# KabuSys — 日本株自動売買システム（README）

KabuSys は日本株の自動売買プラットフォーム向けに設計された Python ライブラリ群です。J-Quants / kabu ステーション等の外部 API からデータを取得・保存し、ETL（データ取得・整形・品質検査）、ニュース収集、マーケットカレンダー管理、監査ログなど自動売買システムに必要な基盤機能を提供します。

主な設計方針：
- データの冪等性（ON CONFLICT / DO UPDATE）を重視
- API レート制限・リトライ・トークン自動リフレッシュ対応
- Look-ahead bias を避けるための fetched_at トレース
- SSRF / XML Bomb 等のセキュリティ対策（news_collector）

---

## 機能一覧

- 環境設定読み込み・管理
  - .env / .env.local の自動ロード（プロジェクトルート検出）
  - 必須環境変数チェック（settings オブジェクト）
  - KABUSYS_ENV（development / paper_trading / live）、LOG_LEVEL 設定

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日次株価（OHLCV）・財務データ・マーケットカレンダー取得（ページネーション対応）
  - レートリミット管理（120 req/min）、リトライ（指数バックオフ）、401 → トークン自動リフレッシュ
  - DuckDB への冪等保存ユーティリティ（raw_prices / raw_financials / market_calendar）

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（最終取得日ベース、自動バックフィル）
  - 日次 ETL の統合エントリ（run_daily_etl）
  - 品質チェック連携（欠損・スパイク・重複・日付不整合）

- データスキーマ管理（kabusys.data.schema）
  - DuckDB のスキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
  - スキーマ初期化関数（init_schema / get_connection）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事収集、前処理、DuckDB への冪等保存（raw_news / news_symbols）
  - URL 正規化（トラッキングパラメータ除去）と記事 ID の生成（SHA-256）
  - SSRF / サイズ制限 / defusedxml による XML 攻撃対策

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、前後営業日取得、夜間バッチ更新ジョブ（calendar_update_job）

- データ品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク、日付不整合の検出
  - QualityIssue オブジェクトで問題を返却（error / warning）

- 監査ログ（kabusys.data.audit）
  - signal → order_request → execution へと続くトレーサビリティ用スキーマ
  - 監査 DB 初期化（init_audit_db）およびスキーマ追加（init_audit_schema）

---

## セットアップ手順

前提
- Python 3.10+ を推奨（PEP 604 型ヒント等を使用）
- pip が利用可能

1. リポジトリをクローン（またはパッケージソースを取得）
2. 仮想環境を作成・有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクト配布に setup/pyproject があれば）pip install -e .

4. 環境変数 / .env ファイルを準備
   - プロジェクトルート（.git か pyproject.toml を基準）に `.env` または `.env.local` を置くと自動読み込みされます（既定）。
   - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

必須環境変数（最低限）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabu API 用パスワード
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack チャネル ID

任意 / デフォルト値あり
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 sqlite パス（デフォルト: data/monitoring.db）
- KABUS_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）

例: .env
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（クイックスタート）

以下はライブラリ API の代表的な使い方です。実際の運用スクリプトではロギングやエラーハンドリング、スケジューラー（cron / Airflow 等）と組み合わせて下さい。

1) DuckDB スキーマ初期化（一度だけ）
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は Path を返す
conn = init_schema(settings.duckdb_path)
# conn を保持して ETL 等で利用
```

2) 監査ログ用 DB 初期化（監査専用 DB を使う場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

3) 日次 ETL 実行
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # 引数で target_date, id_token 等を注入可能
if result.has_errors:
    print("ETL 中にエラーがあります:", result.errors)
for qi in result.quality_issues:
    print(qi.check_name, qi.severity, qi.detail)
```

4) ニュース収集ジョブ（RSS）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 例: 保持している銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print("news collection:", results)
```

5) マーケットカレンダーの夜間バッチ更新
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved calendar records:", saved)
```

6) J-Quants ID トークン取得（必要に応じて）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token が使われる
```

注意点:
- run_daily_etl などは内部でトークン自動取得／キャッシュを行います。テスト時は id_token を明示的に渡すことが可能です。
- news_collector は HTTP リダイレクト先の検査やサイズ制限を行い、SSRF／DoS 対策を施しています。ユニットテストでは _urlopen をモックできます。

---

## ディレクトリ構成

リポジトリ内の主要ファイル / モジュールは以下の通りです（抜粋）。

- src/
  - kabusys/
    - __init__.py
    - config.py                     — 環境変数 / 設定管理
    - data/
      - __init__.py
      - schema.py                   — DuckDB スキーマ定義・初期化
      - jquants_client.py           — J-Quants API クライアント（取得・保存）
      - pipeline.py                 — ETL パイプライン（run_daily_etl 等）
      - news_collector.py           — RSS ニュース収集・保存
      - calendar_management.py      — マーケットカレンダー管理
      - quality.py                  — データ品質チェック
      - audit.py                    — 監査ログスキーマ・初期化
      - pipeline.py
    - strategy/                      — 戦略モジュール用パッケージ（拡張ポイント）
      - __init__.py
    - execution/                     — 発注 / execution 層（拡張ポイント）
      - __init__.py
    - monitoring/                    — 監視 / メトリクス（拡張ポイント）
      - __init__.py

各モジュールは責務ごとに分割されており、外部 API 呼び出し、DB 操作、品質チェック、監査ログなどが整然と実装されています。

---

## 開発・拡張メモ

- テスト可能性: jquants_client の id_token 注入、news_collector の _urlopen の差し替え等、テストフレンドリーな設計が意識されています。
- スケーリング: DuckDB を永続化 DB として使用することでローカル実行やコンテナ運用に適します。大規模運用では外部データレイクやメタデータ管理と組み合わせてください。
- セキュリティ: news_collector は defusedxml、SSRF 検査、受信サイズ上限などを実装。運用環境ではネットワーク egress ポリシーやホワイトリストを併用してください。

---

## 依存関係（主要）

- Python 3.10+
- duckdb
- defusedxml

必要に応じて追加の依存を pyproject.toml / requirements.txt に記載してください。

---

何か特定の使い方（例: 戦略の追加、発注フローの実装、監査テーブルの利用例）のドキュメント化やサンプルコードが必要であれば教えてください。