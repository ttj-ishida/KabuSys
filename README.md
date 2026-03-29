# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買支援ライブラリ。  
DuckDB をバックエンドに、J-Quants / JPX 等のデータ取得、ニュース収集・NLP（OpenAI）、ファクター計算、ETL、監査ログなどをワンパッケージで提供します。

---

## プロジェクト概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API からの株価・財務・マーケットカレンダーの差分取得と DuckDB への保存（ETL）
- RSS ニュース収集と前処理（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント評価（銘柄別 / マクロ）
- 市場レジーム判定（ETF + マクロセンチメントの合成）
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）と統計ユーティリティ
- 監査用テーブル（signal → order → execution のトレーサビリティ）
- データ品質チェック（欠損・スパイク・重複・日付整合性）

設計上の特徴：
- ルックアヘッドバイアス対策（内部で date.today()/datetime.today() に頼らない実装）
- 冪等性（DB への保存は ON CONFLICT / INSERT … DO UPDATE 等）
- ネットワーク / API 呼び出しに対する堅牢なリトライ / バックオフ
- SSRF / XML Bomb / 大容量応答対策などセキュリティ考慮

---

## 主な機能一覧

- data
  - ETL パイプライン: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント: fetch_* / save_*（daily_quotes, financial_statements, market_calendar, listed_info）
  - カレンダー管理: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
  - ニュース収集: fetch_rss, 前処理と raw_news へ保存（news_collector）
  - データ品質チェック: check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks
  - 監査ログ初期化: init_audit_schema / init_audit_db
  - 統計ユーティリティ: zscore_normalize
- ai
  - ニュース NLP（銘柄別 ai_scores 生成）: score_news
  - マクロ + ETF を組み合わせた市場レジーム判定: score_regime
- research
  - ファクター計算: calc_momentum, calc_value, calc_volatility
  - 特徴量探索: calc_forward_returns, calc_ic, factor_summary, rank
- config
  - 環境変数 / .env 自動読み込み、アプリ設定（settings）

---

## セットアップ手順

前提：
- Python 3.10+
- DuckDB（Python パッケージ duckdb）
- OpenAI Python SDK（openai）
- defusedxml（XML パースの安全化）
- ネットアクセス（J-Quants / OpenAI / RSS ソース）

1. リポジトリをクローンしてパッケージをインストール（開発モード推奨）
   ```
   git clone <repo-url>
   cd <repo-root>
   pip install -e .[dev]   # requirements はプロジェクトの setup/pyproject を参照
   ```

2. 必要な OS 環境変数を設定する（.env または環境変数）
   - 必須（例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API パスワード（発注系を使う場合）
     - SLACK_BOT_TOKEN: Slack 通知用トークン（通知機能を利用する場合）
     - SLACK_CHANNEL_ID: Slack チャネル ID
   - 任意 / デフォルト:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を指定すると .env の自動読み込みを無効化
     - DUCKDB_PATH: データベースファイル（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 sqlite（data/monitoring.db）

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   ```

   注意: パッケージはプロジェクトルート（.git または pyproject.toml を基準）から .env/.env.local を自動読み込みします。

3. データディレクトリを作成（必要に応じて）
   ```
   mkdir -p data
   ```

4. DuckDB 接続の初期化（監査DB など）
   Python REPL またはスクリプトで:
   ```py
   import duckdb
   from kabusys.data.audit import init_audit_db

   # 監査用 DB を作る（ファイル or :memory:）
   conn = init_audit_db("data/audit.duckdb")
   ```

---

## 使い方（例）

以下は代表的な利用例です。各関数は DuckDB の接続オブジェクト（duckdb.connect(...) の戻り値）を受け取ります。

- DuckDB 接続を作る:
  ```py
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL を実行する（J-Quants から差分取得して保存 → 品質チェックまで）
  ```py
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP（銘柄別センチメント）を実行する
  ```py
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"書き込み件数: {n_written}")
  ```

- 市場レジーム判定を実行する
  ```py
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 研究用ファクター計算
  ```py
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date

  momentum = calc_momentum(conn, date(2026, 3, 20))
  volatility = calc_volatility(conn, date(2026, 3, 20))
  value = calc_value(conn, date(2026, 3, 20))
  ```

- 統計正規化ユーティリティ
  ```py
  from kabusys.data.stats import zscore_normalize

  normalized = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m"])
  ```

- 監査スキーマ初期化（既存接続への追加）
  ```py
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)
  ```

注意点:
- OpenAI 呼び出しには OPENAI_API_KEY（環境変数か引数で渡す）を必須とする関数があります。
- J-Quants 呼び出しには JQUANTS_REFRESH_TOKEN が必要です（get_id_token を通して id_token を取得）。
- DuckDB の互換性や executemany の空リスト扱いなどに注意（実装内で対応していますが、DB バージョン差異がある場合はログ参照）。

---

## 環境変数 / 設定（要チェック）

主に利用される環境変数：
- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- OPENAI_API_KEY (必須 for AI 機能): OpenAI API キー
- KABU_API_PASSWORD: kabuステーション API のパスワード（発注連携）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視等）パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（動作モード）
- LOG_LEVEL: ログレベル

自動読み込み: パッケージはプロジェクトルートの .env と .env.local を起動時に読み込みます。自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成

重要なファイル / モジュール構成（主要部分を抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py            # ニュースセンチメント（銘柄別）
    - regime_detector.py     # マクロ + ETF で市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント（fetch/save）
    - pipeline.py            # ETL パイプライン（run_daily_etl 等）
    - news_collector.py      # RSS からのニュース収集・保存
    - calendar_management.py # 市場カレンダー管理（is_trading_day など）
    - quality.py             # データ品質チェック（欠損・スパイク等）
    - stats.py               # 統計ユーティリティ（zscore_normalize）
    - audit.py               # 監査ログスキーマ初期化
    - etl.py                 # ETLResult の公開（再エクスポート）
  - research/
    - __init__.py
    - factor_research.py     # モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py # 将来リターン/IC/統計サマリー等

各モジュールは docstring と関数コメントに設計・使用上の注意が記載されています。実運用前に該当ドキュメントとテストを必ず確認してください。

---

## 運用上の注意点

- OpenAI / J-Quants の API 呼び出しは課金が発生します。API キーの管理と利用量に注意してください。
- 本パッケージは取引を行う機能を含みます（監査テーブルや kabu API 向け設定等）。実際の発注を行う前に paper_trading 環境で十分に検証してください。
- データ整合性・品質チェック（data.quality）を ETL 後に必ず実行し、重大な問題が検出された場合は手動確認を行ってください。
- DuckDB のファイル保存先（DUCKDB_PATH）やバックアップ運用を適切に設計してください。

---

もし README に追加したい項目（例: API 使用量の概算、より詳細なデプロイ手順、CI 設定、例データの生成手順など）があれば教えてください。必要に応じて追記・調整します。