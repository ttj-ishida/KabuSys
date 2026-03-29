# KabuSys — 日本株自動売買プラットフォーム（README）

概要
----
KabuSys は日本株のデータ取得・ETL、ニュースセンチメント分析（OpenAI）、市場レジーム判定、ファクター計算、監査ログ構築などを含む自動売買／リサーチ基盤ライブラリです。DuckDB をデータストアに使用し、J-Quants API から株価・財務・市場カレンダーを取得、RSS からニュースを収集して AI によるスコアリングを行います。

主な設計方針
- ルックアヘッドバイアス回避（内部で date.today() を不用意に参照しない）
- DuckDB による効率的な SQL + Python 処理
- 冪等性（ETL／保存処理は ON CONFLICT / DELETE → INSERT により冪等）
- フェイルセーフ（外部 API 失敗時はゼロやスキップで継続）
- テスト容易性（API 呼び出し関数を差し替え可能）

機能一覧
--------
- 環境設定管理
  - .env / .env.local の自動読み込み（OS 環境変数優先、無効化可）
  - settings オブジェクトで設定値を取得
- Data ETL（kabusys.data.pipeline）
  - run_daily_etl：市場カレンダー・株価・財務の差分取得・保存・品質チェック
  - run_prices_etl / run_financials_etl / run_calendar_etl：個別 ETL
- J-Quants クライアント（kabusys.data.jquants_client）
  - fetch / save: 株価日足、財務、上場銘柄、マーケットカレンダー
  - レート制限・リトライ・トークン自動リフレッシュ対応
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、テキスト前処理、raw_news への冪等保存補助
  - SSRF / gzipbomb / XML 攻撃対策
- データ品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク、日付不整合の検出（QualityIssue）
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ
  - init_audit_schema / init_audit_db による初期化
- AI（kabusys.ai）
  - news_nlp.score_news：銘柄ごとのニュースセンチメントを計算して ai_scores に保存
  - regime_detector.score_regime：ETF(1321) MA200 乖離 + マクロニュースで市場レジームを判定し market_regime に保存
  - OpenAI（gpt-4o-mini）を JSON Mode で利用。リトライ/フェイルセーフ実装あり
- リサーチ（kabusys.research）
  - calc_momentum / calc_volatility / calc_value：ファクター計算
  - calc_forward_returns / calc_ic / factor_summary / rank：特徴量解析・統計

セットアップ手順
----------------
前提
- Python 3.10 以上（typing の構文等で互換が必要）
- DuckDB が利用可能（pip でインストールされます）

1. リポジトリをクローン
   - git clone で取得してください。

2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - 必要最低限のパッケージ例:
     - pip install duckdb openai defusedxml
   - 実運用では logging, urllib 等は標準ライブラリのため追加不要です。
   - （プロジェクトに requirements.txt や Poetry がある場合はそちらを使用してください）

4. 環境変数設定（.env）
   - プロジェクトルートに `.env`（もしくは `.env.local`）を配置します。
   - 自動ロードはデフォルトで有効（OS 環境変数 > .env.local > .env の優先順位）。
   - 無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須環境変数（主要なもの）
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- SLACK_BOT_TOKEN=your_slack_bot_token
- SLACK_CHANNEL_ID=your_slack_channel_id
- KABU_API_PASSWORD=your_kabu_station_api_password
- OPENAI_API_KEY=your_openai_api_key  （AI 機能を使う場合）
- （オプション）KABUSYS_ENV=development|paper_trading|live
- （オプション）LOG_LEVEL=DEBUG|INFO|...

.env の例（テンプレート）
- .env.example がある場合はそちらを参照してください。参考例:
  JQUANTS_REFRESH_TOKEN=xxxx
  SLACK_BOT_TOKEN=xoxb-xxxx
  SLACK_CHANNEL_ID=C12345678
  OPENAI_API_KEY=sk-xxxx
  KABU_API_PASSWORD=secret
  DUCKDB_PATH=data/kabusys.duckdb
  SQLITE_PATH=data/monitoring.db
  KABUSYS_ENV=development
  LOG_LEVEL=INFO

使い方（代表例）
----------------

- DuckDB 接続を用意して ETL を実行する（日次 ETL）
  ```python
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())
  ```

- ニュースセンチメントを計算して ai_scores に保存
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, date(2026,3,20))  # OPENAI_API_KEY が必要
  print(f"scored {count} symbols")
  ```

- 市場レジーム（bull/neutral/bear）を計算
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, date(2026,3,20))  # OPENAI_API_KEY が必要
  ```

- 監査ログ DB を初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # ディレクトリを自動作成
  ```

- J-Quants から生のデータ取得（ユーティリティ）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  token = get_id_token()  # JQUANTS_REFRESH_TOKEN が必要
  recs = fetch_daily_quotes(id_token=token, date_from=date(2026,1,1), date_to=date(2026,3,1))
  ```

- リサーチ用関数の呼び出し例
  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date
  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, date(2026,3,20))
  ```

注意点
- AI 機能（news_nlp / regime_detector）は OpenAI の API を利用します。API キーは環境変数 OPENAI_API_KEY か、関数引数 api_key を用いて指定してください。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）から行われます。テストなどで自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の executemany はバージョンによって空リストが渡せない制約があるため、空チェックを行っています。実装に依存した挙動に注意してください。
- audit 初期化時は UTC タイムゾーンを設定します（SET TimeZone='UTC'）。

ディレクトリ構成（主要ファイル）
-----------------------------
以下はパッケージ内の主要モジュールとファイルの概要（src/kabusys 配下）です。

- __init__.py — パッケージ初期化（__version__ 等）
- config.py — 環境変数 / 設定読み込みロジック（自動 .env ロード、Settings）
- ai/
  - __init__.py
  - news_nlp.py — ニュースのセンチメントスコアリング（score_news）
  - regime_detector.py — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch/save）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - etl.py — ETLResult を公開
  - news_collector.py — RSS 取得・前処理
  - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
  - quality.py — データ品質チェック
  - stats.py — 汎用統計ユーティリティ（zscore_normalize）
  - audit.py — 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py — ファクター計算（momentum/value/volatility）
  - feature_exploration.py — 将来リターン・IC・統計サマリー
- その他: モジュールごとの詳細実装はソースを参照してください。

開発者向けメモ
---------------
- テスト中や CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して外部 .env の影響を無効化してください。
- OpenAI の呼び出し部分は内部で _call_openai_api を定義しており、テスト時は unittest.mock.patch で差し替え可能です。
- J-Quants API 呼び出しはレート制限（120 req/min）とリトライロジックを内蔵しています。テスト時は jquants_client._request をモックすると高速化できます。
- DuckDB の型・日付表現についてはコード内で変換処理（date.fromisoformat 等）を行っています。DB スキーマと一致するデータを渡すことが重要です。

ライセンス / 貢献
-----------------
- 本 README はソースコードからの推測に基づくドキュメントです。実際のライセンスや貢献ガイドがプロジェクトに含まれている場合はそちらを優先してください。

問題報告・改善提案
------------------
- バグや改善案があれば Issue を立ててください。AI 呼び出しの安全性、ETL の堅牢性に関するログや再現手順を添えていただけると対応が早くなります。

以上。必要であれば README の英語版や、各モジュールごとの詳細ドキュメント（関数シグネチャ例・DB スキーマ）も作成します。どの部分の追記を希望しますか？