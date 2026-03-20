KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けのデータプラットフォームと戦略層を備えた自動売買基盤です。  
主に以下を提供します：

- J-Quants API からの株価・財務・カレンダー取得と DuckDB での永続化（差分ETL、再取得ロジック含む）
- ニュース（RSS）収集と記事→銘柄紐付け
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）
- 特徴量正規化（Zスコア）・戦略シグナル生成（BUY/SELL）
- 発注・約定・ポジション管理用のスキーマ（監査ログ含む）
- 自動環境変数ロード・設定管理

特徴（機能一覧）
----------------
- データ取得
  - J-Quants API クライアント（ページネーション・レート制限・トークン自動リフレッシュ・リトライ）
  - 日足（OHLCV）、財務データ、JPX マーケットカレンダーの差分ETL
- データ基盤
  - DuckDB を用いた階層的スキーマ（raw / processed / feature / execution）
  - 冪等性を考慮した保存（ON CONFLICT / INSERT ... RETURNING 等）
- ニュース収集
  - RSS フィード取得（SSRF対策、gzip制限、XML安全パース）
  - 記事IDの正規化（URL 正規化 → SHA-256 ハッシュ）
  - 記事と銘柄の紐付け（テキストから4桁銘柄コード抽出）
- 研究・特徴量
  - モメンタム / ボラティリティ / バリューの計算モジュール（prices_daily / raw_financials を参照）
  - クロスセクション Z スコア正規化ユーティリティ
  - 特徴量を features テーブルへ UPSERT（冪等）
- 戦略
  - features と ai_scores を統合して final_score を算出
  - Bear レジーム判定、BUY/SELL シグナル生成（閾値・重み調整可能）
  - SELL 判定（ストップロスなどのエグジット条件の実装）
- 運用
  - マーケットカレンダー管理関数（営業日判定、next/prev/trading days）
  - ETL の結果オブジェクト（品質チェックの結果を含む）
  - 監査ログ用スキーマ（signal_events / order_requests / executions 等）

前提（依存）
------------
- Python 3.9+
- duckdb
- defusedxml
- （標準ライブラリで多くを実装していますが、実行環境に応じて追加のライブラリが必要になることがあります）

セットアップ手順
----------------

1. リポジトリをクローンし、開発用にインストール（editable 推奨）
   $ git clone <リポジトリ>
   $ cd <リポジトリ>
   $ python -m venv .venv
   $ source .venv/bin/activate
   $ pip install -e .[dev]   # setup.cfg/pyproject に extras が定義されている場合

   必要な最低パッケージ例：
   $ pip install duckdb defusedxml

2. 環境変数の準備
   プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（自動ロードはデフォルトで有効）。
   主要な環境変数：
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーションAPIパスワード（必須）
   - KABU_API_BASE_URL: kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack 通知用トークン（必須）
   - SLACK_CHANNEL_ID: Slack 通知先チャンネルID（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG/INFO/...（デフォルト: INFO）

   テストで自動 .env ロードを無効化する場合：
   $ export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

3. データベース初期化
   DuckDB のスキーマを作成します（デフォルトパスは settings.duckdb_path）。
   例（対話的に）:
   $ python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"

   または Python スクリプト内で：
   from kabusys.data.schema import init_schema
   conn = init_schema('data/kabusys.duckdb')

使い方（主要な操作例）
--------------------

- 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）：
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema('data/kabusys.duckdb')
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- 特徴量作成（features テーブルへ書き込み）：
  from datetime import date
  from kabusys.strategy import build_features
  conn = init_schema('data/kabusys.duckdb')
  n = build_features(conn, target_date=date(2025, 1, 10))
  print(f"upserted features: {n}")

- シグナル生成（signals テーブルへ書き込み）：
  from datetime import date
  from kabusys.strategy import generate_signals
  conn = init_schema('data/kabusys.duckdb')
  total = generate_signals(conn, target_date=date(2025, 1, 10))
  print(f"generated signals: {total}")

- ニュース収集ジョブ（RSS → raw_news, news_symbols）：
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  conn = init_schema('data/kabusys.duckdb')
  # known_codes は銘柄コード集合（例えば prices_daily から取得）
  known_codes = {"7203", "6758", "9984"}  # 例
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)

- J-Quants からの生データ取得（低レベル API）：
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  token = get_id_token()
  records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))

注意点 / 運用ヒント
-------------------
- 環境（KABUSYS_ENV）は development / paper_trading / live のいずれかに設定してください。live 実行時は特に caution。
- ETL は差分更新を行いますが、バックフィル日数（デフォルト 3 日）を使って API の後出し修正を取り込みます。設定は run_daily_etl の引数で調整可能です。
- ニュース収集では外部への HTTP アクセスが行われるためネットワーク・SSRF 対策が組み込まれていますが、運用環境ではプロキシやファイアウォール設定に注意してください。
- DuckDB ファイルはファイルロック等の共有アクセスに制約があるため、複数プロセスで同時に書き込む際は設計上の配慮が必要です。

ディレクトリ構成（概観）
-----------------------
src/kabusys/
- __init__.py
- config.py
  - 環境変数読み込み・settings オブジェクト（自動 .env ロード、必須 env チェック）
- data/
  - __init__.py
  - jquants_client.py       : J-Quants API クライアント（取得・保存用ユーティリティ）
  - schema.py               : DuckDB スキーマ定義 & init_schema / get_connection
  - pipeline.py             : ETL パイプライン（差分取得・品質チェック）
  - news_collector.py       : RSS 取得・前処理・DB保存・銘柄抽出
  - calendar_management.py  : マーケットカレンダー管理（営業日判定/next/prev/get_trading_days）
  - features.py             : features 用ユーティリティ（zscore re-export）
  - stats.py                : Zスコア正規化などの統計ユーティリティ
  - audit.py                : 監査ログ（signal_events / order_requests / executions 等）
  - pipeline & 他モジュール：品質チェック関連（quality モジュールは省略されているが pipeline が参照）
- research/
  - __init__.py
  - factor_research.py      : momentum / volatility / value のファクター計算
  - feature_exploration.py  : 将来リターン計算, IC（Spearman）計算, 統計サマリー
- strategy/
  - __init__.py
  - feature_engineering.py  : 生ファクターを正規化して features へ保存
  - signal_generator.py     : features + ai_scores を統合して signals を生成
- execution/
  - __init__.py
  - （発注／broker連携の実装を置く想定）
- monitoring/
  - （運用監視・Slack 通知等を置く想定）

開発・拡張
----------
- strategy 層は発注層（execution）に依存しない設計です。execution 層実装時は signals テーブルを参照して発注処理を行うことが想定されています。
- research の関数は DuckDB 接続を受け取り prices_daily 等を読み込む純粋関数群なので、バックテストや検証に再利用できます。
- 単体テストを実装する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を使って環境に依存しないテストを作成できます。DuckDB の ":memory:" 接続を使うと高速にテストできます。

ライセンス / コントリビュート
----------------------------
（ここにライセンス情報や貢献ルールを追記してください）

サポート / 問い合わせ
---------------------
不具合や質問はリポジトリの Issues に報告してください。README の追記やドキュメント整備の PR も歓迎します。

以上。README の追加項目（例：CI設定、詳細な運用手順、Slack 通知設定、Kabu API 実装方法等）が必要であれば教えてください。