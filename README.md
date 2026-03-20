# KabuSys — 日本株自動売買プラットフォーム

KabuSys は日本株向けのデータ収集・特徴量生成・シグナル生成・監査ログまでを想定した自動売買基盤の一部実装です。J-Quants API や RSS ニュース、DuckDB を利用した ETL と戦略処理の主要コンポーネントを含みます。

主な目的:
- 市場データ・財務データ・ニュースの差分取得と永続化（DuckDB）
- 研究用ファクターの計算・正規化（research）
- 戦略シグナルの生成（strategy）
- ニュース収集と記事—銘柄紐付け（data.news_collector）
- 発注・約定・ポジションなど監査ログ設計（data.audit / schema）

---

## 機能一覧

- データ取得（J-Quants API）
  - 株価日足（OHLCV）
  - 財務データ（四半期 BS/PL）
  - JPX マーケットカレンダー
  - レート制限・リトライ・トークン自動リフレッシュ対応

- ETL（差分更新）
  - 市場カレンダー、株価、財務データの差分取得、保存
  - backfill による後出し修正対処
  - 品質チェック（quality モジュール経由、オプション）

- データストア（DuckDB）
  - Raw / Processed / Feature / Execution 層のスキーマを定義
  - 冪等（ON CONFLICT）での保存処理

- 研究・特徴量計算（research）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン・IC（Spearman）・統計サマリー

- 特徴量エンジニアリング（strategy.feature_engineering）
  - ユニバースフィルタ（最低株価・流動性）
  - Z スコア正規化・クリップ・features テーブルへの UPSERT

- シグナル生成（strategy.signal_generator）
  - 複数コンポーネント（momentum/value/volatility/liquidity/news）の統合スコア
  - Bear レジーム抑制、BUY/SELL シグナル生成、SELL はエグジット条件に基づく
  - signals テーブルへの日付単位置換（トランザクション）

- ニュース収集（data.news_collector）
  - RSS フィードの取得・前処理・重複排除・記事ID生成（正規化URLの SHA-256）
  - SSRF / XML Bomb / レスポンスサイズ制限等の安全対策
  - news_articles / news_symbols への冪等保存

- カレンダー管理（data.calendar_management）
  - market_calendar の管理・営業日判定・前後営業日検索

- 監査ログ（data.audit）
  - signal → order_request → execution の UUID 連鎖によるトレーサビリティ

---

## 必要条件

- Python 3.10+
- 必要な主要パッケージ（例）
  - duckdb
  - defusedxml
（プロジェクトの pyproject.toml / requirements.txt があればそちらを優先してください）

---

## インストール（開発時）

1. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存をインストール
   - pip install -r requirements.txt
   - もしくはプロジェクトを editable インストール:
     - pip install -e .

※ requirements.txt / pyproject.toml がない場合は最低限 duckdb と defusedxml を入れてください。
例: pip install duckdb defusedxml

---

## 環境変数 / 設定

config.Settings クラスで環境変数から設定を読み取ります。自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（CWD に依存しない検出）。読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live) (デフォルト: development)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) (デフォルト: INFO)

例（.env）
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（初回）

1. 仮想環境の作成・依存インストール（上記参照）。
2. 環境変数 (.env) をプロジェクトルートに配置。
3. DuckDB スキーマの初期化:
   Python REPL またはスクリプトから以下を実行します。

   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # :memory: も可
   ```

   これにより必要なテーブルとインデックスが作成されます。

---

## 使い方（主要ワークフロー例）

以下は一連の典型的な操作例です（スクリプト内で実行することを想定）。

1) 日次 ETL の実行（市場カレンダー・株価・財務の差分取得）
```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) 特徴量の構築（features テーブルへ書き込む）
```python
from datetime import date
from kabusys.strategy import build_features
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
```

3) シグナル生成
```python
from datetime import date
from kabusys.strategy import generate_signals
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
n_signals = generate_signals(conn, target_date=date.today())
print(f"signals generated: {n_signals}")
```

4) ニュース収集ジョブ（RSS）
```python
from kabusys.data.news_collector import run_news_collection
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
# known_codes は銘柄コードセット（例: データベースの prices_daily から取得）
known_codes = {"7203", "6758", "9984"}
results = run_news_collection(conn, sources=None, known_codes=known_codes)
print(results)  # {source_name: saved_count}
```

5) 市場カレンダーの夜間更新
```python
from kabusys.data.calendar_management import calendar_update_job
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

---

## 開発者向け API（主要関数）

- kabusys.config.settings — 環境設定アクセス
- kabusys.data.schema.init_schema(db_path) — DuckDB スキーマ初期化
- kabusys.data.pipeline.run_daily_etl(conn, target_date, ...) — 日次 ETL
- kabusys.data.jquants_client.fetch_daily_quotes / save_daily_quotes — 株価取得・保存
- kabusys.data.news_collector.fetch_rss / save_raw_news / run_news_collection — ニュース収集
- kabusys.research.calc_momentum / calc_volatility / calc_value — ファクター計算
- kabusys.strategy.build_features(conn, target_date) — 特徴量構築
- kabusys.strategy.generate_signals(conn, target_date, threshold, weights) — シグナル生成

各関数はドキュメンテーション文字列（docstring）で引数・戻り値・挙動を説明しています。コード上での使用例を参照してください。

---

## 開発・テスト時の注意

- config モジュールはプロジェクトルート（.git または pyproject.toml を含む階層）を自動検出して `.env` / `.env.local` をロードします。テスト実行時に自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- ニュース収集・外部 API 呼び出し部分はネットワーク依存です。ユニットテストでは jquants_client._request、news_collector._urlopen などをモックすることが想定されています。
- DuckDB への接続はスレッドセーフ性やプロセス配置に注意してください（長時間バッチや複数プロセスからの同時書き込みは設計次第で管理が必要です）。

---

## ディレクトリ構成（主要ファイル）

プロジェクトの src/kabusys 以下の主な構成:

- kabusys/
  - __init__.py
  - config.py              — 環境変数 / 設定管理
  - data/
    - __init__.py
    - schema.py            — DuckDB スキーマ定義・初期化
    - jquants_client.py    — J-Quants API クライアント + 保存ユーティリティ
    - pipeline.py          — ETL パイプライン（run_daily_etl など）
    - news_collector.py    — RSS ニュース収集・保存
    - calendar_management.py — 市場カレンダー管理
    - features.py          — zscore_normalize の再エクスポート
    - stats.py             — 統計ユーティリティ（zscore_normalize 等）
    - audit.py             — 監査ログ（signal/order/execution）DDL
    - ...                  — （quality, その他の補助モジュールが想定される）
  - research/
    - __init__.py
    - factor_research.py   — Momentum/Volatility/Value 等の計算
    - feature_exploration.py — IC / forward returns / summary
  - strategy/
    - __init__.py
    - feature_engineering.py — features テーブル作成処理
    - signal_generator.py    — シグナル生成ロジック
  - execution/              — 発注・execution 層（パッケージプレースホルダ）
  - monitoring/            — 監視用コード（プレースホルダ）

（README に含めた以外にも補助モジュールが存在する可能性があります。実装全体はソースツリーを参照してください。）

---

## ライセンス・貢献

本リポジトリのライセンス情報・貢献方法はプロジェクトのルートにある LICENSE / CONTRIBUTING.md を参照してください（存在する場合）。

---

この README はコードの docstring と実装から作成しています。実際に運用する際は本番用の設定値や秘密情報の管理、証券会社 API の接続やリスク管理ルール（ポジション上限・ドローダウン制限等）を必ず整備してください。