# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリセットです。  
データ収集（J-Quants）、DuckDBベースのスキーマ管理、ETLパイプライン、ニュース収集、ファクター研究、監査ログなど、戦略開発から実運用までを想定したユーティリティを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の機能群を持つ Python パッケージです。

- J-Quants API からの市場データおよび財務データ取得（レートリミット・リトライ・トークンリフレッシュ対応）
- DuckDB を用いたデータスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- RSS ベースのニュース収集と銘柄抽出（SSRF 対策、gzip/サイズ制限、トラッキングパラメータ除去）
- ファクター計算（モメンタム / ボラティリティ / バリュー 等）と研究用ユーティリティ（Forward returns, IC, summary）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマ
- 簡易的な設定管理（.env 自動ロード、必須環境変数チェック）

設計方針として、DuckDB と標準ライブラリ中心で実装され、外部依存は最小限に抑えられています（ただし一部モジュールで `defusedxml` を使用）。

---

## 主な機能一覧

- data/jquants_client
  - J-Quants API クライアント（ページネーション、リトライ、レートリミット、トークンリフレッシュ）
  - fetch / save の冪等操作（ON CONFLICT で更新）
- data/schema
  - DuckDB 用の包括的な DDL（Raw / Processed / Feature / Execution / Audit）
  - init_schema / get_connection
- data/pipeline
  - run_daily_etl をはじめとする ETL ジョブ（prices / financials / calendar）
  - 差分取得・バックフィルロジック、品質チェック呼び出し
- data/news_collector
  - RSS 収集、正規化、raw_news 保存、銘柄抽出、SSRF 対策
- data/quality
  - 欠損チェック、重複チェック、スパイク検出、日付整合性チェック
- research
  - calc_momentum, calc_volatility, calc_value（prices_daily / raw_financials を参照）
  - calc_forward_returns, calc_ic, factor_summary, rank
- data/audit
  - シグナル / 発注 / 約定 の監査ログ DDL、audit DB 初期化
- config
  - .env 自動ロード（プロジェクトルート検出）、必須環境変数の取得（settings オブジェクト）

---

## 要件

- Python 3.10 以上（型アノテーションで `X | None` を使用）
- 必要な Python パッケージ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード等）

インストール例（仮に pyproject / setup がある場合）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb defusedxml
# 開発中ならパッケージを編集可能インストール
# pip install -e .
```

---

## 環境変数（主な必須・任意項目）

KabuSys は .env（プロジェクトルート）および .env.local を自動で読み込みます（無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

必須（Settings で _require() が呼ばれるもの）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注系を使う場合）
- SLACK_BOT_TOKEN — Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意／デフォルトあり:
- KABUSYS_ENV — 実行環境: development / paper_trading / live （デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（monitoring 用）（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込み無効化フラグ（1 で無効）

例 .env（プロジェクトルート）:

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順

1. リポジトリをクローン（.git または pyproject.toml がプロジェクトルート判定に使われます）:

   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境作成とパッケージインストール:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb defusedxml
   # 必要に応じて他パッケージを追加
   ```

3. .env を作成して必須環境変数を設定

4. DuckDB スキーマの初期化（ファイルベースまたはインメモリ）:

   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

   またはメモリ DB:
   ```python
   conn = init_schema(":memory:")
   ```

5. 監査ログ専用 DB 初期化（必要な場合）:

   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（代表的な例）

- ETL（日次パイプライン）を実行する:

  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- J-Quants からデータを直接取得して保存する:

  ```python
  from kabusys.data import jquants_client as jq
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, records)
  print(f"saved: {saved}")
  ```

- ニュース収集ジョブの実行:

  ```python
  from kabusys.data.news_collector import run_news_collection
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 既知銘柄セット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- ファクター計算（研究用）:

  ```python
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, zscore_normalize

  conn = duckdb.connect("data/kabusys.duckdb")
  d = date(2024, 3, 1)
  mom = calc_momentum(conn, d)
  vol = calc_volatility(conn, d)
  val = calc_value(conn, d)
  fwd = calc_forward_returns(conn, d, horizons=[1,5,21])
  ic = calc_ic(mom, fwd, "mom_1m", "fwd_1d")
  summary = factor_summary(mom, ["mom_1m", "mom_3m", "ma200_dev"])
  normalized = zscore_normalize(mom, ["mom_1m", "mom_3m", "ma200_dev"])
  ```

- 品質チェック:

  ```python
  from kabusys.data.quality import run_all_checks
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i)
  ```

- 設定値の取得:

  ```python
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  db_path = settings.duckdb_path
  env = settings.env
  ```

---

## 注意事項 / 運用上のヒント

- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に行います。CI やテストで自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants API はレート制限（120 req/min）があります。jquants_client は内部でレート制御・リトライを行いますが、大量ページネーション時は注意してください。
- DuckDB のトランザクション管理や ON CONFLICT 処理を利用しているため、ETL は冪等に設計されていますが、外部から直接データを書き換える場合は品質チェックを実行してください。
- news_collector は RSS の XML をパースするため defusedxml を用いて XML Bomb 等への耐性を向上させています。RSS URL の検証や SSRF 対策も実装していますが、独自ソースを追加する際は URL の正当性を確認してください。
- 実売買（live）環境では `KABUSYS_ENV=live` を設定し、発注・監査ロジックの取り扱いに十分注意してください。実売買用の統制や二重発注防止（冪等キー）は設計に含まれますが、運用手順は別途整備する必要があります。

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内の主要ファイル一覧です（src/kabusys 配下）。

- __init__.py
- config.py

- data/
  - __init__.py
  - jquants_client.py
  - news_collector.py
  - schema.py
  - stats.py
  - pipeline.py
  - features.py
  - calendar_management.py
  - audit.py
  - etl.py
  - quality.py

- research/
  - __init__.py
  - feature_exploration.py
  - factor_research.py

- strategy/
  - __init__.py

- execution/
  - __init__.py

- monitoring/
  - __init__.py

（実装・運用に応じて追加のモジュールや CLI、サンプルスクリプトをプロジェクトルートに置くことを推奨します。）

---

## 貢献・拡張案

- バックテストフレームワークの追加（戦略シミュレーション）
- kdb / ClickHouse 等別 DB へのエクスポート
- Slack 通知や監視ダッシュボード（monitoring モジュール拡充）
- ML 用 Feature Store との連携（特徴量管理の自動化）
- 発注モジュール（kabuステーションや証券会社 API）の実装（安全機構・ロールバック対応）

---

不明点や README の追加要望があれば教えてください。必要に応じて、CLI 例やデプロイ手順（systemd / cron / Kubernetes CronJob）などの具体的な運用ドキュメントも作成します。