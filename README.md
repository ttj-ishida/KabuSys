# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）のリポジトリ用 README（日本語）。

この README はリポジトリ内の主要モジュールに基づいて、プロジェクト概要・機能一覧・セットアップ手順・使い方のサンプル・ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けに設計された Python パッケージです。  
主に次の機能を持ちます。

- J-Quants API などからデータを取得して DuckDB に格納する ETL（差分更新対応、冪等保存）
- 市場カレンダー管理・営業日判定
- ニュース（RSS）収集と記事の前処理・銘柄紐付け
- ファクター（モメンタム、ボラティリティ、バリュー等）計算と特徴量探索（IC 計算等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル→発注→約定 のトレーサビリティ）用スキーマ定義

設計方針として、実行時に本番発注 API へ直接アクセスしないモジュール（data/research 等）と、発注・実行を扱うレイヤーを分離しており、DuckDB を中心に冪等性とトレーサビリティを重視しています。

---

## 主な機能一覧

- データ取得 / 保存
  - J-Quants クライアント（ページネーション・レート制御・自動トークンリフレッシュ・リトライ）
  - raw_prices, raw_financials, market_calendar などへの冪等保存関数
- ETL パイプライン
  - 日次 ETL（run_daily_etl）：カレンダー → 株価 → 財務 → 品質チェック
  - 差分更新、バックフィル対応
- カレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job（夜間バッチ向け）
- ニュース収集
  - RSS 取得（SSRF 対策、gzip 上限、トラッキングパラメータ除去）
  - 記事の正規化・ID 生成（SHA-256）、raw_news 保存、記事→銘柄の紐付け
- 研究・ファクター計算
  - calc_momentum, calc_volatility, calc_value（prices_daily / raw_financials を参照）
  - calc_forward_returns, calc_ic, factor_summary, rank
  - zscore_normalize（data.stats）
- データ品質チェック（quality モジュール）
  - 欠損、スパイク、重複、日付不整合の検出
- スキーマ管理
  - DuckDB のスキーマ初期化（init_schema）、監査ログスキーマの初期化（init_audit_schema / init_audit_db）

---

## 必要環境・依存関係

- Python 3.9 以上 を想定（型注釈に Python 3.10+ の Union 型表記を使っているため、プロジェクトポリシーに合わせて調整してください）
- 必要パッケージ（主なもの）
  - duckdb
  - defusedxml
- 標準ライブラリに依存する箇所も多くあります（urllib, logging, datetime, hashlib など）。

pip を使った導入例（仮想環境推奨）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb defusedxml
# 開発中であればパッケージを editable install
pip install -e .
```

requirements.txt 等がある場合はそれに従ってください。

---

## 環境変数 / 設定

KabuSys は環境変数またはプロジェクトルートの `.env` / `.env.local` ファイルから設定を自動読み込みします（ただし `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動ロードを無効化できます）。

必須の環境変数（Settings で _require() が呼ばれるもの）:

- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD     : kabuステーション等の API パスワード
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID      : Slack 通知先のチャネル ID

オプション（デフォルトあり）:

- KABUSYS_ENV           : "development"（デフォルト） / "paper_trading" / "live"
- LOG_LEVEL             : "INFO"（デフォルト）など ("DEBUG","INFO","WARNING","ERROR","CRITICAL")
- KABUS_API_BASE_URL    : kabu API のベース URL（既定値: http://localhost:18080/kabusapi）
- DUCKDB_PATH           : DuckDB ファイルパス（既定: data/kabusys.duckdb）
- SQLITE_PATH           : SQLite 用パス（監視系などで使用、既定: data/monitoring.db）

例（`.env`）:

```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
DUCKDB_PATH=data/kabusys.duckdb
```

自動読み込みの優先度: OS 環境変数 > .env.local > .env

---

## セットアップ手順（簡易）

1. リポジトリをクローンして仮想環境を作成・有効化する
2. 依存パッケージをインストールする（duckdb, defusedxml 等）
3. `.env` を作成して必要な環境変数を設定する
4. DuckDB スキーマを初期化する

例:

```bash
# 仮想環境（任意）
python -m venv .venv
source .venv/bin/activate

# 依存インストール
pip install duckdb defusedxml

# （任意）パッケージをeditableでインストール
pip install -e .

# .env を用意する（JQUANTS_REFRESH_TOKEN 等を設定）

# Python REPL やスクリプトで DuckDB スキーマ初期化
python - <<'PY'
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
print("initialized")
conn.close()
PY
```

監査ログ用 DB 初期化（監査専用 DB を分離したい場合）:

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/kabusys_audit.duckdb")
```

---

## 使い方（代表的な例）

以下は主要な利用シナリオのサンプルコードです。実行は Python スクリプトやジョブから行います。

- 日次 ETL を走らせる（市場カレンダー→株価→財務→品質チェック）:

```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
conn.close()
```

- ニュース収集ジョブを実行する（RSS から raw_news と news_symbols を保存）:

```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 事前に保持している有効銘柄コードセット
res = run_news_collection(conn, known_codes=known_codes)
print(res)
conn.close()
```

- J-Quants から日足を取得して保存（テスト用／ユーティリティ）:

```python
from kabusys.data.schema import init_schema
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token

conn = init_schema(":memory:")
token = get_id_token()  # 環境変数からリフレッシュトークンを使って取得
records = fetch_daily_quotes(id_token=token, date_from=None, date_to=None)
saved = save_daily_quotes(conn, records)
```

- 研究用ファクター計算（例: モメンタム・IC 計算）:

```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.research import calc_momentum, calc_forward_returns, calc_ic, zscore_normalize

conn = init_schema("data/kabusys.duckdb")
tgt = date(2024, 1, 4)
factors = calc_momentum(conn, tgt)
fwd = calc_forward_returns(conn, tgt, horizons=[1,5,21])
# 例えば mom_1m と fwd_1d の IC を計算
ic = calc_ic(factors, fwd, factor_col="mom_1m", return_col="fwd_1d")
# Zスコア正規化
normed = zscore_normalize(factors, ["mom_1m", "mom_3m", "mom_6m"])
```

- カレンダー関連ユーティリティ:

```python
from kabusys.data.schema import init_schema
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = init_schema("data/kabusys.duckdb")
d = date(2024, 1, 1)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意:
- 多くのデータ取得関数は DuckDB 上の既存テーブル（prices_daily, raw_financials, market_calendar 等）を参照します。初回は ETL で raw_* → processed テーブルを整備してから利用してください。
- J-Quants API 呼び出しはレート制限・リトライ制御・トークンリフレッシュを行います。リフレッシュトークンは必ず安全に管理してください。

---

## ディレクトリ構成

主要なファイル・モジュールは以下の通りです（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                     : 環境変数と Settings 管理（.env 自動ロード）
  - data/
    - __init__.py
    - jquants_client.py            : J-Quants API クライアント（取得・保存）
    - news_collector.py           : RSS 取得・前処理・DB 保存
    - schema.py                   : DuckDB スキーマ定義と初期化（init_schema）
    - stats.py                    : zscore_normalize 等の統計ユーティリティ
    - pipeline.py                 : ETL パイプライン（run_daily_etl 等）
    - features.py                 : 特徴量ユーティリティ公開
    - calendar_management.py      : カレンダー更新・営業日判定・ジョブ
    - audit.py                    : 監査ログ（signal/order/execution）テーブル初期化
    - etl.py                      : ETL インターフェースの再エクスポート
    - quality.py                  : データ品質チェック
  - research/
    - __init__.py
    - feature_exploration.py      : 将来リターン計算、IC、統計サマリー等
    - factor_research.py          : モメンタム／ボラティリティ／バリュー計算
  - strategy/                      : 戦略層（パッケージ用意。実装は別途）
  - execution/                     : 発注/実行層（パッケージ用意。実装は別途）
  - monitoring/                    : 監視・メトリクス（パッケージ用意）

（この README は src の内容に基づいています。実際のリポジトリルートに合わせてパスは変わる可能性があります。）

---

## 開発・運用上の注意

- 自動で .env を読み込む機能は便利ですが、CI/CD やテスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを無効化できます。
- DuckDB ファイルのバックアップやロック・同時接続の取り扱いは運用ルールに従ってください。
- J-Quants の API レート制限（例: 120 req/min）を守るためモジュール側でも制御していますが、大規模なバッチ設計時はさらにバースト制御を検討してください。
- ニュース収集では SSRF・XML Bomb 等に対する防御（defusedxml、受信バイト上限、プライベートホスト拒否）を入れていますが、外部ネットワークの扱いは慎重に。

---

## 付録：よく使う API の一覧（サマリ）

- 設定
  - from kabusys.config import settings
- DB スキーマ
  - from kabusys.data.schema import init_schema, get_connection
- ETL
  - from kabusys.data.pipeline import run_daily_etl, run_prices_etl, run_financials_etl
- J-Quants クライアント
  - from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar, get_id_token, save_daily_quotes, save_financial_statements, save_market_calendar
- ニュース
  - from kabusys.data.news_collector import fetch_rss, save_raw_news, run_news_collection
- 研究
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize
- 品質チェック
  - from kabusys.data.quality import run_all_checks
- カレンダー
  - from kabusys.data.calendar_management import calendar_update_job, is_trading_day, next_trading_day, get_trading_days
- 監査ログ
  - from kabusys.data.audit import init_audit_schema, init_audit_db

---

必要に応じて README を拡張します（例えば CI/CD、デプロイ手順、より詳細な API ドキュメント、サンプルジョブのスケジューリング例など）。特定のセクションの追加や英語版 README も作成可能です。どの部分を詳しく書けばよいか教えてください。