KabuSys — 日本株自動売買 / データ基盤ライブラリ
======================================

概要
----
KabuSys は日本株のデータ取得、ETL、ニュース NLP、ファクター計算、研究ユーティリティ、および監査ログ管理を目的とした Python ライブラリ群です。J-Quants API や RSS、OpenAI（LLM）を利用してデータを収集・加工し、DuckDB に保存・解析するための再利用可能なモジュール群を提供します。

主な特徴
--------
- データ取得 / ETL
  - J-Quants API から株価（日足）・財務・上場銘柄情報・市場カレンダーを差分取得・保存（ページネーション・リトライ・レート制御対応）
  - ETL の結果を ETLResult で集約し品質チェックの実行をサポート
- データ品質管理
  - 欠損、重複、スパイク、日付不整合などのチェックを実行
- ニュース収集・NLP
  - RSS 収集（SSRF対策、トラッキングパラメータ除去、前処理）→ raw_news 保存
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント分析（score_news）
  - マクロニュース + ETF (1321) MA200 乖離を組み合わせた市場レジーム判定（score_regime）
- 研究用ユーティリティ
  - ファクター計算（モメンタム / バリュー / ボラティリティ等）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、Zスコア正規化
- 監査ログ（audit）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化ユーティリティ（DuckDB 用）
- 環境設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート判定、無効化フラグあり）
  - 必須環境変数は Settings クラスで参照可能

セットアップ手順
----------------
1. リポジトリをクローンして開発環境を作る（例: venv）
   - python >= 3.10 を推奨

2. 依存パッケージをインストール
   - 主な依存例:
     - duckdb
     - openai (OpenAI SDK)
     - defusedxml
   - 例:
     - pip install -r requirements.txt
     - または (最低限) pip install duckdb openai defusedxml

3. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）から .env / .env.local が自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須（Settings で require される）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabu ステーション API パスワード
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
   - 推奨/任意:
     - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime で省略時に参照）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
     - KABUSYS_ENV — development / paper_trading / live（デフォルト development）
     - LOG_LEVEL — DEBUG/INFO/…（デフォルト INFO）

   - サンプル .env（抜粋）
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-xxxxx
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-xxxx
     SLACK_CHANNEL_ID=CXXXXXXX
     DUCKDB_PATH=data/kabusys.duckdb

4. データベースの準備（監査用）
   - 監査ログ用 DuckDB を初期化する:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
   - 他のテーブルスキーマ（raw_prices, raw_news, ai_scores 等）は ETL 実行や SQL スクリプトで準備してください（プロジェクト内のスキーマ定義ユーティリティがあればそれを利用）。

使い方（コード例）
-----------------

- 基本的な ETL（日次実行）
  - run_daily_etl は市場カレンダー → 株価 → 財務 → 品質チェック の順で実行します。

  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメント（銘柄別）スコアリング
  - score_news は raw_news と news_symbols を参照して ai_scores に書き込みます。

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # OPENAI_API_KEY を環境変数に設定していれば api_key を省略可能
  written = score_news(conn, target_date=date(2026, 3, 20))
  print("written:", written)

- 市場レジーム判定（ETF 1321 + マクロニュース）
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログの初期化（上記と同様）
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")

- ファクター計算 / 研究関数
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic 等は DuckDB 接続と target_date を渡して利用します。

  from kabusys.research import calc_momentum
  m = calc_momentum(conn, target_date=date(2026,3,20))

設計上の注意点
--------------
- ルックアヘッドバイアス防止: 多くの関数は内部で datetime.today()/date.today() を直接参照せず、target_date を入力として受け取り、DB クエリでも date < target_date などの排他条件を用いています。バッチ・バックテスト用途に配慮した設計です。
- OpenAI 呼び出し:
  - gpt-4o-mini を使用し、JSON Mode（response_format）で厳密な JSON を期待します。
  - API エラー（429、ネットワーク断、5xx 等）はリトライやフォールバック（ゼロスコア）で安全に扱います。
- J-Quants API:
  - RateLimit（120 req/min）を内部で制御し、401 受信時は自動でトークンをリフレッシュします。

ディレクトリ構成（主なファイル）
------------------------------
- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理（Settings）
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュース NLP（score_news）
    - regime_detector.py            — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント / 保存ロジック
    - pipeline.py                   — ETL パイプライン run_daily_etl 等
    - etl.py                        — ETL 型（ETLResult）再エクスポート
    - stats.py                      — 汎用統計ユーティリティ（zscore_normalize）
    - quality.py                    — データ品質チェック
    - calendar_management.py        — 市場カレンダーの判定・更新ロジック
    - news_collector.py             — RSS 収集と前処理（SSRF対策等）
    - audit.py                      — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py            — モメンタム/バリュー/ボラティリティなど
    - feature_exploration.py        — forward returns, IC, 統計サマリー

補足（運用ヒント）
-----------------
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。CI やテストで自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI や J-Quants の呼び出し部分はテスト時に差し替え（モック）できるように実装されています（内部の _call_openai_api 等を patch して置換可能）。
- DuckDB の executemany は一部バージョンで空リストの扱いに制約があるため、モジュール内で空チェックが行われています。

ライセンス / 貢献
-----------------
（この README にライセンス情報は含まれていません。プロジェクトのルートにある LICENSE / CONTRIBUTING.md を参照してください。）

以上。必要があれば、README にサンプル .env.example、実際のテーブルスキーマ、簡易の起動スクリプト例（cron 用 wrapper）なども追記できます。どの情報を追加希望か教えてください。