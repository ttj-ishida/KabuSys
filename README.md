# KabuSys

KabuSys は日本株向けのデータプラットフォーム兼自動売買基盤のライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP スコアリング、ファクター計算、マーケットレジーム判定、監査ログ（トレーサビリティ）など、システム運用に必要なコンポーネントを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

主な目的は以下です。

- J-Quants API から株価・財務・カレンダー等のデータを差分取得・保存（DuckDB）
- RSS ニュース収集と前処理（SSRF対策、トラッキング除去）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄別 / マクロ）
- マーケットレジーム判定（ETF 1321 の MA200 乖離 + マクロセンチメント）
- ファクター計算（モメンタム・ボラティリティ・バリュー等）および研究ユーティリティ
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- マーケットカレンダー管理（JPX カレンダーの差分取得・営業日判定）

設計上の特徴:
- ルックアヘッドバイアス防止（内部で date.today()/datetime.now() を安易に参照しない設計）
- API 呼び出しはリトライ・バックオフ・レートリミット対応
- DuckDB をメインのオンディスク DB として使用（軽量で高速）
- 冪等性（ON CONFLICT / primary key を活用）を重視

---

## 機能一覧

- data
  - ETL パイプライン: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント: fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - 保存関数: save_daily_quotes / save_financial_statements / save_market_calendar
  - カレンダー管理: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
  - ニュース収集: RSS 取得・前処理・保存ロジック（SSRF 対策、gzip 除去等）
  - データ品質チェック: check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
  - 監査ログ初期化: init_audit_schema / init_audit_db
  - 統計ユーティリティ: zscore_normalize
- ai
  - ニュースNLP: score_news（銘柄ごとのセンチメントを ai_scores に書き込み）
  - レジーム判定: score_regime（ETF 1321 の MA200 乖離 + マクロセンチメント）
- research
  - ファクター計算: calc_momentum / calc_value / calc_volatility
  - 特徴量探索: calc_forward_returns / calc_ic / factor_summary / rank
- config
  - 環境変数管理（.env 自動ロード、Settings クラス）
- その他
  - audit テーブル DDL（signal_events / order_requests / executions）とインデックス

---

## セットアップ手順

前提:
- Python 3.10 以上（PEP 604 のタイプヒント（A | B）を使用しているため）
- ネットワークアクセス（J-Quants / OpenAI / RSS ソース）と適切な API キー

1. リポジトリをクローンしてインストール（開発編集を想定）
   ```bash
   git clone <repo-url>
   cd <repo>
   pip install -e .
   ```

2. 必要なパッケージ（例）
   - duckdb
   - openai
   - defusedxml
   - （その他、プロジェクトで使用するライブラリ）
   requirements.txt がない場合は手動でインストールしてください:
   ```bash
   pip install duckdb openai defusedxml
   ```

3. 環境変数の設定
   プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   主な必須環境変数:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime に必要）
   - SLACK_BOT_TOKEN: Slack 通知などに利用する場合
   - SLACK_CHANNEL_ID: Slack の宛先
   - KABU_API_PASSWORD: kabuステーション API のパスワード（運用時）
   
   任意（デフォルトあり）:
   - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
   - DUCKDB_PATH (default: data/kabusys.duckdb)
   - SQLITE_PATH (default: data/monitoring.db)
   - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
   - KABUSYS_ENV: development | paper_trading | live（default: development）
   - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（default: INFO）

   .env の例（抜粋）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-xxxx...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   ```

4. ディレクトリ/データ用フォルダを作成（DuckDB ファイルの親ディレクトリなど）
   ```bash
   mkdir -p data
   ```

---

## 使い方（例）

以下はパッケージ API の簡単な利用例です。実際はアプリケーション固有のラッパーやジョブ制御（cron / Airflow / Systemd）から呼び出すことが想定されます。

- DuckDB 接続を作成して日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（銘柄別）を生成する
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written_count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"scored {written_count} codes")
```

- 市場レジーム（daily）をスコアリングして保存する
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログ DB を初期化する（別 DB ファイルにすることを推奨）
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# 以降 conn を使って監査テーブルへアクセスできます
```

- RSS フィードを取得する（ニュース収集チェーンの一部）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

注意点:
- score_news / score_regime は OpenAI API の呼び出しを行います。API キーと料金に注意してください。
- run_daily_etl は J-Quants API を呼びます。J-Quants のトークンとレート制限に注意してください（モジュール内で制御あり）。
- DuckDB のテーブル（raw_prices, raw_financials, market_calendar, raw_news, ai_scores, market_regime, ...）はスキーマ前提で動作します。ETL の最初にスキーマ初期化処理を用意してください（本リポジトリに schema 初期化用モジュールがある想定）。

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要なソースは `src/kabusys` 以下にあります。主なファイル／モジュール:

- src/kabusys/
  - __init__.py
  - config.py                -- 環境変数 / Settings
  - ai/
    - __init__.py
    - news_nlp.py            -- ニュースセンチメント解析（銘柄別）
    - regime_detector.py     -- 市場レジーム判定（1321 MA200 + マクロ）
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント + 保存ロジック
    - pipeline.py            -- ETL パイプライン（run_daily_etl 等）
    - etl.py                 -- ETLResult の再エクスポート
    - news_collector.py      -- RSS 取得・前処理
    - calendar_management.py -- マーケットカレンダー管理
    - quality.py             -- 品質チェック
    - stats.py               -- 統計ユーティリティ（zscore_normalize）
    - audit.py               -- 監査ログ DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py     -- モメンタム / バリュー / ボラティリティ
    - feature_exploration.py -- 将来リターン / IC / summary / rank
  - research/factor_research.py
  - その他（strategy / execution / monitoring 等は __all__ で参照予定）

（実際の小ファイル群はリポジトリ全体を参照してください）

---

## 設定・運用上の注意

- 環境変数は .env / .env.local から自動読み込みされます（プロジェクトルートは .git または pyproject.toml を基準に探索）。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読込を無効化できます。
- OpenAI 呼び出しはリトライ／バックオフ設計ですが、API 料金とレート制限に注意してください。
- J-Quants 呼び出しは内部でレート制限（120 req/min）を守る設計になっています。大量取得時は ETL のスケジューリングに注意してください。
- DuckDB のバージョン互換性に依存する箇所があります（executemany の空リストや配列バインド等）。DuckDB のバージョン差を考慮して運用してください。
- セキュリティ: news_collector は SSRF 対策（リダイレクト検査、プライベートIP検出、許可プロトコル限定）を実装していますが、運用環境ではプロセスの権限とネットワーク制御も合わせて行ってください。

---

## 貢献・拡張案

- strategy / execution 層を実装し、監査ログ→注文送信→約定ハンドリングを結合する
- Slack / monitoring 連携（現状はトークンを参照するだけ）
- バックテスト用のラッパー（過去時点でのデータ可視化・再現可能な ETL スナップショット）
- スキーマ初期化スクリプト（schema.create など）を提供して DB セットアップを自動化

---

必要であれば、README に含めるコマンド（pytest, linters, CI 設定）、より詳細な API リファレンス、サンプル .env.example、または運用手順（cron / systemd / docker-compose）を追加できます。どれを優先して追記しますか？