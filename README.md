# KabuSys

日本株向け自動売買／データプラットフォーム用ライブラリです。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースセンチメント（LLM）、市場レジーム判定、監査ログなどを含むユーティリティ群を提供します。

---

## プロジェクト概要

KabuSys は日本株向けのデータパイプラインと研究・運用支援機能を集めた Python モジュール群です。主な目的は以下の通りです。

- J-Quants API を使った株価・財務・マーケットカレンダーの差分ETL
- DuckDB を使ったデータ保存・集計
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュースの収集と OpenAI（gpt-4o-mini）を用いた銘柄別センチメント解析
- ETF 指標とマクロニュースを用いた市場レジーム判定（bull/neutral/bear）
- 監査ログ（signal / order_request / executions）用スキーマ初期化ユーティリティ
- 研究用のファクター計算・統計ユーティリティ

設計方針として「ルックアヘッドバイアスを避ける」「DuckDB によるローカル処理」「外部 API 呼び出し時の堅牢なリトライとフォールバック」を重視しています。

---

## 主な機能一覧

- data
  - jquants_client: J-Quants からの取得・DuckDB への保存（差分・ページネーション対応、トークン自動リフレッシュ、レート制御、リトライ）
  - pipeline / etl: 日次 ETL（calendar / prices / financials）・差分取得・品質チェック（ETLResult を返す）
  - calendar_management: 市場カレンダー更新・営業日判定ユーティリティ
  - news_collector: RSS からのニュース収集（SSRF 対策、前処理、冪等保存）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログスキーマ初期化（signal_events / order_requests / executions）
  - stats: z-score 正規化などの統計ユーティリティ
- ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメント取得・ai_scores へ保存（OpenAI JSON mode）
  - regime_detector.score_regime: ETF(1321) の MA200 乖離とマクロニュースセンチメントを合成して market_regime に書き込み
- research
  - factor_research: モメンタム／ボラティリティ／バリューの計算
  - feature_exploration: 将来リターン/IC/要約等の分析ユーティリティ

---

## セットアップ手順

1. リポジトリをクローン（例）
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. Python 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール  
   （本リポジトリに requirements.txt が無い場合、主要な依存は下記）
   ```
   pip install duckdb openai defusedxml
   ```
   プロジェクトを開発モードでインストールする場合:
   ```
   pip install -e .
   ```

4. 環境変数の準備  
   プロジェクトルートに `.env` / `.env.local` を作成して設定できます。自動ロード機能が有効（デフォルト）で、優先順位は:
   OS 環境変数 > .env.local > .env
   自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   主要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能利用時に必須）
   - KABU_API_PASSWORD: kabu ステーション API パスワード（発注系）
   - KABU_API_BASE_URL: kabu API の base URL（デフォルト http://localhost:18080/kabusapi）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
   - LOG_LEVEL: DEBUG, INFO, WARNING, ERROR, CRITICAL（デフォルト INFO）
   - KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT などの監視設定

   例 .env（最小）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（サンプル）

以下は基本的な Python からの使用例です。DuckDB 接続には `duckdb.connect()` を使用します。

- DuckDB 接続と監査DB初期化
  ```python
  import duckdb
  from kabusys.config import settings
  from kabusys.data.audit import init_audit_db

  conn = duckdb.connect(str(settings.duckdb_path))
  # 監査スキーマを初期化（ファイルがなければ作成）
  init_audit_db(settings.duckdb_path)
  ```

- 日次 ETL を実行（市場カレンダー → 株価 → 財務 → 品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn)  # target_date を指定しなければ今日（内部では trading_day に調整）
  print(result.to_dict())
  ```

  run_daily_etl は ETLResult を返します。エラーは result.errors に集約されます。

- ニュースセンチメント（AI）を実行して ai_scores に書き込む
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # 必要: OPENAI_API_KEY を環境変数に設定
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written {written} codes")
  ```

  - LLM 呼び出しで失敗した場合は基本的にフェイルセーフ（そのチャンクはスキップ）します。

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- ファクター計算（研究用）
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
  from datetime import date

  mom = calc_momentum(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))
  ```

注意点:
- AI 機能を使う場合は OpenAI の課金・レート制限に注意してください。
- J-Quants の API 利用には JQUANTS_REFRESH_TOKEN が必要です（jquants_client が ID トークンを取得して使用します）。
- モジュールは「ルックアヘッドバイアスを避ける」設計になっており、target_date 未満のデータのみを参照する等の対策が施されています。

---

## よく使う API（抜粋）

- kabusys.config.settings  
  環境変数から設定値を取得します。例:
  - settings.jquants_refresh_token
  - settings.duckdb_path
  - settings.env / settings.is_live など

- kabusys.data.pipeline.run_daily_etl(conn, target_date=None, id_token=None, ...)  
  日次 ETL のメインエントリポイント。ETLResult を返します。

- kabusys.data.jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar  
  J-Quants からのデータ取得ユーティリティ。

- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)  
  ニュースを LLM でスコア化し ai_scores テーブルへ保存します。

- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)  
  ETF(1321) の MA200 とマクロニュースの LLM スコアを合成して market_regime テーブルへ書き込みます。

- kabusys.data.audit.init_audit_db(path) / init_audit_schema(conn)  
  監査ログ用 DB の初期化（テーブルとインデックス作成）。

---

## ディレクトリ構成

主要ファイル／モジュール（簡易ツリー）

- src/kabusys/
  - __init__.py
  - config.py  -- 環境変数・設定管理（.env 自動ロード機能）
  - ai/
    - __init__.py
    - news_nlp.py       -- ニュースセンチメント（OpenAI）
    - regime_detector.py-- 市場レジーム判定（ETF MA200 + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py -- J-Quants API クライアント（取得・保存）
    - pipeline.py       -- ETL パイプライン（run_daily_etl 等）
    - etl.py            -- ETLResult 再エクスポート
    - news_collector.py -- RSS 収集（SSRF 対策、XML パース安全化）
    - calendar_management.py -- 市場カレンダー管理・営業日判定
    - quality.py        -- データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py          -- zscore_normalize 等
    - audit.py          -- 監査ログスキーマ定義・初期化（signal/order/execution）
  - research/
    - __init__.py
    - factor_research.py -- モメンタム・ボラティリティ・バリュー計算
    - feature_exploration.py -- 将来リターン / IC / 統計サマリ

---

## 動作・設計上の補足（重要）

- 自動 .env ロード:
  - パッケージの config モジュールは実行時にプロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を自動ロードします。
  - 無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - 優先順位: OS 環境変数 > .env.local > .env

- LLM 呼び出し:
  - OpenAI の Chat Completions を JSON mode で使用します（モデル: gpt-4o-mini を想定）。
  - API エラー時はエクスポネンシャルバックオフやフォールバック（スコア = 0.0 等）で安全側に復帰します。

- J-Quants API:
  - レート制限（120 req/min）を守るため内部にレートリミッタを実装しています。
  - 401 時はリフレッシュトークンを使って ID トークンを自動更新します（1回のみリトライ）。
  - DuckDB への保存は冪等（ON CONFLICT DO UPDATE）で重複を防止します。

- Look-ahead バイアス防止:
  - 多くの関数は内部で datetime.today() や date.today() に依存しないように設計されています。必ず target_date を明示したり、ETL の対象日を調整する設計です。

---

## 開発・貢献

- 新機能追加やバグ修正の際は、テストを追加してください。AI 部分や外部 API 呼び出しはモック可能な設計になっています（内部の _call_openai_api 等をパッチする等）。
- セキュリティ: news_collector は SSRF ・ XML Bomb 等に配慮して実装されていますが、実運用では追加の監査や外部接続制限を推奨します。

---

必要であれば、README にサンプル .env.example、requirements.txt、あるいは具体的なデプロイ手順（systemd サービスや監視セットアップ）も追加できます。どの情報を追記しましょうか？