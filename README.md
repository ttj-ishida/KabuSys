KabuSys — 日本株自動売買 / データプラットフォーム
=================================================

概要
----
KabuSys は日本株向けのデータプラットフォーム兼自動売買基盤のプロジェクトです。  
主に次を目的としたモジュール群を含みます。

- データ取得・ETL（J-Quants API 経由）
- ニュース収集・NLP（OpenAI を用いたセンチメント分析）
- 市場レジーム判定（ETF MA とマクロニュースの合成）
- ファクター計算・リサーチユーティリティ
- 監査ログ（signal → order → execution のトレース）
- データ品質チェック、マーケットカレンダー管理 等

設計方針として、バックテストにおけるルックアヘッドバイアスを避ける実装、DuckDB を中心としたローカル DB 管理、外部 API 呼び出しのリトライ/フェイルセーフが組み込まれています。

主な機能一覧
--------------
- data/
  - ETL パイプライン（daily ETL、prices/financials/calendar の差分取得）
  - J-Quants API クライアント（ページネーション・レート制限・トークン自動リフレッシュ）
  - ニュース収集（RSS → raw_news、SSRF 対策・正規化）
  - カレンダー管理（market_calendar、営業日判定/前後営業日の取得）
  - 品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログ初期化／専用 DB ユーティリティ（signal/order/execution）
  - 統計ユーティリティ（Zスコア正規化 等）
- ai/
  - news_nlp.score_news: OpenAI（gpt-4o-mini）でニュースを銘柄別にスコア化して ai_scores に保存
  - regime_detector.score_regime: ETF（1321）200日MA とマクロニュース LLM 結果を合成して market_regime に保存
  - 再試行・API エラー時のフェイルセーフが実装
- research/
  - ファクター計算（momentum, value, volatility）
  - 特徴量探索（forward returns, IC, summary, rank）
- config
  - 環境変数管理、自動 .env ロード（プロジェクトルート検出）と設定オブジェクト

セットアップ手順
----------------

前提
- Python 3.9+（typing の構文などに準拠）
- DuckDB（Python パッケージとしてインストール）
- OpenAI API キー、J-Quants リフレッシュトークン 等の外部サービスのアカウント

1. ソースをチェックアウト / インストール
   - 開発環境から:
     - git clone ...
     - pip install -e .  （プロジェクトに setup/pyproject があることを想定）

2. 必要パッケージをインストール
   - requirements.txt がある場合は:
     - pip install -r requirements.txt
   - 主な依存（例）
     - duckdb
     - openai
     - defusedxml
     - など（プロジェクトの pyproject / requirements を参照）

3. 環境変数設定（.env）
   - プロジェクトルートに .env または .env.local を配置すると自動でロードされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。
   - 必須の環境変数例（.env）:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - KABU_API_PASSWORD=your_kabu_station_password
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C01234567
     - OPENAI_API_KEY=sk-...
   - オプション（デフォルト値あり）:
     - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — default: INFO

4. データベース初期化（監査ログなど）
   - 監査ログ専用 DB を初期化する例:
     - Python REPL:
       from kabusys.data.audit import init_audit_db
       conn = init_audit_db("data/audit.duckdb")
   - または既存の DuckDB 接続で init_audit_schema を呼ぶことができます。

使い方（簡易サンプル）
--------------------

- DuckDB 接続を作り、日次 ETL を実行する例:

  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースのセンチメントスコアを生成する（OpenAI API キー必要）:

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"written: {written}銘柄")

- 市場レジームを判定して保存する:

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")

- 研究用ファクター計算の例:

  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  # records は各銘柄の辞書リスト

重要な環境変数 / 設定一覧
-------------------------
- JQUANTS_REFRESH_TOKEN — 必須（J-Quants 用リフレッシュトークン）
- KABU_API_PASSWORD — 必須（kabuステーション API のパスワード）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — 必須（通知用）
- OPENAI_API_KEY — 必須（AI スコアリング / レジーム判定）
- KABUSYS_ENV — development / paper_trading / live
- LOG_LEVEL — ログレベル
- DUCKDB_PATH / SQLITE_PATH — DB ファイルパス
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化するフラグ（1 を設定）

注意点 / 実装ポリシー
--------------------
- 多くの処理は「ルックアヘッドバイアス」を避けるために datetime.today() や date.today() を直接参照せず、外部から target_date を与える設計です。バックテストで使用する場合は対象日を明示してください。
- 外部 API 呼び出し時にはリトライ・バックオフが実装されています。OpenAI や J-Quants の呼び出し失敗時はフェイルセーフ（スコアを 0 にする等）で継続する箇所があります。
- ニュース収集時は SSRF 対策、受信サイズ制限、XML の安全パース（defusedxml）などを行っています。
- DuckDB 向けの executemany や ON CONFLICT の使い方には DuckDB のバージョン注意点に配慮しています。

ディレクトリ構成（主要ファイル）
------------------------------
（src/kabusys 以下）

- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - jquants_client.py
  - pipeline.py
  - etl.py
  - news_collector.py
  - calendar_management.py
  - quality.py
  - audit.py
  - stats.py
  - (その他: schema/init 等を想定)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- monitoring, strategy, execution, …（パッケージ外部公開対象として __all__ に含めるモジュール群）

開発 / デバッグ
----------------
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml の存在）を基準に行われます。テスト中に自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI クライアントはテスト容易性のため _call_openai_api をパッチして差し替える設計になっています。
- DuckDB はファイルパス（例: data/kabusys.duckdb）または ":memory:" を使えます。監査 DB 初期化時は parent ディレクトリを自動作成します。

ライセンス / 貢献
-----------------
- 本リポジトリのライセンス情報はプロジェクトのルート（LICENSE）を参照してください。
- バグ報告・機能提案は issue を立ててください。プルリクエスト歓迎します。

付録：簡単な .env 例
-------------------
# .env (プロジェクトルート)
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

以上。README に載せてほしい追加の利用例や、デプロイ手順（systemd / docker / k8s など）を希望する場合は用途に合わせて追記します。