# KabuSys

バージョン: 0.1.0

日本株向けのデータプラットフォームと自動売買リサーチ／戦略基盤。  
J-Quants API からのデータ取得（ETL）、ニュース収集と LLM によるニュース NLP、研究（ファクター計算／IC 計測）、監査ログ（発注〜約定のトレーサビリティ）などを包含したモジュール群を提供します。

---

## 概要

KabuSys は次のような目的で設計された Python パッケージです。

- J-Quants API を利用した株価・財務・市場カレンダーの差分 ETL
- RSS ベースのニュース収集と前処理
- OpenAI（gpt-4o-mini）を利用したニュースセンチメント（銘柄別 / マクロ）評価
- 市場レジーム判定（ETF MA とマクロセンチメントの合成）
- リサーチ用のファクター計算（モメンタム／バリュー／ボラティリティ等）と統計ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → executions）のテーブル定義と初期化ユーティリティ

設計上の共通方針として「ルックアヘッドバイアス防止」「冪等性」「API エラーに対するフェイルセーフ」「DuckDB を用いたローカルデータ管理」を重視しています。

---

## 主な機能一覧

- ETL:
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（差分取得、保存、品質チェック）
  - J-Quants API クライアント（認証、ページネーション、レートリミット、リトライ）
- ニュース処理:
  - RSS 収集（SSRF 対策、URL 正規化、前処理）
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを生成して ai_scores テーブルへ保存
- AI:
  - regime_detector.score_regime: ETF（1321）MA200 乖離とマクロニュース LLM スコアを合成して market_regime を更新
  - news_nlp / regime_detector は OpenAI API（gpt-4o-mini）を利用（JSON Mode を想定）
- リサーチ:
  - calc_momentum / calc_value / calc_volatility
  - calc_forward_returns / calc_ic / factor_summary / rank / zscore_normalize
- データ管理:
  - calendar_update_job（JPX カレンダーの差分更新）
  - data.audit: 監査ログテーブル定義と init_audit_db
  - data.jquants_client: save_* 系の冪等保存ユーティリティ
- 品質管理:
  - data.quality.run_all_checks（欠損・重複・スパイク・日付不整合検出）

---

## 要件

- Python 3.10 以上（PEP 604 の型記法や一部機能を利用）
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml

（実行環境に応じて追加の依存が必要になることがあります。setup.py / pyproject.toml を参照してください。）

---

## セットアップ手順

1. リポジトリをクローン

   ```
   git clone <repository-url>
   cd <repository>
   ```

2. 仮想環境を作成・有効化（例: venv）

   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール

   例（pip）:

   ```
   pip install -U pip
   pip install duckdb openai defusedxml
   pip install -e .
   ```

   - project に pyproject.toml / setup.py がある場合は `pip install -e .` でローカルインストールできます。
   - テストや実行に必要な追加パッケージがあれば pyproject.toml を参照してください。

4. 環境変数の設定

   プロジェクトルートに `.env` / `.env.local` を置くと、自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば自動読み込みを無効化できます）。

   主要な環境変数（概要）:

   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須：ETL 実行時）
   - KABU_API_PASSWORD: kabuステーション API パスワード（発注連携を行う場合）
   - KABU_API_BASE_URL: kabuステーション API ベース URL（デフォルト: http://localhost:18080/kabusapi）
   - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 実行時に必要）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知に使用（任意）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - PAPER_FILL_MODE: paper trading の埋め合わせモード（instant|partial|never|reject）
   - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
   - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: 実行監視関連
   - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）

   例: `.env`（最小）

   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（主要なユースケース）

※ 下記は Python スクリプト内や REPL からモジュールを利用する例です。DuckDB 接続は `duckdb.connect(path)` を用います。

- 設定値の取得

  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)  # Path オブジェクト
  ```

- 日次 ETL を実行（例: today の ETL）

  ```python
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- ニュースセンチメントのスコア付け（target_date に対して）

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026,3,20))
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム判定

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026,3,20))
  ```

- ファクター計算（例: モメンタム）

  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect(str(settings.duckdb_path))
  mom = calc_momentum(conn, target_date=date(2026,3,20))
  ```

- 監査ログ DB 初期化（監査用 DuckDB を作成してテーブルを準備）

  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  ```

- カレンダー更新バッチ（JPX カレンダーを取得して market_calendar を更新）

  ```python
  from datetime import date
  import duckdb
  from kabusys.data.calendar_management import calendar_update_job

  conn = duckdb.connect(str(settings.duckdb_path))
  saved = calendar_update_job(conn)
  print(f"保存件数: {saved}")
  ```

注意:
- AI 関連（news_nlp / regime_detector）は OPENAI_API_KEY を必要とします。API の失敗に備えてフェイルセーフ処理が入っていますが、キー未設定の場合は ValueError が発生します。
- run_daily_etl 等は内部で ETL の各ステップを個別に例外ハンドリングしています。結果は ETLResult にまとまります。

---

## 自動環境変数ロードの挙動

- kabusys.config は、プロジェクトルート（.git または pyproject.toml を基準）を探索し `.env` と `.env.local` を自動で読み込みます。
  - 読み込み順序（優先度）: OS 環境変数 > .env.local > .env
  - .env.local は .env を上書き（override=True）します。
- 自動ロードを無効化するには環境変数をセット:

  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - stats.py
    - quality.py
    - news_collector.py
    - calendar_management.py
    - audit.py
    - etl.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/（その他ユーティリティ）
  - monitoring/（監視・実行関連モジュール：コードベース上に存在）

全ファイル構成（抜粋）

```
src/
  kabusys/
    __init__.py
    config.py
    ai/
      news_nlp.py
      regime_detector.py
    data/
      jquants_client.py
      pipeline.py
      calendar_management.py
      news_collector.py
      quality.py
      stats.py
      audit.py
    research/
      factor_research.py
      feature_exploration.py
      __init__.py
    research/...
    monitoring/...
```

---

## 開発上の注意点

- DuckDB を用いるため、SQL の挙動やバージョン差（例: executemany の空リスト挙動）を考慮して実装されています。DuckDB のバージョンが古いと挙動が異なる可能性があります。
- LLM 呼び出しは OpenAI SDK（chat completions の JSON mode）を想定しています。テスト時には内部の API 呼び出しラッパーをモックすることを想定した設計です。
- ルックアヘッドバイアス防止のため、target_date の扱いに注意しています。自動的に今日の日付を参照する実装は避けるように設計されています。
- audit.init_audit_schema は transactional オプションを持ち、DuckDB のトランザクション挙動に注意してください（ネストトランザクション非対応）。

---

## よくある操作例（ショート）

- ETL を毎朝バッチで実行する cron スクリプトを書く（run_daily_etl を呼び出す Python スクリプトを作成）
- AI スコア（ニュース・レジーム）は ETL 後に実行して ai_scores / market_regime を更新
- 監査 DB を初期化して、発注処理実装と連携（order_requests / executions テーブルを利用）

---

## サポート / 貢献

- バグ報告・機能提案は Issue を開いてください。
- コード貢献は PR を歓迎します。設計方針（ルックアヘッドバイアス回避・冪等性・フェイルセーフ）を尊重してください。

---

README の内容や使用例の追加・修正、サンプルスクリプト（実行用 CLI、Systemd ユニット、Dockerfile など）が必要であればお知らせください。