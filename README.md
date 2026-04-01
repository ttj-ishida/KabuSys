# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI）、因子研究、監査ログ、マーケットカレンダー等を備え、バックテストや実運用の基盤として利用できます。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株のデータ取得・品質管理・特徴量生成・市場レジーム判定・監査ログなどを提供するモジュール群です。主な目的は以下です。

- J-Quants API からの差分 ETL（株価/財務/マーケットカレンダー）
- RSS を用いたニュース収集と OpenAI を使ったニュースセンチメント付与
- ファクター計算（モメンタム・バリュー・ボラティリティ等）と研究ユーティリティ
- 監査ログ（シグナル→注文→約定のトレーサビリティ）を DuckDB に構築
- 市場カレンダー管理と営業日判定ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）

設計上の特徴として、Look-ahead バイアスを避ける実装（内部で datetime.today() を直接参照しない等）、API 再試行やフェイルセーフ、DuckDB を用いた冪等保存（ON CONFLICT）などを重視しています。

---

## 機能一覧

- ETL（kabusys.data.pipeline）
  - 日次 ETL 実行（run_daily_etl）: 市場カレンダー、株価日足、財務データの差分取得と品質チェック
  - 個別 ETL: run_prices_etl / run_financials_etl / run_calendar_etl
- J-Quants クライアント（kabusys.data.jquants_client）
  - fetch / save 関数群（fetch_daily_quotes, save_daily_quotes, fetch_financial_statements, ...）
  - レートリミット管理・トークン自動リフレッシュ・リトライ実装
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、前処理、raw_news への冪等保存、銘柄紐付け
  - SSRF / 大容量応答対策済み
- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメントスコア付与（score_news）
  - バッチ処理、リトライ・レスポンス検証、スコアクリップ等
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF(1321) の MA200 乖離とマクロニュースセンチメントを合成して日次レジーム判定（score_regime）
- 研究用ユーティリティ（kabusys.research）
  - calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize（kabusys.data.stats）
- データ品質チェック（kabusys.data.quality）
  - 欠損・重複・スパイク・日付不整合の検出（QualityIssue を返却）
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等のテーブル定義・初期化ユーティリティ（init_audit_schema / init_audit_db）
- 環境設定（kabusys.config）
  - .env ファイル自動読み込み（プロジェクトルート検出）と Settings オブジェクト（settings）で各種設定を参照

---

## セットアップ手順

※ 以下は最小セットアップ例です。プロジェクトの運用環境に合わせて調整してください。

1. リポジトリをクローン / コピー

2. Python 仮想環境を作成・有効化（推奨）

   - Unix/macOS:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows:
     - python -m venv .venv
     - .venv\Scripts\activate

3. 依存パッケージをインストール（例）

   pip install duckdb openai defusedxml

   必要に応じて logging 等の追加パッケージを追加してください。

   （パッケージ管理に requirements.txt / pyproject.toml を用いる場合はそちらを参照してください）

4. 環境変数 / .env の準備

   プロジェクトルート（.git または pyproject.toml の存在するディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます（kabusys.config により自動検出）。
   自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   例 (.env.example):

   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # kabuAPI (kabuステーション)
   KABU_API_PASSWORD=your_kabu_api_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # OpenAI
   OPENAI_API_KEY=sk-...

   # Slack（通知が必要な場合）
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567

   # DB パス等（省略時はデフォルト）
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 実行環境
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB ファイル格納先のディレクトリを作成（必要に応じて）

   mkdir -p data

---

## 使い方（主要ユースケース）

以下は簡単な利用例です。DuckDB を直接使うので、まず接続を用意します。

- DuckDB 接続の作成例

  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL を実行する（run_daily_etl）

  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # target_date を指定（省略すると今日）
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースに対する AI スコア付与（score_news）

  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OPENAI_API_KEY は環境変数か、api_key 引数で指定
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("スコア付与済み銘柄数:", n_written)
  ```

- 市場レジーム判定（score_regime）

  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  r = score_regime(conn, target_date=date(2026, 3, 20))
  print("score_regime result:", r)
  ```

- 監査ログ DB の初期化（監査専用 DB を作る場合）

  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  ```

- RSS フィード取得（ニュース収集ヘルパー）

  ```python
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  ```

- J-Quants の ID トークンを明示的に取得する

  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使用
  ```

注意点:
- AI 関連機能（news_nlp, regime_detector）は OpenAI API を使用します。API キーは環境変数 `OPENAI_API_KEY` に設定するか、各関数の api_key 引数で渡してください。
- J-Quants 関連は `JQUANTS_REFRESH_TOKEN` が必須です（settings により取得）。
- ETL 実行では network/API エラーが起きても他ステップが継続されるよう設計されています。結果の ETLResult の errors / quality_issues を確認してください。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuAPI のパスワード（必須）
- KABU_API_BASE_URL: kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- SLACK_BOT_TOKEN: Slack 通知に使用（オプション）
- SLACK_CHANNEL_ID: Slack 通知先チャンネルID（オプション）
- DUCKDB_PATH: デフォルトの DuckDB パス（data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite DB（data/monitoring.db）
- KABUSYS_ENV: environment（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 真値をセットすると .env 自動読み込みを無効化

---

## ディレクトリ構成

パッケージは src/kabusys 配下に実装されています。主要ファイル・モジュールは以下の通りです。

- src/kabusys/
  - __init__.py
  - config.py                       -- 環境変数・設定管理（settings）
  - ai/
    - __init__.py
    - news_nlp.py                    -- ニュース NLP / score_news
    - regime_detector.py             -- 市場レジーム判定 / score_regime
  - data/
    - __init__.py
    - jquants_client.py              -- J-Quants API クライアント（fetch/save）
    - pipeline.py                    -- ETL パイプライン（run_daily_etl 等）
    - etl.py                         -- ETLResult の再エクスポート
    - news_collector.py              -- RSS 収集・前処理
    - quality.py                     -- データ品質チェック
    - stats.py                       -- zscore_normalize 等の統計ユーティリティ
    - calendar_management.py         -- 市場カレンダー管理
    - audit.py                       -- 監査ログテーブル初期化
  - research/
    - __init__.py
    - factor_research.py             -- calc_momentum / calc_value / calc_volatility
    - feature_exploration.py         -- calc_forward_returns / calc_ic / factor_summary / rank
  - (他：strategy / execution / monitoring などの公開予定モジュールの名前空間登録あり)

---

## 開発・テスト関連

- 自動.env 読み込みを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で有用）。
- AI / 外部 API を使う機能は単体テスト時に HTTP/OpenAI 呼び出しをモックする設計になっています（内部関数を patch して差し替え可能）。
- DuckDB を使う部分はインメモリ ":memory:" でテスト可能（例: duckdb.connect(":memory:")）。

---

## 注意事項 / ベストプラクティス

- OpenAI / J-Quants API キーは漏洩に注意してください。CI に保存する場合は暗号化されたシークレットを利用してください。
- 本ライブラリはデータ取得と解析を目的としており、実際の発注ロジック（ブローカー API 実装）を組み込む場合は追加の安全対策（レート制御・二重発注防止・リスク管理）を実装してください。
- DuckDB のバージョンによっては executemany の挙動に差異があるため（コード内で注意喚起あり）、運用環境で十分に検証してください。
- レート制限や API エラーの再試行は組み込み済みですが、運用時はメトリクス／監視を設定して障害時に早期対応できるようにしてください。

---

必要であれば、各モジュールの使い方やサンプルスクリプト（ETL cron ジョブ、ニュース収集バッチ、AI スコアリングワーカー、監査 DB 初期化スクリプト等）を追加で作成します。どのユースケースに対するサンプルを優先して欲しいか教えてください。