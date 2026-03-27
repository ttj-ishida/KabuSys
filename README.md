# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。データ取得（J-Quants）、ETL、データ品質チェック、ニュースのセンチメント解析（OpenAI を利用した LLM 評価）、市場レジーム判定、監査ログなど、トレード・リサーチ・オペレーションに必要なユーティリティをまとめています。

---

## プロジェクト概要

- 目的: 日本株の自動売買およびリサーチ基盤を支える共通ライブラリ群を提供する。
- 主な対象:
  - 日次 ETL（J-Quants からの株価・財務・カレンダー取得）
  - データ品質チェック（欠損・スパイク・重複・日付整合性）
  - ニュース収集・NLP（OpenAI を用いた銘柄別センチメント）
  - 市場レジーム判定（ETF MA とマクロニュースの組み合わせ）
  - 監査ログ（シグナル→発注→約定を追跡する DB スキーマ）
- 設計方針:
  - ルックアヘッドバイアスに配慮（内部で datetime.today()/date.today() を不用意に参照しない等）
  - 冪等性（DB 保存は ON CONFLICT / UPDATE 等で扱う）
  - フェイルセーフ（API 失敗時は適切にフォールバックして継続）

---

## 機能一覧

- 設定管理
  - .env または環境変数の自動ロード（プロジェクトルート検出）
  - 必須環境変数チェック、環境モード（development / paper_trading / live）検証
- Data（duckdb を用いたデータ基盤ユーティリティ）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（fetch / save 関数、認証リフレッシュ、レートリミット・リトライ）
  - 市場カレンダー管理（is_trading_day / next_trading_day / get_trading_days / calendar_update_job）
  - ニュース収集（RSS → raw_news 保存、SSRF 対策、前処理）
  - データ品質チェック（欠損・スパイク・重複・日付整合性）
  - 監査（audit）スキーマ作成・初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- AI（OpenAI を用いた処理）
  - ニュースセンチメント（score_news: 銘柄別 ai_score を ai_scores に書き込み）
  - 市場レジーム判定（score_regime: ETF 1321 の MA とマクロニュースで判定）
- Research（リサーチ向けユーティリティ）
  - ファクター計算（momentum, volatility, value）
  - 特徴量探索（forward returns, IC（Spearman）、統計サマリー、rank 関数）

---

## セットアップ手順（開発/利用開始）

1. Python（3.10+ 推奨）を用意します。

2. 依存ライブラリをインストールします（例）:
   - duckdb
   - openai
   - defusedxml
   - そのほか標準ライブラリ以外のものが必要な場合は適宜インストールしてください。

   例:
   ```
   pip install duckdb openai defusedxml
   # または develop インストール (パッケージ構成がセットされている場合)
   pip install -e .
   ```

3. 環境変数 / .env を用意します。
   - プロジェクトルート（.git または pyproject.toml のある位置）から自動で `.env` / `.env.local` を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主な環境変数（最低限必要なもの）
     - JQUANTS_REFRESH_TOKEN: J-Quants の refresh token（ETL 用）
     - KABU_API_PASSWORD: kabu ステーション API のパスワード（発注等で使用する想定）
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
     - OPENAI_API_KEY: OpenAI API キー（ニュース NLP / レジーム判定で使用）
     - DUCKDB_PATH: (任意) DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: (任意) 監視用 SQLite（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
   - .env のパースは一般的な shell 形式をサポート（export KEY=val, quotes, コメント等）。

4. DuckDB データベース初期化（監査 DB の例）
   - 監査ログ専用 DB を初期化:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - 通常は既存のメイン DuckDB に対して init_audit_schema(conn) を呼び出してテーブルを追加できます。

---

## 使い方（主要な API 例）

- 設定の参照:
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)   # Path オブジェクト
  print(settings.is_live)       # bool
  ```

- DuckDB 接続:
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行:
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- 個別 ETL ジョブ:
  ```python
  from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl
  run_prices_etl(conn, target_date=date(2026,3,20))
  ```

- ニュースセンチメントスコアリング:
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"wrote {n_written} ai_scores")
  ```

- 市場レジーム判定:
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査スキーマ初期化（既存接続に対して）:
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn)
  ```

- リサーチユーティリティ（例: モメンタム計算）:
  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date

  momentum = calc_momentum(conn, target_date=date(2026,3,20))
  ```

注意:
- OpenAI を使う関数は api_key を引数で注入できます（テスト容易性のため）。指定しない場合は環境変数 `OPENAI_API_KEY` を参照します。
- ETL / news などはネットワーク IO を行うため、例外やレート制限に備えて呼び出し側でログやリトライ設計を行ってください。

---

## 環境変数（主な一覧）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須): kabu API 用パスワード（発注等）
- KABU_API_BASE_URL (任意): kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須): Slack Bot Token
- SLACK_CHANNEL_ID (必須): Slack チャンネル ID
- OPENAI_API_KEY (必須 for AI): OpenAI API キー
- DUCKDB_PATH (任意): DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意): SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意): development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意): DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効化します。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
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
  - calendar_management.py
  - news_collector.py
  - quality.py
  - stats.py
  - audit.py
  - pipeline.py (ETLResult 再エクスポート)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research, monitoring, execution, strategy 等（パッケージ公開用 __all__ はトップレベルで定義）

（上記は本コードベースの主要モジュールです。実際のリポジトリではこの他にテストやドキュメント、スクリプト等が存在する可能性があります。）

---

## 運用上の注意点

- Look-ahead バイアス対策: 本ライブラリはバックテスト等での安易な現在時刻参照を避ける設計になっています。target_date を明示することで過去時点の情報のみを使って処理できます。
- API リトライとレート制御: J-Quants には固定レートリミットとリトライロジック、OpenAI 呼び出しにもエクスポネンシャル・バックオフを実装していますが、運用時は個別の SLA を確認してください。
- データ品質: ETL 実行後に quality.run_all_checks を実行して、欠損やスパイクなどを監視してください。
- セキュリティ: news_collector は SSRF 対策や XML サニタイズを実装していますが、外部フィードの扱いには注意してください。

---

## 参考（よく使う関数）

- kabusys.data.pipeline.run_daily_etl(...)
- kabusys.data.jquants_client.fetch_daily_quotes(...)
- kabusys.data.jquants_client.save_daily_quotes(...)
- kabusys.data.quality.run_all_checks(...)
- kabusys.ai.news_nlp.score_news(...)
- kabusys.ai.regime_detector.score_regime(...)
- kabusys.data.audit.init_audit_db(...) / init_audit_schema(...)

---

README の内容はコードのコメント・ドキュメント文字列（docstring）を基にまとめています。さらに実行例や CI / デプロイ手順、requirements.txt / pyproject.toml に基づく厳密な依存管理は実プロジェクトの配布形態に合わせて追記してください。必要であればサンプル .env.example やよくあるトラブルシュート（API キー・ネットワーク・DB パス）も用意します。どの追加情報が必要か教えてください。