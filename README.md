# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
データ収集（J-Quants）, ETL, データ品質チェック、ニュースNLP（OpenAI）によるセンチメント計算、マーケットレジーム判定、監査ログなどを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は、日本株の自動売買基盤／研究基盤向けに設計されたモジュール群です。主な目的は次のとおりです。

- J-Quants API からのデータ取得（株価日足、財務、マーケットカレンダー）
- ETL（差分取得・保存・品質チェック）の一元化
- ニュース収集（RSS）とニュースに対する LLM（OpenAI）による銘柄別センチメント算出
- ETF を使った市場レジーム判定（MA と マクロニュースの合成スコア）
- 監査ログ（signal → order_request → executions）を保存する監査スキーマ
- 研究（ファクター計算・特徴量解析）ユーティリティ

設計上の特徴:
- Look-ahead bias を避ける実装（date / target_date に基づく処理）
- DuckDB を主要な永続化ストアとして利用（ローカルファイル / インメモリ可能）
- 外部 API 呼び出しはリトライ・バックオフ・レート制御を考慮
- 自動 .env ロード機能（プロジェクトルートを探索）

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（無効化可）
  - 必須環境変数のラップ（settings オブジェクト）
- データ収集 / ETL
  - J-Quants クライアント（fetch / save の idempotent 実装）
  - run_daily_etl：日次 ETL パイプライン（カレンダー → 株価 → 財務 → 品質チェック）
  - calendar_update_job：JPX カレンダーの更新ジョブ
- データ品質チェック
  - 欠損、スパイク（急変動）、重複、日付不整合の検出
- ニュース処理 / NLP
  - RSS フィード収集（SSRF 対策、サイズ上限、トラッキング除去）
  - OpenAI を用いたニュースセンチメント（ai.news_nlp.score_news）
  - 市場レジーム判定（ai.regime_detector.score_regime）
- 研究用ユーティリティ
  - ファクター計算（momentum, value, volatility）
  - 将来リターン計算、IC（情報係数）、統計サマリー、Zスコア正規化
- 監査ログ（audit）
  - signal_events, order_requests, executions のテーブル定義と初期化
  - init_audit_db / init_audit_schema による冪等初期化

---

## セットアップ手順

前提
- Python 3.10 以上（PEP 604 の | 型や from __future__ import annotations を使用）
- DuckDB, OpenAI SDK 等を使用

1. リポジトリをクローン（例）
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

3. 必要パッケージのインストール（プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを使ってください）
   代表的な依存例:
   ```
   pip install duckdb openai defusedxml
   ```
   - duckdb: 内部データベース
   - openai: LLM 呼び出し（gpt-4o-mini 等）
   - defusedxml: RSS パースの安全化

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml のある階層）に `.env` / `.env.local` を配置すると自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主な環境変数（必須・任意）:

     - JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD (必須): kabuステーション API のパスワード
     - KABU_API_BASE_URL (任意): kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN (必須): Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID (必須): Slack チャンネル ID
     - OPENAI_API_KEY (必須 for NLP): OpenAI API キー（news_nlp / regime_detector の呼び出しに必要）
     - DUCKDB_PATH (任意): DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH (任意): monitoring 用 SQLite パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV (任意): environment ('development' | 'paper_trading' | 'live')（デフォルト: development）
     - LOG_LEVEL (任意): ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）

   - .env の手動ロードをスキップしたいテスト時等は環境変数:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

5. データベースの初期化（監査スキーマ例）
   Python から:
   ```python
   import duckdb
   from kabusys.data.audit import init_audit_schema

   conn = duckdb.connect("data/kabusys.duckdb")
   init_audit_schema(conn, transactional=True)
   ```

---

## 使い方（主要なユースケース）

以下はライブラリを直接インポートして使う例です。各関数は DuckDB 接続オブジェクト（duckdb.DuckDBPyConnection）を受け取ります。

- 設定（settings）を使う
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  ```

- 日次 ETL の実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントの算出（OpenAI APIキーは環境変数 OPENAI_API_KEY で設定）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  cnt = score_news(conn, target_date=date(2026, 3, 20))  # OpenAI key は env で
  print(f"scored {cnt} codes")
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査DBの初期化（専用 DB を作る場合）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- 市場カレンダー関連ユーティリティ
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

- ニュース収集（RSS）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  ```

注意点:
- OpenAI を用いる関数は API 呼び出しの失敗に対してフォールバック/スキップする実装がなされていますが、APIキーの設定とレートにご注意ください。
- ETL 処理は id_token の自動取得（J-Quants）やレート制御を内包しています。

---

## ディレクトリ構成（抜粋）

src/kabusys パッケージの主要なファイル/モジュール：

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（settings）
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント（OpenAI 呼び出し含む）
    - regime_detector.py     — ETF MA と マクロニュースで市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch / save）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETLResult 再エクスポート
    - calendar_management.py — マーケットカレンダー管理（is_trading_day など）
    - news_collector.py      — RSS ニュース収集
    - quality.py             — データ品質チェック
    - stats.py               — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py               — 監査ログスキーマ定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py     — モメンタム/バリュー/ボラティリティ等の計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー 等
  - (その他)                 — strategy, execution, monitoring のプレースホルダ等

（実際のプロジェクトルートには pyproject.toml / README.md / .env.example 等がある想定です）

---

## 環境変数まとめ（主要）

- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu ステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API ベース URL（任意、デフォルトあり）
- SLACK_BOT_TOKEN — Slack 通知用（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
- OPENAI_API_KEY — OpenAI API キー（news/regime 関数で必要）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 'development'/'paper_trading'/'live'（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化する場合に "1" を設定

---

## 開発・テストに関する注意

- 自動で .env を読み込む仕組みはプロジェクトルート（.git / pyproject.toml）を基準に行われます。テスト時に環境依存を避けるには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI・J-Quants の実際の API 呼び出しはネットワークを利用するため、ユニットテストでは各所の内部呼び出し（例: kabusys.ai.news_nlp._call_openai_api）をモックすることが前提です。
- DuckDB を使うコードはインメモリ ":memory:" 接続でも動作するように設計されています（init_audit_db の引数などで利用可能）。

---

この README はコードベースの主要機能と基本的な使い方をまとめたものです。詳しい実装仕様や API の細かい振る舞いは各モジュール内のドキュメント文字列（docstring）を参照してください。必要であれば利用シナリオ別のサンプルや運用手順（cron ジョブ、監視、Slack 通知連携等）を追記します。