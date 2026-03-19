# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（モジュール群）。  
データ取得（J-Quants）、ETL、データ品質チェック、特徴量計算、ニュース収集、監査ログやスキーマ管理などを含む組織化されたコードベースです。

---

## プロジェクト概要

KabuSys は日本株の定量投資に必要なデータ基盤と戦略研究用ユーティリティを提供するライブラリです。主な目的は以下です：

- J-Quants API からの株価・財務・マーケットカレンダー取得と DuckDB への保存（冪等性対応）
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- ニュース（RSS）収集と記事→銘柄紐付け
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）と IC / 統計サマリー
- 監査ログ用スキーマ（注文→約定のトレーサビリティ）
- 共通の設定管理（環境変数 / .env 自動読み込み）

設計上、研究モジュールは発注・外部ブローカーへアクセスしないよう分離されています。

---

## 機能一覧

- 環境設定管理（.env 自動読み込み、プロジェクトルート検出）
- J-Quants API クライアント
  - 認証トークン自動リフレッシュ
  - ページネーション対応のデータ取得
  - レートリミット制御、リトライ（指数バックオフ）
- DuckDB スキーマ定義 / 初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得、保存、品質チェック）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- ニュース収集（RSS）と記事保存、銘柄抽出（SSRF 対策・gzip 上限など）
- 特徴量計算（momentum / volatility / value 等）
- 研究ユーティリティ（forward returns / IC / rank / z-score 正規化）
- 監査ログ（signal / order_request / executions）スキーマと初期化支援

---

## 前提（Requirements）

主に次の Python パッケージが必要です（プロジェクトの pyproject.toml / requirements.txt を参照してください）:

- Python 3.9+
- duckdb
- defusedxml

（実行環境に応じて他のパッケージが必要になる可能性があります）

インストール例（開発環境）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb defusedxml
# またはパッケージ化されている場合:
# pip install -e .
```

---

## セットアップ手順

1. リポジトリを取得する（git clone 等）。
2. Python 仮想環境を作成して依存をインストールする（上記参照）。
3. 環境変数を設定する（.env ファイルをプロジェクトルートに置くのが推奨）。

主要な環境変数（必須／任意）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション 等の API パスワード（利用する場合）
- SLACK_BOT_TOKEN (必須) — Slack 通知に使用する BOT トークン（必要な場合）
- SLACK_CHANNEL_ID (必須) — Slack チャネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — SQLite path（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — environment: development / paper_trading / live（デフォルト development）
- LOG_LEVEL (任意) — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL

.env の自動読み込みについて:
- パッケージはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を起点に自動で `.env` と `.env.local` を読み込みます。
- 読み込み順: OS 環境変数 > .env.local > .env
- 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テストなどで使用）。

簡単な `.env` 例:

```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## データベース初期化

DuckDB スキーマを初期化する例:

```python
from kabusys.data.schema import init_schema

# ファイル DB の場合
conn = init_schema("data/kabusys.duckdb")

# インメモリ DB の場合（例: テスト）
# conn = init_schema(":memory:")
```

監査ログ用スキーマを追加する例（既存の接続に対して）:

```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

---

## 使い方（主要なユースケース）

以下に代表的な操作の使い方（Python API 呼び出し）を示します。

- 日次 ETL を実行する（市場カレンダー取得 → 株価差分取得 → 財務データ取得 → 品質チェック）:

```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- J-Quants から日足を取得して保存する（個別利用）:

```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
print(f"saved: {saved}")
```

- ニュース収集ジョブを走らせる（RSS から raw_news と news_symbols を作成）:

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes: 銘柄コードセット（extract_stock_codes で使用）
known_codes = {"7203", "6758", "9433", ...}
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

- 研究用ファクター計算（例: momentum）:

```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_volatility, calc_value, zscore_normalize

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, target_date=date(2025,1,31))
vol = calc_volatility(conn, target_date=date(2025,1,31))
val = calc_value(conn, target_date=date(2025,1,31))

# Zスコア正規化例
normalized = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

- forward returns / IC 計算（研究支援）:

```python
from kabusys.research import calc_forward_returns, calc_ic, factor_summary

fwd = calc_forward_returns(conn, target_date=date(2025,1,31))
ic = calc_ic(factor_records=mom, forward_records=fwd, factor_col="mom_1m", return_col="fwd_1d")
summary = factor_summary(mom, ["mom_1m", "mom_3m", "ma200_dev"])
```

---

## ログ・実行モード

- KABUSYS_ENV により実行モードを指定できます（development / paper_trading / live）。settings.is_live などで参照できます。
- LOG_LEVEL 環境変数でログレベルを変更します（デフォルト INFO）。

---

## セキュリティ・設計上の注意点

- J-Quants クライアント:
  - レート制限（120 req/min）を順守するため内部でスロットリング。HTTP エラー時のリトライと指数バックオフを実装しています。
  - 401 受信時はリフレッシュトークンを用いて自動的に ID トークンを更新して再試行します（1 回のみ）。
- ニュース収集:
  - SSRF 対策（スキーム検証、プライベート IP 拒否、リダイレクト検査）を実装。
  - 受信サイズに上限を設け、gzip 解凍後も上限をチェックしています。
  - XML パースは defusedxml を利用して危険な XML を防ぎます。
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE / DO NOTHING）を基本設計としています。

---

## ディレクトリ構成

主要なファイル／モジュール構成（src/kabusys 以下）:

```
src/kabusys/
├── __init__.py
├── config.py                      # 環境変数 / .env 管理
├── data/
│   ├── __init__.py
│   ├── jquants_client.py          # J-Quants API クライアント
│   ├── news_collector.py          # RSS ニュース収集
│   ├── schema.py                  # DuckDB スキーマ定義・初期化
│   ├── stats.py                   # 統計ユーティリティ（zscore など）
│   ├── pipeline.py                # ETL パイプライン
│   ├── features.py                # features 入口（zscore を再エクスポート）
│   ├── calendar_management.py     # market_calendar 管理
│   ├── audit.py                   # 監査スキーマ初期化
│   ├── etl.py                     # ETL 型の再エクスポート
│   └── quality.py                 # データ品質チェック
├── research/
│   ├── __init__.py
│   ├── feature_exploration.py     # forward returns / IC / summary / rank
│   └── factor_research.py         # momentum / volatility / value 等
├── strategy/
│   └── __init__.py
├── execution/
│   └── __init__.py
└── monitoring/
    └── __init__.py
```

注: strategy, execution, monitoring のパッケージは存在しますが、今回提示されたコードではインターフェースのみ（空 __init__.py）です。

---

## 開発・テストヒント

- テストや一時的な実行では DuckDB の ":memory:" を使用すると便利です。
- 環境変数自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（ユニットテストなどで .env を読みたくない場合）。
- ネットワーク呼び出しを含むモジュール（jquants_client、news_collector）をテストする際は、内部のネットワーク層（例えば news_collector._urlopen や jquants_client._request）をモックすると簡単です。

---

必要であれば README に実行スクリプト例（CLI）や追加の設定例、SQL スキーマ一覧の詳述、CI 用の手順などを追記します。どの情報を優先的に追加したいか教えてください。