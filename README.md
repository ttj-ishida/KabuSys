# KabuSys

KabuSys は日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター研究、監査ログ（発注トレーサビリティ）などを含むモジュール群を提供します。

主な設計方針は「ルックアヘッドバイアスの排除」「冪等性」「フェイルセーフ（外部API障害時の安全なフォールバック）」です。

バージョン: 0.1.0

---

## 機能一覧

- 環境設定管理
  - .env / .env.local を自動読み込み（必要に応じて無効化可能）
  - 必須値チェック（settings オブジェクト経由）

- データ取得 / ETL（J-Quants API 経由）
  - 株価日足（OHLCV）取得・保存（ページネーション・レート制御・トークン自動リフレッシュ）
  - 財務データ取得・保存
  - JPX 市場カレンダー取得・保存
  - 差分更新・バックフィル・品質チェック（欠損、スパイク、重複、日付整合性）

- ニュース収集・NLP
  - RSS フィード収集（SSRF 対策、トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）を使った銘柄別ニュースセンチメント算出（ai_scores への保存）
  - レスポンス検証、リトライ、バッチ処理

- 市場レジーム判定
  - ETF（1321）の 200 日 MA 乖離（70%）とマクロニュースセンチメント（30%）を合成して日次で 'bull'/'neutral'/'bear' を判定
  - LLM 呼び出しの失敗耐性（0.0 にフォールバック）

- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリューのファクター計算
  - 将来リターン、IC（スピアマンランク相関）、統計サマリ、Z スコア正規化

- 監査ログ（audit）
  - シグナル → 発注要求 → 約定 をトレースする監査テーブル群の初期化機能
  - DuckDB による冪等なスキーマ初期化・インデックス作成

- その他ユーティリティ
  - DuckDB ベースのスキーマ/DB 操作ヘルパー
  - 安全な HTTP / XML 処理（defusedxml 等）

---

## セットアップ手順（開発向け）

1. リポジトリをクローン
   ```
   git clone <repository-url>
   cd <repository>
   ```

2. Python バージョン
   - Python 3.10 以上を推奨（PEP 604 の型表記 `X | Y` を使用）

3. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

4. 依存パッケージをインストール
   - requirements.txt がある場合:
     ```
     pip install -r requirements.txt
     ```
   - 無ければ最低限以下をインストールしてください:
     ```
     pip install duckdb openai defusedxml
     ```
   - 開発用 lint/test 等を使う場合は別途追加してください。

5. パッケージを編集モードでインストール（任意）
   ```
   pip install -e .
   ```

6. データディレクトリの作成（デフォルト）
   ```
   mkdir -p data
   ```

7. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を配置すると自動で読み込まれます（ただし環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 推奨/任意:
     - OPENAI_API_KEY（AI モジュールを使う場合）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PID_FILE_PATH（デフォルト: data/execution.pid）
     - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
     - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
     - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）

   サンプル `.env`（例）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_pw
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（簡単な例）

以下は Python スクリプトや REPL で実行する例です。実行前に環境変数・DB パスなどを設定してください。

- DuckDB 接続を作って ETL を1日分実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  res = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(res.to_dict())
  ```

- ニューススコアリング（OpenAI API 使用）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # OPENAI_API_KEY が環境変数に設定されていれば api_key は省略可
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込んだ銘柄数: {written}")
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査DB スキーマ初期化（監査用 DB を別ファイルに作る例）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # これで監査用テーブル群が作成されます
  ```

- 研究モジュールの利用（ファクター計算）
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  results = calc_momentum(conn, target_date=date(2026, 3, 20))
  print(results[:5])
  ```

注意:
- OpenAI 呼び出しは api_key 引数で明示的に渡せます（テスト時など便利）。
- 各関数はルックアヘッドを避けるため内部で date.today() を参照しない設計になっています（target_date を明示してください）。

---

## 主要な設定 / 環境変数

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（必須）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知に使用（必須）
- OPENAI_API_KEY: OpenAI 呼び出しに必要（ai モジュールを使う場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると .env 自動読み込みを無効化

settings オブジェクト（kabusys.config.settings）を通して安全にアクセスできます。

---

## ディレクトリ構成

リポジトリ（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                -- 環境変数 / 設定管理
    - ai/
      - __init__.py
      - news_nlp.py            -- ニュースセンチメント算出（OpenAI）
      - regime_detector.py     -- 市場レジーム判定
    - data/
      - __init__.py
      - jquants_client.py      -- J-Quants API クライアント（取得 & DuckDB 保存）
      - pipeline.py            -- ETL パイプライン（run_daily_etl 等）
      - calendar_management.py -- マーケットカレンダー管理
      - news_collector.py      -- RSS 収集（SSRF 対策等）
      - quality.py             -- データ品質チェック
      - stats.py               -- 統計ユーティリティ（zscore 等）
      - etl.py                 -- ETLResult の再公開
      - audit.py               -- 監査ログスキーマ初期化
    - research/
      - __init__.py
      - factor_research.py     -- ファクター計算（momentum/value/volatility）
      - feature_exploration.py -- 将来リターン・IC・統計サマリ等
    - ai/, data/, research/ 内のユーティリティや補助モジュール多数

主要テーブル（DuckDB、コード内で参照される想定）
- raw_prices (date, code, open, high, low, close, volume, turnover, fetched_at)
- raw_financials (code, report_date, period_type, eps, roe, fetched_at, ...)
- market_calendar (date, is_trading_day, is_half_day, is_sq_day, holiday_name)
- raw_news / news_symbols / ai_scores
- audit 用テーブル: signal_events, order_requests, executions

---

## ロギング / 障害耐性 / セキュリティ上の注意

- OpenAI / J-Quants API 呼び出しはリトライロジックと指数バックオフを備えています。5xx・ネットワーク障害・429 等に対応します。
- J-Quants クライアントは 120 req/min のレート制限を守るため内部でスロットリングしています。
- NewsCollector は SSRF 対策（ホスト検査、リダイレクト検査）、XML の defusedxml による保護、受信サイズ制限などを実装しています。
- ETL・保存処理は冪等（ON CONFLICT DO UPDATE / INSERT ... DO NOTHING 等）を基本としています。
- 設定や API キー類は .env に保存する場合には取り扱いに注意してください（リポジトリへコミットしない）。

---

## 開発 / テスト

- 各種関数は外部 API を呼ぶため、ユニットテストでは HTTP / OpenAI 呼び出しをモックすることを推奨します（コード内でもテスト用に差し替えやすい設計になっています）。
- news_nlp / regime_detector の _call_openai_api はテストでパッチ可能です。
- DB は :memory: の DuckDB を使ってテスト可能（init_audit_db(":memory:") など）。

---

必要があれば README に以下を追加できます:
- 具体的な .env.example ファイル
- SQL スキーマの抜粋
- CI / GitHub Actions の設定例
- 運用時の cron / systemd サンプルジョブ

追加したい内容があれば指示してください。