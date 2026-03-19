KabuSys — 日本株自動売買プラットフォーム
=====================================

概要
----
KabuSys は日本株向けのデータプラットフォーム＋戦略実行基盤です。  
J-Quants API から市場データ・財務データ・マーケットカレンダーを取得し、DuckDB に保存・整形して特徴量を構築、戦略シグナルを生成します。ニュース収集やカレンダー管理、監査ログ（発注〜約定のトレーサビリティ）なども含む、研究（research）→データパイプライン（data）→戦略（strategy）→実行（execution）層を備えた設計になっています。

主な特徴
--------
- J-Quants API クライアント（レートリミット・リトライ・トークン自動リフレッシュ対応）
- DuckDB を用いた冪等的なデータ保存（ON CONFLICT / トランザクション処理）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- 特徴量エンジニアリング（モメンタム / ボラティリティ / バリュー等）
- シグナル生成（複数コンポーネントを統合した final_score、BUY/SELL 判定）
- ニュース収集（RSS、SSRF 対策、記事正規化、銘柄紐付け）
- マーケットカレンダー管理（営業日判定 / next/prev_trading_day 等）
- 監査ログ（signal → order_request → executions のトレーサビリティ）
- 環境設定は .env / 環境変数で管理（自動ロード機能あり）

動作要件（推奨）
----------------
- Python 3.10+
- 必要パッケージ（例）
  - duckdb
  - defusedxml
- J-Quants API アクセス用のリフレッシュトークン
- （発注機能を使う場合）kabuステーションの API 設定・パスワード等

セットアップ手順
----------------

1. リポジトリをクローン
   - git clone ... && cd <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （パッケージ化されている場合）pip install -e .

   ※プロジェクトに requirements.txt や pyproject.toml があればそちらを参照してください。

4. 環境変数の設定
   - プロジェクトルートに .env（または .env.local）を作成してください。キー例:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=INFO|DEBUG|...
   - 自動ロードを無効化したい場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトから init_schema を呼び出してください。

   例:
   - python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"

使い方（主要 API）
------------------

以下はライブラリを直接呼び出す簡単な例です。各関数は DuckDB 接続を引数に取り、冪等性やトランザクション制御を想定しています。

1. DB 初期化（1回）
   - from kabusys.data.schema import init_schema
   - conn = init_schema('data/kabusys.duckdb')

2. 日次 ETL 実行
   - from kabusys.data.pipeline import run_daily_etl
   - from kabusys.data.schema import get_connection
   - conn = get_connection('data/kabusys.duckdb')
   - result = run_daily_etl(conn)  # target_date を指定可能
   - print(result.to_dict())

   run_daily_etl は市場カレンダー、株価、財務データの差分取得・保存、品質チェックまで実施します。

3. 特徴量構築
   - from kabusys.strategy import build_features
   - conn = get_connection('data/kabusys.duckdb')
   - from datetime import date
   - n = build_features(conn, date(2024, 1, 10))
   - print(f"features upserted: {n}")

4. シグナル生成
   - from kabusys.strategy import generate_signals
   - conn = get_connection('data/kabusys.duckdb')
   - total = generate_signals(conn, date(2024,1,10))
   - print(f"signals written: {total}")

   generate_signals は features / ai_scores / positions を参照して BUY/SELL シグナルを作成します。weights や threshold をカスタマイズ可能です。

5. ニュース収集
   - from kabusys.data.news_collector import run_news_collection
   - conn = get_connection('data/kabusys.duckdb')
   - results = run_news_collection(conn, sources=None, known_codes=set(['7203','6758']))
   - print(results)

6. カレンダー更新バッチ
   - from kabusys.data.calendar_management import calendar_update_job
   - conn = get_connection('data/kabusys.duckdb')
   - saved = calendar_update_job(conn)

設定・環境変数（主なもの）
--------------------------
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（発注機能利用時）
- KABU_API_BASE_URL: kabu API の base URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知に使用
- DUCKDB_PATH: デフォルトの DuckDB ファイルパス（data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動ロードを無効化

ディレクトリ構成（コードベース）
-------------------------------

src/kabusys/
- __init__.py
- config.py                      - 環境変数 / 設定管理（.env 自動ロード、必須キーチェック）
- data/
  - __init__.py
  - jquants_client.py            - J-Quants API クライアント（取得・保存用ユーティリティ）
  - news_collector.py            - RSS 収集、記事正規化、raw_news 保存、銘柄抽出
  - pipeline.py                  - 日次 ETL パイプライン（差分取得・保存・品質チェック）
  - schema.py                    - DuckDB スキーマ定義と初期化関数
  - stats.py                     - Zスコア等の統計ユーティリティ
  - features.py                  - features 関連の公開インターフェース（再エクスポート）
  - calendar_management.py       - マーケットカレンダー管理（営業日判定・夜間更新ジョブ）
  - audit.py                     - 監査ログ（signal / order_request / executions 等）
- research/
  - __init__.py
  - factor_research.py           - モメンタム / ボラティリティ / バリュー等のファクター計算
  - feature_exploration.py       - 将来リターン計算、IC（Spearman）、統計サマリ
- strategy/
  - __init__.py                  - build_features, generate_signals を公開
  - feature_engineering.py       - 生ファクターの正規化・フィルタ・features テーブルへの保存
  - signal_generator.py          - features と ai_scores を統合して BUY/SELL を生成
- execution/                      - 発注 / 実行関連（package placeholder）
- monitoring/                     - 監視・メトリクス（package placeholder）

設計上のポイント
----------------
- ルックアヘッドバイアス防止: 各計算は target_date 時点で利用可能なデータのみを参照するよう設計。
- 冪等性: DB 保存は ON CONFLICT や日付単位の DELETE→INSERT による置換で冪等化。
- トレーサビリティ: 監査テーブル群により signal→order→execution の一連を追跡可能。
- セキュリティ: ニュース収集では SSRF 防止、XML パーサは defusedxml を使用。

トラブルシューティング & 注意点
------------------------------
- 必須環境変数が未設定の場合、kabusys.config.Settings のプロパティアクセスで ValueError が発生します。
- DuckDB のファイルパスの親ディレクトリがないと自動作成しますが、権限に注意してください。
- J-Quants API のレート制限（120 req/min）を守るため内部でスロットリングが実装されています。大量の並列リクエストは避けてください。
- news_collector の XML / gzip パース失敗やレスポンスサイズ超過はログに記録してスキップします。

貢献
----
バグレポートや提案は issue を立ててください。パッチは PR を歓迎します。

ライセンス
----------
（リポジトリに LICENSE ファイルがあればその内容をここに記載してください）

以上。必要に応じて README に実行スクリプトや CI / デプロイ手順、sample .env.example を追加します。追加を希望する項目があれば教えてください。