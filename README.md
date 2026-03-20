# KabuSys

日本株向けの自動売買システムのコアライブラリ（プロトタイプ）

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- 要求環境 / 依存パッケージ
- セットアップ手順
- 使い方（例）
- 環境変数（.env）
- 主要モジュールとディレクトリ構成
- 開発上の注意点

---

## プロジェクト概要

KabuSys は日本株を対象としたデータ取得・ETL、特徴量作成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなどを包含する自動売買プラットフォームのコア部分です。DuckDB を内部データベースとして用い、J-Quants API から市場データ・財務データ・カレンダーを取得してデータレイヤを構築します。戦略（feature_engineering / signal_generator）や research ツールも含まれ、発注（execution）や監視（monitoring）と連携する想定です。

設計上のキーワード:
- 冪等性（DB への保存は ON CONFLICT で上書き）
- ルックアヘッドバイアス回避（当日以前のデータのみ参照）
- 明示的な DB スキーマ定義（DuckDB）
- API レート制御・リトライ（J-Quants クライアント）
- セキュリティ配慮（ニュース収集の SSRF 対策、defusedxml 利用 等）

---

## 主な機能一覧

- Data
  - J-Quants API クライアント（fetch/save daily quotes, financial statements, market calendar）
  - ETL パイプライン（差分取得、バックフィル、品質チェック呼び出し）
  - DuckDB スキーマ初期化・接続ユーティリティ
  - ニュース収集（RSS 取得、前処理、記事保存、銘柄抽出）
  - マーケットカレンダー管理（営業日判定・next/prev）
  - 統計ユーティリティ（Z スコア正規化 等）

- Research
  - ファクター計算（momentum / volatility / value）
  - ファクター探索支援（将来リターン、IC、統計サマリー）

- Strategy
  - 特徴量生成（build_features: raw ファクターを正規化して features テーブルへ）
  - シグナル生成（generate_signals: features と ai_scores を統合して BUY/SELL を決定）

- Execution / Audit / Monitoring
  - DB でのシグナル / 注文 / 約定 / ポジション のスキーマ整備（監査用テーブル含む）
  - （発注ロジックは execution 層実装想定）

---

## 要求環境 / 依存パッケージ

- Python 3.10 以上（PEP 604 の型指定 `X | Y` を使用しているため）
- 必須ライブラリ（代表）
  - duckdb
  - defusedxml
- 標準ライブラリを多用する設計のため、余分な重い依存は抑えられていますが、実行環境に応じて追加で requests 等が必要になる場合があります。

インストール例（仮）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# またはプロジェクトに requirements.txt があれば `pip install -r requirements.txt`
```

---

## セットアップ手順

1. リポジトリをクローン / ソースを準備
2. 仮想環境作成・有効化
3. 依存パッケージをインストール（上記参照）
4. 環境変数を設定（下記「環境変数」参照）。プロジェクトルートに `.env` / `.env.local` を置くと自動でロードされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
5. DuckDB スキーマ初期化

DuckDB スキーマ初期化の例:
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # data/ 以下に DB ファイルを作成
```

または簡易 CLI で Python 実行:
```bash
python - <<'PY'
from kabusys.data.schema import init_schema
init_schema("data/kabusys.duckdb")
print("initialized")
PY
```

---

## 使い方（例）

以下は主要な処理を Python REPL / スクリプトから呼ぶ例です。DuckDB 接続には init_schema や get_connection を使ってください。

- 日次 ETL を実行（市場カレンダー・株価・財務の差分取得と品質チェック）:
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量の構築（features テーブルへ書き込む）:
```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
count = build_features(conn, target_date=date(2025, 3, 1))
print("built features:", count)
```

- シグナル生成（signals テーブルへ書き込む）:
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
n_signals = generate_signals(conn, target_date=date(2025, 3, 1))
print("signals written:", n_signals)
```

- ニュース収集ジョブを実行:
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203","6758", ...}  # 有効銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

- マーケットカレンダーの夜間更新:
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("calendar saved:", saved)
```

- J-Quants から日足を取得して保存（低レベル利用例）:
```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2025,1,1), date_to=date(2025,3,1))
saved = jq.save_daily_quotes(conn, records)
print("saved", saved)
```

---

## 環境変数（.env）

プロジェクトは .env/.env.local または OS 環境変数から設定値を読み込みます（自動ロード）。主要な変数:

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API パスワード（execution 層使用）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャネル ID

任意 / デフォルトあり:
- KABUSYS_ENV: 開発環境識別（development / paper_trading / live）デフォルト: development
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）デフォルト: INFO
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: sqlite 用パス（monitoring 用等、デフォルト data/monitoring.db）

自動 .env ロードの挙動:
- プロジェクトルート（.git または pyproject.toml を基準）にある .env を自動読み込みします。
- .env.local が存在すれば .env の後に上書きで読み込み（OS 環境を上書きしない挙動は protected により制御）。
- 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で使用）。

---

## ディレクトリ構成

ソース配下の主なファイル・モジュール（抜粋）

- src/kabusys/
  - __init__.py
  - config.py               : 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py     : J-Quants API クライアント（取得／保存）
    - pipeline.py          : ETL パイプライン（run_daily_etl 等）
    - schema.py            : DuckDB スキーマ定義・初期化
    - stats.py             : 統計ユーティリティ（zscore_normalize 等）
    - news_collector.py    : RSS ニュース収集・保存・銘柄抽出
    - calendar_management.py : カレンダー周りユーティリティと更新ジョブ
    - features.py          : features の再エクスポート
    - audit.py             : 監査ログ（signal_events / order_requests / executions）
    - pipeline.py          : ETL の実装（差分取得等）
  - research/
    - __init__.py
    - factor_research.py   : momentum/volatility/value の算出
    - feature_exploration.py : 将来リターン / IC / summary 等
  - strategy/
    - __init__.py
    - feature_engineering.py : build_features（正規化・ユニバースフィルタ等）
    - signal_generator.py   : generate_signals（final_score 計算・BUY/SELL 判定）
  - execution/              : 発注に関する実装（現状は placeholder）
  - monitoring/             : 監視・Slack 通知等（実装想定）

---

## 開発上の注意点 / 実装メモ

- 型ヒントに Python 3.10 の構文（X | Y）を使用しているため、古い Python では動作しません。
- J-Quants API クライアントは内部でレート制御（120 req/min）とリトライを実装しています。API 利用時はレートやトークン管理に注意してください。
- news_collector は RSS の XML をパースする際に defusedxml を使用しており、SSRF 防御や受信サイズ制限などセキュリティ上の配慮が組み込まれています。
- DuckDB に対する DDL は schema.py にまとまっており、init_schema は冪等に動作します。既存 DB へ接続する場合は get_connection を利用してください。
- features / signals の生成は「target_date 時点で利用可能なデータのみ」を前提とした実装です（ルックアヘッドバイアス対策）。
- settings からの自動 .env 読み込みは、配布後・テスト時等に意図しない影響を与える可能性があります。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

もし README に追加したい項目（詳細な SQL スキーマ解説、例外一覧、CI／デプロイ手順、テスト方法など）があれば教えてください。必要に応じてサンプルスクリプトや簡易 CLI のテンプレートも用意できます。