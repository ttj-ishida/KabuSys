KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株のデータ収集・特徴量生成・シグナル生成・監査（トレーサビリティ）を行うためのライブラリ群です。  
主に DuckDB をローカル DB として利用し、J-Quants API や RSS フィードからのデータ取得、研究用ファクター計算、戦略用特徴量作成、シグナル生成、監査ログ保存までをカバーする設計になっています。

主要な設計方針
- ルックアヘッドバイアス回避（各処理は target_date 時点の情報のみを使用）
- 冪等性（DuckDB への保存は ON CONFLICT / トランザクションで安全に）
- ネットワーク安全性（API レート制限、リトライ、RSS の SSRF 対策 等）
- 本番（live）/ ペーパー（paper_trading）/ 開発（development）を環境で切替可能

主な機能一覧
----------------
- 環境設定管理
  - .env / 環境変数の自動読み込み（プロジェクトルート検出）
  - 必須変数チェック

- データ取得・保存（data/）
  - J-Quants クライアント（株価・財務・カレンダー取得、トークン自動リフレッシュ、リトライ・レート制御）
  - RSS ニュース収集（前処理、ID 生成、SSRF 防御、raw_news 保存、銘柄抽出）
  - DuckDB スキーマ定義・初期化（init_schema）
  - ETL パイプライン（差分取得、バックフィル、品質チェック）
  - 市場カレンダー管理（営業日判定、next/prev/trading days）
  - 監査ログ（signal_events / order_requests / executions 等の監査テーブル）
  - 統計ユーティリティ（Z スコア正規化 等）

- 研究（research/）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン・IC（Information Coefficient）計算、ファクター探索用ユーティリティ

- 戦略（strategy/）
  - 特徴量エンジニアリング（research で生成した raw factor を正規化・合成して features テーブルへ保存）
  - シグナル生成（features + ai_scores を統合して final_score を計算、BUY/SELL シグナルを signals テーブルへ保存）

- 実行層（execution/）と監視（monitoring/）のための骨組み（発展用）

セットアップ手順
----------------

前提
- Python 3.10 以上（`from __future__ import annotations` と型ヒントの union 演算子を利用）
- ネットワーク接続（J-Quants API / RSS）

必須パッケージ（例）
- duckdb
- defusedxml

pip での最低限のインストール例
- 仮想環境を作成・有効化した上で:
  - pip install duckdb defusedxml

環境変数 / .env
- プロジェクトルート（.git や pyproject.toml がある場所）に .env を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
- 主な環境変数（README 用の例）:
  - JQUANTS_REFRESH_TOKEN=xxxxx        # 必須: J-Quants リフレッシュトークン
  - KABU_API_PASSWORD=xxxxx           # 必須: kabuステーション API パスワード（将来の execution 用）
  - SLACK_BOT_TOKEN=xoxb-...          # 必須（監視通知などに使用する場合）
  - SLACK_CHANNEL_ID=C01234567        # 必須（監視通知などに使用する場合）
  - DUCKDB_PATH=data/kabusys.duckdb   # 省略可（デフォルト）
  - SQLITE_PATH=data/monitoring.db    # 省略可（監視用 SQLite）
  - KABUSYS_ENV=development|paper_trading|live
  - LOG_LEVEL=INFO|DEBUG|... 

初期 DB 作成
- DuckDB スキーマを初期化するサンプル:
  - from kabusys.config import settings
    from kabusys.data.schema import init_schema
    conn = init_schema(settings.duckdb_path)
  - 上の呼び出しで必要なテーブル・インデックスが作成されます（冪等）。

使い方（代表的なワークフロー）
------------------------------

1) DuckDB 初期化
- 例:
  - from kabusys.data.schema import init_schema
    conn = init_schema("data/kabusys.duckdb")

2) 日次 ETL（株価・財務・カレンダー取得 + 品質チェック）
- 例:
  - from kabusys.data.pipeline import run_daily_etl
    result = run_daily_etl(conn)  # target_date を指定可能
    print(result.to_dict())

3) 特徴量の作成（features テーブルへの書き込み）
- 例:
  - from kabusys.strategy import build_features
    from datetime import date
    n = build_features(conn, date(2024, 1, 1))
    print(f"features upserted: {n}")

4) シグナル生成（signals テーブルへの書き込み）
- 例:
  - from kabusys.strategy import generate_signals
    from datetime import date
    total = generate_signals(conn, date(2024, 1, 1))
    print(f"signals generated: {total}")

5) ニュース収集ジョブ（RSS 取得・raw_news 保存・銘柄紐付け）
- 例:
  - from kabusys.data.news_collector import run_news_collection
    known_codes = {"7203", "6758", ...}  # 有効な銘柄コードセット
    results = run_news_collection(conn, known_codes=known_codes)
    print(results)

6) J-Quants API を直接利用してデータ取得 → 保存
- fetch/save の組合せ例:
  - from kabusys.data import jquants_client as jq
    records = jq.fetch_daily_quotes(date_from=..., date_to=...)
    saved = jq.save_daily_quotes(conn, records)

注意点・トラブルシューティング
- 環境変数未設定:
  - settings の必須プロパティ（JQUANTS_REFRESH_TOKEN 等）は未設定の場合 ValueError を投げます。 .env.example を参考に .env を準備してください。
- DuckDB ファイルのパス:
  - init_schema は親ディレクトリを自動生成しますが、ファイルのパーミッションに注意してください。
- ネットワーク／API エラー:
  - jquants_client は指定のステータスコードでリトライ、429 の場合は Retry-After を考慮します。トークンの自動リフレッシュも備えていますが、リフレッシュ失敗時のハンドリングを呼び出し側で行ってください。
- RSS 関連:
  - RSS の XML パースに失敗した場合は該当ソースをスキップしてログに警告を出します。SSRF 対策やレスポンスサイズ上限等の安全措置が実装されています。

ディレクトリ構成（主要ファイル）
--------------------------------
以下は src/kabusys 以下の主要ファイルと役割の要約です。

- __init__.py
  - パッケージのバージョンと公開モジュール一覧

- config.py
  - 環境変数/.env 読み込み、Settings クラス（必須変数チェック・環境切替）

- data/
  - jquants_client.py
    - J-Quants API クライアント（取得関数・保存関数・認証）
  - news_collector.py
    - RSS 取得・前処理・raw_news 保存・銘柄抽出・run_news_collection
  - schema.py
    - DuckDB スキーマ定義・init_schema / get_connection
  - stats.py
    - zscore_normalize 等の統計ユーティリティ
  - pipeline.py
    - ETL（run_prices_etl / run_financials_etl / run_calendar_etl / run_daily_etl）
  - features.py
    - data.stats の再エクスポート
  - calendar_management.py
    - market_calendar 更新・営業日判定・next/prev_trading_day 等
  - audit.py
    - 監査ログ用 DDL（signal_events / order_requests / executions 等）

- research/
  - factor_research.py
    - モメンタム / ボラティリティ / バリュー 等のファクター計算
  - feature_exploration.py
    - 将来リターン計算・IC 計算・統計サマリーなど
  - __init__.py
    - 研究用ユーティリティの再エクスポート

- strategy/
  - feature_engineering.py
    - raw ファクターを統合・正規化し features テーブルへ UPSERT
  - signal_generator.py
    - features と ai_scores を統合して final_score を算出し signals を作成
  - __init__.py
    - build_features / generate_signals の公開

- execution/
  - __init__.py
    - 将来的な発注・ブローカ連携ロジック用の場所（現在は骨組み）

- research/*, data/* の各モジュールは DuckDB 接続（duckdb.DuckDBPyConnection）を受け取り SQL を直接実行する設計です。

拡張 / 開発のヒント
- execution 層や監視（monitoring）を追加して、kabuステーション API との実際の発注処理や Slack 通知等を連携できます。
- strategy の重みや閾値は generate_signals の引数で上書き可能です。テスト時には KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env の自動読み込みを無効化してください。
- DuckDB はファイルベースでも in-memory（":memory:"）でも動作するため、ユニットテストや CI では in-memory を使うと便利です。

ライセンス・貢献
----------------
（本 README ではコードベースのライセンス情報を含めていません。リポジトリの LICENSE ファイルを参照してください。）

最後に
-------
この README はコードベースの概要・主要な使い方を短くまとめたものです。詳細な仕様（StrategyModel.md / DataPlatform.md / Research ドキュメント等）がプロジェクト内にある想定のため、アルゴリズムの仕様や DDL の詳細はそちらを参照してください。必要であれば、README に含めるサンプルスクリプトや運用手順（cron / systemd ジョブ例）も追加します。どの情報を拡張したいか教えてください。