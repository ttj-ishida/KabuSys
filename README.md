KabuSys — 日本株自動売買プラットフォーム（README）
======================================

概要
----
KabuSys は日本株向けのデータプラットフォームと研究／戦略基盤のための Python ライブラリ群です。  
主に以下を目的としています。

- J-Quants API からのデータ取得（株価日足、財務データ、マーケットカレンダー）
- DuckDB を用いたデータの永続化（Raw / Processed / Feature / Execution 層）
- データ品質チェックと ETL パイプライン
- RSS ベースのニュース収集と銘柄紐付け
- 戦略向けのファクター計算・特徴量探索（モメンタム、バリュー、ボラティリティ 等）
- 発注・監査用スキーマ（監査ログ・トレーサビリティ）

このリポジトリはライブラリ形式で提供され、モジュール単位で ETL/収集/研究処理を呼び出して利用します。

主な機能
--------
- data/
  - jquants_client: J-Quants API クライアント（認証、ページネーション、レート制御、保存ユーティリティ）
  - schema: DuckDB のスキーマ定義と初期化（Raw, Processed, Feature, Execution 層）
  - pipeline: 日次差分 ETL（calendar, prices, financials）と品質チェック統合
  - news_collector: RSS フィード収集・前処理・DB 保存・銘柄抽出（SSRF対策・gzip上限等を実装）
  - quality: 欠損・スパイク・重複・日付不整合の品質チェック
  - calendar_management: JPX カレンダー管理・営業日ユーティリティ
  - audit: 発注〜約定の監査テーブル定義と初期化
  - stats / features: Zスコア正規化などの統計ユーティリティ
- research/
  - factor_research: モメンタム・ボラティリティ・バリュー等のファクター計算
  - feature_exploration: 将来リターン算出、IC（Spearman）計算、統計サマリー
- config: 環境変数読み込み・設定管理（.env, .env.local 自動ロード、必須設定の検証）
- monitoring / execution / strategy: パッケージ構成用プレースホルダ（実装拡張用）

セットアップ（開発環境）
----------------------
前提:
- Python 3.10+（型ヒントのユニオン表記等を使用）
- DuckDB を利用するため duckdb パッケージ等が必要

例: 仮想環境を作成して依存パッケージをインストールする手順（requirements.txt がある場合は置き換えてください）。

1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（例）
   - pip install duckdb defusedxml

   ※ 実際のプロジェクトでは requirements.txt / pyproject.toml を用意してください。

3. パッケージを editable インストール（開発時）
   - pip install -e .

環境変数（必須 / 推奨）
---------------------
config.Settings が参照する主な環境変数:

必須:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（get_id_token に使用）
- SLACK_BOT_TOKEN       : Slack 通知等に使用する Bot トークン（実装箇所がある場合）
- SLACK_CHANNEL_ID      : Slack チャンネル ID

（kabu ステーション連携などがある場合）
- KABU_API_PASSWORD     : kabu API のパスワード

オプション・デフォルト:
- KABUSYS_ENV           : development / paper_trading / live（デフォルト development）
- LOG_LEVEL             : DEBUG/INFO/...（デフォルト INFO）
- DUCKDB_PATH           : DuckDB のファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH           : 監視 DB などに使用（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 をセットすると .env 自動ロードを無効化

.env 自動ロードについて:
- プロジェクトルート（.git または pyproject.toml のある親ディレクトリ）を探索し、.env → .env.local の順で読み込みます。
- .env.local は .env の上書き（override）を行います。
- OS 環境変数は保護され、.env で上書きされません（ただし override=True の場合 protected を考慮）。

使い方（主要な呼び出し例）
------------------------

1) DuckDB スキーマ初期化
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")

   - ":memory:" を渡すとインメモリ DB として初期化されます。
   - すでにテーブルが存在する場合はスキップ（冪等）。

2) 日次 ETL 実行（市場カレンダー→株価→財務→品質チェック）
   from kabusys.data.pipeline import run_daily_etl
   result = run_daily_etl(conn)
   # result は ETLResult オブジェクト。to_dict() で内容確認ができます。

   run_daily_etl は内部で J-Quants API と通信します（settings.jquants_refresh_token が必要）。

3) RSS ニュース収集と銘柄紐付け
   from kabusys.data.news_collector import run_news_collection
   results = run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
   # results は {source_name: 保存件数} の辞書を返します。

4) ファクター計算 / 研究ユーティリティ
   from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
   from datetime import date
   momentum_records = calc_momentum(conn, date(2024, 1, 31))
   volatility_records = calc_volatility(conn, date(2024, 1, 31))
   value_records = calc_value(conn, date(2024, 1, 31))

   # 将来リターンを計算（翌日・週・月）
   fwd = calc_forward_returns(conn, date(2024, 1, 31), horizons=[1,5,21])

   # IC（Spearman）計算例
   ic = calc_ic(factor_records=momentum_records, forward_records=fwd, factor_col="mom_1m", return_col="fwd_1d")

5) Zスコア正規化（クロスセクション）
   from kabusys.data.stats import zscore_normalize
   normalized = zscore_normalize(momentum_records, ["mom_1m", "ma200_dev"])

ログ・挙動
---------
- config.Settings.log_level によりログレベルを制御します（環境変数 LOG_LEVEL）。
- jquants_client は API のレート制限（120 req/min）を内部で制御し、リトライ（指数バックオフ）や 401 の自動リフレッシュを行います。
- news_collector は SSRF 対策、gzip サイズ制限、XML パースのセーフ機能（defusedxml）を備えています。
- ETL は各ステップで独立してエラーハンドリングする設計で、品質チェックは Fail-Fast にはしていません（呼び出し元で判断可能）。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                # 環境変数読み込み・設定
- data/
  - __init__.py
  - jquants_client.py      # J-Quants API クライアント + 保存ユーティリティ
  - news_collector.py      # RSS収集・保存・銘柄抽出
  - schema.py              # DuckDB スキーマ定義と init_schema
  - pipeline.py            # ETL パイプライン（run_daily_etl など）
  - features.py            # 特徴量ユーティリティ公開（zscore）
  - stats.py               # 統計ユーティリティ（zscore_normalize）
  - calendar_management.py # JPX カレンダー管理
  - audit.py               # 監査ログスキーマと初期化
  - etl.py                 # ETL オブジェクトの公開
  - quality.py             # データ品質チェック
- research/
  - __init__.py
  - factor_research.py     # モメンタム/バリュー/ボラティリティ算出
  - feature_exploration.py # 将来リターン・IC・サマリー
- strategy/                 # 戦略層（拡張ポイント）
- execution/                # 発注実装（拡張ポイント）
- monitoring/               # 監視周り（拡張ポイント）

補足・開発メモ
--------------
- DuckDB のバージョンによっては制約や index の挙動が異なる場合があります（README 内スキーマコメント参照）。運用環境での動作確認を行ってください。
- NewsCollector はデフォルトで Yahoo Finance のニュースフィードを参照する設定があります（DEFAULT_RSS_SOURCES）。
- config モジュールはプロジェクトルートの .env/.env.local を自動で読み込みます。ユニットテスト等で自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 本コードベースは「データ取得・保存・解析」層を中心に実装されています。実際の売買（ブローカー連携）や戦略運用ロジックは strategy / execution で拡張してください。

ライセンス
---------
（必要に応じてここにライセンス情報を記載してください）

お問い合わせ / 参照
-----------------
- モジュール API や関数の詳細は各ファイル内の docstring を参照してください。
- 実運用では secrets 管理・ログ管理・監視・取り消し機構（ロールバック）を必ず組み込んでください。

以上。必要であれば「サンプルスクリプト」「docker-compose」や「CI 用コマンド」「requirements.txt の候補」など具体的な導入手順を追記します。どの情報を優先して追加しますか？