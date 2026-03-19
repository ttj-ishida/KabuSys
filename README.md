# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
J-Quants API からマーケットデータと財務データを取得して DuckDB に格納し、特徴量計算・品質チェック・ニュース収集・監査ログなどを行うためのユーティリティ群を提供します。

---

## 主な概要

- データ取得（J-Quants） → DuckDB 保存（冪等）を中心とした ETL パイプライン
- 研究用途（factor / feature 計算、IC、Zスコア正規化）
- ニュース RSS 取得とテキスト前処理、記事と銘柄の紐付け
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマ
- 市場カレンダー管理（JPX）および営業日判定ユーティリティ

---

## 機能一覧

- data/jquants_client
  - J-Quants API クライアント
  - レート制御、リトライ、トークン自動リフレッシュ、ページネーション対応
  - fetch/save 用ユーティリティ（株価、財務、マーケットカレンダー）
- data/schema
  - DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- data/pipeline
  - 差分 ETL（prices / financials / calendar）、日次 ETL 実行エントリ
- data/quality
  - 欠損、重複、スパイク、日付不整合のチェックと QualityIssue の返却
- data/news_collector
  - RSS 取得（SSRF防御、サイズ制限、XML 脆弱性対策）、記事ID生成、前処理、DB 保存
- research
  - ファクター計算（Momentum, Volatility, Value 等）
  - 特徴量探索（将来リターン計算、IC 計算、統計サマリ）
- data/stats / data/features
  - Zスコア正規化などの統計ユーティリティ
- audit
  - 監査ログ用テーブル定義と初期化ユーティリティ

---

## 要件

- Python 3.10+
- 必須パッケージ（最低限）
  - duckdb
  - defusedxml
- （環境により）ネットワークアクセス: J-Quants API、RSS フィード

例: pip でのインストール
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# パッケージとしてインストールする場合（プロジェクトに pyproject.toml があれば）
pip install -e .
```

---

## 環境変数（設定）

kabusys は .env / .env.local または OS 環境変数から設定を読み込みます。プロジェクトルート（.git または pyproject.toml がある場所）にある `.env` / `.env.local` を自動で読み込みます（無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

主な環境変数:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL (任意) — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL (任意) — ログレベル ("DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL")

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxx...
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン
```bash
git clone <repo-url>
cd <repo-dir>
```

2. 仮想環境の作成・有効化（推奨）
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
```

3. 依存ライブラリのインストール
```bash
pip install duckdb defusedxml
# 任意でプロジェクトを editable インストール（pyproject.toml/setup.py がある場合）
pip install -e .
```

4. 環境変数設定
- プロジェクトルートに `.env` を作成するか、OS 環境変数を設定してください。
- 自動ロードをテスト等で無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

5. DuckDB スキーマ初期化（Python コンソールやスクリプト）
```python
from kabusys.data.schema import init_schema
init_schema("data/kabusys.duckdb")
```
監査用 DB を別途用意する場合:
```python
from kabusys.data.audit import init_audit_db
init_audit_db("data/audit.duckdb")
```

---

## 使い方（基本的な例）

- 日次 ETL を実行して J-Quants からデータを取得し DuckDB に保存する:
```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

# DB 初期化（初回のみ）
conn = init_schema("data/kabusys.duckdb")

# 日次 ETL 実行（例: 今日）
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース収集ジョブを実行する（known_codes を与えると記事→銘柄紐付けも行う）:
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection
import duckdb

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 例: 有効銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

- 研究用ファクター計算の呼び出し（例: momentum, IC 計算）:
```python
from datetime import date
from kabusys.research import calc_momentum, calc_forward_returns, calc_ic
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
t = date(2024, 1, 31)

factors = calc_momentum(conn, t)              # ファクターリスト (date, code, mom_1m, ...)
fwd = calc_forward_returns(conn, t, horizons=[1,5,21])
# calc_ic の例（factor_col と return_col は適宜指定）
ic = calc_ic(factors, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)
```

- J-Quants API を直接使う（例: トークン取得、価格取得）:
```python
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import get_connection

id_token = get_id_token()  # settings.jquants_refresh_token を使用
recs = fetch_daily_quotes(id_token=id_token, date_from=date(2024,1,1), date_to=date(2024,1,31))
conn = get_connection("data/kabusys.duckdb")
saved = save_daily_quotes(conn, recs)
print("saved:", saved)
```

---

## ディレクトリ構成（抜粋）

以下はコードベース内の主要ファイル・モジュールの一覧です（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py --------------------------- 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py ----------------- J-Quants API クライアント（取得・保存）
    - news_collector.py ----------------- RSS 取得・記事処理・保存
    - schema.py ------------------------- DuckDB スキーマと初期化
    - pipeline.py ----------------------- ETL パイプライン（run_daily_etl 等）
    - quality.py ------------------------ データ品質チェック
    - stats.py -------------------------- 統計ユーティリティ（zscore_normalize 等）
    - features.py ----------------------- features の公開インターフェース
    - calendar_management.py ------------ 市場カレンダー関連ユーティリティ
    - audit.py -------------------------- 監査ログスキーマ初期化
    - etl.py ---------------------------- ETLResult の公開
  - research/
    - __init__.py
    - feature_exploration.py ------------ 将来リターン・IC・サマリー
    - factor_research.py ---------------- ファクター計算（momentum, value, volatility）
  - strategy/ -------------------------- 戦略層（雛形）
  - execution/ ------------------------- 発注 / execution 層（雛形）
  - monitoring/ ------------------------ 監視関連（雛形）

---

## 実運用上の注意点

- 環境（KABUSYS_ENV）:
  - "development" / "paper_trading" / "live" のいずれかを指定してください。`is_live`/`is_paper`/`is_dev` プロパティで判定できます。
- セキュリティ:
  - RSS 取得には SSRF 対策と XML の安全パース（defusedxml）を実装していますが、追加のネットワーク制限やプロキシ設定は運用環境で確実に行ってください。
- データ品質:
  - ETL 実行後は quality.run_all_checks で検査結果を確認し、致命的な問題があれば対処してください。
- 冪等性:
  - jquants_client の save_* 系は ON CONFLICT により冪等になっています。ETL は差分取得を行いますが、初回ロード時はすべて取得するため時間がかかります。
- テスト・ローカル実行:
  - 自動 .env 読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利）。

---

## 開発・拡張ガイド

- 研究 (research) と data 層は標準ライブラリ依存のみで設計されている部分が多く、外部依存を最小限に抑えたまま関数を呼び出して試験できます。
- DuckDB を使った SQL ベースの処理が中心なので、新しい集計・チェックを追加する場合は schema にテーブルを追加し、pipeline / quality にクエリを追加してください。
- 発注・モニタリング・戦略エンジンは雛形として構成されているため、ブローカー固有の実装や運用ルールは各組織のポリシーに合わせて実装してください。

---

必要であれば、README に入れる具体的な .env.example、実行スクリプトのサンプル、CI 用コマンド、よくあるトラブルシュート（例: トークンリフレッシュエラー、DuckDB のパス問題）なども追加します。どの情報を優先して追記しますか？