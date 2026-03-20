KabuSys — 日本株自動売買プラットフォーム（README）
================================================================================

概要
----
KabuSys は日本株のデータ収集・ETL・特徴量生成・シグナル生成・監査ログ管理までを想定した
モジュール群です。DuckDB を内部データストアに使い、J-Quants API や RSS フィードからのデータ収集、
research 層でのファクター計算、strategy 層での特徴量合成とシグナル生成を行う設計になっています。

主な設計方針:
- ルックアヘッドバイアスを避ける（常に target_date 時点の情報のみを使用）
- DB 操作は冪等（ON CONFLICT / トランザクション）で安全に行う
- ネットワーク操作にはレート制御／リトライを実装
- RSS（ニュース）収集で SSRF / XML Bomb 対策を行う

機能一覧
--------
- 環境変数管理（自動 .env ロード / 必須チェック）：kabusys.config
- J-Quants API クライアント（レートリミット・自動トークン更新・ページネーション）：kabusys.data.jquants_client
- DuckDB スキーマ定義・初期化：kabusys.data.schema
- ETL パイプライン（市場カレンダー / 株価 / 財務データの差分取得）：kabusys.data.pipeline
- ニュース収集（RSS → raw_news / news_symbols、SSRF 対策）：kabusys.data.news_collector
- カレンダー管理（営業日判定、next/prev_trading_day、夜間更新ジョブ）：kabusys.data.calendar_management
- 統計ユーティリティ（クロスセクション Z スコア正規化等）：kabusys.data.stats
- 研究用ファクター計算（momentum / volatility / value）：kabusys.research.factor_research
- 研究用解析（forward returns / IC / summary / rank）：kabusys.research.feature_exploration
- 特徴量エンジニアリング（raw ファクターの統合・正規化・features テーブル保存）：kabusys.strategy.feature_engineering
- シグナル生成（features と ai_scores を統合して BUY/SELL を生成）：kabusys.strategy.signal_generator
- 監査ログ用スキーマ（signal_events / order_requests / executions 等）：kabusys.data.audit

セットアップ手順
----------------
前提
- Python 3.10+（typing の Union 型の代替等を想定。実行環境に合わせてください）
- DuckDB を利用（Python パッケージ duckdb）
- defusedxml（RSS パースの安全化）

1) リポジトリをクローン
   git clone <repo-url>
   cd <repo-root>

2) 仮想環境作成・有効化（推奨）
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3) 依存パッケージをインストール
   pip install duckdb defusedxml

   （プロジェクトで requirements.txt / pyproject.toml があればそちらを使ってください）
   開発用に editable install:
   pip install -e .

4) 環境変数の設定
   プロジェクトルート（.git または pyproject.toml がある親ディレクトリ）に .env を置くと
   kabusys.config が自動で読み込みます（自動ロードを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

   必要な環境変数（最低限）:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD     : kabu ステーション API パスワード（必須）
   - SLACK_BOT_TOKEN       : Slack 通知用トークン（必須; Slack を使わない場合も設定されていることを期待している設計）
   - SLACK_CHANNEL_ID      : Slack チャンネル ID（必須）
   便利な設定:
   - KABUSYS_ENV           : development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL             : DEBUG / INFO / ...（デフォルト: INFO）
   - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH           : 監視用 sqlite（デフォルト: data/monitoring.db）

   .env（簡易例）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=CXXXXXXX
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5) データベース初期化（DuckDB スキーマ作成）
   Python REPL や小さなスクリプトで実行します。

   例:
   from kabusys.config import settings
   from kabusys.data.schema import init_schema
   conn = init_schema(settings.duckdb_path)

使い方（主要ワークフロー例）
---------------------------
以下は典型的なバッチワークフローの例です（Python スクリプト / REPL で実行）。

1) DB 初期化（初回のみ）
   from kabusys.config import settings
   from kabusys.data.schema import init_schema
   conn = init_schema(settings.duckdb_path)

2) 日次 ETL（市場カレンダー / 株価 / 財務 データ取得 + 品質チェック）
   from kabusys.data.pipeline import run_daily_etl
   result = run_daily_etl(conn)
   print(result.to_dict())

3) 特徴量（features）生成
   from datetime import date
   from kabusys.strategy import build_features
   # ETL の対象日（あるいは ETL 実行日）を使う
   n = build_features(conn, target_date=date.today())
   print(f"features upserted: {n}")

4) シグナル生成
   from kabusys.strategy import generate_signals
   total = generate_signals(conn, target_date=date.today())
   print(f"signals written: {total}")

5) ニュース収集（RSS）
   from kabusys.data.news_collector import run_news_collection
   # known_codes は銘柄抽出に使う有効な銘柄コードセット（任意）
   results = run_news_collection(conn, known_codes=None)
   print(results)

6) カレンダー夜間更新ジョブ（別ジョブとしてスケジュール）
   from kabusys.data.calendar_management import calendar_update_job
   saved = calendar_update_job(conn)
   print(f"calendar saved: {saved}")

運用上の注意
--------------
- 環境変数の自動読み込みは .env / .env.local の順で行われ、OS 環境変数を上書きしない仕様です。
  自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API のレート制限（120 req/min）やリトライロジックは jquants_client で扱われます。
- RSS の取得は SSRF/ZIP Bomb/大容量レスポンス対策を施してありますが、信頼出来ないフィードの追加は注意してください。
- features / signals / raw データの INSERT は冪等性を意識した設計（ON CONFLICT 句やトランザクション）です。
- production 環境で実行する際は KABUSYS_ENV を適切に設定し、ログレベルや監視・通知を整備してください。

主要ディレクトリ構成
--------------------
以下はソースツリー（主要ファイルのみの抜粋）:

src/
  kabusys/
    __init__.py
    config.py                      # 環境変数・設定
    data/
      __init__.py
      jquants_client.py            # J-Quants API クライアント（fetch/save）
      news_collector.py            # RSS ニュース収集・保存
      schema.py                    # DuckDB スキーマ定義・初期化
      pipeline.py                  # ETL パイプライン（run_daily_etl 等）
      stats.py                     # 統計ユーティリティ（zscore_normalize）
      features.py                  # features の公開インターフェース
      calendar_management.py       # カレンダー管理・更新ジョブ
      audit.py                     # 監査ログスキーマ
      ...                          # その他（quality 等が存在する想定）
    research/
      __init__.py
      factor_research.py           # momentum/volatility/value 計算
      feature_exploration.py       # forward returns / IC / summary / rank
    strategy/
      __init__.py
      feature_engineering.py       # features の構築（正規化・UPSERT）
      signal_generator.py          # final_score 計算・BUY/SELL 生成
    execution/                      # 発注関連（空の __init__ など）
    monitoring/                     # 監視・メトリクス（未実装箇所あり）
tests/                              # （存在する場合）テスト群

開発メモ / 実装上のポイント
---------------------------
- ファクター計算・シグナル生成は target_date ベースで設計され、ルックアヘッドを避けています。
- DB 操作は可能な限りトランザクションで囲み、エラー時はロールバックして一貫性を保ちます。
- news_collector は defusedxml を用いて XML 攻撃を軽減し、URL 正規化・トラッキングパラメータ除去を行います。
- jquants_client のトークン管理はモジュールレベルでキャッシュされ、自動リフレッシュを実装しています。
- 監査ログ（audit）は発注フローのトレーサビリティを重視して設計されています（UUID 連鎖）。

よくある運用コマンド（例）
------------------------
- DB 初期化（スクリプト例）
  python - <<'PY'
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  init_schema(settings.duckdb_path)
  print("DB initialized:", settings.duckdb_path)
  PY

- 日次バッチ（ETL → features → signals）
  python - <<'PY'
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.strategy import build_features, generate_signals
  from datetime import date

  conn = init_schema(settings.duckdb_path)
  run_daily_etl(conn)
  t = date.today()
  build_features(conn, t)
  generate_signals(conn, t)
  PY

サポート / 拡張
----------------
- Slack 通知や実際の発注（kabu API 連携）は execution 層に実装を追加できます。
- AI スコア（ai_scores）との統合は既にシグナル生成側で考慮されています。AI モデル出力を ai_scores テーブルに保存すれば自動で反映されます。
- 品質チェック（quality）モジュールは pipeline から参照される想定です。プロジェクトに合わせてチェックを追加してください。

最後に
------
この README はコードベースの現状（主要モジュールの API と設計方針）をまとめたものです。具体的な運用スクリプト・CI 設定・監視設定は運用要件に合わせて追加してください。質問や補足したい点があればお知らせください。