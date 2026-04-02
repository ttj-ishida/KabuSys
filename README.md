# KabuSys

日本株向けのデータプラットフォーム兼自動売買補助ライブラリ。  
DuckDB を中心としたデータ ETL、ニュース NLP（OpenAI 経由）のセンチメント評価、ファクター / リサーチユーティリティ、監査ログ初期化、J-Quants API クライアント等を提供します。

---

## 主要概要

- データ収集（J-Quants）→ DuckDB に保存（冪等）する ETL パイプライン
- RSS ニュース収集と OpenAI を使った銘柄別センチメントスコアリング
- マクロニュース + ETF MA による「市場レジーム」判定（LLM と価格指標の合成）
- ファクター計算（モメンタム / バリュー / ボラティリティ 等）および特徴量解析ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal / order_request / executions）テーブルの初期化ユーティリティ
- J-Quants API クライアント（認証・ページネーション・保存ロジック・レート制御・リトライ付き）

設計上の特徴：
- ルックアヘッドバイアス対策（datetime.today()/date.today() を内部ループから参照しない設計、API 呼び出し時の取得日時記録等）
- 冪等保存（ON CONFLICT / INSERT … DO UPDATE 等）
- フェイルセーフ（外部 API 失敗時でも例外を直接投げずフォールバックする箇所あり）
- 標準ライブラリ中心で実装（外部依存は必要最小限）

---

## 機能一覧（抜粋）

- data/
  - jquants_client: J-Quants API からのデータ取得 & DuckDB への保存（raw_prices, raw_financials, market_calendar 等）
  - pipeline: 日次 ETL の統合エントリ（run_daily_etl）と個別 ETL（run_prices_etl など）
  - news_collector: RSS 収集、前処理、raw_news への保存（SSRF 対策・サイズ制限など実装）
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - calendar_management: JPX カレンダー管理・営業日判定ユーティリティ
  - audit: 監査ログスキーマの初期化（init_audit_schema / init_audit_db）
  - stats: 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI で評価して ai_scores に書込
  - regime_detector.score_regime: ETF(1321) の MA200 乖離とマクロニュース LLM スコアを合成して market_regime に書込
- research/
  - factor_research: calc_momentum / calc_value / calc_volatility（prices_daily / raw_financials 参照）
  - feature_exploration: 将来リターン calc_forward_returns、IC 計算、統計サマリー 等

---

## 要件（主な依存）

- Python 3.10+
- 必要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ：urllib, json, logging, datetime, etc.

（実際には pyproject.toml / requirements.txt に従ってインストールしてください）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - もしくは必要最小限: pip install duckdb openai defusedxml

4. 環境変数設定（.env をプロジェクトルートに配置）
   - 自動ロード機能があるため、プロジェクトルート（.git または pyproject.toml がある階層）に `.env` / `.env.local` を置くだけで読み込まれます（無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
     - SLACK_BOT_TOKEN — Slack 通知に使用する場合
     - SLACK_CHANNEL_ID — Slack 通知先チャンネル
     - KABU_API_PASSWORD — kabuステーション API 用（必要に応じて）
     - OPENAI_API_KEY — OpenAI を直接参照する場合（score_news 等の api_key 引数を省略するため）
   - オプション:
     - KABUSYS_ENV (development | paper_trading | live) デフォルト development
     - LOG_LEVEL (DEBUG | INFO | …)
     - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
     - SQLITE_PATH, PID_FILE_PATH, CPU/MEM/DISK 閾値など

   例 (.env):
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=CXXXXX
   DUCKDB_PATH=data/kabusys.duckdb

5. DuckDB 初期化（監査ログ用 DB 初期化例）
   - Python から:
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")
     - これで監査テーブルとインデックスが作成されます。

---

## 使い方（主要な例）

- DuckDB 接続を作る例:
  - import duckdb
  - conn = duckdb.connect("data/kabusys.duckdb")

- 日次 ETL 実行（pipeline.run_daily_etl）:
  - from datetime import date
    from kabusys.data.pipeline import run_daily_etl
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

  run_daily_etl は以下を順に実行します:
  - カレンダー ETL（market_calendar）
  - 株価日足 ETL（raw_prices）
  - 財務データ ETL（raw_financials）
  - 品質チェック（run_all_checks）

- ニュースセンチメントを評価して ai_scores に書き込む:
  - from kabusys.ai.news_nlp import score_news
    n_written = score_news(conn, target_date=date(2026, 3, 20))
    print(f"written: {n_written}")

  OpenAI API キーは api_key 引数で渡すか環境変数 OPENAI_API_KEY を設定してください。

- 市場レジーム判定（マクロセンチメント + MA200）:
  - from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026, 3, 20))

- ファクター計算（例：モメンタム）:
  - from kabusys.research.factor_research import calc_momentum
    momentum = calc_momentum(conn, target_date=date(2026, 3, 20))

- 統計正規化:
  - from kabusys.data.stats import zscore_normalize
    normed = zscore_normalize(records, ["mom_1m", "mom_3m"])

- ニュース収集（RSS）:
  - from kabusys.data.news_collector import fetch_rss
    articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")

注:
- OpenAI 呼び出し箇所はリトライ・バックオフ等を実装していますが、クォータや料金管理は運用側で行ってください。
- テスト時は内部の _call_openai_api を patch して外部 API 呼出しを差し替え可能です（ユニットテスト向けの設計あり）。

---

## 環境変数一覧（主要）

必須:
- JQUANTS_REFRESH_TOKEN
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID
- KABU_API_PASSWORD（kabu連携を使う場合）

任意 / デフォルトあり:
- OPENAI_API_KEY
- KABUSYS_ENV (development | paper_trading | live) — default: development
- LOG_LEVEL — default: INFO
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- PID_FILE_PATH — default: data/execution.pid
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると自動 .env ロードを無効化

設定はプロジェクトルートの .env / .env.local から自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されている場合は読み込まれません）。

---

## ディレクトリ構成（主なファイル）

src/kabusys/
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
  - etl.py
  - stats.py
  - quality.py
  - news_collector.py
  - calendar_management.py
  - audit.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research 以外に strategy / execution / monitoring パッケージを想定するエントリもあります（トップパッケージの __all__ 参照）。

各モジュールの責務はソース内ドキュメントに詳述されています。README では触れきれない運用政策や設計上の注意点（ルックアヘッドバイアス回避、トランザクションの取り扱い、DuckDB の executemany の注意など）はソースドキュメントを参照してください。

---

## 運用上の注意

- OpenAI / J-Quants の API キーと呼び出しはコストが発生します。ステージングで十分検証してから本番（live）環境へ移行してください。
- DuckDB のファイルパスはバックアップ/権限/ローテーションポリシーを検討してください。
- ETL や LLM 呼出しは外部依存があるため監視・アラートを設定してください（Slack 通知の仕組みがある想定）。
- 大量のニュース収集や API 呼出しは RateLimit や料金問題を引き起こすため、ジョブスケジュールを制御してください。

---

README に記載の使い方は入門ガイドです。各モジュールの詳細な API、引数、戻り値や副作用については該当モジュールの docstring を参照してください。問題や改善点があればソースのドキュメントを拡張してください。