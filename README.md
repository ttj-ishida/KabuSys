KabuSys — 日本株自動売買 / データプラットフォーム
=================================

概要
----
KabuSys は日本株のデータ収集・品質管理・ファクター計算・ニュースNLP・市場レジーム判定・監査ログ管理を目的とした内部ライブラリ群です。J-Quants API と DuckDB を中心に、日次 ETL、ニュースセンチメント評価（OpenAI）、ファクター研究、監査トレーサビリティをサポートします。

主な特徴
--------
- データ ETL（株価・財務・JPX カレンダー）と差分取得ロジック
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- ニュース収集（RSS）とニュースセンチメント評価（OpenAI）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを合成）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）と統計ユーティリティ
- 監査ログ（signal_events / order_requests / executions）スキーマ定義と初期化ユーティリティ
- DuckDB を用いた冪等保存（ON CONFLICT）と効率的クエリ設計
- 環境変数 / .env 自動ロード（プロジェクトルート検出）

動作要件
--------
- Python 3.10+
- 必要なライブラリ（例）:
  - duckdb
  - openai
  - defusedxml
  - そのほか標準ライブラリに依存するモジュール

（実際の requirements.txt に依存します。開発環境では仮想環境を作成してから下記インストールを推奨します。）

インストール
------------
1. 仮想環境を作成・有効化:
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 開発インストール（パッケージがプロジェクト配下にある前提）:
   - pip install -e ".[dev]"  または最低限: pip install duckdb openai defusedxml

（プロジェクトに pyproject.toml / setup.cfg があれば pip install -e . が利用可能です）

設定（環境変数 / .env）
---------------------
KabuSys は環境変数またはプロジェクトルートの .env / .env.local から設定を読み込みます（ルート検出は .git または pyproject.toml を基準）。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主な必須環境変数（例）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（ETL 用）
- KABU_API_PASSWORD     : kabuステーション API パスワード（約定等に使用する想定）
- SLACK_BOT_TOKEN       : Slack 通知に使う Bot トークン
- SLACK_CHANNEL_ID      : 通知先チャンネル ID
- OPENAI_API_KEY        : OpenAI API キー（ニュース NLP / レジーム判定）

任意（デフォルト有り）:
- KABUSYS_ENV (development | paper_trading | live) 既定: development
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) 既定: INFO
- DUCKDB_PATH （既定: data/kabusys.duckdb）
- SQLITE_PATH （既定: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

.sample .env
-------------
例:
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-xxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

初期セットアップ
----------------
- データベースファイル（DuckDB）のディレクトリを作成:
  - mkdir -p data

- 監査ログ用 DB 初期化（例: 別ファイルに監査専用 DB を作る場合）:
  ```python
  import duckdb
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn をそのまま使える
  ```

基本的な使い方（例）
------------------

1) 日次 ETL 実行
- 日次 ETL（株価・財務・カレンダー取得 + 品質チェック）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

2) ニュースセンチメント（AI）スコア付与
- raw_news / news_symbols / ai_scores テーブルを使って OpenAI でスコアを生成:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY 環境変数利用
  print("書込み銘柄数:", n_written)
  ```

3) 市場レジーム判定
- ETF 1321 の MA200 とマクロニュースを合成して regime を算出:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

4) 監査スキーマ初期化（既存接続へ）
- 既存の DuckDB 接続に監査テーブル追加:
  ```python
  from kabusys.data.audit import init_audit_schema
  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

5) カレンダー関連ユーティリティ
- 営業日判定や次の営業日の取得:
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  conn = duckdb.connect("data/kabusys.duckdb")
  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

6) 研究モジュールの利用例
- ファクター計算や forward returns:
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum
  conn = duckdb.connect("data/kabusys.duckdb")
  result = calc_momentum(conn, date(2026,3,20))
  ```

注意点 / テストに関する情報
--------------------------
- OpenAI 呼び出しはモジュール内で分離されており、テスト時は内部関数（例: kabusys.ai.news_nlp._call_openai_api）を unittest.mock.patch で差し替えることを想定しています。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml）を検出して行います。テスト環境で自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の executemany はバージョン差異があるため、空リストで呼ばない実装になっています（呼び出し側で空チェック済み）。

ディレクトリ構成（主なファイル）
----------------------------
src/kabusys/
- __init__.py
- config.py                     — 環境変数 / .env 読込と Settings 定義
- ai/
  - __init__.py
  - news_nlp.py                  — ニュースの OpenAI を使ったセンチメント評価
  - regime_detector.py           — 市場レジーム判定ロジック
- data/
  - __init__.py
  - jquants_client.py            — J-Quants API クライアント（取得 + DuckDB 保存）
  - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
  - etl.py                       — ETLResult の再エクスポート
  - news_collector.py            — RSS 取得と raw_news 保存ロジック
  - calendar_management.py       — 市場カレンダー管理・営業日ユーティリティ
  - quality.py                   — データ品質チェック群
  - stats.py                     — zscore_normalize 等統計ユーティリティ
  - audit.py                     — 監査ログスキーマ定義・初期化
- research/
  - __init__.py
  - factor_research.py           — Momentum / Value / Volatility 等
  - feature_exploration.py       — forward returns, IC, factor summary, rank

付記
----
- 本 README はコード内の docstring と設計方針を基に作成しています。実運用では API キー管理・秘密情報の保護、適切なロギング設定、監視・アラートの整備を行ってください。
- 実行時の挙動や追加の CLI / サービス化（例: cron / systemd ジョブ）はプロジェクト固有の運用手順に合わせて実装してください。

必要であれば README に「運用例（systemd サービス定義）」「CI 設定」「より詳しい .env.example」など追記できます。希望があれば教えてください。