# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）。  
DuckDB を中心としたデータレイヤー、J-Quants からのデータ取得・ETL、ニュース収集、特徴量計算（Research）や監査ログ用スキーマ等を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買システムに必要なデータ取得・整形・品質管理・特徴量生成・監査ログの機能群をまとめたライブラリです。主な設計方針は以下です。

- DuckDB をデータベースとして利用（オンディスク / インメモリ両対応）
- J-Quants API を使った株価・財務・マーケットカレンダーの差分取得（レートリミット・リトライ・トークンリフレッシュ対応）
- RSS ベースのニュース収集（SSRF/サイズ/XML 攻撃対策あり）
- ETL パイプライン（差分取得、保存、品質チェック）
- Research 用のファクター計算（モメンタム、ボラティリティ、バリュー等）と評価指標（IC、forward returns）
- 監査ログ用スキーマ（signal → order → execution のトレーサビリティ）
- 設定は環境変数 / .env ファイルから読み込み（自動ロード機構あり）

---

## 機能一覧

- data
  - jquants_client: J-Quants API クライアント（ページネーション、レート制御、リトライ、トークンリフレッシュ）
  - news_collector: RSS 取得・正規化・保存（SSRF 対策、トラッキングパラメータ除去、記事IDの生成）
  - schema: DuckDB スキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
  - pipeline: 日次 ETL（差分取得・保存・品質チェック）
  - calendar_management: 市場カレンダー管理・営業日判定ユーティリティ
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログスキーマ（signal / order_request / executions）
  - stats: 汎用統計ユーティリティ（zscore 正規化等）
- research
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、統計サマリー、rank 等
  - factor_research: momentum / volatility / value 等のファクター計算
- config: 環境変数管理、.env 自動読み込み（プロジェクトルート検出）
- strategy / execution / monitoring: パッケージ枠組み（実装は各プロジェクトで拡張）

---

## セットアップ手順

前提:
- Python 3.9+ を推奨（型ヒントに union 型や typing の使用あり）
- DuckDB と defusedxml 等を依存としてインストール

1. リポジトリをクローンしてプロジェクトルートへ移動（.git または pyproject.toml が存在する場所が自動 .env 検出の基準になります）。

2. 仮想環境を作成・有効化してパッケージをインストール:

   pip を使った例:
   ```
   python -m venv .venv
   source .venv/bin/activate    # Windows: .venv\Scripts\activate
   pip install -U pip
   pip install duckdb defusedxml
   # 開発中にローカル編集するなら
   pip install -e .
   ```

   ※ プロジェクトが pyproject.toml/requirements を持っていればそちらを利用してください。

3. 必要な環境変数を設定するか、プロジェクトルートに `.env` / `.env.local` を作成します。`.env.local` は `.env` を上書きします。自動読み込みはデフォルトで有効です（無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

   必須環境変数（Settings により参照／必須チェックされます）:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID

   任意（デフォルトあり）:
   - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト: data/monitoring.db)
   - KABUSYS_ENV (development / paper_trading / live)
   - LOG_LEVEL (DEBUG / INFO / WARNING / ERROR / CRITICAL)

   サンプル `.env`（例）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=./data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（代表的な例）

以下は Python スクリプトや REPL での利用例です。

- DuckDB スキーマ初期化（デフォルトパスを使う場合）:
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
# ":memory:" を渡してインメモリ DB にすることも可能
```

- 日次 ETL の実行:
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
# 初回は init_schema を呼ぶこと
# conn = schema.init_schema("data/kabusys.duckdb")

result = run_daily_etl(conn)
print(result.to_dict())  # ETLResult を確認
```

- ニュース収集ジョブの実行:
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
# known_codes は銘柄抽出用の有効な銘柄コード集合 (例: {"7203","6758",...})
res = run_news_collection(conn, known_codes={"7203", "6758"})
print(res)  # {source_name: saved_count}
```

- J-Quants から日足をフェッチして保存（テスト目的など）:
```python
from kabusys.data import jquants_client as jq
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=..., date_to=...)
saved = jq.save_daily_quotes(conn, records)
```

- Research モジュールの利用（ファクター計算・IC 等）:
```python
from datetime import date
from kabusys.research import calc_momentum, calc_forward_returns, calc_ic
from kabusys.data import schema, stats

conn = schema.get_connection("data/kabusys.duckdb")
target = date(2024, 1, 31)
mom = calc_momentum(conn, target)
fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
print(ic)
```

- Z-スコア正規化ユーティリティ:
```python
from kabusys.data.stats import zscore_normalize
normalized = zscore_normalize(records, ["mom_1m", "mom_3m", "ma200_dev"])
```

- 監査ログスキーマ初期化:
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/kabusys_audit.duckdb")
```

---

## 設定の詳細

- .env の自動読み込み:
  - プロジェクトルートは __file__ を起点に `.git` または `pyproject.toml` を探索して決定します。CWD に依存しません。
  - 読み込み順序: OS 環境変数 > .env.local > .env
  - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト等で利用）。

- Settings（kabusys.config.settings）で必須値は `_require` によってチェックされ、未設定だと ValueError を投げます。

---

## ディレクトリ構成

主要なファイル・モジュール構成（src 配下）:

- src/kabusys/
  - __init__.py
  - config.py                 # 環境変数 / .env 管理
  - data/
    - __init__.py
    - jquants_client.py       # J-Quants API クライアント（取得・保存）
    - news_collector.py       # RSS ニュース収集・保存
    - schema.py               # DuckDB スキーマ定義・初期化
    - pipeline.py             # ETL パイプライン
    - calendar_management.py  # カレンダー更新・営業日ユーティリティ
    - quality.py              # データ品質チェック
    - stats.py                # 統計ユーティリティ（zscore など）
    - features.py             # features の公開 API（zscore を再エクスポート）
    - etl.py                  # ETL インターフェース（ETLResult 再エクスポート）
    - audit.py                # 監査ログスキーマ（signal/order/execution）
  - research/
    - __init__.py
    - feature_exploration.py  # 将来リターン、IC、summary、rank
    - factor_research.py      # momentum/volatility/value の計算
  - strategy/                  # 戦略関連（拡張用）
  - execution/                 # 発注・実行層（拡張用）
  - monitoring/                # 監視関連（プレースホルダ）

---

## 注意点 / 実装上の特記事項

- jquants_client は API レート（120 req/min）を守るため内部で固定間隔スロットリングを行います。また 408/429/5xx に対する指数バックオフリトライ、401 時のリフレッシュを実装しています。
- news_collector は SSRF・XML Bomb・大容量レスポンスなどに対する防御を実装しています。RSS の最大受信バイト数（デフォルト 10MB）を超える応答は破棄されます。
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE / DO NOTHING）を基本としています。
- 品質チェックは Fail-Fast ではなく問題を一覧で返す設計です。呼び出し元が重大度に応じた対応を行ってください。
- audit スキーマは UTC タイムゾーンを前提としています（init_audit_schema は SET TimeZone='UTC' を実行します）。

---

## 開発・貢献

- コードは src パッケージ構成です。ローカル開発時は `pip install -e .` してから編集・テストしてください。
- テストや CI のセットアップは本リポジトリに合わせて作成してください（テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用すると便利です）。

---

必要であれば、README に実行例（cron ジョブの例、Dockerfile、systemd ユニット、Slack 通知の利用方法 など）を追加できます。何を追加したいか教えてください。