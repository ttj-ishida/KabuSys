# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
DuckDB をデータレイヤに用い、J-Quants API からのデータ取得、ETL、品質チェック、ニュース収集、研究用のファクター計算などを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を含むパッケージです。

- J-Quants API からの株価・財務・市場カレンダーの取得（rate limit / retry / トークン自動更新を考慮）
- DuckDB スキーマ定義・初期化と冪等保存
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- RSS ベースのニュース収集と銘柄抽出（SSRF 対策・サイズ制限・トラッキングパラメータ除去）
- 研究用（research）モジュール：特徴量探索（forward returns, IC）・ファクター計算（momentum, value, volatility）など
- 監査ログ（audit）スキーマ：シグナル→発注→約定までのトレーサビリティ

設計方針として、外部 API への不用意なアクセスを避け、DuckDB と標準ライブラリ中心に実装されています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（ページネーション・レート制御・リトライ・トークンリフレッシュ）
  - schema: DuckDB の DDL 定義とスキーマ初期化（Raw / Processed / Feature / Execution 層）
  - pipeline: 日次 ETL（差分取得・backfill・品質チェック）
  - news_collector: RSS 収集、前処理、raw_news 保存、銘柄抽出
  - quality: データ品質チェック（欠損・スパイク・重複・日付整合性）
  - calendar_management: 市場カレンダー管理・営業日判定ユーティリティ
  - audit: 監査ログ用スキーマ（signal / order_request / executions）
  - stats: Zスコア正規化などの統計ユーティリティ
- research/
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
  - factor_research: Momentum / Value / Volatility 等のファクター計算
- config: 環境変数と .env 自動読み込み（.env.local 優先、OS 環境変数を保護）

---

## 必要条件（主な依存）

- Python 3.9+
- duckdb
- defusedxml

（本リポジトリのインストール手順で必要パッケージを導入してください。pip で duckdb / defusedxml を追加）

---

## セットアップ手順

1. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate （Windows: .venv\Scripts\activate）

2. パッケージと依存をインストール
   - pip install -U pip
   - pip install duckdb defusedxml
   - （もしパッケージを editable インストールするなら）pip install -e .

3. 環境変数設定 (.env)
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動で読み込まれます。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 主要な環境変数の例:

     J-Quants / API:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

     kabu ステーション（発注用）:
     - KABU_API_PASSWORD=your_kabu_password
     - KABU_API_BASE_URL=http://localhost:18080/kabusapi   (必要に応じて)

     Slack（通知等）:
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C01234567

     DB / システム:
     - DUCKDB_PATH=data/kabusys.duckdb   (デフォルト)
     - SQLITE_PATH=data/monitoring.db
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=INFO|DEBUG|...

   - .env の読み込みはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点として行われます。
   - .env.local は .env を上書きする優先度で読み込まれます（ただし OS 環境変数は保護される）。

---

## 初期化（DuckDB スキーマ）

DuckDB のスキーマを初期化するには Python から次を実行します。

例:

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は .env の DUCKDB_PATH を反映した Path オブジェクト
conn = init_schema(settings.duckdb_path)
```

- init_schema はテーブルが存在する場合はスキップ（冪等）します。
- ":memory:" を渡すとインメモリ DB を使用できます（テスト等）。

監査ログ専用 DB を初期化する場合:

```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
```

---

## 使い方（主要ユースケース）

1. 日次 ETL の実行（市場カレンダー、株価、財務、品質チェック）

```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

conn = init_schema(settings.duckdb_path)  # 初回は init_schema、既存は get_connection でも可
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- run_daily_etl は calendar → prices → financials → quality checks の順で差分 ETL を実行します。
- id_token を直接注入してテストや複数トークン運用も可能です。

2. ニュース収集ジョブ（RSS 取得→raw_news 保存→銘柄紐付け）

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
known_codes = {"7203", "6758", "9984"}  # 例えば既知の銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count, ...}
```

- fetch_rss は SSRF 対策、gzip/サイズ制限、XML 脆弱性対策（defusedxml）を行います。
- save_raw_news はチャンク挿入・ON CONFLICT DO NOTHING・INSERT RETURNING を利用します。

3. 研究/ファクター計算

```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2024, 1, 15)

mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)

fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
summary = factor_summary(mom, ["mom_1m", "mom_3m", "ma200_dev"])
```

- 設計上、research モジュールは prices_daily / raw_financials を参照し、本番発注 API にはアクセスしません。
- zscore 正規化ユーティリティは kabusys.data.stats.zscore_normalize を使用できます。

---

## 重要な挙動・注意点

- 環境設定:
  - .env と .env.local の自動読み込み機能あり（プロジェクトルート検出、OS 環境変数は保護）。
  - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

- J-Quants クライアント:
  - レート制限（120 req/min）を守るため固定間隔スロットリングを実装しています。
  - リトライ（指数バックオフ）と 401 時のトークン自動更新に対応しています。

- DuckDB スキーマ:
  - テーブルは多層（Raw / Processed / Feature / Execution / Audit）で定義。
  - ON CONFLICT / INSERT RETURNING を使って冪等性を確保しています。
  - 一部の制約（ON DELETE CASCADE など）は DuckDB のバージョン性により省略している箇所があります。運用時は設計ドキュメントに従って削除処理をハンドリングしてください。

- ニュース収集:
  - URL 正規化（トラッキングパラメータ除去）→ ID（SHA-256 の先頭 32 文字）で冪等性を担保。
  - SSRF 対策や gzip 解凍後サイズチェックなど、セキュリティ面の配慮あり。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                         : 環境変数/設定管理（.env 自動読込）
  - data/
    - __init__.py
    - jquants_client.py                : J-Quants API クライアント・保存ロジック
    - news_collector.py                : RSS 収集と DB 保存
    - schema.py                        : DuckDB スキーマ定義・初期化
    - pipeline.py                      : ETL パイプライン（run_daily_etl 等）
    - features.py                      : features public API（zscore 再エクスポート）
    - stats.py                         : 統計ユーティリティ（zscore_normalize）
    - calendar_management.py           : 市場カレンダー管理（is_trading_day 等）
    - audit.py                         : 監査ログスキーマ初期化
    - etl.py                           : ETLResult の公開インターフェース
    - quality.py                       : データ品質チェック
  - research/
    - __init__.py
    - feature_exploration.py           : forward returns, IC, factor_summary
    - factor_research.py               : momentum, value, volatility の計算
  - strategy/                          : （戦略関連のエントリポイント、実装場所）
  - execution/                         : （発注/実行関連）
  - monitoring/                        : （監視・メトリクス用のエントリ）
- pyproject.toml / setup.cfg / .gitignore など（プロジェクトルート）

---

## 開発・テストに関するヒント

- 設定の自動読み込みがテストに影響する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を利用して無効化し、テスト側で明示的に環境変数をセットしてください。
- DuckDB のインメモリ DB(":memory:") を使うとテストが簡単になります。
- network / HTTP 周りはモジュール内で注入可能な関数（例: news_collector._urlopen）をモックすることで外部呼び出しを切り離せます。

---

もし README にサンプル .env のテンプレートやユースケース別スクリプト（cron で ETL を回す、Slack 通知を行う等）を追加したい場合は、目的に合わせた例を作成します。必要であれば教えてください。