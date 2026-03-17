# KabuSys

日本株向けの自動売買・データ基盤ライブラリ (KabuSys)。  
J-Quants / RSS 等から市場データ・ニュースを取得して DuckDB に保存し、ETL・品質チェック・監査ログなどの基盤機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の機能を備えた内部用ライブラリです。

- J-Quants API 経由で株価（日足）、財務データ（四半期 BS/PL）、市場カレンダーを取得
- RSS フィードからニュース記事を収集して DuckDB に保存（記事IDは正規化URLの SHA-256 ハッシュ）
- DuckDB のスキーマ定義・初期化（Raw / Processed / Feature / Execution / Audit 層）
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- データ品質チェック（欠損、スパイク、重複、日付整合性）
- 監査ログテーブル（シグナル→発注→約定のトレーサビリティ）
- 環境変数ベースの設定管理（.env 自動読み込み、小さなパーサを内蔵）

設計上の注意点：
- API のレート制限を遵守（J-Quants: 120 req/min のスロットリング）
- 再試行（指数バックオフ）・401 のトークン自動リフレッシュ対応
- ニュースの SSRF/ZIP爆弾対策、トラッキングパラメータ除去、冪等保存（ON CONFLICT）
- すべてのタイムスタンプは UTC を基本とする設計

---

## 機能一覧

- 環境変数/設定管理 (kabusys.config.Settings)
  - 自動でプロジェクトルートの `.env` / `.env.local` を読み込む（無効化可）
- J-Quants クライアント (kabusys.data.jquants_client)
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_* 系で DuckDB に冪等保存
  - レートリミット、リトライ、トークン自動リフレッシュ実装
- RSS ニュース収集 (kabusys.data.news_collector)
  - fetch_rss / save_raw_news / save_news_symbols / run_news_collection
  - URL 正規化、記事ID ハッシュ化、SSRF 対策、gzip 受信制限
- DuckDB スキーマ (kabusys.data.schema)
  - init_schema / get_connection
  - Raw/Processed/Feature/Execution 層のDDL を定義
- ETL パイプライン (kabusys.data.pipeline)
  - run_prices_etl / run_financials_etl / run_calendar_etl / run_daily_etl
  - 差分取得・バックフィル・品質チェックの統合
- 品質チェック (kabusys.data.quality)
  - check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks
- 監査ログ (kabusys.data.audit)
  - signal_events / order_requests / executions の DDL と初期化関数

---

## 要件

- Python 3.10 以上（型注釈の union 演算子などを使用）
- 必須パッケージ（例）
  - duckdb
  - defusedxml

インストール例（仮の requirements.txt がない場合）:
```
pip install duckdb defusedxml
```

プロジェクトをパッケージとして扱う場合は通常の Python packaging の手順に従ってください（例: pip install -e .）。

---

## セットアップ手順

1. Git リポジトリをクローン（既にプロジェクトがある前提）
2. Python 環境を作成（推奨: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install --upgrade pip
   ```
3. 依存パッケージをインストール
   ```
   pip install duckdb defusedxml
   ```
   （他に必要なライブラリがあれば追加してください）
4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を配置すると、自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須の環境変数は下記参照。`.env.example` を用意している場合はそれを元に作成してください。

必須環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須、利用するなら）
- SLACK_BOT_TOKEN: Slack 通知等で使用する Bot トークン（必須、利用するなら）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須、利用するなら）

任意 / デフォルトあり
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG|INFO|...（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると自動 .env ロードを無効化
- KABUSYS_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB 等（デフォルト: data/monitoring.db）

注意: Settings クラスは必要な環境変数が未設定の場合に ValueError を投げます。

---

## 使い方（基本例）

以下はライブラリ API の典型的な使い方例です。実行は Python コンソールやスクリプト内で行います。

1) DuckDB スキーマの初期化
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)  # ファイル不在なら親ディレクトリを作成して初期化
```

2) 日次 ETL を実行（各種取得・保存・品質チェックを含む）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date 等を指定可能
print(result.to_dict())
```

3) ニュース収集ジョブを実行
```python
from kabusys.data.news_collector import run_news_collection

# known_codes は銘柄抽出に使う既知の銘柄コード集合（省略するとシンボル抽出をスキップ）
known_codes = {"7203", "6758", "9984"}
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # 各 RSS source ごとの新規保存件数辞書
```

4) J-Quants API を直接使う（トークンは settings から読み込む）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

id_token = get_id_token()  # settings.jquants_refresh_token を使って取得
quotes = fetch_daily_quotes(id_token=id_token, code="7203", date_from=..., date_to=...)
```

5) 品質チェックだけを実行する
```python
from kabusys.data.quality import run_all_checks

issues = run_all_checks(conn)
for i in issues:
    print(i)
```

---

## 実行上の注意事項

- J-Quants のレート制限（120 req/min）をモジュール内で制御しますが、長時間の大量呼び出しでは運用側でも監視が必要です。
- get_id_token はリフレッシュトークンから ID トークンを取得します。リフレッシュトークンは環境変数 (JQUANTS_REFRESH_TOKEN) に設定してください。
- ニュース収集は外部の RSS を読み込むため、SSRF / XML Bomb / 大容量レスポンス等に対する防御を組み込んでいますが、運用時は接続先の管理やタイムアウト設定を行ってください。
- DuckDB ファイルのバックアップやローテーションは運用で管理してください（大容量化しやすいです）。

---

## ディレクトリ構成

リポジトリの主要なファイル・モジュール（抜粋）:

- src/kabusys/
  - __init__.py
    - パッケージのバージョン定義など（__version__ = "0.1.0"）
  - config.py
    - 環境変数読み込み・Settings クラス（.env 自動読み込みロジック含む）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得+保存ロジック、レート制限、リトライ）
    - news_collector.py
      - RSS 取得・記事正規化・保存・銘柄抽出ロジック
    - schema.py
      - DuckDB の DDL 定義と init_schema / get_connection
    - pipeline.py
      - ETL パイプライン（差分取得、バックフィル、品質チェック統合）
    - audit.py
      - 監査ログ用 DDL と初期化（signal_events, order_requests, executions）
    - quality.py
      - データ品質チェック群と run_all_checks
  - strategy/
    - __init__.py （戦略層のプレースホルダ）
  - execution/
    - __init__.py （実行層のプレースホルダ）
  - monitoring/
    - __init__.py （監視用プレースホルダ）

---

## 開発 / テストに関する補足

- config モジュールはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に `.env` / `.env.local` を自動読み込みします。テスト中に自動読み込みを抑制したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- ニュース収集モジュールのネットワークアクセス部分は `_urlopen` をモックすることでテスト可能です。
- DuckDB のインメモリ利用は `":memory:"` を init_schema に渡すことで可能です（ユニットテストで便利）。

---

## ライセンス・貢献

この README はコードベースから生成した概要ドキュメントです。実際のライセンス表記や貢献ガイドライン（CONTRIBUTING.md 等）はプロジェクトルートに別途追加してください。

---

必要であれば、README に以下を追加できます（ご希望があれば教えてください）：
- .env.example のテンプレート
- よくあるトラブルシューティング（トークン切れ、DuckDB の権限問題等）
- CI / デプロイ手順（Docker, systemd タスク等）
- サンプル cron/airflow ジョブ定義

ご希望の追加事項を教えてください。