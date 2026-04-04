KabuSys
=======

概要
----
KabuSys は日本株向けの自動売買・データ基盤ライブラリです。  
J-Quants からのデータ取得・ETL、DuckDB によるデータ保存、ニュース収集と LLM を用いたニュース・センチメント集約、マーケットレジーム判定、ファクター計算や研究用ユーティリティ、監査ログ（トレーサビリティ）などの機能を提供します。

主な特徴
--------
- ETL パイプライン: J-Quants API から株価・財務・カレンダーを差分取得して DuckDB に保存（冪等）
- データ品質チェック: 欠損・重複・スパイク・日付整合性チェック
- ニュース収集: RSS フィード取得、前処理、raw_news への冪等保存
- ニュース NLP: OpenAI（gpt-4o-mini）で銘柄別センチメントを計算し ai_scores に保存
- レジーム判定: ETF（1321）200 日 MA 乖離とマクロニュースの LLM センチメントを合成して市場レジームを判定
- 研究モジュール: モメンタム／ボラティリティ／バリュー等のファクター算出、将来リターン・IC 計算、Z スコア正規化等
- 監査ログ: シグナル→発注→約定までトレース可能な監査テーブルの初期化ユーティリティ
- 設定管理: .env の自動読み込み（プロジェクトルート基準）と Settings API

必要な環境変数（主なもの）
-------------------------
（settings.Settings プロパティに対応）

必須:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD : kabuステーション API のパスワード

OpenAI（必須で使用する機能のみ）:
- OPENAI_API_KEY : OpenAI API キー（score_news / regime_detector を利用する場合）

任意（デフォルトあり）:
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV (development / paper_trading / live; default: development)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL; default: INFO)

.env 自動読み込みについて
------------------------
- パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml を基準）を探索し、.env → .env.local の順で自動読み込みします。
- テスト等で自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

セットアップ手順
----------------

1. Python 環境を作成
   - Python 3.10+ を推奨
   - 例:
     python -m venv .venv
     source .venv/bin/activate

2. 依存パッケージをインストール
   - 必須ライブラリ（代表例）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを利用してください）

3. パッケージをインストール（開発モード）
   - プロジェクトルートで:
     pip install -e .

4. 環境変数設定
   - プロジェクトルートに .env（および .env.local）を作成して必要な変数を設定します。
   - 例 (.env):
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development

使い方（代表例）
---------------

1) DuckDB 接続を作り ETL を実行する（日次 ETL）
- 例コード:
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str("data/kabusys.duckdb"))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- run_daily_etl は市場カレンダー → 日足 → 財務 → 品質チェックの順に処理し、ETLResult を返します。

2) ニューススコアリング（OpenAI 必須）
- score_news を呼んで、raw_news / news_symbols から銘柄別 ai_scores を作成します:
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")  # api_key を省略すると OPENAI_API_KEY 環境変数を使用
  print(f"scored {n} codes")

3) 市場レジーム判定
- regime_detector.score_regime を呼び、market_regime テーブルへ保存します:
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用

4) 監査ログ DB 初期化
- 監査テーブル（signal_events / order_requests / executions）を DuckDB に作成:
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")

5) ユーティリティ（設定取得）
- settings 経由で設定を参照できます:
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)

主要モジュール・ディレクトリ構成
-----------------------------
（提供済みソースをもとにした代表ツリー）

src/kabusys/
- __init__.py
- config.py            # .env 読み込みと Settings
- ai/
  - __init__.py        # score_news を公開
  - news_nlp.py        # ニュース NLP（銘柄別スコアリング）
  - regime_detector.py # 市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py  # J-Quants API クライアント & DuckDB 保存
  - pipeline.py        # ETL パイプライン（run_daily_etl 等）
  - etl.py             # ETLResult 再エクスポート
  - news_collector.py  # RSS 収集・前処理
  - calendar_management.py  # 市場カレンダー管理
  - quality.py         # データ品質チェック
  - stats.py           # 統計ユーティリティ（zscore_normalize 等）
  - audit.py           # 監査ログ（監査テーブル初期化）
- research/
  - __init__.py
  - factor_research.py     # Momentum/Volatility/Value 等の計算
  - feature_exploration.py # 将来リターン, IC, 統計サマリー 等
- research/*            # 研究系ユーティリティ群
- その他: strategy/, execution/, monitoring/（パッケージ公開あり）

設計上のポイント・注意事項
--------------------------
- Look-ahead バイアス防止: 多くの関数は datetime.today()/date.today() を内部で参照せず、target_date を明示的に渡して処理します。
- 冪等性: ETL の保存処理は ON CONFLICT DO UPDATE（または INSERT ... DO NOTHING）により冪等性を保証します。
- フェイルセーフ: LLM 呼び出しや外部 API エラー時は部分的にフォールバック（ゼロスコア等）し、例外でプロセス全体を停止しない設計が多く採用されています。
- 自動 .env 読込はプロジェクトルートを基準に行います。テストで禁止する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を使用してください。

開発・貢献
----------
- コードの拡張や修正は PR を送ってください。スタイルや型注釈、テストの追加を歓迎します。
- LLM の API 呼び出しなど外部依存部はモックできるよう工夫されています（単体テスト容易性を考慮）。

補足
----
この README はリポジトリ内の実装（config / data / ai / research 等）に基づいています。実運用時は .env.example を参照して必要なキーを設定し、DuckDB ファイルのバックアップ・権限管理、OpenAI の利用制限（料金・レート）に注意してください。