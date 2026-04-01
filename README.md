# KabuSys

日本株向けの自動売買／データ基盤ライブラリ。  
DuckDB をデータストアに、J-Quants や RSS / OpenAI を利用してデータ収集・品質チェック・ファクター計算・AIによるニュースセンチメント評価・監査ログ保持などを行うことを目的としたモジュール群です。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を提供します。

- J-Quants API からの株価・財務・カレンダー取得（差分ETL、ページネーション、レート制御、トークン自動リフレッシュ）
- RSS ベースのニュース収集と前処理（SSRF対策・トラッキング除去・前処理）
- OpenAI を用いたニュースセンチメント解析（銘柄単位のスコアリング、マクロセンチメント）
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）と統計ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）を持つ DuckDB 初期化ユーティリティ
- 環境変数 / .env の自動ロードと設定管理

設計上「ルックアヘッドバイアス防止」「フェイルセーフ（API失敗時の継続）」「冪等性」を重視しています。

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（取得 / 保存 / トークン管理 / レート制御）
  - ニュース収集（fetch_rss, 前処理、保存処理を想定）
  - カレンダー管理（is_trading_day, next_trading_day, prev_trading_day, calendar_update_job）
  - 品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- research/
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）
- ai/
  - ニュースセンチメント（score_news）
  - 市場レジーム判定（score_regime：ETF 1321 の MA200 乖離 + マクロニュース LLM）
- config
  - .env の自動読み込みロジックと Settings クラス（アプリ設定を提供）

---

## 必要条件 / 依存関係

主に以下が必要です（実行環境に応じて追加・調整してください）:

- Python 3.10+
- duckdb
- openai (OpenAI API クライアント)
- defusedxml
- （標準ライブラリ以外で使用している場合）その他 HTTP / SSL が動作する環境

※ 実行には J-Quants のリフレッシュトークンや OpenAI API キーなど外部サービスの認証情報が必要です。

---

## セットアップ手順

1. リポジトリをクローン／配置する

2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （開発用に pip install -e . が使えるよう setup 構成があればそちらを利用してください）

4. 環境変数（.env）を作成
   - プロジェクトルート（pyproject.toml か .git のあるディレクトリ）に `.env` または `.env.local` を置くと自動読み込みされます（自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必要な環境変数の例（下記「環境変数」セクション参照）を設定してください。

5. データベース格納先ディレクトリ作成（必要に応じて）
   - settings.duckdb_path / settings.sqlite_path 等で指定したパスの親ディレクトリを作成しておくことを推奨します。

---

## 環境変数

主に以下を使用します（必須 / 任意は用途により異なります）:

必須（使用する機能により必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL）
- OPENAI_API_KEY — OpenAI API キー（ai.score_news / regime_detector）
- SLACK_BOT_TOKEN — Slack 通知を使う場合
- SLACK_CHANNEL_ID — Slack チャンネル ID（通知先）
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注系を使う場合）

任意 / デフォルトあり:
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PID_FILE_PATH — デフォルト: data/execution.pid
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値（パーセント）
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

.env の書き方については config モジュールがシンプルな .env 形式をパースします。クォートやコメントの扱いがある程度サポートされています。

---

## 使い方（代表的な例）

以下は Python スクリプトや REPL から呼び出すサンプルです。

- DuckDB 接続の作成と ETL 実行

  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")  # settings.duckdb_path を使ってもよい
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのセンチメントスコアを付与（OpenAI 必須）

  ```python
  from kabusys.ai.news_nlp import score_news
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env の OPENAI_API_KEY を使用
  print("scored:", n_written)
  ```

- 市場レジーム判定（ETF 1321 をベースに LLM を併用）

  ```python
  from kabusys.ai.regime_detector import score_regime
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  res = score_regime(conn, target_date=date(2026, 3, 20))
  print("ok:", res)
  ```

- 監査ログ用 DuckDB 初期化

  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit_kabusys.duckdb")
  ```

- ファクター計算 / 研究ユーティリティ

  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, date(2026, 3, 20))
  ```

---

## ディレクトリ構成

（重要なファイル・モジュールの概観）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py (score_news エクスポート)
    - news_nlp.py (ニュースセンチメント、score_news)
    - regime_detector.py (市場レジーム判定、score_regime)
  - data/
    - __init__.py
    - jquants_client.py (J-Quants API クライアント、fetch/save 系)
    - pipeline.py (ETL 実行エントリ)
    - etl.py (ETLResult 再エクスポート)
    - news_collector.py (RSS 取得・前処理)
    - calendar_management.py (マーケットカレンダー管理)
    - quality.py (データ品質チェック)
    - stats.py (zscore_normalize)
    - audit.py (監査ログ DDL・初期化)
  - research/
    - __init__.py
    - factor_research.py (calc_momentum, calc_value, calc_volatility)
    - feature_exploration.py (calc_forward_returns, calc_ic, factor_summary, rank)
  - ai/ その他補助モジュール等

---

## 開発メモ / 実装上の注意点

- config.Settings はプロジェクトルートの .env / .env.local を自動読み込みします（CWD ではなく __file__ の親ディレクトリから .git / pyproject.toml を探索してプロジェクトルートを決定）。自動ロードを止める場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。
- ETL / AI モジュールはルックアヘッドバイアス防止のため、内部で datetime.today() / date.today() をむやみに参照しない設計です。呼び出し側で target_date を明示することを推奨します。
- OpenAI 呼び出しはリトライやフェイルセーフを組み込んでいますが、API レスポンスのパースで失敗した場合はゼロにフォールバックする設計になっています（例外を上げないケースあり）。
- J-Quants API はレート制御（120 req/min）と 401 リフレッシュ処理、ページネーション対応を実装しています。
- DuckDB に対する executemany の空リスト渡しはバージョン依存の挙動があるためコード内でチェックしています（空リスト渡しを避ける実装）。

---

もし README に追記したいサンプル .env.example、pip の extras、CLI や systemd ユニットの起動例、または発注/ブローカー連携部分のドキュメント（機密情報を扱うため注意点）などが必要であれば、その内容を教えてください。README をそれに合わせて拡張します。