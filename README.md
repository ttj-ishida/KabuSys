KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買基盤ライブラリです。  
主に以下を提供します。

- J-Quants からの市場データ／財務データの取得と DuckDB への保存（ETL）
- ニュース収集・前処理とニュース⇄銘柄紐付け
- ファクター計算（Momentum / Volatility / Value 等）と特徴量作成（features テーブル）
- シグナル生成（final_score 計算、BUY/SELL 判定）と signals テーブルへの永続化
- マーケットカレンダー管理、監査ログ/発注履歴用スキーマ等の DB スキーマ
- 研究（research）用のユーティリティ（IC 計算や将来リターン計算など）

設計上のポイント
- DuckDB を主要な永続層として使用（軽量・SQL ベースで分析と運用を同一 DB で実行）
- ルックアヘッドバイアス対策（target_date 時点のデータのみ参照、fetched_at 記録）
- 冪等性重視（API 取得データは ON CONFLICT で更新、ETL は差分・バックフィル対応）
- 外部依存を最小化（pandas 等に依存しない純 Python 実装を基本とする）
- セキュリティ配慮（RSS 收集時の SSRF防止、XMLパースの安全化、API レートリミット制御 等）

主な機能一覧
----------------
- data
  - jquants_client: J-Quants API からの取得（株価・財務・カレンダー）＋保存関数
  - schema: DuckDB スキーマ定義 / init_schema()
  - pipeline: 日次 ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - news_collector: RSS 収集・前処理・DB保存（fetch_rss, save_raw_news, run_news_collection）
  - calendar_management: 市場カレンダーの判定／next/prev 等ユーティリティ
  - stats: zscore_normalize 等の統計ユーティリティ
- research
  - factor_research: calc_momentum / calc_volatility / calc_value
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary 等
- strategy
  - feature_engineering.build_features: raw factor を正規化して features テーブルへ保存
  - signal_generator.generate_signals: features / ai_scores / positions を使って signals を生成
- execution / monitoring / audit（スキーマとログ機能や監査テーブル実装が含まれる）

セットアップ手順
----------------

前提
- Python 3.10 以上（型ヒントで "X | Y" を使用）
- DuckDB が必要（Python パッケージ duckdb）
- defusedxml（安全な XML パース）など一部依存パッケージ

1. リポジトリをクローン
   git clone <リポジトリ>

2. 仮想環境を作成・有効化（任意）
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール
   pip install duckdb defusedxml

   （もしプロジェクトに pyproject.toml 等があれば pip install -e . を推奨）

4. 環境変数設定
   ルートに .env を置くか環境変数として下記を設定します（README の例）:

   必須（実行に必要）
   - JQUANTS_REFRESH_TOKEN   : J-Quants の refresh token
   - KABU_API_PASSWORD       : kabuステーション API 用パスワード
   - SLACK_BOT_TOKEN         : Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID        : Slack チャンネル ID

   任意（デフォルトあり）
   - KABUSYS_ENV             : development / paper_trading / live  (default: development)
   - LOG_LEVEL               : DEBUG/INFO/… (default: INFO)
   - DUCKDB_PATH             : DuckDB ファイルパス (default: data/kabusys.duckdb)
   - SQLITE_PATH             : 監視用 SQLite (default: data/monitoring.db)
   - KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 にすると自動 .env ロードを無効化

   .env の例:
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=xxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567

5. DB スキーマ初期化
   Python REPL やスクリプトで DuckDB ファイルを作成してスキーマを初期化します（data ディレクトリは自動で作成されます）。

   例:
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")

使い方（主要な例）
------------------

1) DB の初期化
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")

2) 日次 ETL 実行（J-Quants から市場データ／財務データ／カレンダーを取得）
   from kabusys.data.pipeline import run_daily_etl
   result = run_daily_etl(conn)
   print(result.to_dict())

   オプションで target_date を指定可能:
   run_daily_etl(conn, target_date=date(2025,1,15))

3) 特徴量（features）構築
   from kabusys.strategy import build_features
   from datetime import date
   count = build_features(conn, date(2025,1,15))
   print(f"upserted features: {count}")

4) シグナル生成
   from kabusys.strategy import generate_signals
   from datetime import date
   total = generate_signals(conn, date(2025,1,15))
   print(f"signals written: {total}")

   重みや閾値を変更することも可能:
   total = generate_signals(conn, date(2025,1,15), threshold=0.65, weights={"momentum":0.5, "value":0.2, "volatility":0.15, "liquidity":0.1, "news":0.05})

5) ニュース収集ジョブ（RSS を取得して raw_news に保存）
   from kabusys.data.news_collector import run_news_collection
   # known_codes を渡すと本文から銘柄コード抽出して news_symbols に紐付ける
   stats = run_news_collection(conn, known_codes={"7203","6758"})
   print(stats)  # {source_name: inserted_count, ...}

6) カレンダー系ユーティリティ
   from kabusys.data.calendar_management import is_trading_day, next_trading_day
   is_trading_day(conn, date(2025,1,15))
   next_trading_day(conn, date(2025,1,15))

運用上の注意
- J-Quants API 呼び出しはレート制限（120 req/min）とリトライを内部で制御しますが、長時間の差分・全銘柄取得は時間がかかるためジョブ設計に注意してください。
- run_daily_etl は品質チェックを行い、問題のリストを返します（ETLResult.quality_issues）。重大な品質問題を検出しても ETL は継続する設計です。
- features / signals の処理は target_date 時点のデータのみを使用するので、所定のワークフロー（ETL → build_features → generate_signals）を順に実行してください。
- ニュース収集では外部 URL の検証や XML の安全パース（defusedxml）を行っていますが、公開環境での動作ログ・監視を推奨します。
- 自動で .env をプロジェクトルートから読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。プロジェクトルートは .git または pyproject.toml を基準に検出します。

ディレクトリ構成（主要ファイル）
--------------------------------

src/kabusys/
- __init__.py
- config.py                     -- 環境変数/設定管理
- data/
  - __init__.py
  - jquants_client.py           -- J-Quants API クライアント + 保存関数
  - news_collector.py           -- RSS 収集・前処理・DB 保存
  - schema.py                   -- DuckDB スキーマ定義と init_schema()
  - pipeline.py                 -- ETL パイプライン（run_daily_etl 等）
  - stats.py                    -- zscore_normalize 等統計ユーティリティ
  - calendar_management.py      -- 市場カレンダー管理ユーティリティ
  - audit.py                    -- 監査ログ用スキーマ（signal_events, order_requests, executions）
  - features.py                 -- data.stats の公開ラッパ
- research/
  - __init__.py
  - factor_research.py          -- calc_momentum / calc_volatility / calc_value
  - feature_exploration.py      -- calc_forward_returns / calc_ic / factor_summary / rank
- strategy/
  - __init__.py
  - feature_engineering.py      -- build_features（features テーブル作成）
  - signal_generator.py         -- generate_signals（signals テーブル作成）
- execution/                     -- 発注関連（プレースホルダ / 層）
- monitoring/                    -- 監視用モジュール（DB/Slack 通知等、実装場所）

テスト・開発
-------------
- settings.py の自動読み込みを抑止したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時の isolation 用）。
- J-Quants や外部 API 呼び出しは関数へ id_token 等を注入できる設計になっているため、ユニットテストでは HTTP 呼び出し部分をモックできます（例: kabusys.data.jquants_client._request や news_collector._urlopen の差し替え）。

ライセンス / 貢献
-----------------
（ここにライセンス情報や貢献方法を記述してください。リポジトリに LICENSE ファイルがあれば参照することを推奨します。）

付記
----
この README はコードベースに含まれる docstring と実装から要点を抽出して作成しています。詳細な仕様（StrategyModel.md / DataPlatform.md 等）がプロジェクト内にある場合はそちらも参照してください。質問や具体的な使い方のサンプルが必要であれば、目的（ETL の定期実行、バックテスト用データ準備、リアルタイム実行等）を教えてください。適した例を追加で提示します。