# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants → DuckDB）、ニュースのNLPスコアリング（OpenAI）、市場レジーム判定、調査用ファクター計算、監査ログスキーマなどを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のデータ収集・品質管理・解析・戦略支援・監査ログ管理を想定した内部ライブラリ群です。主な責務は次の通りです。

- J-Quants API からの日次データ（株価・財務・マーケットカレンダー）差分取得と DuckDB への保存（ETL）
- RSS ベースのニュース収集と OpenAI を用いた銘柄別センチメントスコアリング
- ETF とマクロニュースに基づく市場レジーム判定（LLM を使用）
- 研究用のファクター計算（モメンタム・ボラティリティ・バリュー等）および統計ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 取引監査用の監査テーブル定義・初期化ユーティリティ
- カレンダー・営業日判定ユーティリティ

設計上の重点:
- ルックアヘッドバイアスへ配慮（内部で date.today() の直接参照を避ける箇所あり）
- 冪等性（ETL/保存は ON CONFLICT / DO UPDATE 等で設計）
- フェイルセーフ（外部APIエラー時は部分的にスキップして継続）
- 最小限の外部依存（標準ライブラリ＋必要なライブラリのみ）

---

## 機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save 系）
  - market_calendar 管理・営業日ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days）
  - news_collector（RSS 取得・正規化・raw_news 保存）
  - quality（品質チェック、QualityIssue）
  - audit（監査ログスキーマ初期化 / init_audit_db）
  - stats（zscore_normalize 等）
- ai/
  - news_nlp.score_news(conn, target_date[, api_key]) — ニュースを LLM でスコア化して ai_scores に書き込み
  - regime_detector.score_regime(conn, target_date[, api_key]) — ma200 とマクロニュースで市場レジーム判定
- research/
  - factor_research.calc_momentum / calc_value / calc_volatility
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank

---

## 前提・必須

- Python 3.10+（タイプヒントで Union 記法等を使用）
- DuckDB（Python パッケージとしてインストール）
- OpenAI Python クライアント（LLM 呼び出しに使用）
- defusedxml（RSS パースの安全化）

推奨パッケージ（requirements の例）:
- duckdb
- openai
- defusedxml

（プロジェクトに pyproject.toml があればそれを利用して依存管理してください）

---

## セットアップ手順

1. リポジトリをクローンして開発環境に配置

   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化（任意）

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール

   例（pip）:

   ```bash
   pip install -U pip
   pip install duckdb openai defusedxml
   # 開発時にパッケージとして編集可能にする場合:
   pip install -e .
   ```

4. 環境変数（.env）を用意

   プロジェクトルートに `.env` または `.env.local` を置くと自動的に読み込まれます（.git または pyproject.toml を基準にプロジェクトルートを特定）。自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   .env の例（実際のトークンは安全に管理してください）:

   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=Cxxxxxx
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   - 必須:
     - JQUANTS_REFRESH_TOKEN
     - OPENAI_API_KEY（ai.score_news / regime_detector 実行時に引数で渡すことも可能）
     - KABU_API_PASSWORD（kabu API を使う場合）
     - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（通知に使う場合）
   - 任意:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1（自動 .env 読み込みの無効化）
     - KABUSYS_ENV: development / paper_trading / live
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

---

## 使い方（主要なユーティリティ例）

以下は最小限の使用例です。実行は Python スクリプトやジョブから行います。

- DuckDB 接続の作成例

  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する（J-Quants から差分取得して保存・品質チェック）

  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（OpenAI 必須）

  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"ai_scores に書き込んだ銘柄数: {n_written}")
  ```

- 市場レジーム判定（OpenAI 必須）

  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB の初期化

  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリは自動作成
  # テーブルが作成され、UTC タイムゾーンが設定されます
  ```

- カレンダー / 営業日ユーティリティ

  ```python
  from datetime import date
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

注意点:
- OpenAI API 呼び出し部分は外部 API のためレートやコストに注意してください。api_key は関数引数で明示的に渡せます（テストでモックすることを推奨）。
- DuckDB のバージョン差異に伴う挙動（executemany の空リスト挙動など）に注意する実装上の考慮があります。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py  — 環境変数 / .env 自動読み込みと Settings
    - ai/
      - __init__.py
      - news_nlp.py        — ニュースセンチメントの LLM スコア化
      - regime_detector.py — ma200 + マクロニュースで市場レジーム判定
    - data/
      - __init__.py
      - jquants_client.py  — J-Quants API クライアント（fetch / save）
      - pipeline.py        — ETL パイプライン（run_daily_etl 等）
      - etl.py             — ETL 用公開型（ETLResult）
      - news_collector.py  — RSS 収集・正規化
      - calendar_management.py — 市場カレンダー更新と営業日ユーティリティ
      - quality.py         — データ品質チェック（missing/spike/duplicates/日期整合）
      - audit.py           — 監査ログスキーマ / init_audit_db
      - stats.py           — zscore_normalize 等汎用統計
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - research/（他モジュール）
- pyproject.toml or setup.cfg / setup.py（プロジェクトルートにある想定）

---

## 動作上の注意・設計上のポイント

- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に探索します。CWD に依存しないよう設計されています。
- 設定の優先順位: OS 環境変数 > .env.local > .env。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
- LLM 呼び出し（OpenAI）は冪等性やエラーハンドリング（リトライ、フォールバックスコア）を備えています。テストでは内部呼び出しをモック可能（モジュール内関数を patch）。
- ETL の保存は基本的に冪等（ON CONFLICT DO UPDATE）を採用しています。
- データ品質チェックは Fail-Fast ではなく問題を収集して呼び出し元に返す設計です。ETL 実行側で結果を確認して判断してください。

---

## 開発・テスト

- 外部 API 呼び出し（J-Quants / OpenAI / RSS）を伴う部分はユニットテストではモックして検証することを推奨します。
- settings や自動 .env ロードはテストのために KABUSYS_DISABLE_AUTO_ENV_LOAD を使って無効化できます。

---

もし README に記載してほしい追加の使い方（例: Slack 通知の連携方法、kabuステーション API を使った発注モジュールの利用例、CI 設定例など）があれば教えてください。必要に応じてサンプルスクリプトも作成します。