KabuSys — 日本株自動売買プラットフォーム（README）
=====================================

概要
----
KabuSys は日本株のデータ収集／ETL、品質チェック、特徴量計算、ニュースの NLP 評価、マーケットレジーム判定、監査ログ（トレーサビリティ）などを含む自動売買・リサーチ基盤のコアライブラリ群です。  
主に DuckDB をデータレイヤに、J-Quants API と RSS ソースからのデータ取得、OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価を行います。設計上、ルックアヘッドバイアス対策・冪等性・堅牢なリトライ処理・SSRF 対策などに配慮されています。

主な機能
--------
- データ取得（J-Quants API クライアント）
  - 株価日足（OHLCV）、財務データ、JPX カレンダー、銘柄一覧等の取得・ページネーション対応
  - レートリミット管理・トークン自動リフレッシュ・リトライ（指数バックオフ）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- ETL パイプライン
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl：差分取得・バックフィル・品質チェック
  - ETL の実行結果を ETLResult として集約
- データ品質チェック
  - 欠損（OHLC）検出、スパイク検出（前日比閾値）、重複チェック、日付整合性チェック
  - QualityIssue 型で検出問題を集約
- マーケットカレンダー管理
  - 営業日判定、次/前営業日取得、期間内営業日列挙、JPX カレンダー差分更新ジョブ
- ニュース収集（RSS）
  - RSS フィードの取得、前処理（URL 除去・空白正規化）、記事ID生成（正規化 URL の SHA-256）
  - SSRF 対策、受信サイズ制限、XML の安全パース（defusedxml）
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースをまとめて LLM でセンチメント評価（score_news）
  - マクロニュースを用いた市場レジーム判定（score_regime）
  - JSON Mode・レスポンス検証・リトライポリシーを実装
- 研究・ファクター計算
  - モメンタム・バリュー・ボラティリティ等のファクター計算（calc_momentum / calc_value / calc_volatility）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、Zスコア正規化ユーティリティ
- 監査ログ（Audit）
  - signal_events / order_requests / executions など監査テーブル定義・初期化（init_audit_schema / init_audit_db）
  - 発注フローのトレーサビリティ（UUID ベースの階層）
- 設定管理
  - .env（.env.local）や環境変数から設定を読み込み（自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD 有り）

セットアップ手順
---------------
前提
- Python 3.10 以上（コード中で型 union 表記（A|B）を使用）
- システムにネットワークアクセス可能（J-Quants / OpenAI / RSS）

1. リポジトリをクローン
   - git clone ... （本 README の配布元に合わせてください）

2. 仮想環境作成と依存インストール（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
   - pip install --upgrade pip
   - 必要パッケージをインストール（最小例）:
     - pip install duckdb openai defusedxml

   （プロジェクト用 requirements.txt がある場合は pip install -r requirements.txt を使用）

3. 環境変数 / .env を設定
   - プロジェクトルート（.git または pyproject.toml がある場所）に .env または .env.local を置くと自動で読み込まれます（優先度: OS 環境 > .env.local > .env）。
   - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で利用）。
   - 必須変数（コード内 Settings により必要とされるもの）:
     - JQUANTS_REFRESH_TOKEN = <J-Quants のリフレッシュトークン>
     - KABU_API_PASSWORD = <kabuステーション API パスワード>
     - SLACK_BOT_TOKEN = <Slack Bot トークン>
     - SLACK_CHANNEL_ID = <監視通知先 Slack チャンネル ID>
   - 任意またはデフォルトあり:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト INFO
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視用 SQLite、デフォルト data/monitoring.db）
     - その他監視閾値等（CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, ...）

   例 .env（テンプレート）
   - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   - OPENAI_API_KEY=sk-...
   - KABU_API_PASSWORD=your_kabu_password
   - SLACK_BOT_TOKEN=xoxb-...
   - SLACK_CHANNEL_ID=C01234567
   - DUCKDB_PATH=data/kabusys.duckdb

4. データディレクトリ作成
   - mkdir -p data

使い方（主要な API と実行例）
--------------------------------

設定読み込み
- モジュール全体で設定は kabusys.config.settings から参照できます。
  - 例: from kabusys.config import settings; print(settings.duckdb_path)

監査 DB 初期化（DuckDB）
- 監査テーブルを初期化する簡単な例:
  from kabusys.data.audit import init_audit_db
  from kabusys.config import settings
  conn = init_audit_db(settings.duckdb_path)  # ファイルを自動作成して接続を返す

日次 ETL 実行
- ETL（市場カレンダー・株価・財務・品質チェック）を実行する例:
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

ニュースセンチメント評価（AI）
- OpenAI API キーは env で OPENAI_API_KEY を設定するか、api_key 引数で渡します。
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  conn = duckdb.connect(str(settings.duckdb_path))
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込んだ銘柄数: {n_written}")

市場レジーム判定（AI + ETF MA）
- 1321（日経225 連動 ETF）の 200 日 MA とマクロセンチメントを合成して regime を決定し market_regime テーブルへ保存します。
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))

特徴量・リサーチ関数
- 研究用のユーティリティ（ファクター計算、将来リターン、IC、統計サマリー）:
  from kabusys.research import calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic
  # DuckDB 接続を渡して使用

データ品質チェックを個別に実行
- from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues: print(i)

注意点 / 設計方針（重要）
- ルックアヘッドバイアス対策: 各モジュールは datetime.today()/date.today() を直接参照しない、または外部から target_date を指定する設計の箇所があります。バックテスト時は対象日以前に取得済みのデータだけを使うなど運用に注意してください。
- 冪等性: ETL での保存処理は ON CONFLICT DO UPDATE を利用し、再実行による重複を防ぎます。
- OpenAI 呼び出し: JSON モードを利用し、応答検証とクリップを厳密に行います。API エラー時はフェイルセーフでゼロ評価やスキップを行う設計です。
- RSS 収集: SSRF 対策、XML の安全パース、受信バイト数制限などを備えています。
- 必要な DB スキーマ: 各 save_* 関数は対応テーブル（raw_prices, raw_financials, market_calendar, raw_news, ai_scores, news_symbols, market_regime, など）が前提です。スキーマ定義は DataPlatform ドキュメントに従って事前に作成してください（本リポジトリ内の DDL を利用して初期化できるモジュールも存在します。監査テーブルは init_audit_schema / init_audit_db で作成可能です）。

ディレクトリ構成（主要ファイル）
---------------------------------
src/kabusys/
- __init__.py
- config.py                  — 環境変数 / .env 読み込みと設定アクセス
- ai/
  - __init__.py
  - news_nlp.py              — 銘柄別ニュースセンチメント scoring（score_news）
  - regime_detector.py       — マクロ + ETF MA を使った市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py        — J-Quants API クライアント（取得・保存ロジック）
  - pipeline.py              — ETL パイプライン（run_daily_etl 等）
  - etl.py                   — ETLResult 再エクスポート
  - calendar_management.py   — 市場カレンダー判定・更新ロジック
  - news_collector.py        — RSS 収集・前処理・保存ユーティリティ
  - quality.py               — 品質チェック（欠損・スパイク・重複・日付整合）
  - stats.py                 — 汎用統計ユーティリティ（zscore_normalize）
  - audit.py                 — 監査ログスキーマの定義と初期化
- research/
  - __init__.py
  - factor_research.py       — モメンタム/ボラティリティ/バリューの計算
  - feature_exploration.py   — 将来リターン / IC / 統計サマリー 等
- monitoring/, strategy/, execution/, などのトップレベルパッケージは __all__ に定義されており、実行系・戦略・監視ロジックを配置する想定（実装はコードベース参照）。

その他の情報
-------------
- ログ: settings.log_level に従ってログレベルを設定してください。運用ではファイル出力やログローテーションを併用することを推奨します。
- テスト: 各モジュールは外部依存を引数で注入しやすい設計（例: OpenAI クライアント、HTTP 呼び出し）になっているため、ユニットテストでモック差し替えが容易です。
- セキュリティ: RSS 取得時の SSRF 対策や defusedxml の利用、J-Quants トークン管理、OpenAI キーの取扱いに注意してください。

ライセンス・貢献
----------------
（この README にはライセンス情報は含めていません。配布元の LICENSE をご確認ください。）  

不明点や追加ドキュメントが必要であれば、どの機能について詳しく知りたいかを教えてください。特定のモジュールの API 使用例や DB スキーマ（テーブル定義）サンプルも提供できます。