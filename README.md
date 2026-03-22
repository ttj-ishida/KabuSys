# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
DuckDB をデータレイヤとして用い、データ取得（J-Quants）、ETL、ファクター計算、シグナル生成、バックテスト、ニュース収集などの機能を提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要ワークフローと例）
- 環境変数
- ディレクトリ構成（主要ファイル説明）
- よくあるトラブルとヒント

---

## プロジェクト概要

KabuSys は以下のレイヤを備えた日本株用の自動売買基盤ライブラリです。

- Data Layer（DuckDB）：生データ / 加工データ / 特徴量 / 実行ログ等のスキーマ定義と初期化
- Data Collection：J-Quants API クライアントで日足・財務・カレンダー等を取得・保存
- ETL パイプライン：差分更新、バックフィル、品質チェック（品質チェックモジュールは別途）
- Research & Feature：ファクター計算（Momentum / Volatility / Value 等）、探索ツール（IC、forward returns）
- Strategy：特徴量正規化（features テーブル作成）とシグナル生成（signals テーブルへの書き込み）
- Backtest：バックテストエンジン（インメモリ DuckDB を用いた日次シミュレーション）
- News：RSS からニュース収集・前処理・記事⇆銘柄紐付け（SSRF対策・サイズ制限あり）
- Execution / Monitoring：発注・監視用モジュール（拡張ポイント）

設計方針の要点：
- ルックアヘッドバイアス回避（target_date 時点のデータのみ参照）
- 冪等性（DB への INSERT は ON CONFLICT で衝突を除去）
- 外部依存は最小化（標準ライブラリ優先。ただし DuckDB、defusedxml 等を使用）

---

## 機能一覧

主な提供機能（モジュール単位）

- kabusys.data
  - schema.init_schema(db_path) — DuckDB スキーマの作成・初期化
  - jquants_client.fetch_* / save_* — J-Quants API からの取得・DuckDB 保存（差分／ページネーション対応、リトライ・レート制限）
  - news_collector.fetch_rss / save_raw_news / run_news_collection — RSS 収集・正規化・DB 保存・銘柄抽出
  - pipeline.run_prices_etl 等 — ETL ヘルパ（差分取得・backfill 等）
  - stats.zscore_normalize — クロスセクション Z スコア正規化
- kabusys.research
  - calc_momentum / calc_volatility / calc_value — ファクター計算（prices_daily / raw_financials を参照）
  - calc_forward_returns / calc_ic / factor_summary / rank — 研究用指標・解析ツール
- kabusys.strategy
  - build_features(conn, target_date) — features テーブル作成（Z スコア正規化、ユニバースフィルタ等）
  - generate_signals(conn, target_date, ...) — signals テーブルに BUY/SELL シグナルを生成
- kabusys.backtest
  - run_backtest(conn, start_date, end_date, ...) — インメモリで日次バックテストを実行
  - simulator.PortfolioSimulator — 擬似約定ロジック（スリッページ・手数料考慮）、トレード履歴・日次スナップショット記録
  - metrics.calc_metrics — バックテストの評価指標（CAGR, Sharpe, MaxDD, WinRate 等）
  - backtest CLI: python -m kabusys.backtest.run
- セキュリティ / 安全対策
  - news_collector: SSRF リダイレクト防止、レスポンスサイズ上限、defusedxml を用いた XML パース等
  - jquants_client: レート制限、リトライ、401 時の自動トークン更新

---

## セットアップ手順

前提
- Python 3.10 以上（コード中で X | None などの構文を使用）
- pip / venv 等が利用可能

推奨手順（プロジェクトルートで実行）:

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージのインストール
   - 最小必須: duckdb, defusedxml
   - 例:
     pip install duckdb defusedxml

   （プロジェクトに requirements.txt があればそれを使ってください）

3. パッケージを開発モードでインストール（任意）
   - pip install -e .

4. 環境変数の設定
   - プロジェクトルートに .env を作成するか環境変数を直接設定します（下記「環境変数」参照）。
   - 自動で .env を読み込む仕組みがあります（settings モジュール）。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを抑止できます。

5. DuckDB スキーマ初期化
   - Python REPL で:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()

---

## 環境変数

主に以下が必須／推奨です（settings で参照）:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード（execution 系）
- SLACK_BOT_TOKEN — Slack 通知トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意（デフォルトあり）:
- KABUSYS_ENV — 実行環境 (development|paper_trading|live)（default: development）
- LOG_LEVEL — ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)（default: INFO）
- DUCKDB_PATH — デフォルトの DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite のパス（default: data/monitoring.db）

注意:
- settings モジュールは .env / .env.local を自動で読み込みます（プロジェクトルートの検出: .git or pyproject.toml を基準）。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- 必須変数が未設定の場合、Settings のプロパティ呼び出し時に ValueError を送出します。

---

## 使い方（主要ワークフローと例）

ここでは代表的な操作例を示します。すべて Python から呼び出せます。

1) DuckDB スキーマの初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
conn.close()
```

2) J-Quants から日足を取得して保存（jquants_client を直接利用）
```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,12,31))
saved = jq.save_daily_quotes(conn, records)
print("saved:", saved)
conn.close()
```

3) ニュース収集（RSS）と銘柄紐付け
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コード集合
results = run_news_collection(conn, known_codes=known_codes)
print(results)
conn.close()
```

4) 特徴量ビルド（features テーブル作成）
```python
from kabusys.strategy import build_features
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2024,3,1))
print("features upserted:", n)
conn.close()
```

5) シグナル生成（signals テーブルへの書き込み）
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2024,3,1))
print("signals:", count)
conn.close()
```

6) バックテスト（Python API）
```python
from kabusys.backtest.engine import run_backtest
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
print(result.metrics)
conn.close()
```

7) バックテスト（CLI）
```bash
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --cash 10000000 --db data/kabusys.duckdb
```

8) 研究用ユーティリティ（IC 計算など）
- kabusys.research.calc_forward_returns, calc_ic, factor_summary, rank を使ってファクター検証を行えます。

---

## ディレクトリ構成（主要ファイルと説明）

（プロジェクトの src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動読み込みと Settings クラス（必須変数チェック等）
  - data/
    - __init__.py
    - schema.py — DuckDB スキーマ定義・init_schema / get_connection
    - jquants_client.py — J-Quants API クライアント（取得・保存関数）
    - news_collector.py — RSS 取得・前処理・保存・銘柄抽出
    - pipeline.py — ETL パイプライン（差分取得・バックフィル等）
    - stats.py — zscore_normalize 等の統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py — モメンタム / ボラティリティ / バリュー等のファクター計算
    - feature_exploration.py — forward returns / IC / summary 等の解析
  - strategy/
    - __init__.py
    - feature_engineering.py — features テーブル作成（正規化・ユニバースフィルタ）
    - signal_generator.py — features+ai_scores から final_score を計算して signals を生成
  - backtest/
    - __init__.py
    - engine.py — run_backtest の実装（インメモリコピー・日次ループ等）
    - simulator.py — PortfolioSimulator（擬似約定・履歴記録）
    - metrics.py — バックテスト評価指標
    - run.py — CLI エントリポイント（python -m kabusys.backtest.run）
    - clock.py — 将来拡張用の模擬時計
  - execution/  — 発注関連（拡張ポイント）
  - monitoring/ — 監視・アラート（拡張ポイント）

各モジュールは docstring で仕様・設計方針を明記しており、関数は DuckDB 接続（duckdb.DuckDBPyConnection）を引数に受け取ることが多く、外部副作用を最小化する設計です。

---

## よくあるトラブルとヒント

- 環境変数未設定で ValueError が出る場合：
  - settings のプロパティは必須変数がないとエラーになります。JQUANTS_REFRESH_TOKEN 等を設定してください。
- DuckDB スキーマ未初期化：
  - init_schema() を呼んでテーブルを作成してください。get_connection() は既存 DB に接続するだけでスキーマ作成はしません。
- J-Quants リクエストで 401 が出る：
  - jquants_client はリフレッシュトークンから id_token を取得する実装を持ち、自動でリトライします。refresh token が無効であれば更新してください。
- ニュース収集で XML パースエラー：
  - RSS の XML が不正な場合は警告を出して空結果を返します。ソース単位で失敗しても他ソースは継続します。
- テスト時の .env 自動読み込みを無効化：
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを抑止します。

---

この README はコードベース（src/kabusys）から抽出した主要機能と使い方に基づき記述しています。細かな実装仕様（StrategyModel.md, DataPlatform.md, BacktestFramework.md 等）や追加のユーティリティは各モジュールの docstring を参照してください。必要であれば、.env.example のテンプレートやサンプルワークフローのノート（cron / CI 用）も作成できます。必要な場合はお知らせください。