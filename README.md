# KabuSys

日本株を対象とした自動売買システムのコアライブラリです。データ収集（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログ等の機能を提供します。戦略ロジックは research/ での解析結果を取り込み、feature → signal の流れで発注レイヤへ渡す設計になっています。

## 特徴（概要）
- J-Quants API からの株価・財務・カレンダー取得（レート制限・自動リトライ・トークンリフレッシュ対応）
- DuckDB を用いたローカルデータレイヤ（Raw / Processed / Feature / Execution）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- 研究用ファクター計算（Momentum / Volatility / Value 等）
- 特徴量エンジニアリング（正規化・ユニバースフィルタ）
- シグナル生成（複数コンポーネントの重み付け合算、Bear レジーム抑制、エグジット判定）
- ニュース収集（RSS → raw_news、URL正規化・SSRF対策・トラッキング除去）
- マーケットカレンダー管理／営業日ユーティリティ
- 監査ログ（signal → order → execution をトレースするテーブル設計）

## 主要機能一覧
- data/jquants_client.py: J-Quants API クライアント（fetch_* / save_*）
- data/schema.py: DuckDB のスキーマ定義と初期化（init_schema）
- data/pipeline.py: 日次 ETL（run_daily_etl）・個別 ETL ジョブ
- data/news_collector.py: RSS 取得と raw_news 保存（SSRF 対策・トラッキング除去）
- data/calendar_management.py: market_calendar の更新、営業日判定ユーティリティ
- data/stats.py: zscore_normalize 等の統計ユーティリティ
- research/factor_research.py: モメンタム／ボラティリティ／バリューの計算
- research/feature_exploration.py: 将来リターン計算、IC（Spearman）などの解析ユーティリティ
- strategy/feature_engineering.py: 生ファクターの正規化・ユニバースフィルタ・features への UPSERT
- strategy/signal_generator.py: features と ai_scores を統合して signals を生成
- config.py: 環境変数 / 設定の集中管理（.env 自動読み込み、必須チェック）
- audit / execution / monitoring: 発展的な監査・発注・監視機能（スキーマ定義等）

## セットアップ手順

1. リポジトリをチェックアウト
   - 例:
     git clone <repo-url>
     cd <repo>

2. Python 環境を作成（推奨: venv / pyenv）
   - 例:
     python -m venv .venv
     source .venv/bin/activate
     pip install -U pip

3. 依存パッケージをインストール
   - 本コードベースは外部ライブラリを最小限に抑えていますが、DuckDB や defusedxml 等が必要です。requirements.txt がある場合はそれを使用してください。
     pip install duckdb defusedxml

4. 環境変数ファイルを用意
   - プロジェクトルートに `.env`（または `.env.local`）を作成してください。自動でロードされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可）。
   - 必須環境変数（config.Settings 参照）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabu ステーション API パスワード（発注機能を使う場合）
     - SLACK_BOT_TOKEN — Slack 通知用ボットトークン（通知を利用する場合）
     - SLACK_CHANNEL_ID — Slack チャンネル ID
   - オプション:
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
     - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）

5. DuckDB スキーマ初期化
   - Python でスキーマを作成します（デフォルトパスは settings.duckdb_path）。
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

   - ":memory:" を渡すとメモリ DB が使えます（テスト用）。

## 使い方（主な操作例）

- 日次 ETL（市場カレンダー・株価・財務の差分取得／保存／品質チェック）
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())

  # ETL 結果の確認
  print(result.to_dict())

- 特徴量の作成（build_features）
  from datetime import date
  from kabusys.strategy import build_features
  conn = init_schema("data/kabusys.duckdb")
  count = build_features(conn, date(2024, 1, 31))
  print(f"features upserted: {count}")

- シグナル生成（generate_signals）
  from datetime import date
  from kabusys.strategy import generate_signals
  conn = init_schema("data/kabusys.duckdb")
  total = generate_signals(conn, date.today())
  print(f"signals written: {total}")

  - weights や threshold をカスタマイズ可能:
    generate_signals(conn, date.today(), threshold=0.65, weights={"momentum":0.5,"value":0.2,"volatility":0.15,"liquidity":0.1,"news":0.05})

- ニュース収集ジョブ（RSS）
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)

- カレンダー更新ジョブ
  from kabusys.data.calendar_management import calendar_update_job
  conn = init_schema("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"market_calendar saved: {saved}")

- J-Quants の手動呼び出し（トークン取得 / fetch）
  from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
  token = get_id_token()  # settings.jquants_refresh_token を使用
  records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))

- 設定をプログラムから利用
  from kabusys.config import settings
  print(settings.duckdb_path, settings.env, settings.log_level)

## 実行時の注意点
- .env の自動ロードは config.py がプロジェクトルートを探索して .env/.env.local を読み込みますが、テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。
- KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれかでなければエラーになります。実際に発注を行う場合は is_live フラグに注意してください。
- J-Quants API はレート制限（120 req/min）をモジュール内で守る実装ですが、大量バックフィル時は適切な間引き・時間管理を行ってください。
- DuckDB の ON CONFLICT / トランザクションを多用して冪等性を担保しています。外部から DB を操作する際はトランザクションに注意してください。

## ディレクトリ構成（抜粋）
プロジェクトの主要ファイルとモジュール:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - pipeline.py
      - calendar_management.py
      - features.py
      - stats.py
      - audit.py
      - pipeline.py
      - (その他 data 関連モジュール)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - strategy/
      - __init__.py
      - feature_engineering.py
      - signal_generator.py
    - execution/
      - __init__.py
    - monitoring/
      - (監視・メトリクス用モジュール)

簡易ツリー（CLI 表示例）
- src/kabusys/
  - config.py
  - data/
    - jquants_client.py
    - schema.py
    - pipeline.py
    - news_collector.py
    - calendar_management.py
    - stats.py
    - features.py
    - audit.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - feature_engineering.py
    - signal_generator.py
  - execution/
  - monitoring/

## 開発メモ / 設計方針（抜粋）
- ルックアヘッドバイアス回避: すべての戦略・特徴量計算は target_date 時点で利用可能なデータのみを使うよう設計されています。
- 冪等性: DB への保存は基本的に ON CONFLICT/UPSERT を利用しているため、再実行でデータを壊しにくい構造です。
- セキュリティ: ニュース収集の SSRF 対策、XML パースの defusedxml 使用、J-Quants のトークン管理などを実装。
- テストしやすさ: id_token の注入や KABUSYS_DISABLE_AUTO_ENV_LOAD による環境依存の抑制など、ユニットテストを意識した設計。

## よくある操作とトラブルシューティング
- 環境変数が足りないエラー:
  - settings.jquants_refresh_token など必須変数は .env に設定してください。エラー時は config._require が ValueError を出します。
- DuckDB に接続できない／パスがない:
  - init_schema は親ディレクトリを自動作成しますが、書き込み権限がない場合はエラーになります。パスを確認してください。
- J-Quants 呼び出しで 401 が返る:
  - get_id_token によるトークン取得や jquants_client の自動リフレッシュ処理を確認し、環境変数のトークンが正しいか確認してください。

---

この README はコードベースの主要機能と利用手順の要約です。詳細な設計仕様やデータモデル（StrategyModel.md / DataPlatform.md / DataSchema.md 等）が別途ある前提になっています。具体的な運用手順・運用上の安全チェック（取引量・リスク管理・接続監視等）は運用ドキュメントを参照してください。