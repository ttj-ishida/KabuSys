# KabuSys

日本株向け自動売買・データプラットフォームのコアライブラリ（KabuSys）のリポジトリ用 README。

この README はソースコード（src/kabusys 以下）を元に機能概要、セットアップ、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買・データ基盤向けライブラリ群です。  
主に以下の役割を想定しています。

- J-Quants API からの市場データ（株価日足・財務データ・市場カレンダー）の取得と DuckDB への冪等保存
- RSS ベースのニュース収集と前処理・銘柄抽出
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 研究（ファクター計算、将来リターン、IC 計算、統計サマリ）
- ETL（差分取得、バックフィル、品質チェック）
- DuckDB スキーマ定義・監査ログ用スキーマ
- （将来的に）戦略/発注/監視モジュールのためのインターフェース

設計上のポイント:
- DuckDB を主要なローカル DB として利用し、SQL と Python（標準ライブラリ中心）で処理を記述
- J-Quants など外部 API 呼び出しはレート制御・リトライ・トークン自動更新を実装
- ETL・保存処理は可能な限り冪等（ON CONFLICT / DO UPDATE / DO NOTHING）に実装
- 研究・特徴量計算は本番発注系に影響を与えない（読み取り専用）

---

## 機能一覧（主なモジュール）

- kabusys.config
  - .env / 環境変数の自動読み込み（プロジェクトルート検出）と設定ラッパー
  - 必須環境変数の取得ユーティリティ

- kabusys.data
  - jquants_client: J-Quants API クライアント（ページネーション、レート制御、リトライ、トークン更新）
  - schema: DuckDB スキーマ定義 & 初期化（Raw / Processed / Feature / Execution 層）
  - pipeline: ETL パイプライン（差分取得・backfill・品質チェック）
  - news_collector: RSS 取得・前処理・DB 保存・銘柄抽出（SSRF対策、gzip制御、XML パース安全化）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - calendar_management: 市場カレンダー更新 & 営業日判定ユーティリティ
  - audit: 監査ログ（signal → order → execution のトレーサビリティ用スキーマ）

- kabusys.research
  - factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman rank）計算、ファクター統計サマリ
  - data.stats: Zスコア正規化等の統計ユーティリティ（外部依存を極力排除）

- kabusys.strategy, kabusys.execution, kabusys.monitoring
  - プレースホルダ（将来的な戦略・発注・監視ロジック用）

---

## セットアップ手順

前提:
- Python 3.10 以上を推奨（`X | Y` の型表記や typing の使用があるため）
- ネットワーク接続（J-Quants / RSS）

1. リポジトリをクローン
   - git clone ...（通常の手順）

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (UNIX)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージのインストール
   - 最低必要パッケージ（例）
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml
   - 開発用にローカルパッケージとしてインストールする場合:
     - pip install -e .

   （プロジェクトに requirements.txt があればそれを使用してください）

4. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）が検出されると、自動的に `.env` および `.env.local` が読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須環境変数（config.Settings 参照）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
     - SLACK_BOT_TOKEN — Slack 通知用（必須）
     - SLACK_CHANNEL_ID — Slack チャネル ID（必須）
   - 任意 / デフォルト値:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG|INFO|...) — デフォルト: INFO
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db

   - サンプル .env:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

5. DuckDB スキーマ初期化（任意な初期化）
   - Python REPL / スクリプトで init_schema を実行して DB ファイルを初期化します（親ディレクトリが無ければ自動作成されます）。

---

## 使い方（簡易例）

以下は主要なユースケースの最小実行例です。実行は Python スクリプトまたは対話環境で行えます。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

# ファイルベース DB を初期化（デフォルト path は設定で指定）
conn = init_schema("data/kabusys.duckdb")
# conn は duckdb.DuckDBPyConnection インスタンス
```

2) 日次 ETL の実行（J-Quants からの差分取得 → 保存 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を指定することも可
print(result.to_dict())       # ETLResult の概要が得られる
```

3) ニュース収集ジョブの実行
```python
from kabusys.data.news_collector import run_news_collection

# known_codes を与えると記事 -> 銘柄紐付けを行う
known_codes = {"7203", "6758"}  # 例: 有効な銘柄コードセット
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: 新規保存件数}
```

4) 研究用ファクター計算/IC 計算
```python
from kabusys.research import calc_momentum, calc_forward_returns, calc_ic

# conn は DuckDB 接続、target_date は datetime.date
momentum = calc_momentum(conn, target_date)
forward = calc_forward_returns(conn, target_date, horizons=[1,5,21])
ic = calc_ic(momentum, forward, factor_col="mom_1m", return_col="fwd_1d")
print(ic)
```

5) J-Quants から直接データ取得（テスト／バッチ）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements

quotes = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
financials = fetch_financial_statements(date_from=date(2023,1,1), date_to=date(2024,1,1))
```

注意点:
- jquants_client は内部で自動的に ID トークンを取得/リフレッシュします（settings.jquants_refresh_token が必要）。
- network/HTTP エラーは再試行ロジックやレート制限の影響で挙動します。ログを有効にして詳細を確認してください。

---

## 主要 API（抜粋）

- kabusys.config.settings
  - settings.jquants_refresh_token / kabu_api_password / slack_bot_token / slack_channel_id / duckdb_path / env / is_live など

- kabusys.data.schema
  - init_schema(db_path) -> DuckDB 接続
  - get_connection(db_path) -> DuckDB 接続（スキーマ初期化は行わない）

- kabusys.data.jquants_client
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, ... ) -> ETLResult
  - run_prices_etl / run_financials_etl / run_calendar_etl など個別ジョブ

- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30) -> list[NewsArticle]
  - save_raw_news(conn, articles) -> list[new_ids]
  - run_news_collection(conn, sources=None, known_codes=None, timeout=30) -> dict

- kabusys.research
  - calc_momentum(conn, target_date)
  - calc_volatility(conn, target_date)
  - calc_value(conn, target_date)
  - calc_forward_returns(...)
  - calc_ic(...)
  - factor_summary(...)
  - zscore_normalize(...)

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意 / 推奨:
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視用 DB)
- KABUSYS_ENV (development|paper_trading|live)
- LOG_LEVEL (DEBUG|INFO|...)

自動 .env 読み込み:
- プロジェクトルートを基準に `.env` と `.env.local` を読み込みます。
- テスト等で自動ロードを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ログ・デバッグ

- 各モジュールは標準 logging を利用しています。実行スクリプト側で logging.basicConfig(level=...) を設定することで詳細ログを取得できます。
- 設定は環境変数 LOG_LEVEL（Settings.log_level）でも制御できます。

---

## ディレクトリ構成

以下は主要ファイル・モジュールの一覧（src/kabusys 以下）です。実際のリポジトリには他ファイルが追加されている可能性があります。

- src/
  - kabusys/
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
      - factor_research.py
      - feature_exploration.py
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

各モジュールの役割は前述の「機能一覧」を参照してください。

---

## テスト・開発に関する注意

- 自動で .env を読み込む仕組みはプロジェクトルート検出に依存します。ユニットテストなどで環境を独立させたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使い、テストコード側で os.environ をセットしてください。
- DuckDB 接続はスレッド/プロセス設計に注意が必要です。長時間稼働バッチや並列ジョブでは接続の管理とトランザクションの取り扱いを明確にしてください。

---

## 貢献・ライセンス

（ここではソースにライセンス情報が含まれていないため記載していません。リポジトリルートに LICENSE がある場合はそちらを参照してください。）

---

README の内容はコードベース（src/kabusys）を元に手早く使い始められるように要点をまとめています。さらに詳しい運用手順（運用 cron / systemd ジョブ、Slack 通知の詳細、kabu ステーションとの発注フロー等）は別途運用ドキュメントにまとめることを推奨します。