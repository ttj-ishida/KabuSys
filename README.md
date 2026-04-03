KabuSys
=======

概要
----
KabuSys は日本株のデータプラットフォーム・研究・AI 評価・監査ログ・ETL を含む
自動売買／リサーチ用の内部ライブラリ群です。DuckDB をデータストアに用い、
J-Quants API からマーケットデータを取得、ニュースの NLP 評価や市場レジーム判定、
ファクター計算、ETL パイプライン、監査ログ（発注／約定のトレーサビリティ）等の
機能を提供します。

主な特徴
--------
- データ ETL（株価日足 / 財務 / 市場カレンダー）の差分取得と冪等保存
- ニュース収集（RSS）とニュースごとの銘柄センチメント（LLM を利用）
- 市場レジーム判定（ETF の MA とマクロニュースの LLM センチメントを合成）
- ファクター計算（モメンタム / ボラティリティ / バリュー 等）および特徴量解析ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログスキーマ（signal_events / order_requests / executions）と初期化ユーティリティ
- J-Quants API クライアント（レート制限・リトライ・トークン自動リフレッシュ対応）
- DuckDB ベースでシンプルかつ高速なローカルデータ管理

セットアップ手順
----------------

前提
- Python 3.10 以上（PEP 604 の union 型等を利用）
- Git

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo>

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows PowerShell)

3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （開発用に setuptools / wheel 等が必要であれば追加でインストールしてください）
   - あるいはプロジェクトに requirements.txt があれば: pip install -r requirements.txt

4. 環境変数設定
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（CWD に依存せずモジュール配置パスから探索）。
   - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

推奨環境変数（.env 例）
- JQUANTS_REFRESH_TOKEN=あなたの_jquants_refresh_token_
- KABU_API_PASSWORD=（kabuステーション API パスワード）
- OPENAI_API_KEY=（LLM 用の OpenAI API キー）※ ai モジュール利用時
- KABU_API_BASE_URL=http://localhost:18080/kabusapi
- LINE_CHANNEL_ACCESS_TOKEN=（通知用、任意）
- LINE_USER_ID=（通知用、任意）
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PID_FILE_PATH=data/execution.pid
- KILL_FLAG_PATH=data/kill.flag
- KABUSYS_ENV=development|paper_trading|live
- LOG_LEVEL=INFO|DEBUG|...

（注意）上記以外にも監視閾値などが環境変数として設定可能です（config.Settings を参照してください）。

使い方（代表的な API・コマンド）
------------------------------

以下はライブラリを直接利用する例です。用途に合わせて duckdb.connect() で接続を作成して関数を呼び出します。

1) DuckDB 接続の作成
- デフォルトの DuckDB パスは settings.duckdb_path（デフォルト data/kabusys.duckdb）
- 例:
  from pathlib import Path
  import duckdb
  from kabusys.config import settings
  conn = duckdb.connect(str(settings.duckdb_path))

2) 日次 ETL を実行する
- run_daily_etl が市場カレンダー→株価→財務→品質チェックを順に実行します。
- 例:
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

3) ニュース NLP（銘柄ごとのスコア付け）
- score_news(conn, target_date, api_key=None)
- OpenAI API キーは api_key 引数、または環境変数 OPENAI_API_KEY を使用
- 例:
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  n = score_news(conn, date(2026, 3, 20))  # 書き込み済み銘柄数を返す

4) 市場レジーム判定
- score_regime(conn, target_date, api_key=None)
- 例:
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, date(2026, 3, 20))

5) ファクター計算 / 研究用ユーティリティ
- calc_momentum / calc_volatility / calc_value など
- 例:
  from kabusys.research.factor_research import calc_momentum
  from datetime import date
  res = calc_momentum(conn, date(2026,3,20))
  # 結果は dict のリスト (date, code, mom_1m, mom_3m, mom_6m, ma200_dev)

6) 監査ログ初期化
- 監査テーブルを別 DB として初期化するユーティリティ
- 例:
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  # audit_conn を用いて監査ログを書き込めます

7) ニュース収集（RSS）
- fetch_rss(url, source, timeout=30) がパース済み記事リストを返します
- 取得後は save into raw_news 等の保存ロジックを呼ぶ想定（news_collector モジュールを参照）

環境変数の自動ロード
--------------------
- config モジュールはプロジェクトルート（.git または pyproject.toml を探索基準）にある .env / .env.local を自動で読み込みます。
- 読み込み順: OS 環境変数 > .env.local（override） > .env
- テスト等で自動ロードを無効化する場合:
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

内部設計上の注意点
------------------
- ルックアヘッドバイアス回避: 多くの処理は date.today() や datetime.now() を直接使わず、呼び出し元が target_date を明示する設計です。
- 冪等性: ETL の保存関数は ON CONFLICT DO UPDATE 等を使い冪等に動作します。
- LLM 呼び出し: OpenAI Chat Completion（gpt-4o-mini）を使用する箇所があり、429/ネットワーク断/5xx に対するリトライロジックを含みます。API キーは OPENAI_API_KEY（もしくは関数引数）で与えてください。
- J-Quants API: レート制御とトークン自動リフレッシュ機構を持ちます。JQUANTS_REFRESH_TOKEN を .env 等で用意してください。

ディレクトリ構成
----------------

（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                   : 環境変数 / 設定読み込み
  - ai/
    - __init__.py
    - news_nlp.py                : ニュースセンチメント付与（LLM）
    - regime_detector.py         : 市場レジーム判定ロジック
  - data/
    - __init__.py
    - jquants_client.py          : J-Quants API クライアント & 保存ロジック
    - pipeline.py                : ETL パイプライン（run_daily_etl 等）
    - etl.py                     : ETLResult の再エクスポート
    - calendar_management.py     : 市場カレンダー管理 / is_trading_day 等
    - news_collector.py          : RSS 取得 & 前処理
    - quality.py                 : データ品質チェック
    - stats.py                   : 共通統計ユーティリティ（zscore_normalize 等）
    - audit.py                   : 監査ログスキーマ / 初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py         : ファクター計算（momentum / volatility / value）
    - feature_exploration.py     : forward returns / IC / summary / rank 等

ドキュメント参照
----------------
各モジュール冒頭の docstring に設計方針・処理フロー・返り値仕様が詳述されています。実装を利用する際はそれらのコメントを参照してください。

ライセンス
---------
（プロジェクトに合わせてここに記載してください）

補足（トラブルシューティング）
------------------------------
- OpenAI 呼び出しで JSON 解析エラーが頻発する場合は、API の応答変化やモデル指定（_MODEL）の見直しを検討してください。
- J-Quants の API エラー（401）が出る場合は JQUANTS_REFRESH_TOKEN を確認してください（get_id_token が自動リフレッシュを試みます）。
- DuckDB の executemany に空リストを渡すとエラーになるバージョン差があるため、ライブラリ側で空チェックされています。必要に応じて DuckDB のバージョンを合わせてください。

以上が本リポジトリの概要と主要な使い方です。詳細な API（各関数の引数 / 戻り値）は各ソースファイルの docstring を参照してください。質問や補足があればお知らせください。