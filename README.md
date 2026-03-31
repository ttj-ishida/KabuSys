# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。  
データのETL、ニュースのNLPスコアリング、マーケットレジーム判定、ファクター計算、監査ログ（トレーサビリティ）など、取引システム／研究環境で必要となる共通処理をモジュール化しています。

バージョン: 0.1.0

---

## 概要

KabuSys は以下のような機能を提供する Python パッケージです。

- J-Quants API からのデータ取得（株価日足 / 財務 / 市場カレンダー）と DuckDB への保存（ETL）
- RSS ニュース収集と前処理、ニュース→銘柄紐付け
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント解析（銘柄別）とマクロセンチメント評価
- マーケットレジーム判定（ETF 1321 の MA200 とマクロセンチメントを合成）
- ファクター計算（モメンタム / バリュー / ボラティリティ等）と特徴量探索ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログスキーマ（シグナル→発注→約定のトレースを保証）
- 環境変数ベースの設定管理（.env の自動読み込み）

設計上の要点として、バックテストでのルックアヘッドバイアスを避けるために「target_date を明示する」「datetime.now()/today() を内部で不用意に参照しない」等を徹底しています。

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（レートリミット、リトライ、トークン自動リフレッシュ）
  - news_collector（RSS 取得、SSRF/サイズ/圧縮対策、前処理、記事ID冪等性）
  - calendar_management（JPX カレンダー管理、営業日判定ユーティリティ）
  - quality（データ品質チェック）
  - audit（監査ログスキーマ初期化 / 専用DB初期化ユーティリティ）
  - stats（zscore_normalize 等の統計ユーティリティ）
- ai/
  - news_nlp.score_news(conn, target_date, api_key=None)：銘柄別ニュースセンチメント解析→ai_scores へ書込
  - regime_detector.score_regime(conn, target_date, api_key=None)：マクロセンチメント + MA200 で市場レジーム判定
- research/
  - factor_research.calc_momentum / calc_value / calc_volatility
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank

---

## セットアップ手順

1. リポジトリをチェックアウト／クローン

   git clone <repo-url>
   cd <repo>

2. Python 仮想環境を作成して有効化（例）

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .\.venv\Scripts\activate   # Windows

3. 依存関係をインストール

   ※requirements.txt がある想定での一例（なければ必要なパッケージを個別にインストール）
   pip install -r requirements.txt

   最低限想定されるパッケージ:
   - duckdb
   - openai
   - defusedxml

   開発用にパッケージをローカルインストールする場合:

   pip install -e .

4. 環境変数を準備

   プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（プロジェクトルートは .git または pyproject.toml により検出）。自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください。

   必須（例）:
   - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   - KABU_API_PASSWORD=your_kabu_api_password
   - SLACK_BOT_TOKEN=your_slack_bot_token
   - SLACK_CHANNEL_ID=your_slack_channel_id
   - OPENAI_API_KEY=your_openai_api_key

   任意（デフォルトあり）:
   - KABUSYS_ENV=development|paper_trading|live  （デフォルト: development）
   - LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL  （デフォルト: INFO）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD=1  # 自動 .env 読み込み無効化
   - KABUSYS_ENV 用途に応じて動作を分けられます。

   データベースパス:
   - DUCKDB_PATH=data/kabusys.duckdb  # Settings.duckdb_path のデフォルト
   - SQLITE_PATH=data/monitoring.db   # Settings.sqlite_path のデフォルト

   .env の例（最小）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxx
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=yourpass
   ```

5. DuckDB の初期化（監査ログなど）

   監査ログ用の DB を初期化するには Python REPL やスクリプト内で:

   from kabusys.data.audit import init_audit_db
   from kabusys.config import settings
   conn = init_audit_db(settings.duckdb_path)

   既存接続にスキーマだけ適用する場合は init_audit_schema(conn) を使用します。

---

## 使い方（主要な例）

以下は代表的な利用例です。実運用ではロギング設定や例外処理を適切に行ってください。

- 日次ETL（株価 / 財務 / カレンダー取得 + 品質チェック）

  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニューススコアリング（銘柄別のAIスコアを ai_scores テーブルへ書き込む）

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None => OPENAI_API_KEY を使用
  print(f"書き込み銘柄数: {written}")

- マーケットレジーム判定

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))

- ファクター計算 & 研究ユーティリティ

  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize

  conn = duckdb.connect(str(settings.duckdb_path))
  mom = calc_momentum(conn, target_date=date(2026,3,20))
  val = calc_value(conn, target_date=date(2026,3,20))
  vol = calc_volatility(conn, target_date=date(2026,3,20))
  mom_norm = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])

- RSS フィードの取得（ニュース収集の低レベルAPI）

  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])

- データ品質チェック（ETL 後に）

  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues:
      print(i.check_name, i.severity, i.detail)

注意: 上記の各関数は DuckDB 接続（duckdb.DuckDBPyConnection）を前提にしています。ローカルファイルパスを使用する場合は settings.duckdb_path を利用して接続してください。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- OPENAI_API_KEY (必須 for AI functions) — OpenAI API キー（news_nlp / regime_detector）
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL (任意) — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID (必須) — Slack Channel ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH (任意) — SQLite 監視 DB パス（デフォルト data/monitoring.db）
- KABUSYS_ENV (任意) — 実行環境: development / paper_trading / live（デフォルト development）
- LOG_LEVEL (任意) — ログレベル（DEBUG/INFO/...、デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると .env 自動読み込みを無効化します。

---

## ディレクトリ構成（抜粋）

src/
  kabusys/
    __init__.py
    config.py
    ai/
      __init__.py
      news_nlp.py
      regime_detector.py
    data/
      __init__.py
      pipeline.py
      etl.py
      jquants_client.py
      news_collector.py
      calendar_management.py
      quality.py
      stats.py
      audit.py
      etl.py (ETLResult 再エクスポート)
    research/
      __init__.py
      factor_research.py
      feature_exploration.py
      ...（その他ユーティリティ）
    research/（ファクター・研究用ユーティリティ群）

主要ファイルの説明:
- config.py: 環境変数の読み込み・Settings（getters）を提供。プロジェクトルートの .env/.env.local を自動ロードする機能を持つ。
- data/jquants_client.py: J-Quants API の取得・保存ロジック（保存先は DuckDB）。
- data/pipeline.py: 日次 ETL の統合エントリポイント（run_daily_etl 等）。
- data/news_collector.py: RSS 取得と前処理、raw_news への保存のためのユーティリティ。
- data/quality.py: データ品質チェック群。
- data/audit.py: 監査ログスキーマ定義と初期化ヘルパー。
- ai/news_nlp.py: 記事群を LLM で評価して ai_scores に書込み。
- ai/regime_detector.py: マクロセンチメント + MA200 で市場レジーム判定。
- research/*: ファクター計算・特徴量探索用ユーティリティ。

---

## 開発・テストメモ

- 多くの機能は外部 API（J-Quants / OpenAI / RSS）に依存します。ユニットテストでは外部呼び出し（HTTP / OpenAI クライアント）をモックしてください。コード内にもモック差替えを想定した設計（例えば _call_openai_api をパッチする等）がされています。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テスト環境で自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB に対する executemany や空リストの扱いに留意（コード内で互換性考慮あり）。

---

## 貢献

バグ報告、改善提案、プルリクエスト歓迎です。ドキュメントや型注釈の改善、テストの追加にご協力ください。

---

以上。セットアップや具体的な利用例で不明点があれば、使いたいケース（例: ETL のスケジュール設定、OpenAI のレスポンス形式の扱い、監査ログの運用など）を教えてください。必要に応じて詳しい手順やサンプルスクリプトを作成します。