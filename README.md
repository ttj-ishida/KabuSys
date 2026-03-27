# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
市場データの ETL、ニュース収集と AI によるセンチメント評価、ファクター計算、監査ログ（発注トレース）、JPX カレンダー管理などの機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のリサーチ / バックテスト / 自動売買基盤のためのモジュール群です。主な目的は以下です。

- J-Quants API から日次データ（株価・財務・カレンダー）を差分取得して DuckDB に保存する ETL パイプライン
- RSS 等からニュースを収集し raw_news に保存、銘柄へのマッピング
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント（銘柄ごと）とマクロセンチメント評価
- ETF（1321）200日移動平均乖離とマクロセンチメントの合成による市場レジーム判定
- ファクター計算（モメンタム・バリュー・ボラティリティ等）と研究用ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログ用スキーマ（signal → order_request → execution のトレーサビリティ）
- JPX カレンダー管理（営業日判定、next/prev_trading_day など）

設計上、バックテストや研究での「ルックアヘッドバイアス」を避ける工夫（date 引数ベース、fetch 時刻を記録）や、外部 API 呼び出しのリトライ・フェイルセーフが多く組み込まれています。

---

## 機能一覧

- data
  - ETL: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント（取得＋保存関数）：fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar / save_* 系
  - カレンダー管理：is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
  - ニュース収集：RSS の安全取得・前処理・raw_news への保存を支援
  - 品質チェック：check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
  - 監査ログスキーマ初期化：init_audit_schema / init_audit_db
  - 汎用統計ユーティリティ：zscore_normalize
- ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを生成して ai_scores テーブルへ書込
  - regime_detector.score_regime: ETF (1321) MA200 とマクロセンチメントを合成して market_regime を登録
- research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config
  - 環境変数読み込み・設定管理（.env 自動読み込み機能、settings オブジェクト）
- audit
  - 発注・約定の監査スキーマ定義と初期化ユーティリティ

---

## セットアップ手順

前提:
- Python 3.9+（一部 typing 機能を使用しているため推奨）
- DuckDB を利用します（pip パッケージ duckdb）
- OpenAI SDK（openai）、defusedxml 等が必要

1. リポジトリをクローン / コピー
   - 例: git clone <repo>

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 代表的な依存:
     - duckdb
     - openai
     - defusedxml
   - 例（requirements.txt が無い場合の最小インストール例）:
     - pip install duckdb openai defusedxml

   ※ 実際の環境では他に logging 周り・テスト用ライブラリ等が必要になる場合があります。

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます）。
   - 必須環境変数（Settings で必須とされているもの）:
     - JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
     - KABU_API_PASSWORD=<kabu_api_password>
     - SLACK_BOT_TOKEN=<slack_bot_token>
     - SLACK_CHANNEL_ID=<slack_channel_id>
   - 任意・デフォルト:
     - KABUSYS_ENV=development|paper_trading|live  (デフォルト development)
     - LOG_LEVEL=INFO|DEBUG|... (デフォルト INFO)
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
   - 例 .env の雛形:
     - JQUANTS_REFRESH_TOKEN=xxxxx
     - OPENAI_API_KEY=sk-xxxx   # score_news / score_regime の引数を省略する場合に必要
     - KABU_API_PASSWORD=xxxx
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C01234567
     - DUCKDB_PATH=data/kabusys.duckdb
     - KABUSYS_ENV=development

5. DuckDB の初期化（監査DBを使う場合）
   - 監査用 DB を初期化する例:
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")
     - (この関数は必要なテーブルとインデックスを作成します)

---

## 使い方（簡単なコード例）

注意: すべての操作は DuckDB の接続オブジェクト（duckdb.connect(...) の戻り値）を渡して実行します。

- ETL を日次で回す（簡易例）
  - from datetime import date
  - import duckdb
  - from kabusys.data.pipeline import run_daily_etl
  - conn = duckdb.connect("data/kabusys.duckdb")
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(result.to_dict())

- ニュースセンチメントを生成して ai_scores に保存
  - from datetime import date
  - import duckdb
  - from kabusys.ai.news_nlp import score_news
  - conn = duckdb.connect("data/kabusys.duckdb")
  - n_written = score_news(conn, target_date=date(2026, 3, 20))
  - print(f"written: {n_written}")

  - OpenAI API キーを引数で渡す例:
    - score_news(conn, date(2026,3,20), api_key="sk-...")

- 市場レジーム判定（market_regime テーブルへ書き込む）
  - from datetime import date
  - import duckdb
  - from kabusys.ai.regime_detector import score_regime
  - conn = duckdb.connect("data/kabusys.duckdb")
  - score_regime(conn, target_date=date(2026,3,20))

- ファクター計算（研究用途）
  - from datetime import date
  - import duckdb
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  - conn = duckdb.connect("data/kabusys.duckdb")
  - mom = calc_momentum(conn, date(2026,3,20))
  - vol = calc_volatility(conn, date(2026,3,20))
  - val = calc_value(conn, date(2026,3,20))

- データ品質チェック
  - from kabusys.data.quality import run_all_checks
  - issues = run_all_checks(conn, target_date=date(2026,3,20))
  - for i in issues: print(i)

- 監査スキーマ初期化（既存接続に追加）
  - from kabusys.data.audit import init_audit_schema
  - conn = duckdb.connect("data/kabusys.duckdb")
  - init_audit_schema(conn, transactional=True)

テスト時には内部の API 呼び出し（OpenAI 呼び出しや network I/O）をモックして使用することを想定した設計になっています（例えば kabusys.ai.news_nlp._call_openai_api を patch して差し替え可能）。

---

## 環境変数と設定（主要なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news/score_regime を引数省略で使う場合に必要）
- KABU_API_PASSWORD: kabu API 用パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 をセットすると .env 自動読み込みを無効化

設定は kabusys.config.settings 経由で参照できます。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                         — 環境変数・設定読み込み
- ai/
  - __init__.py
  - news_nlp.py                     — ニュースセンチメント（ai_scores 書込み）
  - regime_detector.py              — マクロ + MA200 の市場レジーム判定
- data/
  - __init__.py
  - calendar_management.py          — JPX カレンダー管理
  - pipeline.py                     — ETL パイプライン（run_daily_etl 等）
  - etl.py                          — ETLResult の再エクスポート
  - stats.py                        — zscore_normalize 等
  - quality.py                      — データ品質チェック
  - audit.py                        — 監査ログスキーマ定義 / 初期化
  - jquants_client.py               — J-Quants API クライアント + 保存関数
  - news_collector.py               — RSS 収集・前処理
- research/
  - __init__.py
  - factor_research.py              — calc_momentum / calc_value / calc_volatility
  - feature_exploration.py          — calc_forward_returns / calc_ic / factor_summary / rank

その他:
- README.md (本ファイル)
- pyproject.toml / setup.cfg 等（プロジェクトルートにある前提）

---

## 実運用上の注意点

- OpenAI 呼び出しはコストとレイテンシが発生します。バッチサイズやリトライ設定はソース内の定数で制御できます。
- J-Quants API はレート制限（120 req/min）を遵守する設計ですが、実運用の際は環境（ネットワーク、トークン有効期限）を監視してください。
- ETL は部分失敗しても可能な限り継続する設計です。ETLResult の errors / quality_issues を監視して運用判断を行ってください。
- DuckDB の executemany の仕様に依存する箇所があるため、DuckDB のバージョン差異に注意してください（ソースに互換性考慮の注記あり）。
- 監査ログは削除しない前提で設計されています。テーブルの変更は慎重に行ってください。

---

必要に応じて README に追記します。README に含めたい具体的な使用例（CI 手順、cron ジョブ例、docker-compose 例など）があればお知らせください。