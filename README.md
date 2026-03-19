# KabuSys

日本株向けの自動売買プラットフォーム向けライブラリ群（データ取得・ETL・特徴量計算・監査ログ等）です。主に研究環境（ファクター探索）とデータプラットフォーム／ETL、監査・発注レイヤーのユーティリティを提供します。

このリポジトリ内の実装は、J-Quants API や RSS などからのデータ取得、DuckDB を利用したローカル DB スキーマ管理、特徴量計算・品質チェック、ニュース収集、監査ログ用テーブル定義などを含みます。

対応想定 Python バージョン
- Python 3.10 以降（型注釈に | を使用）

主要な依存（例）
- duckdb
- defusedxml
（実行環境に合わせて pip でインストールしてください）

---

## 機能一覧

- 環境設定管理
  - .env ファイルや環境変数を自動読み込み（プロジェクトルート検出）。自動ロード無効化フラグあり。
- データ取得（J-Quants）
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダー取得（ページネーション対応）
  - レート制御（120 req/min）、リトライ、401 時のトークンリフレッシュ処理
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- データパイプライン / ETL
  - 差分更新（最終取得日を参照）、バックフィル、カレンダー先読み
  - ETL 実行結果を ETLResult オブジェクトで返却
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit の各レイヤー用テーブル定義と初期化ユーティリティ
  - 監査ログ用スキーマ（signal / order_request / executions 等）初期化
- データ品質チェック
  - 欠損、スパイク（前日比閾値）、重複、日付不整合 等のチェックを実行
  - QualityIssue 型で検出結果を集約
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（prices_daily, raw_financials を参照）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ
  - Zスコア正規化ユーティリティ
- ニュース収集
  - RSS 収集、前処理（URL 除去・空白正規化）、記事ID生成（正規化 URL の SHA-256 先頭）
  - SSRF 対策、gzip サイズ制限、defusedxml を使った安全な XML パース
  - raw_news / news_symbols への冪等保存
- その他
  - マーケットカレンダー管理（営業日判定、next/prev_trading_day、バッチ更新ジョブ）
  - Audit 用 DB 初期化ユーティリティ

---

## セットアップ手順

1. Python（3.10 以上）を用意します。

2. 必要パッケージをインストールします（プロジェクトに requirements.txt がある場合はそちらを利用してください）。最低限の例:
   ```
   pip install duckdb defusedxml
   ```

3. パッケージを開発編集モードでインストール（任意）:
   ```
   pip install -e .
   ```

4. 環境変数を設定します（`JQUANTS_REFRESH_TOKEN` などが必須）。開発ではプロジェクトルートに `.env` を置いても読み込まれます。自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須（または推奨）環境変数一覧
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUS_API_BASE_URL: kabuステーション API ベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（省略時: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB パス（省略時: data/monitoring.db）
- KABUSYS_ENV: 実行環境 ("development" | "paper_trading" | "live")（省略時: development）
- LOG_LEVEL: ログレベル ("DEBUG" | "INFO" | ...)

例 .env（プロジェクトルート）
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=yyyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（基本例）

以下は Python スクリプトから主要ユーティリティを呼ぶ際のサンプルコードです。

- DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# conn は duckdb.DuckDBPyConnection
```

- 監査スキーマ初期化（既存接続へ）
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn, transactional=True)
```

- 日次 ETL 実行（J-Quants トークンは環境変数経由で取得）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース収集ジョブ実行
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES, extract_stock_codes
from kabusys.data.schema import init_schema

conn = init_schema(":memory:")  # またはファイル DB
known_codes = {"7203", "6758", "9984"}  # 事前に用意した銘柄コードセット
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)
```

- ファクター計算（研究用）
```python
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
target = date(2024, 1, 31)
mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)
fwd = calc_forward_returns(conn, target)
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)
```

- Z-score 正規化
```python
from kabusys.data.stats import zscore_normalize
normalized = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

注意点
- research モジュール（calc_momentum 等）は prices_daily / raw_financials のみを参照し、ネットワークや発注APIにアクセスしません（安全にリサーチできます）。
- jquants_client はレート制御・リトライ等を内蔵していますが、APIキー管理や使用制限は各自で確認してください。
- news_collector は SSRF 対策、受信サイズ制限、XMLパースの安全対策を実装していますが、外部 RSS 利用時は運用上の注意（接続先の信頼性）を行ってください。

---

## よく使う関数・モジュールの説明

- kabusys.config
  - Settings クラス: 環境変数から各種設定を取得（jquants トークン、DB パス等）
  - 自動 .env 読み込み（プロジェクトルートに .env / .env.local があれば読み込み）
- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token（トークン取得）
- kabusys.data.schema
  - init_schema(db_path) : DuckDB の全テーブルを作成して接続を返す
  - get_connection(db_path)
- kabusys.data.pipeline
  - run_daily_etl(conn, target_date, ...) : 日次 ETL（カレンダー・株価・財務・品質チェック）
- kabusys.data.news_collector
  - fetch_rss(url, source) : RSS を取得して記事リストを返す
  - save_raw_news(conn, articles) : raw_news に冪等保存
  - run_news_collection(conn, sources, known_codes) : 統合収集ジョブ
- kabusys.research
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary
- kabusys.data.quality
  - run_all_checks(conn, target_date, ...) : 品質チェック一括実行（QualityIssue のリストを返す）
- kabusys.data.audit
  - init_audit_schema(conn) / init_audit_db(db_path) : 監査ログ用スキーマ初期化

---

## ディレクトリ構成

リポジトリの主要なディレクトリ/ファイル構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント（取得・保存）
    - news_collector.py  — RSS ニュース収集・保存
    - pipeline.py        — ETL パイプライン（run_daily_etl 等）
    - schema.py          — DuckDB スキーマ定義と init_schema
    - stats.py           — 統計ユーティリティ（zscore_normalize）
    - features.py        — 特徴量公開インターフェース（zscore の再エクスポート）
    - calendar_management.py — マーケットカレンダー管理（営業日判定等）
    - audit.py           — 監査ログスキーマ初期化
    - etl.py             — ETLResult の再エクスポート
    - quality.py         — データ品質チェック群
  - research/
    - __init__.py
    - feature_exploration.py  — 将来リターン・IC・summary
    - factor_research.py      — momentum/value/volatility の計算
  - strategy/   — 戦略層（空の初期化ファイルがある）
  - execution/  — 発注/実行層（空の初期化ファイルがある）
  - monitoring/ — 監視関連（初期化ファイル）

（実際のプロジェクトでは README に合わせて tests、scripts、docs 等の追加ディレクトリが存在する可能性があります）

---

## 運用上の注意 / ベストプラクティス

- 秘密情報（トークン、パスワード）は .env に直接コミットしないでください。`.env.example` を用意して必要なキーをドキュメント化するとよいでしょう。
- production（live）では KABUSYS_ENV を "live" に設定し、必ず発注モジュールや監査ログを適切に検証してください。
- ETL 実行時はバックアップやトランザクションの取り扱いに注意してください。init_schema は冪等ですが DB ファイルの取り扱いは運用ポリシーに従ってください。
- J-Quants のレート制限や利用規約に従って運用してください。大量取得時はバックオフやスケジューラ（cron / Airflow 等）を導入してください。

---

必要であれば README にサンプル .env.example、さらに CI / テスト実行方法、デプロイ手順（Dockerfile, systemd unit 例）などを追記できます。どの情報を追加しますか？