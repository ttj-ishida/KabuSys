# KabuSys

日本株向け自動売買 / データプラットフォーム用の Python ライブラリ群です。  
DuckDB を中心としたローカルデータレイク、J‑Quants からのデータ取得、ファクター計算、シグナル生成、ニュース収集、監査ログ等の機能を提供します。

---

## プロジェクト概要

KabuSys は以下の層を備えた設計になっています。

- Data layer（DuckDB）
  - J‑Quants から取得した生データ（株価、財務、カレンダー、ニュース等）の保存・スキーマ定義
  - ETL パイプライン（差分取得／バックフィル／品質チェック）
- Research / Feature layer
  - ファクター計算（Momentum / Volatility / Value 等）
  - クロスセクション正規化（Z スコア）
  - 特徴量探索（Forward returns / IC / Summary）
- Strategy layer
  - 特徴量と AI スコアを統合して final_score を計算
  - BUY / SELL シグナル生成（冪等）
- Execution / Audit
  - シグナル → 注文 → 約定 のトレーサビリティ（監査ログ）
- News collector
  - RSS 収集、前処理、銘柄コード抽出、DB への冪等保存（SSRF / XML 攻撃対策あり）

想定用途は「ローカルで DuckDB に市場データを蓄積し、研究・戦略実行に使う」ワークフローです。発注（ブローカー送信）などは別層で行う想定となっており、strategy や data モジュールは発注 API に直接依存しません。

---

## 主な機能一覧

- DuckDB スキーマ定義と初期化（kabusys.data.schema.init_schema）
- J‑Quants API クライアント（認証リフレッシュ、ページネーション、レート制限、リトライ）
  - 日足（OHLCV）・財務データ・市場カレンダー取得
  - 取得データの DuckDB への冪等保存（ON CONFLICT で更新）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
- ファクター計算（research.factor_research）
  - momentum, volatility, value を計算
- 特徴量エンジニアリング（strategy.feature_engineering）
  - ユニバースフィルタ（最低株価・流動性）、Z スコア正規化、features テーブルへの upsert
- シグナル生成（strategy.signal_generator）
  - momentum/value/volatility/liquidity/news を重み付け統合し final_score を算出
  - Bear レジーム抑制、SELL（エグジット）判定、signals テーブルへの書き込み
- ニュース収集（data.news_collector）
  - RSS 取得、テキスト前処理、記事ID生成、raw_news 保存、銘柄紐付け
  - SSRF/XML の防御ロジック、応答サイズ制限
- カレンダー管理（data.calendar_management）
  - 営業日判定、前後営業日の取得、夜間カレンダー更新ジョブ
- 監査ログ（data.audit）
  - signal_events / order_requests / executions 等のテーブル定義（トレーサビリティ）

---

## 前提 / 必要環境

- Python 3.10 以上（コードは | 型注釈などを使用）
- 必須 Python パッケージ（一例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J‑Quants API、RSS ソース）および有効な J‑Quants リフレッシュトークン

（パッケージはプロジェクトの pyproject.toml / requirements に合わせてください）

---

## 環境変数（必須／推奨）

以下の環境変数を設定してください（README 内では大文字で表記）。

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意（デフォルトあり）:
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視用、デフォルト: data/monitoring.db)
- KABUSYS_ENV (development / paper_trading / live。デフォルト: development)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL。デフォルト: INFO)

自動読み込み:
- パッケージ起動時にプロジェクトルート（.git または pyproject.toml の存在する親ディレクトリ）から `.env` と `.env.local` を自動で読み込みます。
  - 読み込み順: OS 環境 > .env.local > .env
  - 無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## セットアップ手順（簡易）

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトに pyproject.toml があれば pip install -e . / pip install -r requirements.txt）

3. 環境変数をセット
   - .env または環境変数で必須値を設定してください（上記参照）。

4. DuckDB スキーマ初期化（例: スクリプトまたは Python REPL）
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ":memory:" も可
   conn.close()
   ```

---

## 使い方（主要な例）

以下はライブラリ関数を直接呼ぶ最小例です。実運用ではログ設定、例外処理、スケジューラ（cron 等）を用いてください。

1) DB 初期化
```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL 実行（J‑Quants から差分取得して保存）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定することも可能
print(result.to_dict())
```

3) 特徴量作成（features のビルド）
```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
count = build_features(conn, date.today())  # target_date に調整済み営業日を渡す
print("features upserted:", count)
```

4) シグナル生成
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
num_signals = generate_signals(conn, date.today())  # threshold, weights を渡せる
print("signals written:", num_signals)
```

5) ニュース収集（RSS）と保存
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes: 有効な銘柄コードセットを渡すと自動で銘柄紐付けを行う
results = run_news_collection(conn, known_codes={"7203","6758"})
print(results)  # 各ソースごとの新規保存件数
```

6) カレンダー更新ジョブ（夜間）
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("calendar saved:", saved)
```

---

## 注意点 / 実装上の設計・運用メモ

- 環境変数は Settings クラス（kabusys.config.Settings）で厳格に検証されるため、未設定・不正値は実行時に ValueError となります。
- J‑Quants クライアントは内部でレート制限（120 req/min）とリトライ（指数バックオフ）を実装しています。401 は自動でリフレッシュを試みます。
- ETL は差分取得＋バックフィル（デフォルト 3 日）を行い、API の後出し修正をある程度吸収します。
- SQL の INSERT は冪等性を念頭に ON CONFLICT （DuckDB の手法）で実装されています。
- News collector は SSRF 対策、XML 攻撃対策（defusedxml）、レスポンスサイズ制限を備えています。
- Strategy 側はルックアヘッドバイアス回避のため、target_date 時点までのデータのみを使用します。
- データベースの初期化は init_schema() を最初に一度実行してください。get_connection() は既存 DB への接続のみを行います。

---

## ディレクトリ構成（主要ファイル）

（プロジェクト src/kabusys 以下の主要モジュール/ファイル）

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
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - execution/
    - __init__.py
  - monitoring/  (パッケージ名は __all__ に含まれるが省略可能)

各ファイルはコメントドキュメントに処理フロー・設計方針・制約が書かれているため、実装の仕様確認は該当ファイルを参照してください。

---

## 開発・テスト時のヒント

- .env の自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（ユニットテストなどで有用）。
- jquants_client の _request はネットワークリトライやトークンリフレッシュを行うため、テストでは get_id_token / _request をモックすると安定します。
- news_collector._urlopen をモックして外部ネットワーク呼び出しを差し替え可能です。
- DuckDB は ":memory:" を指定してインメモリ DB を使えるため、単体テストで高速に検証できます。

---

もし README に追加したい利用シナリオ（Cron 設定例、監視パターン、Slack 通知連携手順など）があれば、必要に応じて追記します。