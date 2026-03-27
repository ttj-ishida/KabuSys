# KabuSys

日本株向けの自動売買・データ基盤ライブラリ群です。  
ETL（J-Quants 経由のデータ取得）、データ品質チェック、ニュース収集・AIによるニュースセンチメント、研究用ファクター計算、監査ログ（注文→約定トレーサビリティ）などを含みます。

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群を提供します。

- J-Quants API からの差分 ETL（株価日足、財務、マーケットカレンダー）と DuckDB への冪等保存
- raw_news の収集・前処理と、銘柄ごとのニュースセンチメント算出（OpenAI）
- 市場レジーム判定（ETF 1321 の MA200 乖離 ＋ マクロニュースの LLM センチメント）
- 研究用途のファクター計算（モメンタム / バリュー / ボラティリティ 等）と統計ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）用テーブル作成ユーティリティ
- 設定は .env または環境変数経由で管理（自動ロード機能あり）

---

## 主な機能一覧

- ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（差分取得・backfill 対応）
  - J-Quants API クライアント（レートリミット・リトライ・401 自動リフレッシュ対応）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- ニュース & AI
  - fetch_rss / news_collector：RSS 取得・前処理・raw_news 登録（SSRF・gzip・サイズ制限対策含む）
  - score_news：銘柄ごとのニュースセンチメント（gpt-4o-mini + JSON mode、バッチ処理・リトライあり）
  - score_regime：ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成して market_regime を作成

- 研究（research）
  - calc_momentum, calc_value, calc_volatility（prices_daily / raw_financials ベース）
  - calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize

- データ管理
  - calendar_update_job：JPX カレンダー差分取得と market_calendar 更新
  - quality.run_all_checks：欠損・重複・スパイク・日付不整合のチェック
  - audit.init_audit_schema / init_audit_db：監査ログテーブルとインデックスの初期化

- 設定管理
  - kabusys.config.settings：環境変数の取得ラッパー（.env 自動読み込み、必須キーチェックなど）

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈に PEP 604 を使用）
- システムに DuckDB（Python パッケージ）をインストールすること

例：ローカル開発環境での手順

1. リポジトリをクローン

   git clone <repo-url>
   cd <repo-root>

2. 仮想環境を作成して有効化

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows (PowerShell 等は別コマンド)

3. 必要パッケージをインストール

   pip install -e .            # パッケージ配布がある場合
   # もしくは最低限:
   pip install duckdb openai defusedxml

   ※ openai パッケージは OpenAI 呼び出し用。実運用ではバージョンに注意してください。

4. 環境変数の設定

   プロジェクトルート（pyproject.toml または .git のあるディレクトリ）に `.env` と `.env.local` を置くと自動で読み込まれます（読み込みは起動時に行われます）。テスト時に自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   主要な環境変数（最低限設定が必要なもの）:

   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 実行時に使用）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必要に応じて）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必要に応じて）
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必要に応じて）
   - DUCKDB_PATH: デフォルト DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視 DB 等の sqlite パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: environment: development / paper_trading / live
   - LOG_LEVEL: ログレベル（DEBUG/INFO/...）

   .env の例:

   ```
   JQUANTS_REFRESH_TOKEN=あなたの_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（主要なエントリ・ユーティリティ）

以下は簡単なコード例です。実行前に環境変数（特に JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY）を設定してください。

- DuckDB に接続して日次 ETL を実行する

  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのセンチメントを算出する（score_news）

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env の OPENAI_API_KEY を使う
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジームを判定して market_regime に書き込む（score_regime）

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用スキーマを初期化する（監査 DB を別に用意する場合）

  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn は初期化済みの duckdb 接続
  ```

- 研究用ファクター計算（例：モメンタム）

  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  rows = calc_momentum(conn, target_date=date(2026, 3, 20))
  # rows は各銘柄ごとの dict のリスト
  ```

- データ品質チェックを実行する

  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026, 3, 20))
  for i in issues:
      print(i)
  ```

注意点
- score_news / score_regime は OpenAI にリクエストを飛ばします。API コストとレートに注意してください。
- 各関数はルックアヘッドバイアス対策のため、内部で datetime.today() を基本的に参照せず、引数で与えた target_date に基づいて処理します（バックテスト用途に適した設計）。

---

## 設定の自動ロード挙動

- モジュール読み込み時にプロジェクトルート（.git または pyproject.toml を含むディレクトリ）を探索し、`.env` と `.env.local` を自動で読み込みます（読み込み順は OS 環境変数 > .env.local > .env）。  
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に有用）。

---

## 参考：主要モジュールとディレクトリ構成

リポジトリの主なディレクトリと役割（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py
    - 環境変数・設定管理、.env 自動読み込み、settings オブジェクト
  - ai/
    - news_nlp.py: ニュースセンチメント算出（score_news）
    - regime_detector.py: 市場レジーム判定（score_regime）
  - data/
    - jquants_client.py: J-Quants API クライアント、保存関数（save_*）
    - pipeline.py: ETL パイプライン（run_daily_etl 等）と ETLResult
    - calendar_management.py: マーケットカレンダー管理・営業日判定
    - news_collector.py: RSS 取得・記事前処理
    - quality.py: データ品質チェック
    - stats.py: 共通統計ユーティリティ（zscore_normalize 等）
    - audit.py: 監査ログ（schema 初期化 / init_audit_db）
    - etl.py: ETLResult の再エクスポート
  - research/
    - factor_research.py: モメンタム / ボラティリティ / バリュー 等
    - feature_exploration.py: 将来リターン計算・IC 等
  - monitoring/ (監視関連の DB や処理が入る想定)
  - execution/, strategy/, monitoring/ 等（パッケージ公開対象として __all__ に含まれるが、詳細実装は別途）

（上記はコードベースに含まれるファイルの抜粋です。プロジェクト全体のルート構成やドキュメントはリポジトリ側の README / docs を参照してください。）

---

## テスト・開発ヒント

- OpenAI 呼び出しや外部ネットワークを伴う関数は内部で呼び出す HTTP クライアントや _call_openai_api / _urlopen 等をモック可能に設計されています。ユニットテスト時はこれらをパッチして外部依存を排除してください。
- DuckDB は file path または ":memory:" で接続可能。テストでは in-memory DB を用いると高速です。
- `.env` をコミットしないでください。機密情報は `.env` に入れる場合は `.gitignore` で管理してください。

---

## ライセンス・貢献

（この README ではライセンス表記は含めていません。実際のリポジトリの LICENSE ファイルを参照してください。）  
貢献やバグレポートは Pull Request / Issue を通じて受け付けてください。

---

以上が KabuSys の概要と基本的な使い方です。追加で具体的な利用シナリオ（ETL スケジューリング、Slack 通知連携、kabuステーションとの実取引フロー等）についてのドキュメントが必要であれば、目的に合わせて詳細ドキュメントを作成します。