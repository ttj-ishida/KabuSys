KabuSys
=======

日本株を対象としたリサーチ / データプラットフォーム兼自動売買基盤のライブラリ群です。  
DuckDB をデータ層に採用し、J-Quants API や RSS を取り込む ETL、ファクター計算、特徴量生成、シグナル生成、ニュース収集、監査ログなどの主要機能を備えています。

主な特徴
-------
- DuckDB ベースの三層データモデル（Raw / Processed / Feature）と実行層（Execution / Audit）
- J-Quants API クライアント（レート制御・リトライ・トークン自動更新対応）
- ETL パイプライン（差分取得、バックフィル、品質チェックと統合）
- ファクター計算（momentum / volatility / value 等）
- 特徴量生成（Z スコア正規化、ユニバースフィルタ、日付単位の冪等アップサート）
- シグナル生成（複数コンポーネントの重み付け合算、Bear レジームフィルタ、エグジット判定）
- RSS ニュース収集（URL 正規化、SSRF対策、XML の安全パース、記事→銘柄紐付け）
- 監査ログ（signal → order_request → execution のトレーサビリティ）

動作環境（推奨）
---------------
- Python 3.10 以上（型ヒントに | を使用）
- 必要主要パッケージ:
  - duckdb
  - defusedxml
- 推奨: 仮想環境（venv、virtualenv、conda など）

インストール（例）
-----------------
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows は .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb defusedxml

3. （任意）開発インストール
   - pip install -e .

環境変数 / 設定
---------------
kabusys は .env ファイル（プロジェクトルート）または環境変数から設定を読み込みます（自動ロードはデフォルトで有効）。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主要な環境変数（Settings から参照されるキー）
- JQUANTS_REFRESH_TOKEN  : J-Quants の refresh token（必須）
- KABU_API_PASSWORD      : kabu ステーション API のパスワード（必須）
- KABU_API_BASE_URL      : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN        : Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID       : Slack 通知対象チャンネル（必須）
- DUCKDB_PATH            : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            : 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV            : 実行環境（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL              : ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）

例: .env（プロジェクトルート）
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- KABU_API_PASSWORD=your_kabu_password
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C01234567
- DUCKDB_PATH=data/kabusys.duckdb
- KABUSYS_ENV=development
（.env は機密情報なのでソース管理に含めないでください）

セットアップ手順（簡易）
---------------------
1. 仮想環境と依存のインストール（上記参照）
2. .env を作成して必要なシークレット・設定を配置
3. DuckDB スキーマを初期化

サンプル: DuckDB スキーマ初期化
- Python REPL / スクリプト例:
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  conn = init_schema(settings.duckdb_path)

主な使い方（コード例）
---------------------

1) 日次 ETL（株価・財務・市場カレンダー + 品質チェック）
- run_daily_etl を使うと、カレンダー → 株価 → 財務 → 品質チェックの順に差分 ETL を行います。

  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)
  print(result.to_dict())

2) 特徴量の構築（features テーブルへの書き込み）
- build_features は research で計算した raw ファクターをマージ、フィルタ、正規化して features テーブルへ UPSERT します。

  from datetime import date
  from kabusys.strategy import build_features
  build_features(conn, date(2024, 1, 5))

3) シグナル生成（signals テーブルへの書き込み）
- generate_signals は features と ai_scores を組み合わせ、BUY/SELL シグナルを signals テーブルへ書き込みます。

  from kabusys.strategy import generate_signals
  generate_signals(conn, date(2024, 1, 5), threshold=0.6)

4) ニュース収集ジョブ
- RSS フィードを取得して raw_news / news_symbols に保存します。

  from kabusys.data.news_collector import run_news_collection
  known_codes = {"7203", "6758", ...}  # 検出対象の有効銘柄コードセット
  run_news_collection(conn, known_codes=known_codes)

5) J-Quants 直接呼び出し（データ取得・保存）
- fetch_daily_quotes / save_daily_quotes などを組み合わせて使えます（jquants_client）。

  from kabusys.data import jquants_client as jq
  recs = jq.fetch_daily_quotes(date_from=..., date_to=...)
  saved = jq.save_daily_quotes(conn, recs)

注意点 / 運用上のポイント
------------------------
- トークンやパスワードは環境変数で管理し、リポジトリにコミットしないこと。
- DuckDB ファイルの保存先ディレクトリは init_schema が自動作成しますが、バックアップやパーミッション管理を行ってください。
- J-Quants API のレート制限（120 req/min）に従っていますが、大量の同時ジョブを走らせると制限に達するため調整が必要です。
- ニュース収集は SSRF 対策や応答サイズ制限、XML の安全パース等を実装していますが、外部フィードが多様な場合は例外処理を追加してください。
- 本ライブラリには実際の注文送信（ブローカー接続）層は含まれますが、実運用時は必ず paper_trading 環境やリスク管理の上で検証してください（KABUSYS_ENV=live を切り替えることで実口座判定に使用されます）。

ディレクトリ構成（主要ファイル）
-------------------------------

src/kabusys/
- __init__.py                (パッケージメタ情報)
- config.py                  (環境変数 / Settings)
- data/
  - __init__.py
  - jquants_client.py        (J-Quants API クライアント、取得・保存ユーティリティ)
  - news_collector.py       (RSS ニュース取得・保存、銘柄抽出)
  - schema.py               (DuckDB スキーマ定義・初期化)
  - pipeline.py             (ETL パイプライン・ジョブ)
  - stats.py                (Z スコア正規化等の統計ユーティリティ)
  - features.py             (data.stats の再エクスポート)
  - calendar_management.py  (market_calendar 管理・営業日判定)
  - audit.py                (監査ログ DDL)
- research/
  - __init__.py
  - factor_research.py      (momentum / volatility / value ファクター計算)
  - feature_exploration.py  (将来リターン・IC 計算・統計サマリー)
- strategy/
  - __init__.py
  - feature_engineering.py  (features テーブル構築)
  - signal_generator.py     (final_score 計算と signals 書き込み)
- execution/
  - __init__.py             (発注層のエントリポイント（将来実装）)
- monitoring/                (パッケージ指数に含まれるがコードは別途)

開発に関する補足
----------------
- 型・ロギングが充実しているため、ローカルでの単体実行・デバッグが容易です。
- テスト用に KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して .env の自動読み込みを抑制できます。
- jquants_client の _request は urllib を使った実装のため、ユニットテストではネットワーク呼び出しをモックしてください。
- news_collector._urlopen や jquants_client._request などは外部依存を差し替えやすく設計されています（テスト用にモック可能）。

ライセンス・貢献
----------------
- リポジトリに LICENSE が含まれている想定です。貢献やバグ報告はプルリクエスト / Issue を通じてお願いします。

問い合わせ
--------
具体的な使い方や拡張の相談があれば、どの機能（ETL / feature / signal / news 等）について知りたいかを教えてください。簡単な実行例や追加のコマンド例を用意します。