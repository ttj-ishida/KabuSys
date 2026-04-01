KabuSys
=======

バージョン: 0.1.0

概要
----
KabuSys は日本株向けのデータプラットフォームと研究・自動売買基盤のコアライブラリ群です。  
主に以下を提供します。

- J-Quants API を用いた日次データの ETL（株価・財務・市場カレンダー）
- ニュース収集・NLP による銘柄ごとの AI スコアリング（OpenAI）
- 市場レジーム判定（ETF MA とマクロニュースの合成）
- 研究用ファクター計算・特徴量解析（モメンタム・バリュー・ボラティリティ等）
- データ品質チェック・監査ログ（監査テーブルの初期化・操作）
- news collector（RSS 取得）、jquants_client（API クライアント）、DuckDB 連携 等

主な機能
--------
- ETL（run_daily_etl）: 市場カレンダー、株価（raw_prices）、財務（raw_financials）を差分取得・保存し品質チェックを実行
- J-Quants クライアント: 安全なリトライ・レート制御・トークン自動リフレッシュを備えた API 呼び出し
- ニュース収集: RSS を取得して raw_news に冪等保存（SSRF 対策・トラッキング除去・前処理）
- ニュース NLP（score_news）: OpenAI を用いた銘柄別センチメントスコア生成（ai_scores へ保存）
- レジーム判定（score_regime）: ETF(1321) の 200 日 MA 乖離とマクロニュースセンチメントを合成して market_regime に保存
- 研究ライブラリ: ファクター計算（calc_momentum, calc_value, calc_volatility 等）、将来リターン計算、IC/統計サマリー
- データ品質チェック（quality.run_all_checks）: 欠損・重複・スパイク・日付不整合検出
- 監査ログ（audit.init_audit_db / init_audit_schema）: 発注・約定フローのトレーサビリティ用テーブル群の初期化

動作要件（推奨）
----------------
- Python 3.10+
- パッケージ（主なもの）
  - duckdb
  - openai (OpenAI SDK)
  - defusedxml
- ネットワークアクセス（J-Quants API, RSS ソース, OpenAI）

セットアップ手順
----------------

1. リポジトリを取得（パッケージ配布形態に応じて）
   - 開発時: リポジトリをクローンしてソースを使う

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 例（最小）:
     pip install duckdb openai defusedxml

   - 実際は requirements.txt / pyproject.toml に依存関係を追加して pip install -e . 等を使用してください。

4. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）に .env / .env.local を置くことで自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化）。
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - SLACK_BOT_TOKEN: Slack 通知に使用する場合
     - SLACK_CHANNEL_ID: Slack 通知チャネル
     - KABU_API_PASSWORD: kabu API を使う場合
     - OPENAI_API_KEY: OpenAI を利用する場合（score_news/score_regime 等）
   - 任意 / 既定値
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト INFO
     - DUCKDB_PATH — デフォルト data/kabusys.duckdb
     - SQLITE_PATH — デフォルト data/monitoring.db
     - PID_FILE_PATH — デフォルト data/execution.pid

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C0123456
   KABU_API_PASSWORD=secret
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

使い方（基本例）
----------------

- DuckDB 接続を作成して日次 ETL を実行する（簡易例）:

  ```python
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（score_news）:

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print("scored codes:", n_written)
  ```

- 市場レジーム判定（score_regime）:

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 監査 DB の初期化:

  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # これで監査用テーブルが作成されます
  ```

- データ品質チェックの実行:

  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026, 3, 20))
  for i in issues:
      print(i)
  ```

注意点 / 設計方針（概要）
------------------------
- ルックアヘッドバイアス防止: 多くの関数は内部で date.today()/datetime.today() に依存せず、target_date を明示的に受け取る設計です。バックテスト時は必ず適切な target_date を渡してください。
- 冪等性: ETL の保存処理（save_* 系）は ON CONFLICT DO UPDATE 等で冪等的に動作します。
- フェイルセーフ: LLM/API 呼び出しが失敗した場合（OpenAI/J-Quants の一時エラーなど）は、明示的にフェイルセーフ（デフォルト値・処理スキップ）を行い、システム全体の停止を避ける設計です。
- セキュリティ: news_collector では SSRF 対策・XML 脆弱性対策（defusedxml）・受信サイズ制限などを実施しています。

主なモジュール/ディレクトリ構成
-----------------------------
（パッケージルート: src/kabusys）

- __init__.py
  - バージョンと公開パッケージ定義

- config.py
  - .env / 環境変数の読み込みと Settings（各種設定値）

- ai/
  - news_nlp.py: ニュースを OpenAI でスコアリングして ai_scores に保存
  - regime_detector.py: ETF MA とマクロニュースを合成して市場レジーム判定
  - __init__.py

- data/
  - jquants_client.py: J-Quants API クライアント（取得・保存ユーティリティ含む）
  - pipeline.py: ETL パイプライン（run_daily_etl 等）
  - etl.py: ETLResult の公開
  - news_collector.py: RSS 収集・正規化・保存
  - calendar_management.py: 市場カレンダー管理（営業日判定・更新ジョブ）
  - quality.py: データ品質チェック群（欠損・スパイク・重複・日付整合性）
  - stats.py: zscore_normalize などの汎用統計ユーティリティ
  - audit.py: 監査ログ用テーブルの作成/初期化
  - __init__.py

- research/
  - factor_research.py: calc_momentum, calc_value, calc_volatility（ファクター計算）
  - feature_exploration.py: 将来リターン, IC, 統計サマリー等
  - __init__.py

開発 / テスト時の便利な設定
--------------------------
- 自動 .env 読み込みを無効化したい場合:
  KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を環境変数に設定することで自動ロードを停止できます（ユニットテスト等で便利）。

- OpenAI や外部 API 呼び出しは各モジュール内の _call_openai_api 等をモック可能にしてあるため、テスト時は patch して外部トラフィックを遮断できます。

ライセンス / 貢献
-----------------
本 README はリポジトリ内のソースコードを元に作成した概要ドキュメントです。実プロジェクトとして利用する場合は LICENSE、CONTRIBUTING 等のファイルを参照してください。

付録: よく使う環境変数一覧（まとめ）
------------------------------------
- JQUANTS_REFRESH_TOKEN (必須: J-Quants トークン)
- OPENAI_API_KEY (AI スコアリングで必須)
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (通知)
- KABU_API_PASSWORD (kabu API)
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- SQLITE_PATH (デフォルト data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG | INFO | WARNING | ...)

以上。必要があれば各モジュールごとの詳細な API ドキュメント（引数・戻り値・例外）を追記します。どの項目を深掘りしますか？