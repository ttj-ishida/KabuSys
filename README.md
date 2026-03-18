# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリです。  
DuckDB をデータ層に用い、J-Quants API からマーケットデータや財務データを取得して ETL → 品質チェック → 特徴量生成 → 研究・戦略開発へとつなぐことを目的としたモジュール群を提供します。

現在のバージョン: 0.1.0

---

## 概要

KabuSys は次のレイヤーを含むデータ処理・研究基盤を提供します。

- Raw Layer: API から取得した生データ（株価、財務、ニュース等）
- Processed Layer: 日次整形データ（prices_daily、market_calendar 等）
- Feature Layer: 戦略・AI 用の特徴量テーブル
- Execution / Audit Layer: シグナル / 発注 / 約定 / 監査ログ（監査用スキーマあり）

設計上のポイント:

- DuckDB を用いた単一ファイル DB（ローカル）で管理可能
- J-Quants API クライアント（ページネーション・レート制御・リトライ・トークンリフレッシュ付き）
- RSS ベースのニュース収集（SSRF 対策、トラッキングパラメータ除去、重複除去）
- ETL は差分更新・バックフィルをサポートし、品質チェックを実行
- 研究モジュールは外部サービスに影響を与えない（read-only、標準ライブラリ中心）

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API からの取得（株価、財務、カレンダー）および DuckDB への冪等保存
  - news_collector: RSS 取得・前処理・raw_news への保存、記事 → 銘柄紐付け
  - schema: DuckDB スキーマ定義（Raw/Processed/Feature/Execution）と初期化 `init_schema`
  - pipeline: 日次 ETL パイプライン（差分取得・保存・品質チェック）
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合等）
  - calendar_management: 市場カレンダー管理と営業日ユーティリティ
  - audit: 発注〜約定を追跡する監査スキーマの初期化
  - stats / features: Zスコア正規化などの統計ユーティリティ
- research/
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
  - factor_research: Momentum / Volatility / Value などのファクター計算
- config: 環境変数管理（.env 自動ロード、必須変数検証）

その他、strategy/、execution/、monitoring/ の骨格モジュールを含みます（詳細は各実装を参照）。

---

## 動作環境・依存関係

- Python 3.10+
- 必須ライブラリ（少なくともこれらをインストールしてください）:
  - duckdb
  - defusedxml

インストール例:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# 開発パッケージをセットアップ済みのパッケージとしてインストールする場合:
# pip install -e .
```

---

## 環境変数（.env）

config.Settings で参照される主な環境変数:

- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン（API 認証）
- KABU_API_PASSWORD (必須): kabu ステーション API のパスワード（発注等で使用）
- KABU_API_BASE_URL (任意): kabu API ベース URL。デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須): Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須): Slack 通知先チャンネル ID
- DUCKDB_PATH (任意): デフォルト DB ファイルパス。デフォルト: data/kabusys.duckdb
- SQLITE_PATH (任意): 監視用 SQLite パス。デフォルト: data/monitoring.db
- KABUSYS_ENV (任意): 環境 ("development" | "paper_trading" | "live")、デフォルト "development"
- LOG_LEVEL (任意): ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると、プロジェクトルートの .env / .env.local 自動読み込みを無効化できます（テスト時等に便利）

README 配布パッケージには .env.example を置いておくことを推奨します（config._require() は必須変数未定義時に ValueError を投げます）。

---

## セットアップ手順（簡易）

1. リポジトリをクローン

```bash
git clone <repo-url>
cd <repo-dir>
```

2. 仮想環境を作成・アクティベート、依存をインストール

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# もしパッケージ化されているなら:
# pip install -e .
```

3. 環境変数を設定（.env を作成）

例: .env

```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

4. DuckDB スキーマの初期化

Python から実行:

```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # :memory: も可能
```

5. 監査ログ用スキーマ（必要な場合）

```python
from kabusys.data.audit import init_audit_schema, init_audit_db
# 既存 conn に追加する場合:
init_audit_schema(conn, transactional=True)
# 監査専用 DB を作る場合:
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

---

## 使い方（代表的な API）

- 日次 ETL を実行する（株価・財務・カレンダー取得＋品質チェック）

```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

# DB 初期化（初回）
conn = init_schema("data/kabusys.duckdb")

# ETL 実行（today を対象）
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 差分で株価 ETL を個別実行

```python
from kabusys.data.pipeline import run_prices_etl
fetched, saved = run_prices_etl(conn, target_date=date.today())
```

- ニュース収集ジョブを実行する（既知銘柄セットを渡して銘柄紐付けまで）

```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

known_codes = {"7203", "6758", "9432"}  # など
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)
```

- 研究用ファクター計算の例

```python
from kabusys.research import calc_momentum, calc_volatility, calc_value, zscore_normalize
from datetime import date

mom = calc_momentum(conn, target_date=date(2024, 1, 31))
vol = calc_volatility(conn, target_date=date(2024, 1, 31))
val = calc_value(conn, target_date=date(2024, 1, 31))

# Zスコア正規化
normed = zscore_normalize(mom, columns=["mom_1m", "mom_3m", "mom_6m"])
```

- 将来リターン／IC 解析

```python
from kabusys.research import calc_forward_returns, calc_ic, factor_summary
fwd = calc_forward_returns(conn, target_date=date(2024,1,31), horizons=[1,5,21])
ic = calc_ic(factor_records=mom, forward_records=fwd, factor_col="mom_1m", return_col="fwd_1d")
summary = factor_summary(mom, ["mom_1m","mom_3m","mom_6m"])
```

注意: research モジュールは DuckDB の prices_daily / raw_financials テーブルのみを参照し、発注や外部サービスへのアクセスは行いません。

---

## よく使うユーティリティ関数

- schema.init_schema(db_path): DuckDB スキーマ作成・接続取得
- data.jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar: API からのデータ取得
- data.jquants_client.save_*: DuckDB への冪等保存
- data.pipeline.run_daily_etl: 日次 ETL（全体）の主要エントリポイント
- data.news_collector.run_news_collection: RSS 収集 → raw_news 保存 → 銘柄紐付け
- data.quality.run_all_checks: 品質チェック一括実行
- data.calendar_management.is_trading_day / next_trading_day / prev_trading_day / get_trading_days: 営業日判定・検索
- audit.init_audit_schema / init_audit_db: 監査ログ用テーブル初期化

---

## ディレクトリ構成

リポジトリの主要ファイル・ディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py
  - __version__ = "0.1.0"
  - config.py  — 環境変数管理 (.env 自動ロード、必須チェック)
  - data/
    - __init__.py
    - jquants_client.py         — J-Quants API クライアント & DuckDB 保存関数
    - news_collector.py        — RSS 収集・保存・銘柄抽出
    - schema.py                — DuckDB スキーマ定義 & init_schema
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - quality.py               — データ品質チェック
    - calendar_management.py   — 市場カレンダー更新・営業日ユーティリティ
    - audit.py                 — 監査スキーマ初期化
    - stats.py                 — zscore_normalize 等の統計ユーティリティ
    - features.py              — public re-export（zscore_normalize）
    - etl.py                   — ETLResult の再エクスポート
  - research/
    - __init__.py              — factor / feature_exploration の再エクスポート
    - factor_research.py       — Momentum / Value / Volatility 計算
    - feature_exploration.py   — forward returns / IC / summary
  - strategy/                  — 戦略レイヤ（骨格）
  - execution/                 — 発注実行レイヤ（骨格）
  - monitoring/                — 監視・メトリクス（骨格）

---

## 注意事項・運用上のポイント

- API レート制御やリトライは jquants_client 内で実装済みですが、運用時は J-Quants の利用制限・ポリシーに従ってください。
- デフォルトではプロジェクトルート（.git または pyproject.toml）から .env を自動読み込みします。テスト時に自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB に対する DDL は冪等に設計されていますが、監査スキーマ等は init のオプション（transactional）に注意してください（DuckDB のトランザクション特性を参照）。
- ニュース収集では SSRF 対策や受信サイズ制限、トラッキングパラメータ除去、XML パースの安全化（defusedxml）など基本的な防御を組み込んでいますが、外部ソースの扱いには引き続き注意してください。
- 本ライブラリは研究／ペーパートレード用途での利用を想定しており、本番の売買（live）運用時は十分な検証とリスク管理が必要です。

---

もし README に追加したい「例外処理の運用方法」や「CI/テストのセットアップ」、「詳細なテーブル定義ドキュメント」を希望される場合は、その内容に合わせて追記します。