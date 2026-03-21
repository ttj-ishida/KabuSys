# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ群。  
データ取得（J-Quants API）・ETL・マーケットカレンダー管理・ニュース収集・ファクター計算・特徴量作成・シグナル生成・DuckDB スキーマ管理など、戦略開発〜運用に必要な機能をモジュール化して提供します。

現在のバージョン: 0.1.0

---

## 主要機能 (機能一覧)

- 環境変数/設定読み込み（.env / .env.local / OS 環境変数）
- J-Quants API クライアント
  - 日次株価（OHLCV）、財務データ、マーケットカレンダー取得
  - レートリミット・リトライ・トークン自動リフレッシュ対応
- DuckDB スキーマ定義と初期化（冪等）
- ETL（差分取得・保存・品質チェック）
- マーケットカレンダー管理（営業日判定・next/prev/trading days）
- ニュース収集（RSS → raw_news、記事ID正規化、SSRF対策）
- ファクター計算（Momentum / Volatility / Value 等）
- 特徴量エンジニアリング（正規化・ユニバースフィルタ・features テーブル書込）
- シグナル生成（特徴量 + AIスコア統合 → BUY/SELL 判定・signals テーブル書込）
- 発注/監査用スキーマ（orders / executions / signal_events 等）

---

## 要件

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml
- 標準ライブラリ以外に必要なパッケージはプロジェクトの packaging / requirements に合わせてインストールしてください。

---

## 環境変数 / 設定

`kabusys.config.Settings` が参照する主な環境変数:

- J-Quants / API
  - JQUANTS_REFRESH_TOKEN (必須)
- kabuステーション API
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- Slack通知
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
- データベースパス
  - DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- 実行モード / ログ
  - KABUSYS_ENV (development / paper_trading / live; デフォルト: development)
  - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL; デフォルト: INFO)

自動的にプロジェクトルートの `.env` / `.env.local` を読み込みます（環境変数優先）。自動読み込みを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順

1. Python 3.10+ を用意する。

2. 仮想環境を作成・有効化（任意）:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なパッケージをインストール:
   - pip install duckdb defusedxml
   - その他プロジェクト依存がある場合は requirements.txt / pyproject.toml に従ってください。

4. 環境変数を設定:
   - プロジェクトルートに `.env` または `.env.local` を作成する（例は下記）。
   - 例 (.env):
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

5. DuckDB スキーマ初期化:
   - Python REPL やスクリプトから初期化します（下記「使い方」を参照）。

---

## クイックスタート / 使い方

以下は主要ワークフロー（DB 初期化 → ETL → 特徴量作成 → シグナル生成 → ニュース収集）のサンプルです。

1. DuckDB スキーマを初期化
```python
from kabusys.data.schema import init_schema

# デフォルト: data/kabusys.duckdb を使う場合
conn = init_schema("data/kabusys.duckdb")
```

2. 日次 ETL を実行（市場カレンダー・株価・財務データ）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

3. 特徴量（features）を構築（target_date を指定）
```python
from kabusys.strategy import build_features
from datetime import date

target = date(2025, 1, 31)
count = build_features(conn, target)
print(f"features upserted: {count}")
```

4. シグナル生成（threshold / weights は任意で上書き）
```python
from kabusys.strategy import generate_signals

total_signals = generate_signals(conn, target_date=target)
print(f"signals written: {total_signals}")
```

5. ニュース収集ジョブ（RSS 取得 → raw_news 保存 → 銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection
# known_codes に有効な銘柄コード集合を渡すと、記事中の4桁数字からコード抽出して紐付けします。
results = run_news_collection(conn, known_codes=set(["7203", "6758"]))
print(results)  # {source_name: saved_count, ...}
```

Notes:
- 各操作は冪等に設計されています（対象日を削除して再挿入など）。
- run_daily_etl は品質チェック（quality モジュール）を呼び出します（実行継続ポリシーあり）。
- J-Quants API 呼び出しは内部でレート制御・リトライ・トークンリフレッシュを行います。

---

## よく使う API 概要

- データベース
  - init_schema(db_path) → DuckDB 接続（初期化）
  - get_connection(db_path) → DuckDB 接続（既存 DB）

- ETL / データ取得
  - run_daily_etl(conn, target_date=None, ...) → ETLResult
  - run_prices_etl, run_financials_etl, run_calendar_etl（個別 ETL）

- J-Quants クライアント
  - fetch_daily_quotes / save_daily_quotes
  - fetch_financial_statements / save_financial_statements
  - fetch_market_calendar / save_market_calendar

- ニュース
  - fetch_rss(url, source) → list[NewsArticle]
  - save_raw_news(conn, articles) → list[new_ids]
  - run_news_collection(conn, sources=None, known_codes=None)

- 研究用 / ファクター
  - kabusys.research.calc_momentum / calc_volatility / calc_value
  - calc_forward_returns, calc_ic, factor_summary, rank

- 戦略
  - build_features(conn, target_date) → upsert count
  - generate_signals(conn, target_date, threshold=0.60, weights=None) → signals count

---

## 挙動に関する注意点 / 運用上のポイント

- 環境変数は OS 環境変数が最優先、その後 `.env.local`、`.env` の順に読み込まれます。自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能です。
- DuckDB の初期化は init_schema() を用いてください。既存テーブルがある場合はスキップされます（冪等）。
- J-Quants API のレート制限（120 req/min）を内部で尊重します。大量ページネーションやバッチ取得の際は実行時間を考慮してください。
- NewsCollector は外部フィードに対して SSFR / gzip bomb 対策を実装していますが、実運用ではソースリストの監視をしてください。
- Strategy 層は Look-ahead bias を避ける設計で、target_date 時点の情報のみを使用します。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント + 保存ユーティリティ
    - news_collector.py         — RSS ニュース収集・保存・銘柄抽出
    - schema.py                 — DuckDB スキーマ定義・初期化
    - stats.py                  — 統計ユーティリティ（zscore_normalize 等）
    - pipeline.py               — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py    — マーケットカレンダー管理
    - features.py               — features 用再エクスポート
    - audit.py                  — 監査ログスキーマ
  - research/
    - __init__.py
    - factor_research.py        — Momentum / Volatility / Value 等のファクター計算
    - feature_exploration.py    — IC / forward return / summary
  - strategy/
    - __init__.py
    - feature_engineering.py    — features 作成（正規化・フィルタ）
    - signal_generator.py       — final_score 計算・BUY/SELL シグナル生成
  - execution/                   — 発注/実行関連（プレースホルダ）
  - monitoring/                  — 監視系（プレースホルダ）

---

## 開発・貢献

- コードはモジュール単位でテスト・モック可能な設計。  
- ETL / API 呼び出し部分は id_token の注入や HTTP 呼び出しのモックに対応しています。  
- バグ報告・機能提案は issue を立ててください（リポジトリに合わせて運用してください）。

---

必要であれば README にサンプル .env.example のテンプレートや、より詳細なコマンド（CI / デプロイ / docker）手順を追記します。どの内容を優先して追加しますか？