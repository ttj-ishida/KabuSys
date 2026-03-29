KabuSys
=======

日本株向けのデータ基盤・リサーチ・自動売買補助ライブラリです。  
DuckDB をデータストアとして利用し、J-Quants API からの ETL、RSS ニュース収集、LLM を使ったニュースセンチメント評価・市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（オーダー/約定トレーサビリティ）などを提供します。

主な特徴
--------
- J-Quants API クライアント（レート制限／トークン自動リフレッシュ／ページネーション対応）
- ETL パイプライン（株価・財務・カレンダー差分取得、品質チェック）
- ニュース収集（RSS、SSRF 対策、トラッキングパラメータ除去、冪等保存）
- ニュース NLP（OpenAI を使った銘柄別センチメントスコアリング）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの LLM 評価を合成）
- 研究用ユーティリティ（モメンタム、ボラティリティ、バリューのファクター計算、将来リターン、IC、統計サマリ等）
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- 監査ログスキーマ（signal → order_request → execution のトレーサビリティ）
- 自動 .env 読み込み（プロジェクトルート基準、テスト時に無効化可能）

必要な環境
----------
- Python 3.10+
- 推奨パッケージ（抜粋）:
  - duckdb
  - openai
  - defusedxml

（実際の requirements.txt はプロジェクトに合わせて作成してください）

環境変数（主要）
----------------
KabuSys は環境変数から設定を読み込みます。プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

必須:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD     : kabu ステーション API パスワード（発注連携等で使用）
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID      : Slack 通知先チャンネル ID

任意（デフォルトあり／運用モード指定など）:
- KABU_API_BASE_URL     : kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : 監視用 SQLite パス（デフォルト: data/monitoring.db）
- OPENAI_API_KEY        : OpenAI API キー（news_nlp / regime_detector で利用）
- KABUSYS_ENV           : 環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL             : ログレベル (DEBUG/INFO/WARNING/ERROR/CRITICAL)

セットアップ手順
----------------

1. リポジトリをチェックアウト / クローン
   - git clone ... など

2. 仮想環境を作る（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - その他プロジェクトで必要なパッケージを requirements.txt に合わせてインストールしてください。

4. 環境変数 / .env を作成
   - プロジェクトルートに .env を置き、必要なキーを設定してください。
   - 例（簡易）:
     JQUANTS_REFRESH_TOKEN=xxxxx
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     OPENAI_API_KEY=sk-...

   - 自動読み込みはプロジェクトルート（.git または pyproject.toml がある親ディレクトリ）を基準に行われます。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します（テスト用途等）。

5. データベースの初期化（監査ログ用例）
   - 監査ログ専用の DuckDB を初期化するには、Python から次を実行します:

     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

   - 他のテーブルスキーマ初期化が必要な場合は、プロジェクト内にある schema 初期化ユーティリティを用意している場合があります（プロジェクト固有）。

基本的な使い方（コード例）
-------------------------

- DuckDB に接続して日次 ETL を実行する:

  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメントを算出して ai_scores に書き込む:

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を環境変数から読む
  print(f"written: {n_written}")

- 市場レジーム判定を実行する:

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を使用

- 研究用ファクター計算（例: モメンタム）:

  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  print(records[:5])

注意点 / 実運用のヒント
-----------------------
- OpenAI 呼び出しは外部 API のため課金・レート制限があります。テスト時は該当関数（kabusys.ai.news_nlp._call_openai_api など）をモックしてください。
- LLM が失敗した場合、多くの処理がフェイルセーフ（スコア 0.0 を用いる、該当銘柄をスキップする等）で継続するよう設計されています。
- ETL は差分更新・バックフィルを行います。run_daily_etl の backfill_days 等のパラメータで挙動を調整可能です。
- news_collector には SSRF 対策やレスポンスサイズ制限が実装されていますが、RSS ソースの信頼性を確認して運用してください。
- 環境変数設定ミスでサービスが起動できない場合、kabusys.config.Settings のプロパティが ValueError を投げます。ログや例外内容を確認してください。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py
  - 環境変数の自動読み込み、Settings クラス（各種設定取得）
- ai/
  - __init__.py
  - news_nlp.py         : RSS ニュースを銘柄別にまとめて OpenAI でスコア化（ai_scores への書き込み）
  - regime_detector.py  : ETF 1321 の MA200 とマクロニュースの LLM スコアを合成して market_regime に書き込み
- data/
  - __init__.py
  - jquants_client.py   : J-Quants API クライアント（fetch / save 系）
  - pipeline.py         : ETL パイプライン（run_daily_etl など）および ETLResult
  - etl.py              : ETLResult の再エクスポート
  - news_collector.py   : RSS フィード収集、前処理、raw_news 保存
  - calendar_management.py : マーケットカレンダー管理・営業日判定・calendar_update_job
  - quality.py          : データ品質チェック（欠損・重複・スパイク・日付不整合）
  - stats.py            : 汎用統計ユーティリティ（zscore_normalize）
  - audit.py            : 監査ログスキーマ初期化（signal_events / order_requests / executions）
- research/
  - __init__.py
  - factor_research.py  : Momentum / Volatility / Value 等のファクター計算
  - feature_exploration.py : 将来リターン / IC / 統計サマリ / ランク関数 等
- monitoring / execution / strategy / etc.
  - （リポジトリに実装がある場合はここに含まれる想定。今回のコードベースでは data/ ai/ research/ config が中心です）

開発・テスト
-------------
- 自動 .env 読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します（ユニットテスト時に環境を汚さないようにする用途）。
- OpenAI 呼び出しやネットワーク I/O はモック可能に設計されています（例: kabusys.ai.news_nlp._call_openai_api を patch）。
- DuckDB の :memory: を使えばテスト用にインメモリ DB を容易に作成できます（kabusys.data.audit.init_audit_db(":memory:") 等）。

ライセンス・貢献
----------------
- 本 README ではライセンス情報を含めていません。実際のプロジェクトでは LICENSE ファイルを配置してください。  
- バグ報告や機能追加は Issue / Pull Request を通じてお願いします。

最後に
------
この README はコードベースに含まれるモジュールと関数の役割を簡潔にまとめたものです。実装の詳細や追加のユーティリティは各モジュールの docstring（ソースコード内コメント）を参照してください。必要であれば、README にデプロイ手順・CI 設定・詳細なスキーマ定義などを追記できます。