# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
ETL（J-Quants からのデータ取得）・ニュース収集とAIによるセンチメント評価・市場レジーム判定・ファクター計算・監査ログなど、アルゴリズム取引基盤の主要コンポーネントを提供します。

主な想定利用ケース
- J-Quants API を用いた日次 ETL（株価・財務・マーケットカレンダー）の自動取り込み
- RSS ニュース収集 → OpenAI によるニュースセンチメント評価 → ai_scores の生成
- ETF とマクロニュースを合成した市場レジーム判定（bull/neutral/bear）
- リサーチ用ファクター計算（モメンタム・バリュー・ボラティリティ）
- 監査ログ用の DuckDB スキーマ初期化（シグナル→発注→約定のトレーサビリティ）

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルートを探索）
  - 環境変数の必須チェックを行う `kabusys.config.settings`
- データ取得・保存（J-Quants クライアント）
  - 株価日足（OHLCV）、財務データ、JPX マーケットカレンダーの取得・DuckDB への冪等保存
  - レート制限 / リトライ / トークン自動リフレッシュ対応
- ETL パイプライン
  - 日次 ETL: カレンダー、株価、財務の差分取得・保存・品質チェック
  - 品質チェック（欠損、重複、スパイク、日付不整合）
- ニュース収集・NLP
  - RSS 取得、前処理、raw_news への保存、news_symbols との紐付け（news_collector）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメントスコアリング（`kabusys.ai.news_nlp.score_news`）
  - マクロニュース + ETF MA を用いた市場レジーム判定（`kabusys.ai.regime_detector.score_regime`）
  - API 呼び出しはリトライ / バックオフ / フォールバックを備える（失敗時は安全側の値で継続）
- リサーチ用ユーティリティ
  - モメンタム / ボラティリティ / バリュー計算（`kabusys.research`）
  - 将来リターン・IC・統計サマリー等の解析ユーティリティ
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブルの DDL とインデックス、初期化ユーティリティ
  - 監査用の専用 DuckDB 初期化関数を提供（UTC タイムゾーン固定）
- 汎用ツール
  - Z スコア正規化等の統計ユーティリティ（`kabusys.data.stats`）
  - 市場カレンダーの営業日判定ユーティリティ（next/prev/get_trading_days 等）

---

## 動作環境 / 前提

- Python 3.10 以上（PEP 604 の型アノテーション `|` を使用）
- 主な依存パッケージ（最低限）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス: J-Quants API、各 RSS ソース、OpenAI API へアクセスできること

---

## セットアップ手順

1. Python 仮想環境を作成・有効化（例）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

2. 必要パッケージをインストール
   - 最低限:
     ```
     pip install duckdb openai defusedxml
     ```
   - 開発/パッケージ構成がある場合は pyproject/requirements に従ってください。

3. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml が存在する場所）に `.env` を置くと自動読み込みされます。
   - 読み込み優先順位: OS 環境変数 > .env.local > .env
   - 自動読み込みを無効化するには: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

   推奨される最低必須環境変数（.env の例）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development   # development / paper_trading / live
   LOG_LEVEL=INFO
   ```

   - データベースのパスは環境変数で上書き可能:
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
   - 監視・閾値:
     - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
   - PID ファイルパス:
     - PID_FILE_PATH (default: data/execution.pid)

4. DuckDB ファイル用ディレクトリを作る（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（主要例）

以下は簡単な Python スニペット例です。DuckDB 接続を渡して各機能を呼び出します。

- 日次 ETL 実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（OpenAI API キーは環境変数 OPENAI_API_KEY から取得）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"ai_scores に書き込んだ銘柄数: {written}")
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化
  ```python
  from kabusys.data.audit import init_audit_db

  conn_audit = init_audit_db("data/audit.duckdb")
  # conn_audit 上で監査テーブルが初期化されます
  ```

- リサーチ用ファクター計算
  ```python
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  date0 = date(2026, 3, 20)
  mom = calc_momentum(conn, date0)
  val = calc_value(conn, date0)
  vol = calc_volatility(conn, date0)
  ```

- 設定値を参照する
  ```python
  from kabusys.config import settings

  print(settings.jquants_refresh_token)  # 未設定なら ValueError
  print(settings.kabu_api_base_url)      # デフォルト: http://localhost:18080/kabusapi
  print(settings.is_live)
  ```

注意点
- OpenAI 呼び出しや外部 API はネットワーク依存でコストがかかる場合があるため、ローカル実行時はキーや呼び出し回数に注意してください。
- 関数群は「ルックアヘッドバイアス」を避ける設計（内部で date.today() を直接参照しない）になっています。テスト/バックテスト時は target_date を明示的に渡してください。

---

## よく使う API / モジュール一覧

- kabusys.config
  - settings: 環境変数からの設定取得（必須値チェック含む）
- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token
- kabusys.data.pipeline
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - ETLResult
- kabusys.data.quality
  - run_all_checks, check_missing_data, check_spike, check_duplicates, check_date_consistency
- kabusys.data.news_collector
  - fetch_rss, preprocess_text, news 保存ワークフロー（raw_news への保存は実装側）
- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None)
- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.data.audit
  - init_audit_schema / init_audit_db

---

## .env 自動読み込みの挙動

- パッケージロード時にプロジェクトルート（.git または pyproject.toml が見つかる場所）を探索して `.env` と `.env.local` を自動読み込みします。
  - 優先度: OS 環境変数 > .env.local > .env
  - OS 環境変数は保護され、.env による上書きは行われません（.env.local は上書き可能）。
- 自動読み込みを無効化するには環境変数を設定:
  ```
  KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

---

## ディレクトリ構成（主要ファイル）

以下はソースの主要なディレクトリ構成（src/kabusys）です。README 用に要約しています。

- src/kabusys/
  - __init__.py
  - config.py                  # 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py              # ニュースのセンチメント評価（OpenAI）
    - regime_detector.py       # 市場レジーム判定（ETF MA + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py        # J-Quants API クライアント + DuckDB 保存
    - pipeline.py              # ETL パイプライン（run_daily_etl 等）
    - quality.py               # データ品質チェック
    - news_collector.py        # RSS 収集と前処理
    - stats.py                 # 統計ユーティリティ（zscore_normalize 等）
    - calendar_management.py   # マーケットカレンダー管理（営業日判定等）
    - audit.py                 # 監査ログスキーマ初期化
    - etl.py                   # ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py       # モメンタム/バリュー/ボラティリティ計算
    - feature_exploration.py   # 将来リターン・IC・統計サマリー

---

## 運用上の注意 / ベストプラクティス

- OpenAI / J-Quants の API キーは適切に管理し、公開リポジトリに含めないでください。
- ETL や AI 呼び出しはコストとレート制限があるため、スケジューラで適切に間隔を設定してください。
- DuckDB ファイルはバックアップ/バージョン管理の対象とするか、運用に合わせた永続化戦略を考慮してください。
- 監査ログ（audit DB）は削除しない前提で設計されています。大きくなる可能性があるためアーカイブ戦略を用意してください。
- テスト時は自動環境読み込みを無効化（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）し、必要な設定をテスト側で注入してください。

---

必要があれば、README にサンプル .env.example、CI 実行例、詳細な API 仕様（各関数の引数・返り値）を追記できます。追加で欲しい項目を教えてください。