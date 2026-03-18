# KabuSys

日本株向け自動売買基盤のライブラリ（KabuSys）の README。  
本ドキュメントはリポジトリ内のコード構成と主要な使い方、セットアップ手順をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株のデータ収集・ETL、ファクター計算、ニュース収集、監査ログ（発注→約定のトレーサビリティ）などを提供する自動売買基盤のライブラリ群です。主に以下を目的としています。

- J-Quants API からのデータ取得（株価日足・財務・市場カレンダー）
- DuckDB を用いたデータの永続化（Raw / Processed / Feature / Execution 層）
- 日次 ETL パイプライン（差分更新・バックフィル・品質チェック）
- ニュース RSS 収集と銘柄紐付け
- ファクター（モメンタム・バリュー・ボラティリティ等）計算と研究ユーティリティ
- 発注・監査ログ用のスキーマ（監査トレース）

設計上、ETL / データ処理・研究系モジュールは本番口座の発注 API に直接アクセスしないようになっており、冪等性やレート制御、基本的なセキュリティ対策（SSRF対策・XML防御など）を考慮しています。

---

## 主な機能一覧

- 環境変数設定の自動読み込み（`.env`, `.env.local`）
- J-Quants API クライアント
  - トークン自動リフレッシュ
  - ページネーション対応、レート制限（120 req/min）順守、再試行ロジック
- DuckDB スキーマ定義・初期化（raw_prices / prices_daily / features / audit 等）
- ETL パイプライン（差分更新、バックフィル、品質チェック）
- 品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS -> raw_news / news_symbols）
  - URL 正規化、トラッキング除去、SSRF/サイズ/XML攻撃対策
- ファクター計算（モメンタム / ボラティリティ / バリュー 等）
- 研究ユーティリティ（将来リターン計算、IC 計算、Zスコア正規化 等）
- 監査ログスキーマ（signal_events / order_requests / executions）と初期化

---

## 前提・依存パッケージ

最低限必要な Python パッケージ（一例）:

- duckdb
- defusedxml

必要に応じて他のパッケージ（例: slack SDK など）を追加してください。  
仮に最低限だけインストールする例:

```bash
python -m pip install duckdb defusedxml
```

（プロジェクトで requirements.txt / pyproject.toml がある場合はそちらを利用してください）

---

## 環境変数（主なキー）

以下はコード内で参照される環境変数の一覧（必須は README 内で明記）：

必須（Settings._require により未設定で例外）:
- JQUANTS_REFRESH_TOKEN (J-Quants のリフレッシュトークン)
- KABU_API_PASSWORD (kabuステーション API パスワード)
- SLACK_BOT_TOKEN (Slack 通知用トークン)
- SLACK_CHANNEL_ID (Slack チャネル ID)

オプション / デフォルトあり:
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development / paper_trading / live、デフォルト: development)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化できます（テスト用途）

例として、プロジェクトルートに `.env` を置くことで自動的に読み込まれます（プロジェクトルートは .git または pyproject.toml を基準に検出）。

簡単な `.env` の例（ファイル名: .env）:

```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（ローカルでの開発向け）

1. リポジトリをクローンする

```bash
git clone <repo-url>
cd <repo-dir>
```

2. Python 仮想環境を作成・有効化（推奨）

```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
.\.venv\Scripts\activate   # Windows
```

3. 依存パッケージをインストール

（最小構成の例）
```bash
python -m pip install --upgrade pip
python -m pip install duckdb defusedxml
```

4. 環境変数を設定（.env をプロジェクトルートに配置する、または OS 環境変数で設定）
   - 上記「環境変数」セクション参照

5. DuckDB スキーマを初期化（例: settings.duckdb_path を使用）

Python スクリプトから:

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)  # ファイルを自動作成して全テーブルを作る
conn.close()
```

メモリ DB を使ってテストする場合:

```python
from kabusys.data.schema import init_schema
conn = init_schema(":memory:")
```

---

## 使い方（主なユースケース例）

以下はいくつかの典型的な利用方法のサンプルです。

1) 日次 ETL の実行（市場カレンダー・株価・財務の差分取得 + 品質チェック）

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

# DB 初期化（既に作成済みならスキップ可）
conn = init_schema(settings.duckdb_path)

# ETL 実行（target_date を指定しなければ今日）
result = run_daily_etl(conn)

print(result.to_dict())
conn.close()
```

run_daily_etl は J-Quants トークンキャッシュを内部で使い自動的に API 呼び出しを行います。テストやカスタムトークン注入のため id_token を渡すことも可能です。

2) ニュース収集ジョブを単独で実行

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes を与えると本文から銘柄コード抽出して news_symbols を作る
res = run_news_collection(conn, known_codes={"7203", "6758", "9984"})
print(res)  # {source_name: saved_count}
```

3) ファクター計算 / 研究ユーティリティ（例: モメンタム計算）

```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
from kabusys.data.stats import zscore_normalize

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2024, 1, 31)
mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)

# 将来リターンの取得（翌日・5日・21日）
fwd = calc_forward_returns(conn, target, horizons=[1,5,21])

# IC の例（mom_1m と fwd_1d の相関）
ic = calc_ic(mom, fwd, "mom_1m", "fwd_1d")
print("IC:", ic)

# Zスコア正規化
normed = zscore_normalize(mom, ["mom_1m", "ma200_dev"])
```

4) J-Quants API 直接利用（データ取得・保存）

```python
from kabusys.data import jquants_client as jq
from kabusys.config import settings
import duckdb

id_token = jq.get_id_token()  # settings.jquants_refresh_token を使用して取得
records = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2023,1,1), date_to=date(2023,12,31))

conn = duckdb.connect("data/kabusys.duckdb")
saved = jq.save_daily_quotes(conn, records)
print("saved", saved)
```

---

## 開発・テスト時のヒント

- 環境変数自動読み込みを無効にしたい場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください（テスト等で .env を読み込ませたくない場合）。
- テスト用にインメモリ DuckDB を使う: db_path=":memory:" を渡すと便利です。
- ログレベルは LOG_LEVEL 環境変数で制御できます（INFO がデフォルト）。
- J-Quants の API はレート制限が厳格なので、大量取得時は pipeline の差分ロジック・ページネーションを活用してください。

---

## ディレクトリ構成（主要ファイルの説明）

以下はコードベースの主要なファイルとディレクトリです（src/kabusys 以下）。

- __init__.py
  - パッケージ宣言、バージョン情報

- config.py
  - 環境変数読み込み・Settings クラス（J-Quants トークンや DB パス、ログレベル等）

- data/
  - __init__.py
  - jquants_client.py：J-Quants API クライアント（取得・保存ロジック、レート制御、リトライ）
  - news_collector.py：RSS ニュース収集・前処理・DB 保存（SSRF対策・サイズ制限・XML防御）
  - schema.py：DuckDB のスキーマ定義・初期化（Raw/Processed/Feature/Execution 層）
  - stats.py：汎用統計ユーティリティ（zscore_normalize）
  - pipeline.py：ETL パイプライン（差分取得・品質チェックの統合）
  - features.py：特徴量ユーティリティ（エクスポート）
  - calendar_management.py：市場カレンダー管理（is_trading_day 等のユーティリティ）
  - audit.py：監査ログ（signal_events / order_requests / executions）初期化
  - etl.py：ETL 結果データクラスの公開

- research/
  - __init__.py：research API の再エクスポート
  - factor_research.py：モメンタム・ボラティリティ・バリュー計算
  - feature_exploration.py：将来リターン計算・IC/統計サマリー

- strategy/
  - __init__.py（将来の戦略モデルやシグナル生成を置くためのパッケージ）

- execution/
  - __init__.py（発注実行やブローカ API アダプタを置く場所）

- monitoring/
  - __init__.py（モニタリング関連モジュールを配置予定）

---

## ライセンス・貢献

ライセンス情報やコントリビュート方法はリポジトリルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

---

## 最後に（注意点）

- 本ライブラリには実トレードにつながる機能が含まれうるため、live 環境で利用する際は十分なテストとリスク管理を行ってください。
- 設定ミスで API トークンや証券会社の実取引を誤って発動しないように、開発時は KABUSYS_ENV を `development` または `paper_trading` に設定してください。
- DuckDB のバージョンによってはサポートされない構文や制約があるため、schema モジュールの DDL 実行時にエラーが出る場合は DuckDB のバージョン確認を行ってください。

---

必要なら README に載せるコマンド例や、より詳細な API リファレンス（各関数の引数説明・戻り値）を追加で作成します。どの部分を詳細化したいか教えてください。