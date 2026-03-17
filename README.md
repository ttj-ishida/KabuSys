# KabuSys

日本株自動売買プラットフォーム用ユーティリティライブラリ（KabuSys）。  
データ取得・ETL・品質チェック・監査ログの初期化など、戦略・実行レイヤーで利用する共通機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムで利用する基盤モジュール群です。主に以下を提供します。

- J-Quants API を使った市場データ（株価日足、財務、マーケットカレンダー）の取得と DuckDB への永続化（冪等保存）
- RSS ベースのニュース収集と記事・銘柄紐付け（SSRF 対策・gzip/size 保護・トラッキングパラメータ削除）
- ETL パイプライン（差分更新、バックフィル、カレンダー先読み、品質チェック）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → executions のトレーサビリティ）用スキーマ初期化
- 環境設定の管理（.env 自動読み込み・必須変数チェック）

設計上のポイント:
- API レートリミット遵守（J-Quants: 120 req/min）
- リトライ（指数バックオフ）、401 時のトークン自動リフレッシュ
- Look-ahead bias 対策のため fetched_at を UTC で記録
- DB 書き込みは冪等（ON CONFLICT）で安全化
- セキュリティ対策（defusedxml, SSRF/プライベートホストブロック、サイズ上限）

---

## 機能一覧

- 環境管理: .env の自動読み込み（プロジェクトルート検出）、必須環境変数チェック
- data.jquants_client:
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB への save_* 関数（raw_prices, raw_financials, market_calendar）
  - レートリミター・リトライ・トークンキャッシュ
- data.news_collector:
  - RSS フェッチ（gzip 対応・XML サニタイズ）
  - 記事正規化（URL 正規化・トラッキングパラメータ除去）
  - raw_news, news_symbols への冪等保存
  - 銘柄コード抽出・SSRF 対策
- data.schema:
  - DuckDB スキーマ定義（Raw / Processed / Feature / Execution 層）
  - init_schema, get_connection
- data.pipeline:
  - 差分 ETL（run_prices_etl, run_financials_etl, run_calendar_etl, run_daily_etl）
  - backfill, calendar lookahead、品質チェック統合
- data.quality:
  - check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks
- data.audit:
  - 監査テーブル（signal_events, order_requests, executions）初期化
- strategy/, execution/, monitoring/:
  - パッケージプレースホルダ（戦略実装・実行インターフェース・監視ロジック用）

---

## 要件

- Python 3.10+
- 必要な主要パッケージ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants / RSS）

（実際の requirements.txt はリポジトリ側で用意してください — 最低限上記パッケージが必要です）

---

## セットアップ手順

1. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb defusedxml

   （パッケージ一覧がある場合は pip install -r requirements.txt）

3. リポジトリを開いて開発インストール（任意）
   - pip install -e .

4. 環境変数の準備
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（プロジェクトルートは .git または pyproject.toml を探して判定）。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須環境変数（Settings 内参照）
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API パスワード
- SLACK_BOT_TOKEN: Slack Bot トークン
- SLACK_CHANNEL_ID: Slack チャネル ID

任意（デフォルトあり）
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: 自動 .env ロードの無効化
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD を使うと .env の自動読み込みを停止できます。

例 .env（参考）
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方（代表的な操作例）

下記は Python REPL またはスクリプトからの利用例です。settings は kabusys.config.Settings のラッパーを通じて環境変数を参照します。

1) DuckDB スキーマ初期化
```python
from kabusys.config import settings
from kabusys.data import schema

# settings.duckdb_path に基づく DB を初期化して接続を取得
conn = schema.init_schema(settings.duckdb_path)
```

2) J-Quants トークン取得（明示的に）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用して id_token を取得
```

3) 日次 ETL 実行（市場カレンダー取得 → 株価・財務差分取得 → 品質チェック）
```python
from datetime import date
from kabusys.data import pipeline, schema
from kabusys.config import settings

conn = schema.get_connection(settings.duckdb_path)  # 既存 DB に接続 (init_schema で初期化済みを推奨)
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

4) RSS ニュース収集の実行
```python
from kabusys.data import news_collector, schema
from kabusys.config import settings

conn = schema.get_connection(settings.duckdb_path)
# sources を省略するとデフォルトソース（Yahoo Finance 等）を使用
results = news_collector.run_news_collection(conn, known_codes={'7203','6758'})
print(results)  # {source_name: saved_count}
```

5) データ品質チェック単独で実行
```python
from kabusys.data import quality, schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")
issues = quality.run_all_checks(conn, target_date=date.today(), reference_date=date.today())
for issue in issues:
    print(issue)
```

注意:
- J-Quants クライアントは内部でレートリミット・リトライ・トークン自動リフレッシュを行います。テスト時は id_token を注入して外部依存を切ることができます。
- news_collector は SSRF/プライベートアドレスの検査や gzip 解凍後のサイズチェックを行います。

---

## ディレクトリ構成

下記はコードベースの主なファイル・パッケージ構成です。

- src/
  - kabusys/
    - __init__.py
    - config.py                 # 環境設定・.env 自動読み込み・Settings
    - data/
      - __init__.py
      - jquants_client.py       # J-Quants API クライアント + DuckDB 保存器
      - news_collector.py       # RSS ニュース収集・正規化・保存
      - schema.py               # DuckDB スキーマ定義 / init_schema
      - pipeline.py             # ETL パイプライン（差分取得・品質チェック）
      - audit.py                # 監査ログ（signal/order_request/executions）初期化
      - quality.py              # データ品質チェック
    - strategy/
      - __init__.py             # 戦略関連（プレースホルダ）
    - execution/
      - __init__.py             # 発注・ブローカー連携（プレースホルダ）
    - monitoring/
      - __init__.py             # 監視・メトリクス（プレースホルダ）

---

## 実運用・運用上の注意点

- KABUSYS_ENV を `live` に設定すると実運用モードを想定した挙動を行う場合があります。運用時は credentials（API トークン等）の管理に注意してください。
- DuckDB ファイル（デフォルト data/kabusys.duckdb）はバックアップを取ることを推奨します。
- ETL の実行スケジュールは OS の cron やジョブランナー（Airflow 等）で管理するのが一般的です。
- news_collector は外部 URL を扱うため、社内ネットワークからの実行時は SSRF 検査や DNS 解決の挙動を理解しておいてください（ライブラリは安全側に倒しており、解決失敗時は通過許容します）。

---

## 開発・テスト時のヒント

- 自動 .env ロードを無効化したいテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してからモジュールを import してください。
- jquants_client のネットワーク呼び出しはテストで差し替え可能（モック化して id_token を注入）。
- news_collector._urlopen をモックすると HTTP 層を容易にテストできます。

---

README は以上です。必要に応じて利用方法、追加の CLI、CI 設定、requirements.txt やサンプル .env.example を追加するドキュメントを作成しますので、希望があれば教えてください。