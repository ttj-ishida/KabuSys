# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）。  
データ取得（J‑Quants）、DuckDBベースのスキーマ管理、ETLパイプライン、ニュース収集、特徴量・ファクター計算、監査ログなどを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は以下を目的とした Python パッケージです。

- J‑Quants API から株価・財務・カレンダー等を安全に取得して DuckDB に保存する（レートリミット・リトライ・トレーサビリティ対応）
- raw → processed → feature → execution といった多層スキーマ（DuckDB）を定義・初期化する
- ETL（差分更新・バックフィル・品質チェック）パイプラインを提供
- RSS からニュースを収集し、銘柄紐付けまで行うニュースコレクター
- 研究（Research）用途のファクター計算（モメンタム/バリュー/ボラティリティ等）とユーティリティ
- 監査ログ（signal→order→execution の連鎖）用スキーマとユーティリティ

設計上、データ取得や ETL の処理は本番発注系（ブローカーAPI）には依存せず、DuckDB と標準ライブラリ・最小限の外部ライブラリで完結するようになっています。

---

## 主な機能一覧

- 環境変数管理（.env 自動読み込み、必須チェック）
- J‑Quants API クライアント
  - ページネーション対応、レートリミット、指数バックオフ、トークン自動更新
  - 日足 / 財務 / マーケットカレンダー取得関数
  - DuckDB へ冪等的に保存する save_* 関数
- DuckDB スキーマ定義 / 初期化（data.schema.init_schema）
- ETL パイプライン（差分更新・バックフィル・品質チェック）
  - run_daily_etl（カレンダー → 株価 → 財務 → 品質チェック）
- ニュース収集（RSS）、前処理、記事ID生成、raw_news 保存、銘柄抽出
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 研究（research）モジュール：ファクター計算（calc_momentum, calc_value, calc_volatility 等）、IC 計算、Zスコア正規化

---

## 必要要件

- Python 3.10+
- 必要なパッケージ（最小）
  - duckdb
  - defusedxml

インストール例（仮想環境推奨）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# パッケージを editable インストールできる場合:
# pip install -e .
```

（プロジェクトに requirements.txt があればそちらを使用してください。）

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を構築、依存をインストールします。

2. 環境変数を準備します。プロジェクトルートに `.env`（あるいは `.env.local`）を作成すると、自動的に読み込まれます（必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

例（.env）:

```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

必須のキー（Settings が要求するもの）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

3. DuckDB スキーマを初期化します（ファイル DB を使う場合は `DUCKDB_PATH` を確認）:

Python で実行例:

```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)  # 指定パスに DB とテーブルを生成
conn.close()
```

---

## 使い方（クイックスタート）

以下は主要ユースケースの簡単なコード例です。

- DB 初期化（先述）

- 日次 ETL 実行

```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # 引数で target_date, id_token などを指定可能
print(result.to_dict())
conn.close()
```

- ニュース収集ジョブ実行

```python
from kabusys.data.schema import get_connection
from kabusys.data.news_collector import run_news_collection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
# known_codes を与えると記事に含まれる4桁銘柄コードを抽出して紐付けする
known_codes = {"7203", "6758"}  # 有効銘柄コードセット（実運用では全銘柄セットを用意）
res = run_news_collection(conn, known_codes=known_codes)
print(res)
conn.close()
```

- 研究用ファクター計算

```python
from kabusys.data.schema import get_connection
from kabusys.research import calc_momentum, calc_value, calc_volatility
from datetime import date

conn = get_connection("data/kabusys.duckdb")
target = date(2024, 1, 31)
mom = calc_momentum(conn, target)
val = calc_value(conn, target)
vol = calc_volatility(conn, target)
# さらに zscore_normalize を使って正規化可能
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
conn.close()
```

- J‑Quants からのデータ取得（個別呼び出し）

```python
from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements, get_id_token

token = get_id_token()  # settings.jquants_refresh_token を使用
records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
# DuckDB に保存するなら save_* を利用
from kabusys.data.jquants_client import save_daily_quotes
from kabusys.data.schema import get_connection
conn = get_connection("data/kabusys.duckdb")
save_daily_quotes(conn, records)
```

---

## よく使う API と説明（抜粋）

- kabusys.config.settings  
  環境変数から取得する設定オブジェクト。主要プロパティ:
  - jquants_refresh_token, kabu_api_password, kabu_api_base_url
  - slack_bot_token, slack_channel_id
  - duckdb_path, sqlite_path
  - env, log_level, is_live / is_paper / is_dev

- kabusys.data.schema
  - init_schema(db_path) : DuckDB スキーマを初期化して接続を返す
  - get_connection(db_path) : 既存 DB への接続を返す

- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...), fetch_financial_statements(...), fetch_market_calendar(...)
  - save_daily_quotes(conn, records), save_financial_statements(conn, records), save_market_calendar(conn, records)

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, id_token=None, ...): ETL の高レベル実行

- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)
  - save_raw_news(conn, articles)
  - run_news_collection(conn, sources=None, known_codes=None, timeout=30)

- kabusys.research
  - calc_momentum(conn, target_date), calc_volatility(...), calc_value(...)
  - calc_forward_returns(conn, target_date, horizons=None)
  - calc_ic(factor_records, forward_records, factor_col, return_col)
  - factor_summary(records, columns)

- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5)

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) : J‑Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) : kabuステーション API のパスワード
- KABU_API_BASE_URL : kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) : 通知用 Slack ボットトークン
- SLACK_CHANNEL_ID (必須) : Slack チャネル ID
- DUCKDB_PATH : DuckDB DB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視系用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV : development | paper_trading | live（デフォルト: development）
- LOG_LEVEL : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

補足:
- 自動 .env ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成

以下は主要ファイル・モジュールの一覧（コードベースから抜粋）:

- src/kabusys/
  - __init__.py
  - config.py         -- 環境変数 / 設定
  - data/
    - __init__.py
    - jquants_client.py    -- API クライアント & 保存ロジック
    - news_collector.py    -- RSS ニュース収集と保存
    - schema.py            -- DuckDB スキーマ定義 / init_schema
    - stats.py             -- 統計ユーティリティ（zscore_normalize 等）
    - pipeline.py          -- ETL パイプライン（run_daily_etl 等）
    - features.py          -- features の公開インターフェース
    - calendar_management.py -- calendar 更新 / 営業日判定ユーティリティ
    - audit.py             -- 監査ログ用スキーマ初期化
    - etl.py               -- ETLResult 再エクスポート
    - quality.py           -- データ品質チェック
  - research/
    - __init__.py
    - feature_exploration.py -- 将来リターン・IC・summary
    - factor_research.py     -- momentum/value/volatility 計算
  - strategy/             -- 戦略関連（初期化済み）
    - __init__.py
  - execution/            -- 発注/執行関連（初期化済み）
    - __init__.py
  - monitoring/           -- 監視・モニタリング（初期化済み）

---

## トラブルシューティング・注意点

- DuckDB ファイルの親ディレクトリは init_schema 内で自動作成されますが、ファイルパーミッションなどが原因で失敗する場合があります。権限を確認してください。
- J‑Quants API のレート制限（120 req/min）を守るため、fetch_* は内部でスロットリングを行います。大量取得の際は時間がかかります。
- news_collector は defusedxml を使用して XML に対する安全対策を行っています。RSS のパースエラーはロギングされ空リストが返されます。
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml）を起点に探索します。パッケージを別場所へコピーした場合、自動読み込みが期待どおりに動作しないことがあります。この場合、環境変数を手動で設定してください。
- settings.env の値が不正な場合（例: KABUSYS_ENV に未知値を入れる等）は ValueError が発生します。

---

## 貢献・拡張

- 新しいデータソースの追加（jquants_client に類似の fetch/save 関数を実装）
- strategy / execution 層の接続（kabu API を使った発注実装等）
- 品質チェックや特徴量の追加・改善

---

必要であれば、README に「実行可能スクリプト／CLI」「CI 設定」「テストの実行方法（pytest 等）」のセクションを追加します。どの情報を追記したいか教えてください。