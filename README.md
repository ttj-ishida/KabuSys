# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI を用いたセンチメント解析）、ファクター計算、監査ログ（発注→約定のトレーサビリティ）、マーケットカレンダー管理、品質チェック、研究用ユーティリティなどを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株アルゴリズム取引に必要なデータ基盤と研究／運用用ユーティリティ群を提供します。主な機能は以下の通りです。

- J-Quants API からの差分 ETL（株価日足、財務、マーケットカレンダー）
- ニュース収集（RSS）およびニュースの NLP（OpenAI）による銘柄ごとのスコアリング
- 市場レジーム判定（ETF MA とマクロニュースを組み合わせた判定）
- ファクター計算（モメンタム、ボラティリティ、バリュー等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログテーブルの初期化/管理（シグナル→発注→約定のトレース）
- DuckDB を用いたローカルデータ管理
- 環境変数ベースの設定管理（.env 自動ロード機能）

設計上、ルックアヘッドバイアスを避ける実装や、API 呼び出しの堅牢なリトライ／レート制御等が組み込まれています。

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save）
  - ニュース収集（fetch_rss）と news_symbols の関連付け処理
  - カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job）
  - 品質チェック（check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP による銘柄スコアリング（score_news）
  - 市場レジーム判定（score_regime）
- research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）
- config
  - 環境変数 / .env 読み込み、settings オブジェクトによるアクセス

---

## セットアップ手順

前提:
- Python 3.10+（typing の | 型やその他構文に依存）
- DuckDB, OpenAI SDK 等のライブラリを使用

1. リポジトリをクローン / ダウンロード
2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows の場合は .venv\Scripts\activate）
3. 必要パッケージをインストール
   - 例（pip）:
     - pip install duckdb openai defusedxml
   - プロジェクトに requirements.txt / pyproject.toml があればそちらを利用
   - （開発時）pip install -e .

4. 環境変数設定 (.env)
   - プロジェクトルートに `.env` / `.env.local` を配置すると自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須環境変数（少なくとも ETL / AI を使う際に必要）:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
     - KABU_API_PASSWORD — kabu ステーション API パスワード
     - SLACK_BOT_TOKEN — Slack 通知に使用するボットトークン
     - SLACK_CHANNEL_ID — 通知先チャンネルID
     - OPENAI_API_KEY — OpenAI を利用する場合（score_news / score_regime）
   - 任意 / デフォルト:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルトは development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト INFO
     - DUCKDB_PATH — デフォルト data/kabusys.duckdb
     - SQLITE_PATH — デフォルト data/monitoring.db

   例 .env:
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=CXXXXXXX
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development

5. データベース初期化（監査ログなど）
   - 監査ログ用 DB を初期化する例:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
   - 既存 DuckDB 接続に監査テーブルだけ追加する場合:
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn, transactional=True)

---

## 使い方（基本例）

以下は Python REPL / スクリプトからの利用例です。

- 設定値にアクセス:
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  if settings.is_live: ...

- DuckDB 接続を開く:
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行:
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニューススコアの生成:
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written: {n_written}")

  ※ OPENAI_API_KEY は環境変数か api_key 引数で指定可能:
  score_news(conn, target_date=date(2026,3,20), api_key="sk-...")

- 市場レジーム判定:
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026,3,20))

- ファクター計算・研究ユーティリティ:
  from kabusys.research.factor_research import calc_momentum
  recs = calc_momentum(conn, target_date=date(2026,3,20))
  # zscore 正規化
  from kabusys.data.stats import zscore_normalize
  normed = zscore_normalize(recs, ["mom_1m", "mom_3m"])

- ニュース RSS 取得（単独）:
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles: print(a["title"], a["datetime"])

注意:
- 多くの機能は DuckDB のテーブルスキーマ（raw_prices, raw_financials, raw_news, ai_scores, market_regime, market_calendar 等）に依存します。ETL を実行してテーブルを生成するか、事前にスキーマ移行を行ってください。
- OpenAI 呼び出しは API 使用料が発生します。ローカルでテストする際はモックすることを推奨します（モジュール内の _call_openai_api を patch して差し替えられます）。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須: J-Quants 用)
- KABU_API_PASSWORD (必須: kabuステーション API 用)
- KABU_API_BASE_URL (任意: デフォルト http://localhost:18080/kabusapi)
- OPENAI_API_KEY (必要時)
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (Slack 通知)
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- SQLITE_PATH (デフォルト data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG/INFO/...)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env を読み込まない

settings オブジェクトからプログラム内でアクセスできます:
from kabusys.config import settings
settings.duckdb_path, settings.is_live など。

---

## ディレクトリ構成（概要）

src/kabusys/
- __init__.py — パッケージ初期化（__version__ 等）
- config.py — 環境変数 / .env ロードと settings オブジェクト
- ai/
  - __init__.py — ai API エクスポート
  - news_nlp.py — ニュース NLP（score_news, calc_news_window 等）
  - regime_detector.py — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch/save + 認証/レート管理）
  - pipeline.py — ETL パイプライン（run_daily_etl など）
  - etl.py — ETLResult 再エクスポート
  - news_collector.py — RSS 取得 / 前処理 / 保存ユーティリティ
  - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
  - quality.py — データ品質チェック（QualityIssue / 各チェック）
  - stats.py — 統計ユーティリティ（zscore_normalize）
  - audit.py — 監査ログ（監査テーブル DDL / 初期化）
- research/
  - __init__.py
  - factor_research.py — モメンタム／ボラ／バリュー計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリー
- monitoring/, strategy/, execution/, などの名前は __all__ に含まれていますが実装ファイルは上記が中心（プロジェクト全体の設計上その他モジュールも存在する想定）。

---

## テストと開発上の注意

- OpenAI や外部 API 呼び出しはテストでモック可能なように設計されています（内部の _call_openai_api を patch など）。
- データのルックアヘッドバイアスを防ぐため、関数は date/datetime の引数を受け取り、内部で date.today() を直接参照しないようになっています。バックテストや再現性のために target_date を明示してください。
- DuckDB の executemany はバージョン差異があるため、空リストでの呼び出しを避ける実装になっています。
- jquants_client は API レート制御（120 req/min）とリトライを内包しています。

---

## ライセンス / 貢献

この README はコードベースの説明です。実際のライセンス情報や貢献ガイドがリポジトリに含まれている場合はそちらを参照してください。

---

README に載せきれない詳細（テーブルスキーマ、より詳細な ETL 設定、Slack 通知や発注フローのコード例など）が必要であれば、どのセクションを拡張するか教えてください。