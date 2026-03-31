KabuSys — 日本株自動売買 / データ基盤ライブラリ
=================================

概要
----
KabuSys は日本株のデータ取得・品質チェック・特徴量算出・ニュース NLP（LLM）評価・市場レジーム判定・監査ログ等を備えた内部ライブラリです。  
主に DuckDB をデータレイクとして利用し、J-Quants API からのデータ取得（株価・財務・市場カレンダー）、RSS ニュース収集、OpenAI（gpt-4o-mini）によるニュースのセンチメント解析や市場レジーム判定、研究用ファクター計算や ETL パイプラインを提供します。

主な特徴
--------
- J-Quants API クライアント（差分取得・ページネーション・トークン自動リフレッシュ・レート制御・リトライ）
- 日次 ETL パイプライン（prices / financials / calendar の差分取得と品質チェック）
- ニュース収集モジュール（RSS -> raw_news、SSRF 対策・トラッキング除去）
- ニュース NLP（OpenAI を用いた銘柄別センチメント付与、バッチ処理・リトライ実装）
- 市場レジーム判定（ETF 1321 の MA 乖離とマクロニュースセンチメントの合成）
- 研究用モジュール（モメンタム / バリュー / ボラティリティ等のファクター計算、将来リターン、IC 計算、Z スコア正規化）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログスキーマ/初期化（signal → order_request → execution のトレーサビリティ）
- 環境変数 / .env 自動読み込み（プロジェクトルート検出ベース）

セットアップ手順
----------------

前提
- Python 3.10 以上（typing の union 演算子 | を利用）
- DuckDB、OpenAI SDK、defusedxml などの依存ライブラリ

インストール（開発）
1. リポジトリをチェックアウト
2. 仮想環境作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Unix)
   - .venv\Scripts\activate     (Windows)
3. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

（パッケージ化されている場合）
- pip install -e .

環境変数
- 自動でプロジェクトルート（.git または pyproject.toml）を探し、.env → .env.local を読み込みます。CWD に依存せずパッケージ配布後も動作するよう設計されています。
- 自動ロードを無効化する場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須（少なくとも本機能を利用する場合）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（jquants_client.get_id_token で使用）
- KABU_API_PASSWORD : kabuステーション API のパスワード（取引機能利用時）
- OPENAI_API_KEY : OpenAI API キー（news_nlp / regime_detector で使用）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID : Slack 通知機能を使う場合
- （データベースパス） DUCKDB_PATH / SQLITE_PATH はデフォルト設定あり（data/kabusys.duckdb 等）

設定の確認
- プログラム内で settings を参照できます:
  from kabusys.config import settings
  settings.jquants_refresh_token など

使い方例
--------

1) DuckDB 接続を開く
- DuckDB をファイル DB として使う例:
  import duckdb
  from kabusys.config import settings
  conn = duckdb.connect(str(settings.duckdb_path))

- インメモリで試す:
  conn = duckdb.connect(":memory:")

2) 日次 ETL を実行する
- 日付を指定して ETL を一括実行:
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

3) ニュースのセンチメントスコア付与（OpenAI が必要）
- OpenAI API キーは env OPENAI_API_KEY を設定するか、api_key 引数で指定可能:
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  wrote = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込んだ銘柄数:", wrote)

- テスト時は kabusys.ai.news_nlp._call_openai_api をモックして API 呼び出しを差し替えられます。

4) 市場レジーム判定
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026, 3, 20))

5) 監査 DB の初期化（監査専用 DB を作る）
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")

6) カレンダー更新ジョブ（夜間バッチ）
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print("保存レコード数:", saved)

よくある操作・補足
- OpenAI 呼び出し関連は冪等性やリトライを考慮して実装されています。Unit test では _call_openai_api を patch して挙動を模擬してください。
- J-Quants API は 120 req/min に制限されており、内部に RateLimiter を持っています。get_id_token / fetch_* は自動でトークン管理・リトライを行います。
- ETL の run_daily_etl は個々のステップで例外を捕捉して継続する設計です。結果の ETLResult で quality_issues や errors を確認してください。
- .env のフォーマットは一般的な KEY=VAL、export KEY=VAL やクォートされた値、行末コメントなどに対応しています。必要な環境変数がない場合は config.Settings のプロパティが ValueError を投げます。

ディレクトリ構成（主要ファイル）
--------------------------------
例: src/kabusys 以下の主なモジュール

- kabusys/
  - __init__.py
  - config.py                          # 環境変数/.env 読み込みと Settings
  - ai/
    - __init__.py
    - news_nlp.py                       # ニュース NLP（銘柄別スコア）
    - regime_detector.py                # 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py                 # J-Quants API クライアント + 保存関数
    - pipeline.py                       # ETL パイプライン
    - etl.py                            # ETL インターフェース（ETLResult 再エクスポート）
    - calendar_management.py            # マーケットカレンダー管理
    - news_collector.py                 # RSS ニュース収集（SSRF 対策等）
    - stats.py                          # 共通統計ユーティリティ（zscore_normalize）
    - quality.py                        # データ品質チェック
    - audit.py                          # 監査ログスキーマ初期化
    - (その他 jquants_client に関連する補助関数)
  - research/
    - __init__.py
    - factor_research.py                # ファクター計算（momentum/value/volatility）
    - feature_exploration.py            # 将来リターン・IC・統計サマリー等

開発・テストのヒント
--------------------
- OpenAI・ネットワーク依存処理は直接テストしないで、内部の _call_openai_api や _urlopen をモックすることを推奨します。
- .env 自動読み込みはプロジェクトルート検出に依存するため、CI テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して明示的に env をセットするか、モジュール内の settings を差し替えて下さい。
- DuckDB の executemany は空リストを受け付けないバージョン差異があるため、保存処理は空リストチェック後に executemany を実行するパターンになっています。テストでは入出力データの有無を確認してください。

必要な外部ライブラリ（例）
-------------------------
- duckdb
- openai
- defusedxml
- （標準ライブラリのみで動作する箇所も多いです）

ライセンス・貢献
----------------
- README にライセンス情報や貢献ルールが必要ならプロジェクトのルートに LICENSE / CONTRIBUTING.md を配置してください。

お問い合わせ
------------
実装の詳細や利用法について質問があれば、具体的なユースケース（目的・使いたい機能・動かしたコマンド・発生したエラーなど）を添えて教えてください。README の補足や使い方のサンプルを追加します。