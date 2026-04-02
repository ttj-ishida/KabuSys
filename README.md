# KabuSys

KabuSys は日本株のデータ収集・品質管理・因子計算・ニュース NLP・市場レジーム判定・監査ログ等を備えた日本株向け自動売買 / リサーチ基盤の軽量ライブラリ群です。DuckDB をデータレイヤに用い、J-Quants API / RSS / OpenAI（LLM）などと連携して日次 ETL、ファクター計算、ニュースセンチメント評価、監査ログ管理を行います。

主な設計方針
- ルックアヘッドバイアスを避ける（内部で date.today()/datetime.today() を参照しない設計）
- DuckDB を用いた SQL + Python の組合せで高速に処理
- 冪等性（ON CONFLICT 等）とフォールトトレランス（リトライ・フェイルセーフ）を重視
- 外部 API 呼び出しは明確なリトライ／レート制御を実装

---

## 機能一覧

- data（ETL / J-Quants クライアント / カレンダー管理 / ニュース収集 / 品質チェック / 監査ログ）
  - J-Quants API クライアント（fetch / save / id_token リフレッシュ / rate limiter）
  - 日次 ETL パイプライン（run_daily_etl）: 市場カレンダー、株価日足、財務データの差分取得と保存 + 品質チェック
  - market_calendar 管理、営業日判定、next/prev_trading_day 等
  - RSS ニュース収集（SSRF 保護、トラッキングパラメータ除去、前処理、raw_news への冪等保存想定）
  - データ品質チェック（欠損／スパイク／重複／日付不整合）
  - 監査ログスキーマ（signal_events / order_requests / executions）の初期化・管理
- research（ファクター計算 / 特徴量探索）
  - Momentum / Volatility / Value ファクター計算（prices_daily / raw_financials）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリ、Zスコア正規化
- ai（ニュース NLP / 市場レジーム判定）
  - ニュースセンチメント評価（gpt-4o-mini / JSON Mode）→ ai_scores 書込み（batch）
  - 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュース LLM スコアの合成）→ market_regime 書込み

---

## セットアップ手順

以下は開発環境での例です。実運用では適宜サービスや監視設定を追加してください。

1. Python 仮想環境の作成（例）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   ```

2. 必要な依存をインストール
   - このリポジトリに requirements.txt は含まれていませんが、基本的に以下のパッケージが必要です:
     - duckdb
     - openai
     - defusedxml
     - （標準ライブラリ以外のものがあれば追記してください）
   ```bash
   pip install duckdb openai defusedxml
   ```
   （プロジェクト化されていれば `pip install -e .` を想定）

3. 環境変数の用意
   - プロジェクトルートに `.env` または `.env.local` を置くと自動読み込みされます（自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
     - OPENAI_API_KEY（ai モジュールを使う場合）
   - 任意:
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
     - KABUSYS_ENV（development / paper_trading / live; デフォルト development）
     - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）

   サンプル `.env`:
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

4. DB ディレクトリ作成（必要に応じて）
   ```bash
   mkdir -p data
   ```

---

## 使い方（代表的な例）

以下は Python REPL / スクリプトでの利用例です。DuckDB 接続オブジェクト（duckdb.connect(...)）を各関数に渡して使用します。

- 日次 ETL の実行（例: 当日 ETL を実行）
  ```python
  import duckdb
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを算出して ai_scores に書く
  ```python
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print("written:", n_written)
  ```

- 市場レジーム判定（market_regime に書く）
  ```python
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 監査ログ DB の初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # テーブルが作成され、UTC タイムゾーン設定が適用されます
  ```

- カレンダー・営業日判定ユーティリティ
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

- 研究系（因子計算・IC）
  ```python
  from kabusys.research.factor_research import calc_momentum
  conn = duckdb.connect("data/kabusys.duckdb")
  factors = calc_momentum(conn, target_date=date(2026,3,20))
  ```

注意点
- OpenAI を呼ぶ関数（news_nlp / regime_detector）は api_key 引数を受け取ります。明示せずに実行する場合は環境変数 OPENAI_API_KEY を設定してください。
- ETL / 保存関数は DuckDB のスキーマ（raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, market_regime 等）を前提とします。実行前にスキーマの初期化が必要です。

---

## 主要ディレクトリ構成

下記はパッケージ内の主要ファイル・モジュール（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py               -- 環境変数・設定管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py           -- ニュースセンチメント評価（LLM 統合・バッチ処理・検証）
    - regime_detector.py    -- 市場レジーム判定（ETF 1321 MA200 + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py     -- J-Quants API クライアント + 保存関数（rate-limit / retry / id_token）
    - pipeline.py           -- ETL パイプライン（run_daily_etl / run_*_etl）
    - calendar_management.py-- JPX カレンダー管理・営業日判定
    - news_collector.py     -- RSS 収集（SSRF 対策・正規化・前処理）
    - quality.py            -- データ品質チェック（欠損、スパイク、重複、日付不整合）
    - stats.py              -- zscore_normalize 等の統計ユーティリティ
    - audit.py              -- 監査ログスキーマ定義・初期化
    - etl.py                -- ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py    -- Momentum / Volatility / Value 等の因子計算
    - feature_exploration.py-- 将来リターン・IC・統計サマリ・ランク関数

---

## 設定・運用上の注意

- 自動 .env 読み込み
  - config.py はプロジェクトルート（.git または pyproject.toml を基準）から .env/.env.local を自動読み込みします。テスト時や明示的に無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - 読み込み順: OS 環境 > .env.local > .env. .env.local は上書き可能（override=True）。
- API レート・認証
  - J-Quants はレート制限（120 req/min）を尊重するよう RateLimiter が組み込まれています。id_token は自動でリフレッシュされます。
  - OpenAI 呼び出しはリトライ／バックオフが入っていますが、API 料金とレートにご注意ください。
- 時刻とタイムゾーン
  - 監査ログ初期化時に TimeZone を UTC に固定します。保存されるタイムスタンプは UTC を前提に扱います。
- ルックアヘッドバイアス対策
  - 多くの関数は target_date を明示して使うことを想定しており、実行時の現在時刻を参照しない設計です。バックテストでの使用時は過去のみのデータを DB に格納してから利用してください。

---

もし README に追加してほしい項目（例: CI / テスト実行方法、完全な依存リスト、SQL スキーマ初期化スクリプト、運用例の systemd / cron 設定など）があれば教えてください。必要に応じて具体例を追記します。