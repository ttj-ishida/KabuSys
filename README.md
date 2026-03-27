KabuSys
======

KabuSys は日本株向けのデータプラットフォーム / 研究・自動売買基盤のコアライブラリです。  
J-Quants / RSS / OpenAI 等の外部ソースと連携してデータ取得・品質検査・特徴量生成・AI評価・監査ログを行うことを目的としています。

主な特徴
-------
- データ収集（J-Quants API 経由の株価・財務・カレンダー）と差分 ETL（DuckDB に保存／冪等処理）
- ニュース収集（RSS → raw_news）と LLM を使った銘柄別ニュースセンチメント評価（gpt-4o-mini）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースセンチメントを合成）
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ、将来リターン、IC、統計要約）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（signal / order_request / execution）用スキーマおよび初期化ユーティリティ
- 設定は環境変数または .env ファイルで管理（自動読み込み機構あり）
- Look-ahead バイアス防止、API レート制御、リトライ、冪等性を意識した設計

機能一覧（主要モジュール）
-----------------
- kabusys.config
  - 環境変数管理、.env 自動読み込み（OS 環境変数 > .env.local > .env）
  - 必須変数の取得ユーティリティ（settings オブジェクト）
  - 自動ロード無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- kabusys.data
  - pipeline.py: run_daily_etl をはじめとする ETL ワークフロー
  - jquants_client.py: J-Quants API クライアント（取得・保存・リトライ・レート制御）
  - news_collector.py: RSS 取得・正規化・raw_news への保存ロジック（SSRF 対策等）
  - calendar_management.py: market_calendar の管理、営業日判定ユーティリティ
  - quality.py: データ品質チェック群（欠損・スパイク・重複・日付不整合）
  - stats.py: zscore_normalize 等の統計ユーティリティ
  - audit.py: 監査ログ用スキーマ定義と初期化ユーティリティ（init_audit_db 等）
  - etl.py: ETLResult の公開
- kabusys.ai
  - news_nlp.py: ニュースを LLM でスコアリングして ai_scores テーブルへ書き込む（score_news）
  - regime_detector.py: ETF 1321 MA とマクロニュースを合成して market_regime に書き込む（score_regime）
- kabusys.research
  - factor_research.py: モメンタム / ボラティリティ / バリュー等のファクター計算
  - feature_exploration.py: 将来リターン、IC、統計サマリー、ランク化ユーティリティ等
- そのほかモジュール（data.audit, data.jquants_client, ...）が補助的機能を提供します。

セットアップ手順
-------------
1. Python 依存パッケージ（例）
   - duckdb
   - openai
   - defusedxml
   - （標準ライブラリ以外の依存は pyproject.toml / requirements.txt を参照してください）

   例（pip）:
   ```
   pip install duckdb openai defusedxml
   ```
   ※プロジェクト配布がある場合は `pip install -e .` を想定。

2. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env または .env.local を置くと自動読み込みされます（自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 主な必須環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabu ステーション API パスワード（発注連携がある場合）
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（通知を使う場合）
     - SLACK_CHANNEL_ID: Slack チャンネル ID
     - OPENAI_API_KEY: OpenAI（LLM）を利用する場合は明示的に設定するか、score_* 関数へ api_key を渡す
   - 省略時の設定（defaults）は config.Settings の各プロパティの docstring /実装を参照:
     - KABUSYS_ENV (development | paper_trading | live)、LOG_LEVEL、KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH など

   サンプル .env:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-xxxxx
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=your_password
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

3. データベースディレクトリの準備
   - デフォルトの DuckDB パスは data/kabusys.duckdb（settings.duckdb_path を参照）
   - 監査ログ専用 DB を作る場合は init_audit_db を利用（data ディレクトリを自動作成）

基本的な使い方（Python から）
--------------------
- 設定と DB 接続
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行（カレンダー / 株価 / 財務 / 品質チェックを順に実行）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())
  ```

- ニューススコアリング（score_news）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # API キーを引数で渡すか、環境変数 OPENAI_API_KEY を設定
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム判定（score_regime）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログ DB の初期化（監査専用 DB を作る場合）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # init_audit_db はテーブル作成まで行い、接続を返す
  ```

- 研究用ファクター計算（例: momentum）
  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date

  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  # records は dict のリスト: [{"date":..., "code":..., "mom_1m":..., ...}, ...]
  ```

注意点・設計上の考慮
----------------
- Look-ahead Bias 回避: 多くの処理は date 引数や DB クエリで未来データを参照しないように実装されています（datetime.today()/date.today() を直接参照しない設計）。
- 冪等性: J-Quants から取得したデータ保存（save_* 関数）は ON CONFLICT DO UPDATE を使って冪等に保存します。
- リトライ/レート制御: J-Quants クライアントはレート制限（120 req/min）を守るためのスロットリングと、ネットワーク・429/5xx に対する指数バックオフリトライを実装しています。
- LLM 呼び出し: news_nlp と regime_detector の両方で OpenAI を使用します。API 呼び出し失敗時のフェイルセーフ処理（スコアを 0 に折り合う等）を行っています。テスト時には内部の _call_openai_api をモックすることを想定しています。
- 自動 .env 読み込み: プロジェクトルートを __file__ から探索して .env を読み込みます。テスト等で自動読み込みを抑えたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（主要ファイル）
------------------------
- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - pipeline.py
    - jquants_client.py
    - news_collector.py
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
    - etl.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research では zscore_normalize などを再利用してファクター研究を行います

開発・テスト時のヒント
--------------------
- DB の初期化やテストでは duckdb の ":memory:" を利用すると簡便です。
- OpenAI 呼び出し部分はモック可能に設計されています（内部の _call_openai_api を patch）。
- .env のサンプルは .env.example を参照する想定（リポジトリに含めるときは秘密情報を含めないこと）。
- ログレベルは LOG_LEVEL で制御できます（DEBUG/INFO/...）。

ライセンス・貢献
---------------
- 本リポジトリのライセンス情報やコントリビュート方法はプロジェクトルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

問い合わせ
--------
- 実運用・発注連携（kabu API）を行う場合は事前に十分なテストを実施し、実口座では KABUSYS_ENV を "live" に設定して挙動を確認してください。監査ログや冪等キーを活用して二重発注や不可逆操作を防いでください。

以上が KabuSys の概要と基本的な使い方です。README に不足している具体的な CLI や追加サンプルが必要であれば教えてください。