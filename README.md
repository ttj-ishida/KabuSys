# KabuSys

日本株向けの自動売買 / データプラットフォーム用 Python ライブラリです。  
ETL、ニュースNLP（LLM を用いたセンチメント）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログなど、バックテスト・運用で必要となる主要機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的とするモジュール群をまとめたパッケージです。

- J-Quants API からの市場データ取得（株価・財務・カレンダー）と DuckDB への保存（ETL）
- RSS ニュース収集と前処理、LLM（OpenAI）を用いたニュースセンチメント集計
- マクロ＋テクニカル指標を使った市場レジーム判定（bull / neutral / bear）
- ファクター（モメンタム・バリュー・ボラティリティ等）の計算・探索
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル→発注→約定の追跡用テーブル群）の初期化ユーティリティ

設計方針としては「ルックアヘッドバイアス防止」「冪等性」「外部 API に対する堅牢なリトライ/レート制御」「DuckDB を中心としたローカル DB 保存」「テスト可能性（依存注入）」を重視しています。

---

## 主な機能一覧

- data.jquants_client
  - J-Quants API からの取得（株価、財務、上場情報、カレンダー）と DuckDB 保存（冪等）
  - レートリミット（120 req/min）とリトライ、401 の自動トークンリフレッシュ対応
- data.pipeline
  - 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）を一括実行
  - ETLResult による実行サマリ返却
- data.news_collector
  - RSS フィード取得、前処理、raw_news への冪等保存
  - SSRF / Gzip bomb 等のセキュリティ対策
- ai.news_nlp
  - 指定ウィンドウのニュースを銘柄別に集約し OpenAI（gpt-4o-mini）でセンチメント評価
  - バッチ化、リトライ、レスポンスバリデーション、ai_scores テーブルへの保存
- ai.regime_detector
  - ETF 1321 の MA200 乖離（70%）とマクロニュース LLM センチメント（30%）を合成し日次で市場レジーム判定
- research
  - ファクター計算（モメンタム・バリュー・ボラティリティ）、将来リターン、IC 計算、z-score 正規化など
- data.quality
  - 欠損チェック、スパイク検出、重複チェック、日付整合性チェック
- data.audit
  - signal_events / order_requests / executions 等の監査テーブルを冪等に初期化するユーティリティ

---

## セットアップ手順

前提:
- Python 3.10+（typing の一部で union 型表記などを利用）
- DuckDB、OpenAI SDK、defusedxml などの依存ライブラリ

1. リポジトリをクローンし、パッケージインストール（開発モード推奨）:

   ```bash
   git clone <repo-url>
   cd <repo-root>
   pip install -e ".[dev]"    # setup.cfg / pyproject に依存関係がある想定
   ```

   依存例（requirements）:
   - duckdb
   - openai
   - defusedxml

2. 環境変数の設定 (.env を推奨)
   - プロジェクトルート（.git または pyproject.toml のある場所）に `.env` / `.env.local` を置くと自動で読み込まれます。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須環境変数（主なもの）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - OPENAI_API_KEY: OpenAI の API キー（score_news / score_regime で使われる）
   - KABU_API_PASSWORD: kabuステーション API パスワード（発注系で使用）
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
   - DUCKDB_PATH (任意): デフォルトは `data/kabusys.duckdb`
   - SQLITE_PATH (任意): 監視用途の SQLite（デフォルト `data/monitoring.db`）
   - KABUSYS_ENV (任意): development / paper_trading / live（デフォルト development）
   - LOG_LEVEL (任意): DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

   .env の例（.env.example を作成して利用）:

   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

3. データベース用ディレクトリ作成（必要に応じて）:

   ```bash
   mkdir -p data
   ```

---

## 使い方（主要な例）

以下はライブラリを直接呼ぶ簡単なサンプルです。実運用ではジョブスケジューラ（cron / Airflow 等）から呼ぶ想定です。

- DuckDB 接続を開く（例: ファイル DB）

  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL を実行

  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントのスコア付け（score_news）

  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # OPENAI_API_KEY が環境変数に設定されていれば api_key 引数は不要
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {n_written}")
  ```

- 市場レジーム判定（score_regime）

  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- ファクター計算の例（研究用途）

  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date

  momentum = calc_momentum(conn, date(2026, 3, 20))
  value = calc_value(conn, date(2026, 3, 20))
  volatility = calc_volatility(conn, date(2026, 3, 20))
  ```

- 監査テーブルの初期化（取引監査ログ）

  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # conn_audit に対して order_requests / signal_events / executions テーブルが作成されます
  ```

- 設定取得

  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)
  ```

注意点:
- LLM（OpenAI）呼び出しは外部 API を使用するため使用量に注意してください。
- score_news / score_regime は API 呼び出しに失敗してもフォールバック（0.0 等）する設計ですが、API キーは必須です（未設定時は ValueError が発生します）。
- DuckDB の executemany に空リストを渡すと失敗するバージョンがあるため、内部で確認を行っています。

---

## ディレクトリ構成

プロジェクトの主要なファイル/モジュール（抜粋）は以下のとおりです。

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数・設定読み込みロジック（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py            # ニュースセンチメント（OpenAI）関連
    - regime_detector.py     # 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント + DuckDB 保存
    - pipeline.py            # 日次 ETL のオーケストレーション
    - etl.py                 # ETLResult の再エクスポート
    - calendar_management.py # 市場カレンダー管理（営業日判定等）
    - stats.py               # 汎用統計ユーティリティ（z-score）
    - quality.py             # データ品質チェック
    - news_collector.py      # RSS 収集・保存
    - audit.py               # 監査ログテーブル初期化
  - research/
    - __init__.py
    - factor_research.py     # ファクター（momentum/value/volatility）
    - feature_exploration.py # 将来リターン / IC / サマリー等
  - (そのほか strategy / execution / monitoring 等のモジュールが想定される)

パッケージは必要に応じて拡張できるよう分離されています（ai, data, research, execution, monitoring 等）。

---

## 実装上の重要な挙動・注意事項

- .env の自動読み込み
  - 実行環境にてプロジェクトルート（.git または pyproject.toml）を探索し、`.env` と `.env.local` を自動的にロードします。
  - ロード優先度: OS 環境変数 > .env.local > .env
  - テスト等で自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- Look-ahead bias の防止
  - 多くの処理（score_news, score_regime, ETL, ファクター計算）は内部で datetime.today() や date.today() を直接参照せず、呼び出し側から target_date を渡す設計になっています。バックテストでの利用時は必ず過去日付を指定してください。

- 冪等性
  - DuckDB への保存は基本的に ON CONFLICT DO UPDATE を使った冪等保存になっています（save_* 関数）。

- セキュリティ
  - news_collector は SSRF 対策、XML パースの安全化、レスポンスサイズ制限などセーフガードを実装しています。

---

## テスト・開発

- ユニットテストを書く際は、外部 API 呼び出し（OpenAI / J-Quants / URL open）をモックして実行してください。コード内にはモック差し替えを想定した設計（例えば _call_openai_api をパッチ）があります。
- 環境変数はテスト用に `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定し、必要なキーをテストコード内で注入してください。

---

## サポート / 貢献

バグ報告やプルリクエストはリポジトリの issue/PR を利用してください。設計方針（ルックアヘッド回避、冪等性、テスト容易性）を重視したコードベースですので、互換性やセキュリティに配慮した変更を歓迎します。

---

README の内容を参照してセットアップ・初期化を行ってください。必要であれば README に追記するサンプルや運用手順（cron ジョブ、Airflow DAG、Slack 通知フローなど）を追加できます。