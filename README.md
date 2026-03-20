kabusys
=======

日本株向けの自動売買 / データ基盤ライブラリです。データ取得（J-Quants）、ETL、特徴量作成、シグナル生成、ニュース収集、監査ログなどを含むモジュール群を提供します。DuckDB を主要な永続層として利用する設計です。

主な特徴
--------
- J-Quants API クライアント（レート制御・リトライ・トークン自動リフレッシュ）
- DuckDB ベースのスキーマ定義と初期化（冪等）
- ETL パイプライン（差分取得・バックフィル・品質チェック統合）
- ファクター計算（Momentum / Volatility / Value）と Z スコア正規化
- 特徴量の構築（features テーブルへの UPSERT）
- シグナル生成（AI スコア統合・Bear 判定・BUY/SELL 生成・冪等保存）
- RSS ベースのニュース収集（SSRF 対策・追跡パラメータ除去・銘柄抽出）
- 監査ログ（シグナル→発注→約定のトレーサビリティ用テーブル群）
- テストしやすい設計（関数へトークン注入や自動環境読み込みの無効化）

要求事項
--------
- Python >= 3.10（型注釈に「|」構文を使用）
- 必要パッケージ（最低限）
  - duckdb
  - defusedxml
- （任意）J-Quants API 利用時にネットワークアクセス可能な環境

インストール（開発環境）
-----------------------
1. 仮想環境作成（推奨）:
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows

2. 必要ライブラリをインストール:
   pip install duckdb defusedxml

3. パッケージを開発モードでインストール（プロジェクトルートで）:
   pip install -e .

環境変数 / .env
----------------
このプロジェクトは .env（/.env.local）または OS 環境変数から設定を自動読み込みします（プロジェクトルート判定は .git または pyproject.toml）。自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主な環境変数（settings が参照します）
- JQUANTS_REFRESH_TOKEN (必須) : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) : kabuステーション API パスワード
- KABU_API_BASE_URL (任意) : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) : Slack ボットトークン（通知等）
- SLACK_CHANNEL_ID (必須) : Slack チャネル ID
- DUCKDB_PATH (任意) : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) : SQLite（モニタリング用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) : 環境（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL (任意) : ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）

セットアップ手順（初期化）
-------------------------
1. .env を作成し、必要な環境変数をセットします（上記参照）。
2. DuckDB スキーマを初期化します。Python REPL やスクリプトで:

   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")

   これで必要なテーブルとインデックスが作成されます。

基本的な使い方（例）
-------------------

- DuckDB 接続 / スキーマ初期化

  from kabusys.data.schema import init_schema, get_connection
  conn = init_schema("data/kabusys.duckdb")  # 初期化して接続を取得
  # 既存 DB に接続するだけなら:
  # conn = get_connection("data/kabusys.duckdb")

- 日次 ETL 実行（J-Quants からの差分取得・品質チェック含む）

  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)
  print(result.to_dict())

- データ取得（J-Quants クライアント単体利用）

  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  records = fetch_daily_quotes(date_from=..., date_to=...)
  saved = save_daily_quotes(conn, records)

  注意: fetch 系関数は内部でレート制御・リトライ・トークンリフレッシュを行います。

- 特徴量構築

  from kabusys.strategy import build_features
  from datetime import date
  n = build_features(conn, date(2024, 1, 10))
  print(f"features upserted: {n}")

- シグナル生成

  from kabusys.strategy import generate_signals
  from datetime import date
  total = generate_signals(conn, date(2024, 1, 10))
  print(f"signals saved: {total}")

  追加の引数で閾値（threshold）や重み（weights）を変更可能です。

- ニュース収集ジョブ

  from kabusys.data.news_collector import run_news_collection
  # known_codes は銘柄コードの集合（抽出に使う）
  results = run_news_collection(conn, known_codes={"7203", "6758"})
  print(results)

- スキーマ / 監査ログ
  監査用テーブルや execution 層は kabusys.data.audit / schema で定義されています。order_request_id 等を使ってフローのトレーサビリティを確保します。

主要モジュールと概要（ディレクトリ構成）
---------------------------------------

src/kabusys/
- __init__.py
- config.py
  - 環境変数／設定管理（.env 自動ロード、Settings クラス）
- data/
  - __init__.py
  - jquants_client.py   : J-Quants API クライアント（取得・保存ユーティリティ）
  - schema.py           : DuckDB スキーマ定義と初期化ロジック
  - pipeline.py         : ETL パイプライン（差分更新／日次 ETL）
  - stats.py            : 汎用統計ユーティリティ（zscore_normalize など）
  - news_collector.py   : RSS 収集・前処理・保存ロジック（SSRF, size guard 等）
  - calendar_management.py : 市場カレンダー管理（営業日判定、更新ジョブ）
  - features.py         : features 用ユーティリティ（再エクスポート）
  - audit.py            : 監査ログ（signal_events / order_requests / executions）
  - (その他: quality モジュール等はパッケージ内に存在する想定)
- research/
  - __init__.py
  - factor_research.py  : Momentum / Volatility / Value の計算ロジック
  - feature_exploration.py : IC / forward returns / 統計サマリー
- strategy/
  - __init__.py
  - feature_engineering.py : 生ファクターの正規化・features への保存
  - signal_generator.py    : final_score 計算、BUY/SELL シグナル生成
- execution/
  - __init__.py
  - （発注・ブローカー連携の実装はここを想定）
- monitoring/
  - （監視・Slack 通知などを想定）

設計上の注意点 / 動作ポリシー
-----------------------------
- 冪等性: 多くの保存処理（raw_* / features / signals / raw_news 等）は ON CONFLICT を利用して冪等に実行されます。
- ルックアヘッドバイアス対策: 戦略・特徴量・シグナル生成では target_date 時点のデータのみを参照する方針です。
- レート制御: J-Quants API は 120 req/min の制限を想定し、固定間隔のスロットリングで制御します。
- セキュリティ: news_collector は SSRF/XML 攻撃/巨大レスポンス等を考慮した防御を実装しています（defusedxml、ホストチェック、最大バイト数制限など）。
- テスト性: トークン注入や自動 env 読み込み無効化（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）によりユニットテストが容易です。

よくあるコマンド例
------------------
- スキーマ初期化（スクリプト形式）:

  python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"

- 日次 ETL を実行する最小スクリプト例:

  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema('data/kabusys.duckdb')
  res = run_daily_etl(conn, target_date=date.today())
  print(res.to_dict())

Tips / トラブルシューティング
------------------------------
- .env が読み込まれない場合:
  - プロジェクトルートの判定は .git または pyproject.toml を基準に行います。パッケージを展開して使う場合は OS 環境変数で設定するか KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して手動で os.environ を設定してください。
- DuckDB バージョンや Python 環境でエラーが出る場合は Python >=3.10、duckdb の互換性を確認してください。
- J-Quants の 401 が発生してもクライアントは自動でトークンリフレッシュを試みます（但し1回のみ）。refresh トークンが無効な場合は設定を見直してください。

貢献
----
バグ報告・機能提案は Issue へお願いします。コントリビュートする際はテスト・ドキュメントを添えて Pull Request を送ってください。

免責
----
本リポジトリのコードは投資助言を目的とするものではありません。実運用する場合は必ず十分な検証とリスク管理を行ってください。

以上。必要があれば README に CI、テスト実行方法、より詳細な API 使用例（関数ごとの引数説明や戻り値例）を追加します。どの情報を優先して追加しますか？