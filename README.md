# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI を利用したセンチメント）、ファクター計算、監査ログ（約定トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株を対象としたデータ基盤とリサーチ / 自動売買コンポーネント群を提供する Python パッケージです。主な目的は以下です。

- J-Quants API からの株価 / 財務 / カレンダー ETL（差分取得・冪等保存）
- RSS ベースのニュース収集と OpenAI を使った銘柄別センチメントスコア算出
- 市場レジーム判定（ETF の MA とマクロニュースセンチメントの融合）
- ファクター計算（モメンタム / ボラティリティ / バリュー 等）と研究用ユーティリティ
- 監査ログ用の DuckDB スキーマ（シグナル→発注→約定のトレース）
- データ品質チェック（欠損・重複・スパイク・日付不整合）

設計方針は「ルックアヘッドバイアス回避」「冪等性」「API のレート制御とリトライ」「フェイルセーフ（部分失敗時の継続）」です。

---

## 機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（認証、自動リフレッシュ、ページネーション、レート制御）
  - カレンダー管理（営業日判定、next/prev_trading_day、calendar_update_job）
  - ニュース収集（RSS -> raw_news、トラッキングパラメータ除去、SSRF 防止）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ初期化（監査テーブル・インデックス、init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news: ニュース集合を LLM に送り銘柄別スコアを ai_scores に保存
  - regime_detector.score_regime: ETF（1321）の MA200 乖離とマクロニュースの LLM スコアを合成して市場レジーム判定を保存
  - OpenAI 呼び出しはリトライ・タイムアウト制御、レスポンス検証を実装
- research/
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索・IC 計算・統計サマリー（calc_forward_returns, calc_ic, factor_summary, rank）
- config
  - 環境変数の自動ロード（.env/.env.local をプロジェクトルートから読み込み）
  - settings オブジェクトで環境変数にアクセス（必須キーは例外を投げる）

---

## セットアップ手順

※ このリポジトリに pyproject.toml/requirements.txt がある想定での一般的な手順です。プロジェクト用の仮想環境を作成して依存をインストールしてください。

1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要なパッケージをインストール（最小例）
   - pip install duckdb openai defusedxml

   実際にはプロジェクトの requirements / pyproject を参照してインストールしてください。

3. 環境変数（.env）を用意
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に .env を置くと自動ロードされます（.env.local は .env を上書き）。
   - 自動ロードを無効にする場合: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

例: .env（必要最小限）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_station_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
OPENAI_API_KEY=sk-...
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

設定値は kabusys.config.settings 経由で参照できます。未設定の必須キーを参照すると ValueError が発生します。

---

## 使い方（簡易ガイド）

以下は主要機能の簡単な使用例です。実行前に .env を準備し、必要な Python パッケージをインストールしてください。

- DuckDB 接続を作る例
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))  # settings は kabusys.config.settings

- 日次 ETL を実行する
  ```
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのセンチメントをスコア化する（OpenAI API キーが必要）
  ```
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026,3,20))
  print(f"{count} 銘柄を書き込みました")
  ```

- 市場レジームの判定
  ```
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査 DB 初期化
  ```
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  ```

- 設定値の参照
  ```
  from kabusys.config import settings
  print(settings.env, settings.log_level, settings.duckdb_path)
  ```

注意点:
- OpenAI 呼び出しが失敗した場合、news/regime の実装は安全側（macro_sentiment=0.0 等）で継続します。
- J-Quants API 呼び出しは内部でレート制御・リトライ・401 のトークン自動リフレッシュを行います。

---

## 環境変数一覧（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（ai/news_nlp / regime_detector で使用）

オプション / デフォルトあり:
- KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
- LOG_LEVEL — DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（monitoring 用）パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動ロードを無効化

---

## ディレクトリ構成

主要ファイル / ディレクトリ（src/kabusys 以下）

- __init__.py
- config.py — 環境変数読み込み・settings
- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメント（score_news）
  - regime_detector.py — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch / save）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）、ETLResult
  - etl.py — ETL インターフェース（ETLResult 再エクスポート）
  - news_collector.py — RSS 収集（fetch_rss / 前処理）
  - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
  - quality.py — データ品質チェック（check_missing_data, check_spike, ...）
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - audit.py — 監査ログスキーマ作成 / init_audit_db
- research/
  - __init__.py
  - factor_research.py — calc_momentum, calc_value, calc_volatility
  - feature_exploration.py — calc_forward_returns, calc_ic, factor_summary, rank

（テスト、ドキュメント、CI の構成はリポジトリにより異なります）

---

## 開発者向け補足

- 自動で .env を読み込む仕組みはプロジェクトルート（.git または pyproject.toml がある場所）を起点に探索します。テストで環境読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- OpenAI 呼び出し関数はユニットテスト容易化のためモックしやすい構造（内部 _call_openai_api を patch）を設計上採用しています。
- DuckDB の executemany は空リストを受け付けないバージョンがあるため、コード中では呼び出し前に空チェックが入っています。
- ETL の各ステップは独立して例外処理され、部分失敗しても他ステップは継続します（結果は ETLResult に集約）。

---

## トラブルシューティング / よくある質問

- .env が読み込まれない
  - プロジェクトルートの検出ロジックは __file__ を起点に親ディレクトリを探索します。作業ディレクトリ（CWD）ではなくパッケージファイルの位置を基にするため、開発環境によっては .env を正しい場所に置く必要があります。
  - 自動ロードを無効化している可能性があるので KABUSYS_DISABLE_AUTO_ENV_LOAD を確認してください。

- OpenAI・J-Quants の API エラー
  - 多くのケースで内部リトライ・フォールバックが実装されていますが、API キーが無い／無効な場合は ValueError が発生します。環境変数を確認してください。
  - API レート制限や 5xx は指数バックオフでリトライします。

- DuckDB スキーマの初期化
  - 監査ログなど専用スキーマは kabusys.data.audit.init_audit_db() を使って初期化してください。

---

必要があれば、README にサンプル .env.example のテンプレート、より詳細な API 仕様、実行用 CLI（cron / Airflow 連携例）や CI 設定の章を追加できます。どの追加情報が必要か教えてください。