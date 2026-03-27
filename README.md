KabuSys
=======

概要
----
KabuSys は日本株向けのデータプラットフォームおよび自動売買基盤のライブラリ群です。  
J-Quants からのデータ取得（株価・財務・市場カレンダー）、RSS ベースのニュース収集、OpenAI を用いたニュースセンチメント評価、各種ファクター計算、ETL パイプライン、監査ログ（発注〜約定トレーサビリティ）などを提供します。  
設計方針として「ルックアヘッドバイアス排除」「DuckDB を用いた高速な分析」「冪等操作」「外部 API の堅牢なリトライ/レート制御」を重視しています。

主な機能
---------
- データ収集 / ETL
  - J-Quants API から株価日足・財務データ・市場カレンダーを差分取得し DuckDB に冪等保存（pipeline.run_daily_etl 等）
  - RSS からニュース収集・前処理・raw_news への保存（news_collector.fetch_rss 等）
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合などを検知（data.quality）
- NLP / LLM 連携
  - ニュース銘柄別センチメント算出（ai.news_nlp.score_news）
  - マクロニュース + ETF MA による市場レジーム判定（ai.regime_detector.score_regime）
  - OpenAI (gpt-4o-mini) の JSON Mode を利用（結果検証・リトライあり）
- リサーチ用ユーティリティ
  - モメンタム / バリュー / ボラティリティなどのファクター計算（research.factor_research）
  - 将来リターン、IC 計算、ファクター統計（research.feature_exploration）
  - クロスセクション Z スコア正規化（data.stats.zscore_normalize）
- オーディット（監査）テーブル
  - signal_events / order_requests / executions のスキーマ定義と初期化（data.audit.init_audit_db）
- 市場カレンダー管理
  - 営業日判定、前後営業日の取得、夜間カレンダー更新ジョブ（data.calendar_management）

要件（推奨）
------------
- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API / RSS / OpenAI）

セットアップ手順
----------------
1. リポジトリをクローン（またはパッケージをプロジェクトに組み込む）
   - 例: git clone ... && cd ...

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存インストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （プロジェクトが setuptools/pyproject を持つ場合）
   - pip install -e .

4. 環境変数設定
   - プロジェクトルートに .env を置くと自動で読み込まれます（.env.local で上書き可）。
   - 自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   主要な環境変数:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD     : kabu ステーション API 用パスワード（必須）
   - KABU_API_BASE_URL     : kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN       : Slack 通知用ボットトークン（必須）
   - SLACK_CHANNEL_ID      : Slack 通知先チャネル ID（必須）
   - OPENAI_API_KEY        : OpenAI API キー（score_news / score_regime で利用）
   - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH           : SQLite (monitoring 用) パス（デフォルト data/monitoring.db）
   - KABUSYS_ENV           : environment (development / paper_trading / live)（デフォルト development）
   - LOG_LEVEL             : ログレベル（DEBUG/INFO/...、デフォルト INFO）

使い方（サンプル）
------------------

- DuckDB 接続を作って日次 ETL を実行する（ETL のメインエントリポイント）:

  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(<path_to_duckdb>))  # settings.duckdb_path を利用するのが簡単
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメントを生成する（OpenAI キーが必要）:

  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"written scores: {written}")

- 市場レジーム（マクロセンチメント + ETF MA）をスコアリングする:

  from kabusys.ai.regime_detector import score_regime
  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")

- 監査ログ用の DB を初期化する:

  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit_duckdb.db")
  # 必要に応じて transactional=True で init_audit_schema を呼ぶことも可能

- リサーチ用関数の利用例:

  from kabusys.research.factor_research import calc_momentum
  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  # その後 data.stats.zscore_normalize で正規化など

自動環境変数読み込みについて
-----------------------------
- パッケージ起動時にプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し、
  .env → .env.local の順で自動的に環境変数を読み込みます（既存 OS 環境変数は保護）。
- 無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に利用）。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py                (パッケージ定義)
- config.py                  (環境変数 / 設定管理)
- ai/
  - __init__.py
  - news_nlp.py              (ニュースセンチメントスコア)
  - regime_detector.py       (市場レジーム判定)
- data/
  - __init__.py
  - jquants_client.py        (J-Quants API クライアント + 保存関数)
  - pipeline.py              (ETL パイプライン / run_daily_etl / ETLResult)
  - etl.py                   (ETL 型の再エクスポート)
  - news_collector.py        (RSS 収集・前処理)
  - calendar_management.py   (市場カレンダー管理)
  - quality.py               (データ品質チェック)
  - stats.py                 (統計ユーティリティ)
  - audit.py                 (監査ログテーブル定義 / 初期化)
- research/
  - __init__.py
  - factor_research.py       (momentum/value/volatility)
  - feature_exploration.py   (forward returns / IC / summary)

設計上の注意点
--------------
- ルックアヘッドバイアス防止
  - 各モジュールは内部で date.today()/datetime.today() の乱用を避け、
    外部から target_date を渡す設計です。バックテスト時は必ず過去時点のデータのみを使うよう注意してください。
- 冪等性
  - 多くの保存処理は ON CONFLICT DO UPDATE 等で冪等に実装されています。
- フェイルセーフ
  - LLM/API の失敗時は基本的にゼロスコアやスキップで継続する設計です（ただし重大エラーはログに記録）。
- テスト容易性
  - OpenAI 呼び出しやネットワーク関数はモック差替え可能なように内部で分離してあります。

補足
----
- 本 README はコードベースの実装に基づく概要・利用ガイドです。プロダクション運用時は権限管理、シークレット管理、監視、バックアップなど運用面の整備を必ず行ってください。
- 追加のコンフィグ例や .env.example がプロジェクト内にある場合はそれを参照して環境変数を準備してください。

もし README に追記したい具体的な使い方（例: ETL の Cron スケジュール例、Slack 通知の設定方法、kabu API 発注フローの説明など）があれば教えてください。必要に応じてサンプルコードや運用手順を追加します。