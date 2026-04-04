# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ（モジュール群）。  
価格・財務・カレンダー等の ETL、ニュース収集・NLP（OpenAI）によるスコアリング、ファクター計算、監査ログなどを提供します。

※ 本 README はリポジトリ内のソースコード（src/kabusys 以下）を元に作成しています。

## プロジェクト概要

KabuSys は日本株の自動売買システムや研究環境向けのユーティリティ群をまとめた Python パッケージです。主な目的は以下です。

- J-Quants API からのデータ取得（株価日足、財務、上場銘柄、JPX カレンダー）
- DuckDB を用いた差分 ETL と品質チェック
- RSS によるニュース収集と記事の前処理／紐付け
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント分析（銘柄別スコア）および市場レジーム判定
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用テーブル初期化ユーティリティ

設計上の特徴として、ルックアヘッドバイアスを避けるために日付参照の扱いに注意した実装（target_date ベース）や、外部 API 呼び出しでのリトライ／バックオフ、DuckDB への冪等保存などが組み込まれています。

## 機能一覧

- 環境変数 / .env ロードと設定管理（kabusys.config）
  - 自動でプロジェクトルートの `.env` / `.env.local` を読み込む（無効化可）
- J-Quants クライアント（kabusys.data.jquants_client）
  - 認証（refresh token → id token）、レートリミット、リトライ、ページネーション対応
  - データ取得: daily_quotes（株価）、financial_statements（財務）、trading_calendar（JPX カレンダー）、listed/info（上場情報）
  - DuckDB への保存（raw_prices, raw_financials, market_calendar 等）を冪等に実行
- ETL パイプライン（kabusys.data.pipeline）
  - 差分取得、バックフィル、品質チェック（kabusys.data.quality）を含む日次 ETL 実行
  - ETLResult に結果を集約
- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク、重複、日付不整合等の検出と QualityIssue レポート
- ニュース収集（kabusys.data.news_collector）
  - RSS フィードの取得、URL 正規化、前処理、SSRF 対策、raw_news への冪等保存（設計に沿った処理）
- AI/NLP（kabusys.ai）
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを取得し ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成して market_regime を生成
  - OpenAI 呼び出しはリトライ・パースフェイルセーフ設計
- 研究モジュール（kabusys.research）
  - calc_momentum / calc_value / calc_volatility 等のファクター計算
  - calc_forward_returns, calc_ic, factor_summary, rank 等の特徴量解析ユーティリティ
  - data.stats.zscore_normalize（クロスセクション正規化）
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等のテーブル定義と初期化関数
  - init_audit_schema / init_audit_db による冪等初期化

## セットアップ手順

前提
- Python 3.10 以上（コード内の型記法 Path | None 等を利用）
- ネットワークアクセス（J-Quants API / OpenAI / RSS 等）

基本的な手順（例）

1. リポジトリをクローン
   ```bash
   git clone <this-repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージのインストール（代表的なもの）
   ```bash
   pip install duckdb openai defusedxml
   ```
   ※ 実際にはプロジェクトに requirements.txt / pyproject.toml がある想定です。あればそちらを使ってください。
   例:
   ```bash
   pip install -e .
   # or
   pip install -r requirements.txt
   ```

4. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を作成してください（.env.example を参照する想定）。
   - 重要な環境変数（主要なもの）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector を使う場合）
     - KABU_API_PASSWORD: kabuステーション API を使う場合のパスワード
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知を使う場合
     - DUCKDB_PATH: デフォルトの DuckDB ファイルパス（例: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite パス（例: data/monitoring.db）
     - KABUSYS_ENV: environment（development / paper_trading / live）
     - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

   自動ロードについて:
   - パッケージ import 時にプロジェクトルートを特定して `.env` / `.env.local` を読み込みます。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト時等に利用）。

5. データベース準備（監査 DB 初期化例）
   ```python
   import duckdb
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   ```

## 使い方（代表的な例）

以下は主要ユースケースの簡易例です。詳細は各モジュールの docstring を参照してください。

- DuckDB 接続を作成（デフォルトパスは settings.duckdb_path）
  ```python
  import duckdb
  from kabusys.config import settings
  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行（差分取得 → 品質チェック）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース（銘柄別）スコアリング（OpenAI 必須）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  # api_key を明示的に渡すか OPENAI_API_KEY を環境変数に設定
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print("written:", n_written)
  ```

- 市場レジームの判定（ETF 1321 MA200 乖離 + マクロニュース）
  ```python
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- ファクター計算・研究用ユーティリティ
  ```python
  from datetime import date
  from kabusys.research import calc_momentum, calc_value, calc_volatility
  mom = calc_momentum(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  ```

- 監査スキーマの初期化（既存接続に対して）
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)
  ```

注意点
- OpenAI 呼び出しはレートや料金が発生します。API キー管理とコストに注意してください。
- J-Quants API の利用には有効なトークンとアカウントが必要です。
- ETL / 研究処理は DuckDB 上のスキーマ（raw_prices, raw_financials, raw_news, market_calendar, ai_scores, market_regime 等）を前提としています。初期スキーマ作成はプロジェクト側で用意してください（schema 初期化ユーティリティがある想定）。

## 主要な環境変数

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 等）
- KABU_API_PASSWORD: kabuステーション API パスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
- DUCKDB_PATH: デフォルト DuckDB ファイルパス（例: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite ファイルパス
- PID_FILE_PATH / KILL_FLAG_PATH: 実行監視用ファイルパス
- KILL_FLAG_CLEAR_ON_START: 起動時に kill flag をクリアするか（"1" で True）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値（%）
- KABUSYS_ENV: "development" / "paper_trading" / "live"
- LOG_LEVEL: "DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL"

## ディレクトリ構成（抜粋）

リポジトリの中核モジュールは src/kabusys にあります。主要ファイルと短い説明を示します。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数/.env 読み込み、Settings クラス（設定値の集約）
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースを銘柄ごとに集約して OpenAI でスコアリングし ai_scores に保存
    - regime_detector.py
      - ETF 1321 の MA200 乖離とマクロニュースの LLM 評価を合成して market_regime を生成
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存ロジック、認証、レート制御）
    - pipeline.py
      - ETL の上位制御（run_daily_etl 等）
    - etl.py
      - ETLResult の再エクスポート
    - news_collector.py
      - RSS フィードの取得・前処理・保存（SSRF 対策等）
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - calendar_management.py
      - 市場カレンダー管理、営業日判定、calendar_update_job
    - audit.py
      - 監査ログ用テーブル DDL と初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py
      - Momentum / Value / Volatility / Liquidity 等のファクター計算
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリー等

（注）コードベースにより細かいユーティリティや補助モジュールが含まれます。上記は主要コンポーネントの抜粋です。

## 運用上の注意・ベストプラクティス

- ルックアヘッドバイアスに注意
  - 多くの関数は target_date 引数に基づいて過去データのみを参照するよう設計されています。実運用・バックテストでは target_date を適切に与えてください。
- 環境分離
  - KABUSYS_ENV により挙動を切替可能です（development / paper_trading / live）。本番（live）では十分な監視と検証を行ってください。
- API キー管理
  - J-Quants / OpenAI / kabu API のキーは安全に管理し、公開リポジトリ等に含めないでください。
- コスト管理
  - OpenAI の呼び出しはコストが発生します。バッチサイズや頻度を制御して運用してください。
- テストとモック
  - OpenAI 呼び出し等はテストでモック交換できるよう内部抽象化（_call_openai_api をモックする等）されています。CI での実行時には外部呼び出しを防ぐことを推奨します。

---

詳細な使い方やスキーマ定義、運用用ドキュメントは別途 DataPlatform.md / StrategyModel.md 等を参照してください（コード内 docstring にも多くの設計意図が記載されています）。

ご不明点や README に追加したいサンプル（Docker 化、systemd unit、cron スケジュール等）があれば教えてください。必要に応じて追記します。