# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP スコアリング（OpenAI）、ファクター計算・リサーチユーティリティ、監査ログ（約定トレース）などを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムおよびデータプラットフォーム向けのモジュール群です。主な目的は以下です。

- J-Quants API を用いた株価・財務・マーケットカレンダーの差分 ETL（DuckDB への保存、冪等性を意識）
- RSS ニュース収集と OpenAI を用いた記事/銘柄ごとのセンチメント（ai_scores）生成
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの LLM センチメントの合成）
- ファクター計算（モメンタム、バリュー、ボラティリティ等）とリサーチ用ユーティリティ（forward returns, IC 等）
- データ品質チェック、監査ログスキーマの初期化・管理
- kabuステーション 等の実行・監視に必要な設定管理

設計上の特徴:
- ルックアヘッドバイアスを避ける実装（多くの関数は明示的な target_date を受け取り、date.today() を直接参照しない）
- DuckDB を中心としたローカルデータ格納と効率的な SQL 処理
- API 呼び出しはリトライ・バックオフ・レート制御を備え、フェイルセーフに設計

---

## 主な機能一覧

- data/
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（認証・ページネーション・保存関数）
  - market calendar 管理（営業日判定、next/prev/trading days）
  - ニュース収集（RSS -> raw_news、SSRF/サイズ対策、トラッキング除去）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマ初期化（audit.init_audit_db / init_audit_schema）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news: 銘柄単位にまとめたニュースを OpenAI でスコア化し ai_scores に保存
  - regime_detector.score_regime: ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成して市場レジームを market_regime に保存
- research/
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- config
  - 環境変数ベースの設定管理（.env / .env.local 自動ロード、必要な環境変数の取得）

---

## セットアップ手順

前提:
- Python 3.10+（型ヒントで | を使用しているため）
- Git が利用可能（プロジェクトルート検出に使用される）

1. リポジトリをクローン:
   - git clone <repo-url>
   - cd <repo>

2. 仮想環境を作成（推奨）:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール:
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （プロジェクトに pyproject.toml / requirements.txt があれば `pip install -e .` または `pip install -r requirements.txt` を使用）

4. 環境変数 / .env の設定:
   - プロジェクトルートに `.env`（必要に応じて `.env.local`）を用意します。主なキー:

     - 必須（ETL / J-Quants 用）:
       - JQUANTS_REFRESH_TOKEN
     - 必須（kabu API を使う場合）:
       - KABU_API_PASSWORD
       - KABU_API_BASE_URL (省略可、デフォルト: http://localhost:18080/kabusapi)
     - OpenAI:
       - OPENAI_API_KEY （score_news / score_regime で使用）
     - データベース / パス等（省略可、デフォルトあり）:
       - DUCKDB_PATH (例: data/kabusys.duckdb)
       - SQLITE_PATH (例: data/monitoring.db)
       - PID_FILE_PATH, KILL_FLAG_PATH, など
     - 実行環境・ログ:
       - KABUSYS_ENV (development / paper_trading / live)
       - LOG_LEVEL (DEBUG/INFO/...)
     - 自動 .env ロード無効化:
       - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   - config.py はプロジェクトルート（.git または pyproject.toml を検出）から .env / .env.local を自動で読み込みます。

5. データ格納ディレクトリ作成:
   - mkdir -p data

---

## 使い方（主要例）

以下はライブラリを Python インタプリタやスクリプトから使う際の例です。DuckDB 接続は duckdb.connect(path) で作成します。

- 共通: settings の利用
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)  # Path オブジェクト
  ```

- DuckDB 接続を作って ETL を実行（1日分）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースの NLP スコアリング（OpenAI API 必須）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  # OPENAI_API_KEY が環境変数でセットされているか、api_key 引数で渡す
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written: {n_written}")
  ```

- 市場レジーム判定
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- ファクター計算例
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  import duckdb
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  date_ = date(2026, 3, 20)
  mom = calc_momentum(conn, date_)
  vol = calc_volatility(conn, date_)
  val = calc_value(conn, date_)
  ```

- 監査ログ DB の初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # これで監査テーブル(signal_events, order_requests, executions 等)が作成されます
  ```

- カレンダー・営業日ユーティリティ
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  import duckdb
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

注意点:
- OpenAI 呼び出しを含む機能（news_nlp, regime_detector）は OPENAI_API_KEY が必要です。api_key を直接渡すことも可能です。
- ETL 周りは J-Quants のリフレッシュトークン（JQUANTS_REFRESH_TOKEN）を必要とします。
- 多くの関数は target_date を明示的に渡すことでルックアヘッドバイアスを防いでいます。バックテスト時は注意してください。

---

## 設定 (環境変数)

主な環境変数（config.Settings から参照）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API パスワード
- KABU_API_BASE_URL — デフォルト http://localhost:18080/kabusapi
- OPENAI_API_KEY — OpenAI API キー（news/regime で使用）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 通知用（任意）
- DUCKDB_PATH — デフォルト data/kabusys.duckdb
- SQLITE_PATH — デフォルト data/monitoring.db
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START — 実行監視用
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視閾値
- KABUSYS_ENV — development / paper_trading / live
- LOG_LEVEL — DEBUG/INFO/...
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — .env 自動ロードを無効にする

config.py はプロジェクトルート（.git または pyproject.toml）から .env を自動ロードします。変更したい場合は .env.local を用いて上書きできます。

---

## ディレクトリ構成

主要ファイル／ディレクトリ（src/kabusys 内）:

- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py         — ニュースを銘柄別にまとめて OpenAI でスコア化し ai_scores に保存
  - regime_detector.py  — MA200 とマクロニュースで市場レジームを判定
- data/
  - __init__.py
  - jquants_client.py   — J-Quants API クライアント（取得・保存）
  - pipeline.py         — ETL パイプライン（run_daily_etl 等）および ETLResult
  - etl.py              — ETLResult の再エクスポート
  - news_collector.py   — RSS 取得・前処理・保存
  - calendar_management.py — market_calendar 管理（営業日判定・更新ジョブ）
  - quality.py          — データ品質チェック（欠損/スパイク/重複/日付不整合）
  - stats.py            — zscore_normalize 等の統計ユーティリティ
  - audit.py            — 監査ログスキーマ定義・初期化
- research/
  - __init__.py
  - factor_research.py  — モメンタム/バリュー/ボラティリティ計算
  - feature_exploration.py — forward returns, IC, factor summary, rank
- monitoring / execution / strategy 等（パッケージ化想定） — __all__ に含まれる想定のモジュール群

（プロジェクトルートには .env / .env.local / pyproject.toml や tests/ 等がある想定）

---

## 実装上の重要な注意点

- ルックアヘッドバイアスの回避: 多くの関数は target_date パラメータを使用し、date.today() を直接参照しない方針です。バックテストや再現性のある処理のためにこの設計を尊重してください。
- 冪等性: J-Quants の保存関数や監査スキーマ初期化は冪等（ON CONFLICT / IF NOT EXISTS）を意識して実装されています。複数回実行してもデータの一貫性が保たれるようになっています。
- API 呼び出しはレートリミット・リトライ・指数バックオフ・401 リフレッシュ処理等を備えていますが、外部サービスの仕様変更に注意してください。
- ニュース取得では SSRF・XML Bomb・大容量レスポンス対策を実装しています。fetch_rss() は HTTP(S) スキームとホストの検証を行います。

---

## 開発とテスト

- 開発中は仮想環境を利用し、必要なモック（OpenAI / HTTP）を使ってユニットテストを行うことを推奨します。news_nlp や regime_detector では内部の API 呼び出しヘルパーをモックすることでテスト可能です（関数名にコメントあり）。
- 自動 .env ロードはテストで邪魔な場合、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。

---

## ライセンス / 貢献

（この README では記載していません。実プロジェクトに合わせて LICENCE、CONTRIBUTING.md を追加してください。）

---

README はここまでです。必要であれば、セットアップスクリプト（requirements.txt / dev-requirements）、実行用サンプルスクリプト、または各モジュールの API リファレンス（docstring から生成）を追加で作成します。どれを優先しますか？