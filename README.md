# KabuSys

日本株向けのデータプラットフォーム / 自動売買基盤のライブラリ群です。  
ETL（J-Quants 経由の株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI）、ファクター計算・リサーチ、監査ログ（発注／約定トレーサビリティ）などの機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを支える共通ライブラリ群です。  
主な目的は次のとおりです。

- J-Quants API を用いたデータ ETL（株価日足、財務、JPX カレンダー）
- ニュースの収集と LLM によるセンチメントスコアリング
- 市場レジーム判定（ETF MA とマクロニュースの合成）
- ファクター計算（モメンタム / バリュー / ボラティリティ等）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- 実行時設定は環境変数／.env で管理（自動ロード機能あり）

設計上の特徴として「ルックアヘッドバイアスを防ぐ」実装（内部で現在日時を直接参照しない）、DuckDB を用いた計算・永続化、OpenAI API 呼び出しの堅牢なリトライ設計、安全対策（RSS の SSRF 対策や XML の安全パーシング）などがあります。

---

## 機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save 系）
  - カレンダー管理（is_trading_day、next_trading_day、calendar_update_job）
  - ニュース収集（RSS 取得、トラッキングパラメータ除去、SSRF 対策）
  - データ品質チェック（missing / duplicates / spike / date consistency）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP（score_news: ニュースを銘柄ごとに LLM でスコア）
  - レジーム検出（score_regime: ETF MA とマクロニュースを合成）
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索（calc_forward_returns / calc_ic / factor_summary / rank）
- config
  - 環境変数読み込みと Settings（.env 自動読み込み、必須変数チェック）
- audit / execution / monitoring（監査・発注・監視系の基盤）

---

## セットアップ手順（ローカル開発向け）

以下は一般的なセットアップ例です。プロジェクトに requirements.txt / pyproject.toml がある場合はそちらに従ってください。

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成して有効化（例: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 必要なパッケージをインストール（目安）
   - duckdb
   - openai
   - defusedxml
   - そのほか標準ライブラリ以外に依存しているものがあれば pyproject.toml / requirements.txt を参照してください。

   例:
   ```
   pip install duckdb openai defusedxml
   # 開発用に editable インストール
   pip install -e .
   ```

4. 環境変数 / .env を準備  
   パッケージはプロジェクトルートの `.env` と `.env.local` を自動読み込みします（ただし環境変数が優先）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   最低限設定すべき（例）:
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx

   # kabuステーション API
   KABU_API_PASSWORD=your_password
   # KABU_API_BASE_URL はデフォルト: http://localhost:18080/kabusapi

   # OpenAI
   OPENAI_API_KEY=sk-...

   # Slack (通知等が必要な場合)
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789

   # DB パス（デフォルトは data/ 以下）
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 実行環境
   KABUSYS_ENV=development   # development | paper_trading | live
   LOG_LEVEL=INFO           # DEBUG|INFO|WARNING|ERROR|CRITICAL
   ```

5. DuckDB のスキーマ初期化（必要箇所で実行）
   監査ログを使う場合:
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   ```

---

## 使い方（主要な関数例）

※ 以下は Python から直接利用する場合の簡単な例です。実運用ではログ設定や例外処理を適切に行ってください。

- ETL（日次パイプライン）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（OpenAI を使用）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム判定:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 監査ログ DB 初期化:
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- 研究用ファクター計算:
  ```python
  import duckdb
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  # records は dict のリスト
  ```

---

## 環境変数（主な項目）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu ステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（ai モジュールを使う場合必須）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用（必要な場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB（デフォルト: data/monitoring.db）
- PID_FILE_PATH: 実行監視 pid ファイルパス（デフォルト: data/execution.pid）
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視閾値（%）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）

Settings クラスは必須変数が未設定の場合に ValueError を送出します。自動 .env ロードはプロジェクトルート（.git または pyproject.toml）を基準に `.env` → `.env.local` の順で読み込み、OS 環境変数を保護します。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイル）

以下は `src/kabusys` 以下の主なモジュール／ファイル一覧です（抜粋）。

- kabusys/
  - __init__.py
  - config.py                -- 環境変数 / Settings
  - ai/
    - __init__.py
    - news_nlp.py            -- ニュース NLP（score_news）
    - regime_detector.py     -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - pipeline.py            -- ETL パイプライン（run_daily_etl 等）
    - jquants_client.py      -- J-Quants API クライアント（fetch/save）
    - news_collector.py      -- RSS 収集（SSRF 対策等）
    - calendar_management.py -- 市場カレンダー管理
    - quality.py             -- データ品質チェック
    - stats.py               -- 統計ユーティリティ（zscore_normalize）
    - audit.py               -- 監査ログスキーマ初期化
    - etl.py                 -- ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py     -- ファクター計算（momentum/value/volatility）
    - feature_exploration.py -- 将来リターン / IC / 統計サマリ
  - ai/, data/, research/ はそれぞれのサブ機能をカプセル化

（実際のツリーはリポジトリ全体を参照してください）

---

## 運用上の注意点 / 実装ポリシー

- ルックアヘッドバイアス対策: モジュールの多くは内部で date.today() や datetime.today() を直接参照せず、呼び出し元から target_date を受け取る設計です。バックテストでは対象日を明示してください。
- OpenAI 呼び出しはモデル `gpt-4o-mini`（レスポンスは JSON mode）を使用する前提で実装されています。API 呼び出しはリトライや 5xx の扱いなど堅牢性を確保していますが、API キーの制御には注意してください。
- RSS 取得には SSRF 対策、XML 安全パーサ（defusedxml）、受信サイズ制限などを実装しています。
- DuckDB に対する INSERT は可能な限り冪等（ON CONFLICT DO UPDATE / DO NOTHING）で行われ、ETL は差分取得とバックフィル（過去数日分の再取得）に対応します。
- 監査ログは削除しない前提で設計されています（トレース性維持）。

---

## よくある操作（短いコマンドまとめ）

- 仮想環境作成 / 有効化
  - python -m venv .venv
  - source .venv/bin/activate

- 依存インストール（例）
  - pip install duckdb openai defusedxml

- 日次 ETL を手動実行（対話的 Python）
  - python -c "import duckdb, datetime; from kabusys.data.pipeline import run_daily_etl; conn=duckdb.connect('data/kabusys.duckdb'); print(run_daily_etl(conn, datetime.date(2026,3,20)).to_dict())"

---

README はここまでです。さらに README に追加してほしい内容（例: リリース手順、CI 設定、テストの実行方法、完全な依存関係リストなど）があれば教えてください。