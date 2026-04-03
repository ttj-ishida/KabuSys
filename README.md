# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ集です。  
ETL（J-Quants からの株価・財務・カレンダー収集）、ニュース収集・NLP スコアリング、研究用ファクター計算、監査ログ（発注〜約定のトレーサビリティ）、市場レジーム判定などを含むモジュール群を提供します。

主な用途：
- 日次 ETL パイプラインで株価・財務・カレンダーを DuckDB に保存
- RSS ニュース収集・前処理と OpenAI を使ったニュースセンチメント付与（ai_scores）
- ファクター計算 / 研究用ユーティリティ
- 戦略監査ログ（signal → order_request → execution）の DB スキーマ初期化
- マーケットレジーム判定（ETF の MA 指標と LLM によるマクロセンチメントの合成）

---

## 機能一覧

- data
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（fetch / save 関数、認証トークン自動リフレッシュ、レート制御、リトライ）
  - カレンダー管理（営業日判定、前後営業日の取得、calendar_update_job）
  - ニュース収集（RSS の安全な取得・前処理・raw_news 保存補助）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログスキーマ作成 / 監査 DB 初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore 正規化）

- ai
  - ニュース NLP スコアリング（gpt-4o-mini を使用する JSON mode での一括スコア取得）
  - 市場レジーム判定（ETF 1321 の 200 日 MA 乖離 + マクロセンチメント合成）

- research
  - ファクター計算（momentum / value / volatility 等）
  - 特徴量探索ユーティリティ（forward returns, IC, 統計サマリ, rank）
  
- config
  - .env の自動読み込み（プロジェクトルートの .env / .env.local、環境変数優先）
  - 設定アクセサ（settings オブジェクト）

---

## 前提条件

- Python 3.10 以上（ソースは型注釈に | を使用）
- 必要な Python パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - その他標準ライブラリ（urllib, json, logging 等）

setup.py / pyproject.toml がある場合はそちらに依存関係をまとめてください。リポジトリ内で利用する最低限の外部依存は上記です。

---

## セットアップ手順

1. Python 仮想環境の作成（例）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. パッケージのインストール（開発インストール）
   ```bash
   pip install -e .    # pyproject.toml / setup.py がある想定
   ```
   もしくは必要パッケージを個別に：
   ```bash
   pip install duckdb openai defusedxml
   ```

3. 環境変数の設定
   プロジェクトルートに `.env` を置くと自動的に読み込まれます（優先順は OS 環境 > .env.local > .env）。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必要な主な環境変数（例）：
   ```
   JQUANTS_REFRESH_TOKEN=...       # 必須（J-Quants のリフレッシュトークン）
   OPENAI_API_KEY=...             # OpenAI API キー（score_news / score_regime に必要）
   KABU_API_PASSWORD=...          # kabuステーション API のパスワード（使用する場合）
   KABU_API_BASE_URL=http://localhost:18080/kabusapi
   LINE_CHANNEL_ACCESS_TOKEN=...  # 任意（LINE 通知を使う場合）
   LINE_USER_ID=...               # 任意
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   PID_FILE_PATH=data/execution.pid
   KILL_FLAG_PATH=data/kill.flag
   KILL_FLAG_CLEAR_ON_START=0
   CPU_THRESHOLD_PCT=90.0
   MEMORY_THRESHOLD_PCT=85.0
   DISK_THRESHOLD_PCT=90.0
   KABUSYS_ENV=development   # development | paper_trading | live
   LOG_LEVEL=INFO
   ```

   .env のサンプルはリポジトリ内の `.env.example` を参考にしてください（存在する想定）。

4. DuckDB ファイルの親ディレクトリ作成（必要に応じて）
   ```bash
   mkdir -p data
   ```

---

## 使い方（主要な例）

以下はコード内 API を直接呼ぶ簡単な利用例です。実運用ではログ設定や例外処理、ジョブスケジューラ（cron 等）やプロセスマネージャと組み合わせてください。

- DuckDB 接続を作成して ETL を実行する（日次 ETL）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースの NLP スコアリング（OpenAI が必要）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY が環境変数にあれば api_key 引数は不要
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written scores: {written}")
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化（別 DB を使う場合）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- RSS フィードから記事を取得（news_collector）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  for a in articles:
      print(a["id"], a["title"], a["datetime"])
  ```

注意点：
- OpenAI の呼び出しには gpt-4o-mini（コード内指定）を使用します。API 利用に応じた料金・レートに注意してください。
- score_news と score_regime は API トークンを引数で渡すこともできます（テストや分離実行に便利）。

---

## 環境変数 / 設定（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news, score_regime に必要）
- KABU_API_PASSWORD: kabu API のパスワード（必要に応じて）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite のパス（デフォルト: data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START: 実行監視に関する設定
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視しきい値
- KABUSYS_ENV: development / paper_trading / live
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みを無効化します。

---

## ディレクトリ構成

主要なファイル・モジュール構成（リポジトリの src/kabusys を想定）：

- src/kabusys/
  - __init__.py
  - config.py                     -- 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                  -- ニュース NLP スコアリング（score_news）
    - regime_detector.py           -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py            -- J-Quants API クライアント（fetch/save 等）
    - pipeline.py                  -- ETL パイプライン（run_daily_etl 等）
    - etl.py                       -- ETLResult の再エクスポート
    - news_collector.py            -- RSS 取得/前処理
    - calendar_management.py       -- 市場カレンダー管理
    - quality.py                   -- 品質チェック（欠損・スパイク等）
    - stats.py                     -- 統計ユーティリティ（zscore_normalize）
    - audit.py                     -- 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py           -- Momentum / Value / Volatility 等
    - feature_exploration.py       -- forward returns / IC / summary / rank

（上記は主要なファイルのみ抜粋）

---

## 開発・テスト上の補足

- config.py はパッケージ初期化時にプロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を自動で読み込みます。テストで自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- openai クライアント呼び出し部分は内部でリトライやエラーフェールセーフ化されています。テスト時は各モジュールの _call_openai_api をモックして API 呼び出しを差し替えられるよう実装されています。
- DuckDB を使用する SQL は互換性を考慮して記述されていますが、環境によってはバージョン差異で微修正が必要になる場合があります。

---

README はここまでです。特定の使い方（例: cron での ETL 実行、kabu ステーションとの接続、具体的な .env.example 内容、CI 設定など）について詳細が必要であれば、用途に合わせて追加の章を作成します。どの部分を詳しく書きますか？