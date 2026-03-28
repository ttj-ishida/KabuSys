# KabuSys

日本株向けのデータプラットフォームおよび自動売買支援ライブラリです。  
J-Quants / DuckDB を中心とした ETL、ニュースセンチメント（LLM）解析、研究用ファクター計算、監査ログ（発注/約定トレーサビリティ）といった機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム開発を支援するためのモジュール群です。主な目的は次のとおりです：

- J-Quants API からのデータ取得（株価日足・財務・マーケットカレンダー）
- DuckDB を用いた高速なローカルデータ格納
- ETL パイプライン（差分取得、保存、品質チェック）
- ニュースの収集と LLM による銘柄別センチメント付与
- 市場レジーム判定（MA200 + マクロニュース）
- 研究用ファクター計算・特徴量解析（モメンタム、ボラティリティ、バリュー等）
- 監査ログ（signal → order_request → executions）の初期化・管理

設計上、バックテスト時のルックアヘッドバイアス防止や API リトライ・レート制限、ETL の冪等性（ON CONFLICT / INSERT UPDATE）を重視しています。

---

## 機能一覧

- Data
  - J-Quants クライアント（fetch / save）
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - 市場カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - ニュース収集（RSS → raw_news）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計（zscore_normalize）

- AI / NLP
  - ニュースセンチメント付与（score_news）
  - 市場レジーム判定（score_regime; MA200 とマクロニュースの合成）

- Research
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）

- 設定管理
  - .env 自動ロード（プロジェクトルート検出: .git または pyproject.toml）
  - 環境変数検証・ラッパー（kabusys.config.settings）

---

## 必要条件

- Python 3.10 以上（Union 型記法などを使用）
- 必要パッケージ（代表例）
  - duckdb
  - openai
  - defusedxml
  - （その他: requests を使わない実装のため標準ライブラリ中心ですが、利用環境に応じて追加）

pip のインストール要件ファイルがある場合はそちらを使用してください。

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置

   git clone ... またはプロジェクト配布に従ってソースを入手してください。

2. 仮想環境を作成して依存関係をインストール

   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install duckdb openai defusedxml

   （プロジェクトで requirements.txt / pyproject.toml がある場合はそちらを利用してください）

3. 環境変数の設定（.env）

   プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可）。

   主要な環境変数例（.env）:

   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=your_openai_api_key
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=your_slack_token
   SLACK_CHANNEL_ID=your_slack_channel
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

   注意: Settings クラスは必須変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）を _require で検査します。実行前に適切に設定してください。

4. データベースディレクトリの作成（必要なら）

   デフォルトの DB パスは data/ 以下なので、プロジェクトで使用する場合は事前にディレクトリを作ると安全です。

---

## 使い方（主要なユースケース例）

以下はライブラリを直接インポートして使う基本例です。実行はプロジェクトルートで行ってください。

- DuckDB 接続の生成例

  from pathlib import Path
  import duckdb
  from kabusys.config import settings

  db_path = str(settings.duckdb_path)  # デフォルト data/kabusys.duckdb
  Path(db_path).parent.mkdir(parents=True, exist_ok=True)
  conn = duckdb.connect(db_path)

- 日次 ETL を実行する

  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

  - run_daily_etl はカレンダー → 株価 → 財務 → 品質チェックを順に実行し ETLResult を返します。

- ニュースセンチメント取得（LLM）例

  from kabusys.ai.news_nlp import score_news
  from datetime import date

  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_KEY")
  print(f"written scores: {n_written}")

  - OPENAI_API_KEY は api_key 引数か環境変数で渡せます。
  - raw_news / news_symbols テーブルが前提です。

- 市場レジーム判定（MA200 + マクロニュース）

  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_KEY")

- 監査ログスキーマ初期化

  from kabusys.data.audit import init_audit_db, init_audit_schema
  conn_audit = init_audit_db("data/audit.duckdb")  # ディレクトリを自動作成
  # あるいは既存 conn に対して
  init_audit_schema(conn, transactional=True)

- 市場カレンダーの判定ユーティリティ

  from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days
  from datetime import date

  is_trading = is_trading_day(conn, date(2026, 3, 20))
  next_day = next_trading_day(conn, date(2026, 3, 20))
  days = get_trading_days(conn, date(2026, 3, 1), date(2026, 3, 31))

- 研究用ファクター計算

  from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
  from datetime import date

  m = calc_momentum(conn, target_date=date(2026,3,20))
  v = calc_volatility(conn, target_date=date(2026,3,20))
  val = calc_value(conn, target_date=date(2026,3,20))

---

## 設定・環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（LLM 呼び出しに使用）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: 環境（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動ロードを無効化

.env のパースはシェルの export KEY=val やコメント、クォートをある程度許容する実装です。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
  - 環境変数読み込みと settings オブジェクト定義
- ai/
  - __init__.py
  - news_nlp.py           — ニュースを LLM でスコアリング（score_news）
  - regime_detector.py    — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py     — J-Quants API クライアント / DuckDB 保存関数
  - pipeline.py           — ETL パイプライン（run_daily_etl 等）
  - etl.py                — ETLResult の公開（再エクスポート）
  - calendar_management.py— 市場カレンダーユーティリティ
  - news_collector.py     — RSS 収集・前処理・保存ロジック
  - quality.py            — データ品質チェック
  - stats.py              — 汎用統計（zscore_normalize）
  - audit.py              — 監査ログスキーマ（signal/order_requests/executions）
- research/
  - __init__.py
  - factor_research.py    — モメンタム / ボラティリティ / バリュー算出
  - feature_exploration.py— 将来リターン / IC / 統計サマリー 等
- research/（モジュール群は研究目的で、実取引系 API 呼び出しは行わない）
- その他モジュール群（strategy / execution / monitoring）へのエクスポートプレースホルダあり

---

## 開発・運用上の注意

- ルックアヘッドバイアス防止:
  - 多くの関数は内部で datetime.today()/date.today() を直接参照せず、target_date を受け取る設計です。バックテストで正しく時系列整合を保つために target_date を明示してください。
- 冪等性:
  - ETL / save_* 関数は ON CONFLICT / INSERT ... DO UPDATE により冪等化されています。
- API レート・リトライ:
  - J-Quants, OpenAI 呼び出しでリトライ・指数バックオフ・レート制限を実装しています（ただし実行環境での追加制御が必要な場合があります）。
- 安全性:
  - news_collector は SSRF 対策や XML 攻撃対策（defusedxml）を組み込んでいます。RSS フィード取り扱い時は注意して設定してください。

---

## 貢献・テスト

- ユニットテストでは外部 API 呼び出しをモックすることを想定しています（例: kabusys.ai.news_nlp._call_openai_api を patch）。
- .env 自動ロードはテストで影響するため、必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化してください。

---

もし README に追加したい使い方（CLI、具体的なワークフロー、CI 設定、Docker 化など）があれば教えてください。必要に応じてサンプルスクリプトやテンプレート .env.example を作成します。