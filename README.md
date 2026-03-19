# KabuSys

日本株向け自動売買プラットフォームの一部（ライブラリ群）

このリポジトリは、データ取得・ETL、特徴量計算（リサーチ）、ニュース収集、DuckDB スキーマ定義、監査ログ等を含む日本株自動売買システムの基盤モジュール群です。  
本 README は、プロジェクトの概要、主要機能、セットアップ手順、簡単な使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は次の要素を提供します。

- J-Quants API からのデータ取得クライアント（株価、財務、マーケットカレンダー）
- DuckDB ベースのスキーマ定義と初期化ユーティリティ
- ETL パイプライン（差分取得・保存・品質チェック）
- ニュース（RSS）収集とテキスト前処理、銘柄抽出・DB 保存
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）
- 共通設定読み込み（.env 自動読み込み、環境判定、ログレベル等）
- 監査ログ用スキーマ（シグナル→発注→約定のトレーサビリティ）

設計上、ETL / research / data モジュールはいずれも「DuckDB 接続」を受け取り、ローカル DB のみを操作します。本番の発注 API（kabuステーションなど）へのアクセスは別モジュールで扱う想定です。

---

## 主な機能一覧

- 環境設定の自動読み込み（プロジェクトルートの `.env`, `.env.local`）
- J-Quants API クライアント（レートリミット、リトライ、トークン刷新対応）
- DuckDB スキーマ定義 / 初期化（raw / processed / feature / execution / audit 層）
- 日次 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）
- ニュース収集（RSS、URL 正規化、SSRF 対策、トラッキングパラメータ除去）
- ファクター計算（モメンタム・ボラティリティ・バリュー等）
- 統計ユーティリティ（Zスコア正規化、IC 計算、要約統計）
- データ品質チェック（欠損・スパイク・重複・日付不整合）

---

## 前提条件

- Python 3.10 以上（型注釈に `X | None` 形式を利用）
- 必要ライブラリ（最低限）
  - duckdb
  - defusedxml

推奨インストール例（仮に仮想環境を使用）:
```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install duckdb defusedxml
# パッケージとしてインストール可能なら:
# python -m pip install -e .
```

（プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを利用してください）

---

## 環境変数 / .env

`kabusys.config.Settings` で参照される主な環境変数:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu API のパスワード（発注を行う場合）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用トークン（必須／通知機能利用時）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須／通知機能利用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite パス（モニタリング用、デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境モード（development / paper_trading / live、デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）

自動読み込み:
- パッケージ import 時にプロジェクトルート（.git または pyproject.toml を探索）を基準に `.env` と `.env.local` を読み込みます。
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時などに便利です）。

例（.env.example 的な内容）:
```env
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・アクティベートする。
2. 依存パッケージをインストール（上記参照）。
3. .env をプロジェクトルートに配置して必要なシークレットを設定する（J-Quants トークン等）。
4. DuckDB スキーマを初期化する。

DuckDB スキーマ初期化（Python REPL 例）:
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # デフォルトパスと同じ
# 必要であれば監査ログ用スキーマも追加
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)
```

監査ログ専用 DB を個別で作る場合:
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

---

## 使い方（主要な操作例）

以下は最小限の利用例です。各モジュールは DuckDB 接続を受け取る設計です。

- 日次 ETL 実行:
```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 市場カレンダー更新ジョブ:
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print("saved:", saved)
```

- ニュース収集（RSS）と保存:
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
print(res)
```

- J-Quants から日足を取得して保存（テスト／デバッグ）:
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
records = fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
saved = save_daily_quotes(conn, records)
```

- ファクター計算（研究）:
```python
from datetime import date
from kabusys.research import calc_momentum, calc_volatility, calc_value

moms = calc_momentum(conn, target_date=date(2024,1,10))
vols = calc_volatility(conn, target_date=date(2024,1,10))
vals = calc_value(conn, target_date=date(2024,1,10))
# Zスコア正規化
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(moms, ["mom_1m", "mom_3m", "mom_6m"])
```

- IC 計算やサマリー:
```python
from kabusys.research import calc_forward_returns, calc_ic, factor_summary
fwd = calc_forward_returns(conn, target_date=date(2024,1,10), horizons=[1,5,21])
ic = calc_ic(factor_records=moms, forward_records=fwd, factor_col="mom_1m", return_col="fwd_1d")
summary = factor_summary(moms, ["mom_1m","ma200_dev"])
```

---

## 運用上の注意

- J-Quants API はレート制限があります。クライアント側で 120 req/min を制御する仕組みが入っていますが、大量取得時は注意してください。
- ETL は差分更新を行います。初回は過去データ全件を取得するよう設計されていますが、date_from や backfill_days を指定して調整できます。
- ニュース収集では SSRF / XML Bomb / 大きなレスポンス対策等の安全対策が組み込まれています。
- 環境モード（KABUSYS_ENV）により挙動（例: 発注を行うか否か）を切り替える想定です。live での実行は特に慎重に設定してください。
- 自動環境変数ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト環境で便利）。

---

## ディレクトリ構成（主なファイル）

以下は主要モジュールの一覧（実際のリポジトリルートが異なる場合があります）。

- src/kabusys/
  - __init__.py
  - config.py                         # 環境変数 / 設定管理（.env 自動ロード含む）
  - data/
    - __init__.py
    - jquants_client.py               # J-Quants API クライアント（fetch/save）
    - news_collector.py               # RSS 収集・正規化・DB 保存
    - schema.py                       # DuckDB スキーマ定義・初期化
    - stats.py                        # 統計ユーティリティ（zscore_normalize）
    - pipeline.py                     # ETL パイプライン（run_daily_etl 等）
    - calendar_management.py          # マーケットカレンダー管理
    - audit.py                        # 監査ログスキーマ（signal/order/execution）
    - etl.py                          # ETL の公開インタフェース
    - features.py                     # 特徴量ユーティリティ（再エクスポート）
    - quality.py                      # データ品質チェック
  - research/
    - __init__.py
    - factor_research.py              # モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py          # forward returns / IC / summary / rank
  - strategy/                          # 戦略関連（空 __init__ 、戦略実装はここに）
  - execution/                         # 発注/実行管理（空 __init__）
  - monitoring/                        # 監視（空 __init__）

（上記は現コードベースの主要ファイルを抜粋したものです）

---

## 開発・テストのヒント

- 単体テストや CI では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して環境変数自動読み込みを抑制すると安定します。
- DuckDB のインメモリ DB（db_path=":memory:"）を使えばファイルのクリーンアップ不要でテストできます。
- ネットワーク呼び出し（J-Quants / RSS）はモックしやすいように設計されています（関数引数でトークン注入や _urlopen を差し替えられます）。

---

以上が README の概要です。実際の運用・詳細実装（発注ロジック、リスク管理、Slack 通知等）はこの基盤に機能を追加していくことを想定しています。必要であれば「発注フロー」「戦略実装テンプレ」「監視/アラート設定」のサンプル README も追加できます。どの部分を優先して文書化しますか？