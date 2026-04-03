# KabuSys

日本株向けの自動売買基盤ライブラリ（KabuSys）のコードベース向け README（日本語）

概要、機能、セットアップと使い方、ディレクトリ構成を簡潔にまとめています。ライブラリは主にデータ取得（J-Quants）、ETL、ニュース NLP（OpenAI）、市場レジーム判定、リサーチ（ファクター計算）、監査ログ（約定トレーサビリティ）などを提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買基盤を構成するモジュール群です。主な役割は次のとおりです。

- J-Quants API からのデータ取得（株価日足・財務・マーケットカレンダー）
- DuckDB を用いたデータ格納と ETL パイプライン
- ニュース記事の収集・前処理・LLM によるセンチメントスコアリング（OpenAI）
- 市場レジーム判定（ETF の MA とマクロニュースの LLM スコアを合成）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー 等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 発注／約定を追跡する監査ログスキーマ（DuckDB 上の冪等テーブル群）
- 簡易的な監視 / 実行設定管理（環境変数読み込み）

設計方針としては「ルックアヘッドバイアスの排除」「冪等性」「外部 API の堅牢なリトライ」「DuckDB ベースでのローカル永続化」を重視しています。

---

## 主な機能一覧

- データ取得 / ETL
  - J-Quants クライアント（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - データ保存（save_daily_quotes / save_financial_statements / save_market_calendar）

- データ品質
  - 欠損、スパイク、重複、日付不整合を検出する quality モジュール
  - run_all_checks で一括チェック

- ニュース収集 / NLP
  - RSS 取得と前処理（news_collector.fetch_rss / preprocess_text）
  - OpenAI を用いた銘柄別ニュースセンチメント（ai.news_nlp.score_news）
  - 市場レジーム判定（ai.regime_detector.score_regime）

- 研究（Research）
  - ファクター計算（research.factor_research: calc_momentum, calc_volatility, calc_value）
  - 特徴量探索（research.feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank）
  - 統計ユーティリティ（data.stats.zscore_normalize）

- 監査 / トレーサビリティ
  - 監査テーブル定義と初期化（data.audit.init_audit_schema / init_audit_db）
  - order_requests / signal_events / executions テーブル（冪等性・インデックス含む）

- 環境設定
  - settings（kabusys.config）で .env 自動読み込み、必須項目の取得、各種パス・閾値の取得

---

## セットアップ手順

前提: Python 3.9+（型注釈や構文から互換性が高い環境を想定）

1. リポジトリをクローン／配置

   git clone <repo-url>
   cd <repo-dir>

2. 仮想環境の作成（推奨）

   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate

3. インストール（開発モード）

   pip install -e .   # setup.py/pyproject がある場合

   もしくは必要パッケージを直接インストール：
   pip install duckdb openai defusedxml

   ※ 実行環境に合わせて追加パッケージをインストールしてください。

4. 環境変数設定
   プロジェクトルートに `.env`（および `.env.local`）を置くと自動読み込みされます（kabusys.config が .git または pyproject.toml を基準に自動検出）。

   必須（最低限）:
   - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   OpenAI を使う場合:
   - OPENAI_API_KEY=your_openai_api_key

   その他（任意・デフォルトあり）:
   - KABU_API_PASSWORD
   - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
   - LINE_CHANNEL_ACCESS_TOKEN
   - LINE_USER_ID
   - DUCKDB_PATH (default: data/kabusys.duckdb)
   - SQLITE_PATH (default: data/monitoring.db)
   - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
   - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
   - KABUSYS_ENV (development | paper_trading | live)
   - LOG_LEVEL (DEBUG/INFO/...)

   例 .env（抜粋）:
   ```
   JQUANTS_REFRESH_TOKEN=XXXXXXXXXXX
   OPENAI_API_KEY=sk-xxxx...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. 自動 .env 読み込みを無効化したい場合:
   - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

---

## 使い方（主要な例）

以下は代表的な利用パターンです。基本は DuckDB の接続を作成し、各 API を呼ぶ形です。

- 共通準備（Python REPL / スクリプト内）

  from datetime import date
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する（市場カレンダー、株価、財務、品質チェック含む）

  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメントを算出して ai_scores に書き込む

  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # API キーは OPENAI_API_KEY 環境変数、または第3引数で渡す
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュース LLM を合成）

  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))

- 監査 DB の初期化

  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # audit_conn 上で発注・約定の監査ログを管理できます

- リサーチ（ファクター計算 例）

  from kabusys.research.factor_research import calc_momentum
  from datetime import date

  records = calc_momentum(conn, date(2026, 3, 20))
  # records は各銘柄ごとの辞書リスト

- 設定参照例

  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)

---

## 注意点・運用上のポイント

- Look-ahead バイアス防止
  - 多くのモジュール（news_nlp, regime_detector, pipeline 等）は date.today() を直接参照せず、関数引数で日付を与える設計になっています。バックテストや再現性のため、target_date を明示して利用してください。

- 冪等性
  - ETL の保存メソッドは ON CONFLICT DO UPDATE を使って冪等性を保ちます（DuckDB）。同一キーでの二重処理に配慮しています。

- 外部 API のリトライ・レート制御
  - J-Quants クライアントは固定間隔の RateLimiter と指数バックオフを組み合わせています。OpenAI 呼び出しもリトライ／フェイルセーフの実装があります（失敗時に 0.0 を代替など）。

- セキュリティ
  - news_collector は SSRF 対策（リダイレクト検査、プライベート IP チェック）、defusedxml による XML パース防御、最大レスポンスサイズ制限などを実装しています。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                   -- 環境変数・設定管理
- ai/
  - __init__.py
  - news_nlp.py               -- ニュースセンチメント（OpenAI）
  - regime_detector.py        -- 市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py         -- J-Quants API クライアント & DuckDB 保存
  - pipeline.py               -- ETL パイプライン / run_daily_etl 等
  - etl.py                    -- ETLResult 再エクスポート
  - quality.py                -- データ品質チェック
  - news_collector.py         -- RSS 収集・前処理
  - calendar_management.py    -- 市場カレンダー管理 / is_trading_day など
  - stats.py                  -- 統計ユーティリティ（zscore_normalize）
  - audit.py                  -- 監査（監査テーブル定義・初期化）
- research/
  - __init__.py
  - factor_research.py        -- ファクター計算（momentum/volatility/value）
  - feature_exploration.py    -- 将来リターン、IC、統計サマリー
- ai & research パッケージは研究・分析用途の API を公開

---

## 開発・テスト

- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探します。テスト時に自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し部や外部 HTTP はユニットテスト時にモックすることを想定して実装されています（内部関数のパッチ等）。

---

## 最後に

この README はコードベースの主要な使い方と構成を簡潔にまとめたものです。各モジュールには docstring や詳細なログ・設計思想が書かれているため、実装側のドキュメントや API コメントを参照してください。何か追記してほしい項目があれば教えてください。