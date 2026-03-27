# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
ETL（J-Quants）によるマーケットデータ収集、ニュースのNLPスコアリング（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（発注・約定トレーサビリティ）などを提供します。

---

## 概要

KabuSys は日本株の自動売買システムを構成するコア機能群をライブラリ化したプロジェクトです。主な目的は以下：

- J-Quants API からの株価／財務／マーケットカレンダー等の差分ETL
- RSS ベースのニュース収集と OpenAI を用いたニュースセンチメント（銘柄別）スコアリング
- ETF（1321）を用いた市場レジーム判定（MA + マクロニュースの LLM センチメント）
- ファクター計算（モメンタム、バリュー、ボラティリティ等）および特徴量解析ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → executions）用のスキーマ初期化ユーティリティ
- DuckDB を中心に設計（軽量で高速な分析DB）

設計上の共通方針として、バックテスト時に生じるルックアヘッドバイアスを避けるために日付参照を直接現在時刻に依存しない実装がなされています。

---

## 機能一覧（抜粋）

- data：
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch/save daily quotes, financial statements, market calendar）
  - market calendar 管理（is_trading_day, next_trading_day, prev_trading_day, get_trading_days）
  - ニュース収集（RSS fetch, 前処理、raw_news への保存ロジック）
  - データ品質チェック（missing_data, spike, duplicates, date consistency）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai：
  - ニュース NLP（score_news: 銘柄別センチメントを ai_scores に書き込み）
  - 市場レジーム判定（score_regime: ETF MA200 乖離 + マクロ記事の LLM センチメント）
- research：
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索・評価（calc_forward_returns, calc_ic, factor_summary, rank）
- config：
  - 環境変数管理（.env の自動読み込み、必須変数チェック）
  - settings オブジェクトによる設定取得

---

## 必要条件（想定）

- Python 3.10+
- 主要依存ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
  - その他: 標準ライブラリを中心に実装されていますが、実行環境により追加パッケージが必要になる場合があります。

（プロジェクトに requirements.txt / pyproject.toml があればそちらを参照してください）

---

## 環境変数（主なもの）

以下は本ライブラリ内で参照される主要な環境変数です。`.env` または OS 環境変数で設定してください。

必須（使用する機能により必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL 実行時）
- SLACK_BOT_TOKEN — Slack 通知に使用する場合
- SLACK_CHANNEL_ID — Slack 通知チャンネル
- KABU_API_PASSWORD — kabuステーション API パスワード（実行環境で発注を行う場合）
- OPENAI_API_KEY — OpenAI 呼び出し（news_nlp / regime_detector）を行う際に必要

任意 / デフォルトあり:
- KABU_API_BASE_URL — kabuAPI の base URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視DBパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 ("development", "paper_trading", "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG", "INFO", ... )（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動ロードを無効化

.env ファイルのフォーマットは一般的な KEY=VAL 形式に対応しています。`.env.local` は `.env` を上書きする形で読み込まれます。

---

## セットアップ手順（例）

1. リポジトリをクローン
   - git clone ...

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリのインストール
   - pip install duckdb openai defusedxml
   - ※ プロジェクトの pyproject.toml / requirements.txt がある場合はそちらを使用してください。
   - 開発インストール: pip install -e .

4. 環境変数の準備
   - プロジェクトルートに `.env` を作成
     例:
       JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
       OPENAI_API_KEY=your_openai_api_key
       SLACK_BOT_TOKEN=xoxb-...
       SLACK_CHANNEL_ID=C01234567
       DUCKDB_PATH=data/kabusys.duckdb

   - テストや CI 等で自動読み込みを無効にする場合:
       export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. データベースの準備（監査DB等）
   - 監査DBを初期化する例は「使い方」参照

---

## 使い方（主要な例）

以下はライブラリをプログラムから利用する際のサンプルフロー（Python REPL / スクリプト内で実行）。

- DuckDB 接続を作る（デフォルトのパスを settings から取得）:
  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行（run_daily_etl）:
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())

- ニュースのセンチメントスコアを計算して ai_scores に書き込む:
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  n_written = score_news(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY が必要
  print("書込銘柄数:", n_written)

- 市場レジームを判定して market_regime に書き込む:
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY が必要

- 監査DB を初期化（監査専用DBファイルの作成とスキーマ適用）:
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")

- calendar ユーティリティの利用例:
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  from datetime import date
  d = date(2026,3,20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))

- RSS フェッチ例（news_collector.fetch_rss）:
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
  for a in articles[:5]:
      print(a["id"], a["title"], a["datetime"])

注意:
- OpenAI 呼び出し（news_nlp / regime_detector）は `OPENAI_API_KEY` を必要とします。API 呼び出しの失敗はログに記録され、フォールバックで継続する設計ですが、キーが未設定の場合は ValueError が送出されます。
- J-Quants 関連の ETL は `JQUANTS_REFRESH_TOKEN` に依存します。

---

## ディレクトリ構成（主要ファイル）

プロジェクトは src/kabusys 配下にモジュールを配置しています。主なファイル一覧（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / settings
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュースセンチメント（ai_scores への書込み）
    - regime_detector.py            — 市場レジーム判定（1321 MA200 + マクロ記事 LLM）
  - research/
    - __init__.py
    - factor_research.py            — momentum / value / volatility など
    - feature_exploration.py        — forward returns, IC, summary, rank
  - data/
    - __init__.py
    - calendar_management.py        — 市場カレンダー管理
    - etl.py / pipeline.py          — ETL の実装 / run_daily_etl
    - stats.py                      — zscore_normalize
    - quality.py                    — データ品質チェック
    - audit.py                      — 監査ログスキーマ（signal/order_requests/executions）初期化
    - jquants_client.py             — J-Quants API クライアント + DuckDB 保存
    - news_collector.py             — RSS 収集 / 前処理 / SSRF 対策 等
    - other modules...
  - research/                      — 研究用ユーティリティ群
  - ...（その他ユーティリティ / モジュール）

---

## ログ・デバッグ

- settings.log_level でログレベルを制御できます（環境変数 LOG_LEVEL）。
- 多くの関数は内部で logging を用いて情報・警告・例外を出力します。問題発見時はログを参照してください。

---

## テスト / 開発

- モジュール内の多くの外部 API 呼び出し（OpenAI / J-Quants / HTTP）は差し替え可能なヘルパー関数を通して実装されており、unit test では patch してモックすることを想定しています。
- 自動 .env ロードはデフォルトで有効ですが、テスト実行時に環境依存を排除したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 貢献

バグ報告・機能追加の提案は issue を立ててください。コード修正は PR を送ってください。テストと破壊的変更のないことを確認の上でレビューします。

---

この README はコードベースの主要機能と使用方法の概要を示すものです。詳細な API ドキュメントや運用手順（デプロイ、ジョブ設定、監視、Slack 通知フローなど）は別途運用ドキュメントを用意してください。