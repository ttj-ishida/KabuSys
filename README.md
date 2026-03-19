# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリコア（読み取り専用・研究用コンポーネントを含む）

このリポジトリは、J-Quants など外部データソースからデータを取得して DuckDB に格納し、戦略用特徴量の計算や監査ログ、発注フローのためのスキーマ・ユーティリティを提供する Python パッケージ群です。研究（Research）用途のファクター計算・IC 評価モジュールや、RSS ニュース収集、データ品質チェック・ETL パイプライン、監査ログスキーマなどを含みます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- 必要条件
- セットアップ手順
- 環境変数（.env）
- 使い方（基本例）
  - DuckDB スキーマ初期化
  - 日次 ETL 実行
  - RSS ニュース収集ジョブ
  - 研究用ファクター計算（例）
- ディレクトリ構成
- トラブルシューティング / 補足

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構築するためのライブラリ群のコアです。主な目的は次のとおりです。

- J-Quants API からのデータ取得（株価日足、四半期財務、マーケットカレンダー）
- DuckDB ベースのデータスキーマ定義と初期化
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- ニュース（RSS）収集と銘柄抽出
- 研究用途のファクター計算（モメンタム、バリュー、ボラティリティ 等）と評価（IC）
- 発注・監査用スキーマ（監査ログ、order_request, executions 等）
- 環境設定管理（.env 自動ロード、必須キーの検証）

設計上、Research / Data 用モジュールは実際の発注 API などにアクセスしない（読み取り専用）ように分離されています。

---

## 機能一覧

主なモジュールと機能（概要）:

- kabusys.config
  - .env ファイル（.env / .env.local）または環境変数から設定を自動ロード
  - 必須設定の検証（例: JQUANTS_REFRESH_TOKEN）
  - KABUSYS_ENV（development / paper_trading / live）など

- kabusys.data
  - jquants_client: J-Quants API クライアント（レートリミット、リトライ、token リフレッシュ）
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
    - save_daily_quotes, save_financial_statements, save_market_calendar（DuckDB へ冪等保存）
  - schema: DuckDB 用 DDL 定義と init_schema()
  - pipeline: ETL ジョブ（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - news_collector: RSS 収集・前処理・DB 保存（SSRF 対策、gzip 制限、トラッキングパラ常除去）
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - calendar_management: 営業日判定ユーティリティ（is_trading_day, next_trading_day 等）
  - audit: 監査ログ用スキーマと初期化（order_requests, signal_events, executions）
  - stats: zscore_normalize（特徴量正規化）

- kabusys.research
  - factor_research: calc_momentum, calc_volatility, calc_value（DuckDB を参照して特徴量計算）
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank（IC・フォワードリターン計算等）

- その他
  - schema/feature/ai_scores 等を含む DuckDB スキーマ（Raw / Processed / Feature / Execution 層）

---

## 必要条件

（代表的な依存パッケージ。プロジェクトの requirements.txt を参照してください）

- Python 3.9+
- duckdb
- defusedxml

その他、J-Quants API を利用するためにインターネット接続が必要です。RSS 取得もネットワークを使用します。

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成・有効化します。

   bash:
   ```
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

2. 必要パッケージをインストールします（例）:

   ```
   pip install duckdb defusedxml
   ```

   実際はプロジェクトの requirements.txt / pyproject.toml を利用してください。

3. 環境変数を設定します。プロジェクトルートに .env（および .env.local）を置くと自動ロードされます。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 環境変数（.env の例）

以下は最低限必要な環境変数（一部）です。必須のものはコード中で _require を通じて検査されます。

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード（使用する場合）
- SLACK_BOT_TOKEN (必須) — Slack 通知に使用する場合
- SLACK_CHANNEL_ID (必須) — Slack チャネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境（development / paper_trading / live）、デフォルトは development
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）、デフォルト INFO

例 (.env):
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意: .env の読み込みルールは robust に実装されており、シングル/ダブルクォートやコメントの扱い、export プレフィックスに対応します。

---

## 使い方（基本例）

以下はパッケージ API を直接使う最小例です。インポート方法はパッケージ命名空間を使います。

1) DuckDB スキーマの初期化

Python REPL / スクリプト:
```python
from kabusys.data import schema

# ファイルに永続化する DB を初期化（ディレクトリがなければ自動作成）
conn = schema.init_schema("data/kabusys.duckdb")
# 必要に応じて監査ログを追加
from kabusys.data import audit
audit.init_audit_schema(conn, transactional=True)
```

2) 日次 ETL（J-Quants からデータを差分取得して保存）

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB へ接続
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- run_daily_etl は内部で市場カレンダー→株価→財務の順で差分取得を行い、品質チェックを実行します。
- J-Quants の認証は settings.jquants_refresh_token を使って自動で id_token を取得・キャッシュします。

3) RSS ニュース収集と銘柄紐付け

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
# known_codes を渡すと記事から4桁銘柄コードを抽出して news_symbols に紐付ける
known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット
result = run_news_collection(conn, known_codes=known_codes)
print(result)  # {source_name: saved_count, ...}
```

4) 研究用ファクター計算・評価

```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
from kabusys.data.stats import zscore_normalize

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2025, 1, 31)

momentum_records = calc_momentum(conn, d)
vol_records = calc_volatility(conn, d)
value_records = calc_value(conn, d)

# 将来リターン計算
fwd = calc_forward_returns(conn, d, horizons=[1,5,21])

# IC 計算（例: mom_1m と fwd_1d の Spearman ρ）
ic = calc_ic(momentum_records, fwd, "mom_1m", "fwd_1d")
print("IC (mom_1m vs fwd_1d):", ic)

# Zスコア正規化
norm = zscore_normalize(momentum_records, ["mom_1m", "mom_3m", "mom_6m"])
```

---

## ディレクトリ構成

主なファイル / ディレクトリ（src/kabusys 以下）:

- __init__.py
- config.py — 環境設定・.env 自動ロード・settings オブジェクト
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（レートリミット・リトライ・保存）
  - news_collector.py — RSS 取得・前処理・DB 保存（SSRF 対策など）
  - schema.py — DuckDB スキーマ DDL と init_schema / get_connection
  - pipeline.py — ETL パイプライン（差分取得・バックフィル・品質チェック）
  - quality.py — データ品質チェック（欠損/スパイク/重複/日付不整合）
  - calendar_management.py — 営業日判定・カレンダー更新ジョブ
  - audit.py — 監査ログテーブル（signal_events, order_requests, executions）
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - features.py, etl.py — 公開 API の再エクスポートなど
- research/
  - __init__.py
  - factor_research.py — momentum / volatility / value の計算
  - feature_exploration.py — forward return / IC / summary / rank
- strategy/ (空の __init__ など、戦略層用プレースホルダ)
- execution/ (発注周りのモジュール用プレースホルダ)
- monitoring/ (監視用モジュール用プレースホルダ)

（開発中のモジュールは空実装ファイルが含まれます）

---

## トラブルシューティング・補足

- 環境変数未設定時:
  - settings オブジェクトの必須プロパティ（例: jquants_refresh_token）は未設定だと ValueError を送出します。`.env.example` を参考に .env を設置してください。
- 自動 .env ロード:
  - プロジェクトルートは __file__ から見て .git または pyproject.toml を探索して決めます。CWD に依存しません。
  - 自動ロードを無効にするには: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- J-Quants API の振る舞い:
  - 内部で 120 req/min のレート制御、最大 3 回リトライ（指数バックオフ）、401 でのトークン自動リフレッシュを実装しています。
- DuckDB トランザクション:
  - schema.init_schema はテーブル作成をトランザクションでまとめて行います。audit.init_audit_schema は transactional 引数によりトランザクション制御が可能です。
- News Collector の安全対策:
  - SSRF を意識したリダイレクト検査、プライベートアドレス拒否、レスポンスサイズ制限、defusedxml で XML 攻撃軽減、トラッキングパラメータ除去などを実装しています。
- テスト:
  - テスト用に env 自動ロードを抑止するフラグ、jquants_client の id_token 注入などテスト容易性を考慮した設計になっています。

---

これで README の基本の説明は終わりです。追加で「運用手順（cron / CI の例）」「より詳しい .env.example」「API 使用上の注意（レート制限の運用）」「サンプルデータの準備スクリプト」などを追記したい場合は、用途（運用/開発/CI）を教えてください。