# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
DuckDB を用いたデータレイヤ（Raw / Processed / Feature / Execution）および J-Quants API / RSS ニュース収集・品質チェック・ETL・戦略評価（Research）機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的とした内部ライブラリ群です。

- J-Quants API から株価・財務・マーケットカレンダーを取得して DuckDB に保存する ETL
- RSS ベースのニュース収集と銘柄紐付け
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- ファクター（モメンタム・ボラティリティ・バリュー等）計算、将来リターン / IC 評価などのリサーチ用ユーティリティ
- 発注・監査（Audit）用のスキーマ設計（監査ログ初期化機能）
- 汎用統計ユーティリティ（Zスコア正規化等）

設計上のポイント:
- DuckDB を中心に冪等的な保存（ON CONFLICT）を前提とした実装
- J-Quants API はレート制限・リトライ・トークン自動リフレッシュに対応
- 本番の発注 API には直接アクセスしないモジュール（Research / Data）は安全に設計

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants からの日次株価・財務・カレンダー取得、DuckDB への保存ユーティリティ
  - schema: DuckDB のスキーマ定義・初期化（Raw / Processed / Feature / Execution）
  - pipeline / etl: 差分取得ロジック・日次 ETL 集約処理（run_daily_etl）
  - news_collector: RSS 取得・前処理・記事保存・銘柄抽出・一括保存
  - quality: データ品質チェック群（欠損・重複・スパイク・日付不整合）
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - audit: 監査ログ（signal / order_request / executions）スキーマ初期化ユーティリティ
  - stats: zscore_normalize 等の統計ユーティリティ
- research/
  - feature_exploration: 将来リターン計算 (calc_forward_returns)、IC 計算 (calc_ic)、統計サマリー
  - factor_research: momentum / volatility / value 等のファクター計算
- strategy/, execution/, monitoring/ は将来的な拡張点（パッケージ初期化はある）

---

## 必要要件

- Python 3.10 以上（型注釈に `|` を使用しているため）
- 必要な Python パッケージ（最低限）
  - duckdb
  - defusedxml

推奨: 仮想環境（venv / virtualenv / poetry / pipenv 等）を使用してください。

例（pip）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

プロジェクト単位の requirements.txt があればそれを使ってください。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成して依存をインストール
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb defusedxml
   ```

3. 環境変数の設定
   - プロジェクトルートに `.env`（と任意で `.env.local`）を配置することで自動で読み込まれます。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード（発注系を使う場合）
     - SLACK_BOT_TOKEN — Slack 通知用トークン（使用する場合）
     - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
   - オプション:
     - KABUSYS_ENV — environment ("development" | "paper_trading" | "live")（デフォルト development）
     - LOG_LEVEL — ログレベル（例: INFO）
     - KABU_API_BASE_URL — kabuAPI の base URL（デフォルト http://localhost:18080/kabusapi）
     - DUCKDB_PATH / SQLITE_PATH — データベースパス（デフォルト data/kabusys.duckdb など）

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマ初期化
   - メインデータベース:
     ```python
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")
     ```
   - 監査ログ専用 DB（任意）:
     ```python
     from kabusys.data import audit
     conn_audit = audit.init_audit_db("data/kabusys_audit.duckdb")
     ```

---

## 使い方（代表的な例）

- 日次 ETL（株価・財務・カレンダー取得 + 品質チェック）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data import schema, pipeline

  conn = schema.init_schema("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- J-Quants から日次株価を直接取得して保存
  ```python
  import duckdb
  from kabusys.data import jquants_client as jq

  conn = duckdb.connect("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, records)
  print("saved", saved)
  ```

- RSS ニュース収集ジョブ
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data import schema

  conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB を使用
  known_codes = {"7203", "6758", "9432"}  # 事前に用意した有効銘柄セット
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  ```

- ファクター計算 / リサーチ
  ```python
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

  conn = duckdb.connect("data/kabusys.duckdb")
  t = date(2024, 1, 31)
  mom = calc_momentum(conn, t)
  vol = calc_volatility(conn, t)
  val = calc_value(conn, t)
  fwd = calc_forward_returns(conn, t, horizons=[1,5,21])

  # 例: mom の "mom_1m" と翌日リターン "fwd_1d" の IC
  ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
  print("IC:", ic)
  ```

- Zスコア正規化
  ```python
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(mom, columns=["mom_1m", "ma200_dev"])
  ```

---

## .env 自動読み込み挙動

- パッケージ import 時にプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し、以下の順で環境変数をロードします:
  1. OS 環境変数（既存のものは保護される）
  2. .env（既存の OS 環境変数を上書きしない）
  3. .env.local（上書き許可）
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト用途など）。

.env のパースは Bourne-ish な形式（export KEY=val, コメント、クォート対応）に対応しています。

---

## ディレクトリ構成

主要ファイル・モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数/設定管理（settings オブジェクト）
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - pipeline.py
    - etl.py
    - quality.py
    - stats.py
    - calendar_management.py
    - audit.py
    - features.py
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

（実際のリポジトリにはさらにファイルやドキュメントを配置してください）

---

## 主要 API（抜粋）

- kabusys.config.settings — 設定オブジェクト（settings.jquants_refresh_token, settings.duckdb_path, settings.env 等）
- kabusys.data.schema.init_schema(db_path) — DuckDB スキーマ初期化（戻り値: DuckDB 接続）
- kabusys.data.jquants_client:
  - fetch_daily_quotes(...)
  - save_daily_quotes(conn, records)
  - fetch_financial_statements(...)
  - save_financial_statements(conn, records)
  - fetch_market_calendar(...)
  - save_market_calendar(conn, records)
- kabusys.data.pipeline.run_daily_etl(conn, target_date, ...) — 日次 ETL 実行
- kabusys.data.news_collector.run_news_collection(conn, sources, known_codes) — RSS 収集ジョブ
- kabusys.data.quality.run_all_checks(conn, target_date, reference_date) — 品質チェックをまとめて実行
- kabusys.research:
  - calc_momentum(conn, target_date)
  - calc_volatility(conn, target_date)
  - calc_value(conn, target_date)
  - calc_forward_returns(conn, target_date, horizons)
  - calc_ic(factor_records, forward_records, factor_col, return_col)
- kabusys.data.stats.zscore_normalize(records, columns)

---

## 注意点 / 補足

- DuckDB のバージョンや SQL 機能差に依存するため、実稼働環境では事前に動作確認を行ってください（特に ON CONFLICT の挙動やインデックス挙動）。
- news_collector は外部ネットワークに接続します。SSRF 対策・レスポンスサイズ制限等の安全設計を実装していますが、運用時にアクセス許可やネットワーク制限を検討してください。
- J-Quants API のレート制限や認証の扱いに注意してください（refresh token の管理、安全な保管を推奨）。
- 発注・実際のブローカー API を組み込む際は、監査ログ（audit）を有効にして冪等性とトレースを確保してください。

---

## 貢献 / ライセンス

このリポジトリは開発段階のコード群です。貢献や改善提案は PR や Issue を通して受け付けてください。ライセンスはリポジトリルートの LICENSE を参照してください（無ければプロジェクトポリシーに従って追加してください）。

---

必要であれば、README に含めるサンプルスクリプトや `.env.example` のテンプレートを作成します。ご希望があれば指示してください。