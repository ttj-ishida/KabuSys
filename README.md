# KabuSys（日本株自動売買システム）README

以下はこのリポジトリ（パッケージ名: kabusys）の概要・セットアップ・使い方・ディレクトリ構成の説明です。

## プロジェクト概要
KabuSys は日本株のデータプラットフォーム、リサーチ、AI ニュースセンチメント、監査ログ、ETL、マーケットカレンダー管理、及び取引戦略向けユーティリティを含むモジュール集合です。主な目的は以下のとおりです。

- J-Quants API からの株価・財務・カレンダー取得と DuckDB への ETL
- RSS ニュース収集と記事の前処理（SSRF・サイズ制限等の保護あり）
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価（銘柄別 / マクロ）
- 市場レジーム判定（ETF を用いた MA とマクロセンチメントの合成）
- 研究用ファクター計算・特徴量解析ユーティリティ（モメンタム、バリュー、ボラティリティ等）
- データ品質チェックと監査ログ（signal → order → execution トレーサビリティ）
- kabuステーション等への発注ロジック（別モジュール想定）

設計上、ルックアヘッドバイアスを避けるために日付処理は明示的で、外部依存（OpenAI / J-Quants）はリトライ・フォールバックが組み込まれています。

## 機能一覧
- data/
  - jquants_client: J-Quants API クライアント（取得・保存・ページング・レート制御・トークン自動リフレッシュ）
  - pipeline: 日次 ETL（prices / financials / calendar）、ETLResult を返却
  - news_collector: RSS 収集、記事正規化、raw_news へ保存支援
  - calendar_management: 市場カレンダーの判定・更新・next/prev_trading_day 等
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査テーブルの DDL / 初期化（signal_events / order_requests / executions）
  - stats: zscore 正規化ユーティリティ
- ai/
  - news_nlp: 銘柄単位のニュースセンチメントを OpenAI でスコアリング（ai_scores へ保存する処理と組み合わせて使用）
  - regime_detector: ETF (1321) の MA200 乖離とマクロニュースセンチメントを合成して市場レジームを判定し market_regime に保存
- research/
  - factor_research: momentum / value / volatility ファクター計算
  - feature_exploration: 将来リターン計算、IC 計算、サマリー等
- config: 環境変数の読み込み（.env 自動ロード、必須キー取得用ユーティリティ）

## 前提条件
- Python 3.10+
- 必要な主要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続（J-Quants / OpenAI / RSS フィード など）

実際のプロジェクトでは pyproject.toml / requirements.txt を用意してください。

## セットアップ手順（例）
1. Python 仮想環境を作成して有効化:
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）:
   - pip install duckdb openai defusedxml

   ※ 実際にはプロジェクトの requirements.txt / pyproject.toml を使ってください。

3. 環境変数を設定（.env をプロジェクトルートに置くと自動で読み込まれます。読み込みは config モジュールで行われ、.env.local が優先されます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します）。

4. DuckDB ファイルや監査用 DB の初期化（例）:
   - Python REPL で:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

   - または ETL 用の DB パスは環境変数 settings.duckdb_path を使用できます。

## 環境変数（主なもの）
以下はコード内で参照される主な環境変数です（実運用では .env.example を用意してください）。

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- OPENAI_API_KEY (必須 for AI features) — OpenAI API キー
- KABU_API_PASSWORD — kabu API パスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — 通知用 Slack 設定
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（デフォルト data/monitoring.db）
- KABUSYS_ENV — environment: development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル：DEBUG/INFO/WARNING/ERROR/CRITICAL

config.Settings 経由で安全に取得できます。必須キーは取得時にエラーを投げます。

## 使い方（簡易例）

- DuckDB に接続して ETL を実行（日次 ETL）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースの銘柄別スコア（OpenAI を使う）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY を環境変数か引数で渡す
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print(f"wrote {written} ai_scores")
  ```

- 市場レジーム判定:
  ```python
  from kabusys.ai.regime_detector import score_regime
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- RSS フィード取得（news_collector.fetch_rss）:
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  ```

- 監査ログテーブル初期化:
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

注意点:
- AI 関連関数（score_news, score_regime）は OPENAI_API_KEY が必要です。api_key を引数で渡すか環境変数を設定してください。
- 日付操作は全て明示的に target_date を渡す設計です（内部で date.today() に依存しないよう考慮されています）。

## ディレクトリ構成（抜粋）
パッケージルート: src/kabusys 以下の主なファイルとモジュールを示します。

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py (score_news を再エクスポート)
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - calendar_management.py
    - pipeline.py
    - etl.py
    - jquants_client.py
    - news_collector.py
    - quality.py
    - stats.py
    - audit.py
    - etl.py (ETLResult エクスポート)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/*（factor / feature exploration modules）

各ファイルはモジュール別に明確な責務（ETL, API クライアント, AI, 研究用ユーティリティ, 品質チェック, 監査）を持っています。

## 開発・テスト時のヒント
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml があるディレクトリ）から行われます。テストから自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し部分は内部で _call_openai_api を呼んでおり、テスト時は unittest.mock.patch で差し替え可能です（モジュールごとに別実装になっているため依存を分離しています）。
- J-Quants クライアントは内部でレートリミッタとリトライを実装しています。local 環境でのテストやモックを推奨します。

## 付記
- 実運用での注文実行・ブローカー連携は注意が必要です。実際の約定・送信ロジックは別モジュールで安全性（冪等性・エラーハンドリング・金額制限等）を確実に実装してください。
- ライセンス情報や CI / packaging（pyproject.toml、tests、requirements.txt）はプロジェクトルートに追加して整備してください。

必要であれば README にサンプル .env.example、詳細な API 使用例、よくあるエラーと対処方法、開発ルール（型・ロギング基準）なども追記します。どの項目を拡張したいか教えてください。