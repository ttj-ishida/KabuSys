# KabuSys

日本株自動売買／リサーチ基盤ライブラリ。J-Quants からデータを取得して DuckDB に蓄積し、ニュースの NLP スコアリングや市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（発注〜約定のトレーサビリティ）等を提供します。

---

## 概要

KabuSys は以下を主目的とする Python パッケージです。

- J-Quants API から株価・財務・マーケットカレンダー等を差分取得して DuckDB に保存する ETL パイプライン
- RSS ニュース収集と OpenAI を用いたニュースセンチメント（銘柄別）スコアリング
- ETF を用いた市場レジーム判定（MA とマクロニュースの LLM センチメントの合成）
- ファクター計算（モメンタム・バリュー・ボラティリティ等）と特徴量解析ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- 発注・約定の監査ログ用テーブル定義と初期化ユーティリティ（DuckDB）
- 各種ユーティリティ（カレンダー管理、統計ユーティリティ等）

設計面の特徴：
- ルックアヘッドバイアスを避ける設計（内部で date.today() を不用意に参照しない等）
- DuckDB をデータレイク兼 OLAP ストアとして利用
- 冪等性（ON CONFLICT / idempotent insert）とフォールトトレランスを重視
- OpenAI 呼び出しや外部 API 呼び出しに対するリトライ・バックオフ処理を内蔵

---

## 主な機能一覧

- データ取得・ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - J-Quants API クライアント（kabusys.data.jquants_client）
- ニュース処理・NLP
  - RSS 取得と前処理（kabusys.data.news_collector.fetch_rss / preprocess_text）
  - 銘柄別ニュースセンチメント算出（kabusys.ai.news_nlp.score_news）
- 市場レジーム判定
  - ETF（1321）200日MA乖離 + マクロニュース LLM を合成（kabusys.ai.regime_detector.score_regime）
- リサーチ / ファクター計算
  - calc_momentum / calc_value / calc_volatility（kabusys.research.factor_research）
  - 将来リターン・IC・統計サマリー（kabusys.research.feature_exploration）
  - zscore 正規化（kabusys.data.stats.zscore_normalize）
- データ品質チェック
  - 欠損・重複・スパイク・日付不整合チェック（kabusys.data.quality.run_all_checks）
- カレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job（kabusys.data.calendar_management）
- 監査ログ初期化
  - init_audit_schema / init_audit_db（kabusys.data.audit）

---

## 要件（主な依存ライブラリ）

- Python 3.9+
- duckdb
- openai（OpenAI の新 SDK を想定）
- defusedxml
- その他標準ライブラリ（urllib, json, datetime, logging など）

（実プロジェクトでは requirements.txt / pyproject.toml を参照してください）

---

## セットアップ手順

1. リポジトリをクローン（またはパッケージを入手）
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   （プロジェクトに pyproject.toml / requirements.txt があればそちらを使用）
   ```
   pip install duckdb openai defusedxml
   # または開発中なら
   pip install -e .
   ```

4. 環境変数を設定
   - 開発時はプロジェクトルートに `.env` または `.env.local` を配置すると自動読み込みされます（kabusys.config により .git または pyproject.toml をルート判定）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

   必須と思われる環境変数（コード内の Settings を参照）：
   - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD — kabu ステーション API 用パスワード（該当機能を使う場合）
   - SLACK_BOT_TOKEN — Slack 通知を利用する場合
   - SLACK_CHANNEL_ID — Slack チャンネル ID
   - OPENAI_API_KEY — OpenAI を使う場合（score_news / score_regime 等）
   任意（デフォルトあり）：
   - KABUSYS_ENV (development | paper_trading | live) — 動作モード
   - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）

   例 .env（簡易）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxxx
   SLACK_BOT_TOKEN=xoxb-xxxxx
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（クイックスタート）

以下は主要ユーティリティの利用例です。実行前に必要な環境変数（特に API キー類）を設定してください。

- DuckDB 接続を作成して日次 ETL を実行する（J-Quants から差分取得）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュースセンチメントを生成して ai_scores テーブルに書き込む:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # OPENAI_API_KEY を環境変数に設定するか、api_key 引数で渡す
  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {count} codes")
  ```

- 市場レジーム判定（ETF 1321 とマクロニュース）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用の DuckDB を初期化する:
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn は初期化済み DuckDB 接続
  ```

- RSS を取得する（ニュース収集の一部を単体で使いたい場合）:
  ```python
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles:
      print(a["datetime"], a["title"])
  ```

注意:
- OpenAI 呼び出しを行う関数は api_key 引数にキーを直接渡せます（テスト時に差し替え可能）。
- 各 ETL / スコア関数は外部 API の失敗時にフェイルセーフ動作を取る設計ですが、環境変数未設定など明白な前提違反は例外を出します（ValueError）。

---

## ディレクトリ構成（主要ファイル）

以下はコードベースの主要モジュール構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py            — 銘柄別ニュースセンチメント生成（OpenAI）
    - regime_detector.py     — 市場レジーム判定（ETF MA + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント & 保存関数（raw_prices, raw_financials, market_calendar 等）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - news_collector.py      — RSS 取得 / 前処理 / raw_news への保存ロジック
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - quality.py             — データ品質チェック
    - stats.py               — zscore_normalize 等統計ユーティリティ
    - audit.py               — 監査ログスキーマ初期化（signal_events, order_requests, executions）
    - etl.py                 — ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py     — モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py — 将来リターン計算・IC・統計サマリー
  - (その他) strategy/, execution/, monitoring/ が参照される可能性あり（プロジェクト全体の一部）

各モジュールは README 内で上に挙げた役割を持ち、DuckDB の特定テーブル（raw_prices, raw_financials, raw_news, ai_scores, market_calendar, market_regime 等）を想定しています。

---

## トラブルシューティング & 注意点

- 環境変数未設定時は Settings のプロパティが ValueError を投げます。必須キー（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY, SLACK_* 等）を確認してください。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行われます。テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI, J-Quants の呼び出しはレート制限とリトライロジックを実装していますが、利用量に応じた API の制限に注意してください。
- DuckDB の executemany に関するバージョン依存の挙動（空リスト渡せない等）に対応した実装となっていますが、実行環境の duckdb バージョンによって挙動が変わる可能性があります。
- news_collector は SSRF 対策・受信サイズ制限・gzip 解凍チェック等、堅牢性を考慮した設計です。外部 RSS の扱いに注意してください。

---

必要であれば、README にサンプル .env.example、より詳細な API 利用手順（J-Quants の token 取得手順や Slack 通知のセットアップ）、CI / テストの実行方法、データベーススキーマ（DDL）抜粋などを追加できます。どの情報を優先して追加しますか？