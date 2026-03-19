# KabuSys

日本株向け自動売買・データプラットフォームライブラリ（KabuSys）のリポジトリ向け README.md（日本語）

概要、機能、セットアップ、使い方、ディレクトリ構成をまとめています。

---

## プロジェクト概要

KabuSys は日本株のデータ取得・ETL・特徴量算出・監査ログ・ニュース収集・研究向けユーティリティを提供する内部ライブラリです。  
主な用途は以下のとおりです。

- J-Quants API から株価・財務・市場カレンダーを取得して DuckDB に保存（差分更新・バックフィル対応）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 特徴量（モメンタム、ボラティリティ、バリュー等）計算と正規化
- RSS ベースのニュース収集と銘柄抽出
- 監査ログ（シグナル→発注→約定）用スキーマの初期化
- 研究用ユーティリティ（将来リターン計算・IC計算 等）

設計方針としては、DuckDB を中心に冪等性（ON CONFLICT）、Look-ahead バイアス回避（fetched_at の記録）、外部依存最小化（研究系は標準ライブラリのみ）を重視しています。

---

## 主な機能一覧

- 環境変数管理（自動 .env ロード、必須チェック）
  - モジュール: `kabusys.config`
- DuckDB スキーマ定義・初期化
  - モジュール: `kabusys.data.schema`
  - 関数: `init_schema(db_path)` / `get_connection(db_path)`
- J-Quants API クライアント（レート制御・リトライ・トークン自動リフレッシュ・ページネーション）
  - モジュール: `kabusys.data.jquants_client`
  - 主要関数: `fetch_daily_quotes`, `fetch_financial_statements`, `fetch_market_calendar`, `save_*`
- ETL パイプライン（差分取得、保存、品質チェック）
  - モジュール: `kabusys.data.pipeline`
  - 主要関数: `run_daily_etl`, `run_prices_etl`, `run_financials_etl`, `run_calendar_etl`
- データ品質チェック
  - モジュール: `kabusys.data.quality`
  - 主要関数: `run_all_checks`, `check_missing_data`, `check_spike`, `check_duplicates`, `check_date_consistency`
- ニュース収集（RSS → 正規化 → DuckDB 保存 → 銘柄抽出）
  - モジュール: `kabusys.data.news_collector`
  - 主要関数: `fetch_rss`, `save_raw_news`, `save_news_symbols`, `run_news_collection`
- 監査ログ用スキーマ（signal / order_requests / executions）
  - モジュール: `kabusys.data.audit`
  - 初期化: `init_audit_schema(conn)` / `init_audit_db(db_path)`
- 研究（Research）ユーティリティ
  - モジュール: `kabusys.research.factor_research`, `kabusys.research.feature_exploration`
  - 主要関数: `calc_momentum`, `calc_volatility`, `calc_value`, `calc_forward_returns`, `calc_ic`, `factor_summary`
- 汎用統計ユーティリティ
  - モジュール: `kabusys.data.stats`
  - 主要関数: `zscore_normalize`

---

## 要求環境 / 依存

- Python 3.10 以上（コードは union 型 `|` を利用）
- 必要な Python パッケージ（最低限）:
  - duckdb
  - defusedxml
- （ネットワーク呼び出しを行う場合）インターネット接続と J-Quants API の資格情報

インストール例（仮想環境推奨）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# パッケージとしてインストールする場合（プロジェクトに setup/pyproject があれば）
# pip install -e .
```

---

## 環境変数（必須・任意）

このプロジェクトは .env ファイルまたは環境変数から設定を読み込みます（`kabusys.config`）。自動ロードはプロジェクトルートに `.git` または `pyproject.toml` がある場合に .env/.env.local を読み込みます。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須環境変数（Settings が参照するもの）:

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu ステーション API 用パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID（必須）

任意・デフォルトあり:

- KABUSYS_ENV — 実行環境 (development | paper_trading | live)、デフォルト: development
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）、デフォルト: INFO
- DUCKDB_PATH — DuckDB ファイルパス、デフォルト: data/kabusys.duckdb
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化（1 を設定）

例: `.env`（最小例）

```
JQUANTS_REFRESH_TOKEN=あなたの_refresh_token
KABU_API_PASSWORD=あなたの_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリクローン / コピー
2. Python 仮想環境作成（推奨）
3. 必須パッケージのインストール（duckdb, defusedxml 等）
4. `.env` を作成して必須環境変数を設定
5. DuckDB スキーマを初期化

例:

```bash
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml

# .env を作成（上記参照）
# DuckDB スキーマ初期化（Python REPL かスクリプト）
python - <<'PY'
from kabusys.data.schema import init_schema
init_schema("data/kabusys.duckdb")  # :memory: も可
print("init done")
PY
```

監査ログ専用 DB の初期化（任意）:

```python
from kabusys.data.audit import init_audit_db
init_audit_db("data/kabusys_audit.duckdb")
```

---

## 使い方（よく使う API/コマンド例）

以下はライブラリを直接呼び出す Python での最小例です。

1) DuckDB 接続の取得 / スキーマ初期化

```python
from kabusys.data.schema import init_schema, get_connection

# 初回: スキーマを作成して接続を得る
conn = init_schema("data/kabusys.duckdb")

# 既存 DB に接続する場合:
conn = get_connection("data/kabusys.duckdb")
```

2) 日次 ETL 実行（J-Quants から差分取得して保存 → 品質チェック）

```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)
print(result.to_dict())
```

オプション:
- `target_date` を指定して任意日を対象にする
- `id_token` を渡すことでトークン注入（テスト容易性）

3) ニュース収集ジョブの実行

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 銘柄リスト（任意）
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # sourceごとの新規保存件数
```

4) 研究用ファクター・IC 計算の呼び出し例

```python
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
d = date(2024, 1, 4)

mom = calc_momentum(conn, d)
vol = calc_volatility(conn, d)
val = calc_value(conn, d)

# 将来リターンを計算して IC を測る例
fwd = calc_forward_returns(conn, d, horizons=[1,5,21])
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)
```

5) 統計正規化ユーティリティ

```python
from kabusys.data.stats import zscore_normalize
normalized = zscore_normalize(mom, ["mom_1m", "mom_3m", "ma200_dev"])
```

---

## 注意事項 / セキュリティ・運用メモ

- J-Quants API のレート制限を守るため内部でスロットリング（120 req/min）とリトライ制御を行います。
- ニュース収集は SSRF・Gzip ボム等の対策が組み込まれています（スキーム検証、プライベートIPブロック、サイズ上限）。
- DuckDB のスキーマ作成は冪等（IF NOT EXISTS）になっています。
- 環境変数が未設定のときは `kabusys.config.Settings` がエラーを投げます。`.env.example` を用意して設定してください。
- 本コードベースには実際の発注（証券会社API）とのインターフェースは含まれますが、運用で「live」環境を使用する際は十分なテストと保護（安全なキー管理・ロギング）を行ってください。
- 自動 .env ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要モジュール構成は次の通りです（src 配下）:

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch/save）
    - news_collector.py — RSS 収集・保存・銘柄抽出
    - schema.py — DuckDB スキーマ定義・初期化
    - stats.py — 統計ユーティリティ（zscore）
    - pipeline.py — ETL パイプライン（差分更新・品質チェック）
    - features.py — 特徴量ユーティリティ公開
    - calendar_management.py — カレンダー更新・営業日判定
    - audit.py — 監査ログ用スキーマ初期化
    - etl.py — ETL 型の公開（ETLResult）
    - quality.py — データ品質チェック
  - research/
    - __init__.py — 研究向けユーティリティの再エクスポート
    - feature_exploration.py — 将来リターン・IC・サマリー
    - factor_research.py — モメンタム/ボラティリティ/バリュー計算
  - execution/ (プレースホルダ)
  - strategy/ (プレースホルダ)
  - monitoring/ (プレースホルダ)

各モジュール内にドキュメンテーション文字列があり、関数の引数・戻り値・設計方針が明記されています。API を使う際は該当モジュールの docstring を参照してください。

---

## さらに学ぶ / 拡張ポイント

- 発注フロー・ブローカー接続（kabu ステーション等）を実装して Execution Layer を完成させる
- 監査ログ（audit）を用いた end-to-end のトレーサビリティ実装
- モデルや戦略を組み込むための strategy / monitoring 層の実装
- CI や定期ジョブ（cron / Airflow / GitHub Actions）で ETL を自動化

---

もし README に追記したい具体的な使用例（エンドツーエンドのスクリプト、Docker 化、CI 定義 など）があれば教えてください。必要に応じてサンプルスクリプトや .env.example を作成します。