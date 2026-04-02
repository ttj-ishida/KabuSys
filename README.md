# KabuSys

日本株向けのデータプラットフォーム＆自動売買補助ライブラリです。  
DuckDB をデータレイヤに使用し、J-Quants / JQ API からの ETL、ニュース収集・NLP、ファクター計算、監査ログなどのユーティリティを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の要件を満たすことを目的としたモジュール群です。

- J-Quants API からの差分 ETL（株価・財務・カレンダー）
- ニュース RSS 収集と LLM を用いたニュースセンチメント集約（銘柄毎）
- マーケットレジーム判定（ETF + マクロニュースの組合せ）
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と研究向けユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- DuckDB ベースでの冪等保存、OpenAI / J-Quants API 呼び出しラッパー、各種ユーティリティ

設計上のポイント：
- ルックアヘッドバイアスを避ける（内部で date.today() を不用意に参照しない等）
- 冪等性（ON CONFLICT 等）を重視
- API 呼び出しはリトライ/バックオフやレート制御を実装
- テスト容易性のため環境依存の自動ロードを制御可能

---

## 主な機能一覧

- data
  - ETL: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント（fetch / save 関数、トークン自動リフレッシュ・レート制御）
  - calendar management（営業日判定・next/prev/trading days）
  - news_collector（RSS 取得・前処理・SSRF 対策）
  - quality（欠損・スパイク・重複・日付不整合チェック）
  - audit（監査ログテーブルの初期化と DB 接続ユーティリティ）
  - stats（zscore_normalize 等）
- ai
  - news_nlp.score_news(conn, target_date, api_key=None) — 銘柄毎ニューススコアを生成し ai_scores へ書込
  - regime_detector.score_regime(conn, target_date, api_key=None) — 市場レジーム判定を market_regime へ書込
- research
  - factor_research（calc_momentum / calc_value / calc_volatility）
  - feature_exploration（calc_forward_returns / calc_ic / factor_summary / rank）
- config
  - Settings（環境変数読み込み、自動 .env ロード）

---

## 必要な環境変数（主要）

必須（基本動作に必要）
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（ETL）
- KABU_API_PASSWORD — kabuステーション API パスワード（実行/発注を統合する場合）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（通知を使う場合）
- SLACK_CHANNEL_ID — Slack チャンネル ID（通知を使う場合）

AI / LLM を利用する場合
- OPENAI_API_KEY — OpenAI の API キー（news_nlp / regime_detector）

オプション（デフォルト値あり）
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/...（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 sqlite パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT 等（監視用）

自動で .env, .env.local をプロジェクトルートから読み込みます。自動ロードを無効にするには環境変数:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

簡易 .env.example:
NODE:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C...

---

## 依存パッケージ（代表例）

- duckdb
- openai
- defusedxml
- その他標準ライブラリのみで多くのロジックを実装

（プロジェクト配布時に requirements.txt / pyproject.toml で管理すると良いです）

---

## セットアップ手順

1. リポジトリをチェックアウト
   - 例: git clone ...

2. 仮想環境作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate

3. 依存パッケージをインストール
   - pip install -e .  # パッケージ化されている場合
   - または最低限:
     - pip install duckdb openai defusedxml

4. 環境変数を用意
   - プロジェクトルートに .env を作成（.env.example を参考に）

5. データディレクトリ作成（必要なら）
   - mkdir -p data

6. DuckDB スキーマ初期化（監査テーブル等）
   - Python REPL またはスクリプトで init_audit_db を呼び出す（例を後述）

---

## 使い方（サンプル）

以下は主なユーティリティの利用例です。すべての操作は DuckDB 接続（kabusys.config.settings.duckdb_path など）を受け取ります。

- DuckDB 接続を用意する
  - from pathlib import Path
  - import duckdb
  - from kabusys.config import settings
  - conn = duckdb.connect(str(settings.duckdb_path))

- ETL（日次）を実行する
  - from datetime import date
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(result.to_dict())

- 個別 ETL（株価）を実行する
  - from kabusys.data.pipeline import run_prices_etl
  - fetched, saved = run_prices_etl(conn, target_date=date(2026,3,20))

- ニューススコア（AI）を実行する
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - n = score_news(conn, target_date=date(2026,3,20))
  - print(f"書き込み銘柄数: {n}")

  注意: OPENAI_API_KEY を環境変数で指定するか、api_key 引数を渡してください。

- 市場レジーム判定
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date=date(2026,3,20))

- 監査ログ DB 初期化（監査用専用 DB を作る）
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")

- カレンダー関連
  - from kabusys.data.calendar_management import is_trading_day, next_trading_day
  - is_trading = is_trading_day(conn, date(2026,3,20))
  - next_day = next_trading_day(conn, date(2026,3,20))

- ニュース収集（RSS）
  - from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
  - articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  - 返り値は NewsArticle 型のリスト（id, datetime, source, title, content, url）

---

## 注意点 / 運用メモ

- OpenAI 呼び出しはリトライとフォールバック（失敗時は中立スコア）実装済みですが、API 料金やレートを考慮してください。
- J-Quants API はレート制限があり、module 内に RateLimiter を実装しています。大量リクエスト時は遅延が発生します。
- DuckDB の executemany に関するバージョン差（空リスト渡し不可等）に注意しているため、呼び出し側は通常の利用で問題ありません。
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml を探索）を基準に行います。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを抑止できます。

---

## 主要ディレクトリ構成

（抜粋）src/kabusys/ 以下:

- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - jquants_client.py
  - pipeline.py
  - etl.py (ETLResult 再エクスポート)
  - news_collector.py
  - calendar_management.py
  - quality.py
  - stats.py
  - audit.py
  - (その他: schema 初期化やユーティリティ等)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- ai, data, research の各モジュールはそれぞれ公開 API を持ちます（README 上部の一覧参照）。

簡単なツリー例:
- src/
  - kabusys/
    - __init__.py
    - config.py
    - ai/
      - news_nlp.py
      - regime_detector.py
    - data/
      - jquants_client.py
      - pipeline.py
      - news_collector.py
      - calendar_management.py
      - quality.py
      - stats.py
      - audit.py
    - research/
      - factor_research.py
      - feature_exploration.py

---

## テスト・デバッグ

- モジュール内の外部 API 呼び出しはテスト時にモック可能（例: news_nlp._call_openai_api を patch する等）。
- settings（kabusys.config.Settings）により環境変数の取り扱いを一元化。テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して .env 自動読み込みを無効化できます。
- ログレベルは環境変数 LOG_LEVEL で制御可能（DEBUG/INFO/...）。

---

## ライセンス / 貢献

この README はコードベースに基づく概要と使用手順を示しています。各モジュール内に詳細なドキュメントと設計メモがコメントとして含まれているため、機能拡張やバグ修正の際は該当モジュール内の docstring を参照してください。

質問・改善提案があればリポジトリの Issue/PR を通じてご連絡ください。