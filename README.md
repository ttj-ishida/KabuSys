# KabuSys

日本株向けのデータプラットフォーム & 自動売買支援ライブラリです。  
ETL、ニュースNLP、市場レジーム判定、ファクター計算、監査ログなどの機能を備え、J-Quants / kabuステーション / OpenAI と連携して運用・研究用途に利用できます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の主要コンポーネントを提供します。

- データ収集・ETL（J-Quants API 経由の株価・財務・カレンダー取得、DuckDB への保存）
- ニュース収集・前処理（RSS）とニュースを用いた銘柄ごとの AI スコアリング（OpenAI）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースセンチメントを合成）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC 計算、Zスコア正規化）
- 監査ログスキーマ（signal → order_request → execution のトレーサビリティ）
- データ品質チェック（欠損・スパイク・重複・日付整合性）

設計上の注意点：
- ルックアヘッドバイアスを防ぐため、内部関数は明示的な target_date を受け取り、date.today() を直接参照しないようにしています。
- DuckDB を主要なデータストアとして使用し、ETL は冪等に設計されています。
- OpenAI 呼び出しはリトライやパースのフォールバックを備えています。

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（取得 / 保存関数）
  - 市場カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / calendar_update_job）
  - ニュース収集（RSS -> raw_news）
  - データ品質チェック（check_missing_data / check_spike / check_duplicates / check_date_consistency）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 汎用統計（zscore_normalize）
- ai
  - ニュース NLP（score_news: ニュースを銘柄ごとにスコア化して ai_scores に保存）
  - 市場レジーム判定（score_regime: MA とマクロセンチメントから regime を保存）
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量解析（calc_forward_returns / calc_ic / factor_summary / rank）
- config
  - 環境変数の自動読み込み (.env / .env.local の順) と Settings クラス

---

## セットアップ手順

前提:
- Python 3.10+ を推奨（typing | union など使用）
- DuckDB（Python パッケージ）、OpenAI Python SDK、defusedxml 等が必要

1. リポジトリをクローンしてパッケージをインストール（開発モード推奨）
   ```
   git clone <repo-url>
   cd <repo-dir>
   pip install -e .
   ```
   あるいは必要パッケージを個別にインストール:
   ```
   pip install duckdb openai defusedxml
   ```

2. 環境変数を設定
   - プロジェクトルートに `.env` や `.env.local` を配置すると、自動的に読み込まれます（既定：OS環境変数 > .env.local > .env）。
   - 自動読み込みを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須で ETL に使用）
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
   - KABU_API_PASSWORD: kabuステーション API パスワード（発注等がある場合）
   - KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知に使用（オプション）
   - DUCKDB_PATH: デフォルト DB パス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START 他監視パラメータ
   - KABUSYS_ENV: {development, paper_trading, live}（デフォルト development）
   - LOG_LEVEL: {DEBUG, INFO, WARNING, ERROR, CRITICAL}（デフォルト INFO）

3. データベースの準備
   - DuckDB ファイルを使う場合は、アプリケーション内で `duckdb.connect(settings.duckdb_path)` のように接続します。
   - 監査ログ専用 DB を初期化する例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```

---

## 使い方（サンプル）

以下は主要なユースケースの簡単な例です。実運用ではログ設定や例外処理、環境変数管理を適切に行ってください。

- DuckDB に接続して ETL を日次実行（run_daily_etl）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースをスコア化して ai_scores に保存（score_news）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY が環境変数にセットされている前提
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"wrote {written} ai_scores")
  ```

- 市場レジーム判定を実行（score_regime）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログスキーマの初期化（既存コネクションに追加）
  ```python
  from kabusys.data.audit import init_audit_schema
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

- ファクター計算（研究用）
  ```python
  from kabusys.research.factor_research import calc_momentum
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  res = calc_momentum(conn, target_date=date(2026,3,20))
  print(len(res), res[:3])
  ```

---

## 環境変数（まとめ）

主に Settings クラスで参照されるキー（.env ファイルに記載する例）:

- JQUANTS_REFRESH_TOKEN (必須)
- OPENAI_API_KEY (score_news / score_regime で必須)
- KABU_API_PASSWORD
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- LINE_CHANNEL_ACCESS_TOKEN
- LINE_USER_ID
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PID_FILE_PATH (デフォルト: data/execution.pid)
- KILL_FLAG_PATH (デフォルト: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (0/1)
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV (development / paper_trading / live)
- LOG_LEVEL (DEBUG / INFO / WARNING / ERROR / CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 を設定すると .env 自動読み込みを無効化)

.env.example をプロジェクトルートに置いて、例に従って `.env` を作成してください。

---

## ディレクトリ構成

主要ファイルとディレクトリ（src/kabusys 配下）:

- __init__.py
  - パッケージのエクスポート設定（data, strategy, execution, monitoring 等）
- config.py
  - 環境変数読み込み・Settings クラス（自動 .env ロード、バリデーション）
- ai/
  - __init__.py
  - news_nlp.py: ニュースを銘柄別に集約して OpenAI でスコアリング（score_news）
  - regime_detector.py: ETF 1321 の MA とマクロニュースで市場レジームを判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py: J-Quants API クライアント（fetch_* / save_*）
  - pipeline.py: ETL 管理・run_daily_etl など
  - calendar_management.py: 市場カレンダーの判定・更新ロジック
  - news_collector.py: RSS 取得・前処理・raw_news 保存ロジック
  - quality.py: データ品質チェック（欠損・スパイク・重複・日付整合性）
  - stats.py: 汎用統計ユーティリティ（zscore_normalize）
  - audit.py: 監査ログスキーマ定義と初期化（init_audit_schema / init_audit_db）
  - etl.py: ETLResult の再エクスポート
- research/
  - __init__.py
  - factor_research.py: モメンタム/バリュー/ボラティリティの計算
  - feature_exploration.py: 将来リターン、IC、統計サマリー等
- その他（strategy, execution, monitoring 等のサブパッケージは __all__ に含まれていますが、ここにある主要機能を参照して下さい）

---

## 運用上の注意

- OpenAI 呼び出しにはレート制限とコストが発生します。バッチサイズやリトライ挙動は設定済みですが、プロダクション環境ではモニタリングを行ってください。
- J-Quants API のリクエストもレート制限があるため、ETL は RateLimiter を介して実行されます。ID トークンの自動リフレッシュをサポートします。
- DuckDB クエリや ETL は大きなデータ量を扱うため、ディスク容量や I/O 性能に注意してください。
- ニュースの RSS 取得では SSRF 対策や読み込みサイズ制限が実装されていますが、ソース追加時は信頼できる RSS を登録してください。

---

必要であれば、README にサンプル .env.example、より詳細な API 使用例（jquants_client の fetch/save 関数の挙動や news_collector の RSS 設定方法）、運用チェックリストなどを追加します。どの箇所を詳述したいか教えてください。