KabuSys — 日本株自動売買基盤（README）
=================================

概要
---
KabuSys は日本株向けのデータプラットフォームと戦略層を備えた自動売買フレームワークです。  
主な目的は以下です。

- J-Quants API からの市場データ（株価・財務・マーケットカレンダー）収集と DuckDB への蓄積
- ニュース（RSS）収集と記事と銘柄の紐付け
- 研究（research）モジュールによるファクター計算・探索
- 戦略（strategy）モジュールでの特徴量生成・シグナル作成
- 発注・実行（execution）・監査（audit）テーブル設計（DBレイヤ）
- ETL パイプライン（差分更新・品質チェック）の提供

プロジェクトはモジュール化されており、データ層（data）、研究層（research）、戦略層（strategy）、実行／監視層（execution / monitoring）で役割が分かれています。

主な機能一覧
-------------
- 環境設定管理（kabusys.config）
  - .env / .env.local を自動読み込み（プロジェクトルート検出）
  - 必須環境変数の抽象化（例: JQUANTS_REFRESH_TOKEN, SLACK_* 等）
  - 実行環境（development / paper_trading / live）とログレベル検証

- データ収集（kabusys.data.jquants_client）
  - J-Quants API クライアント（ページネーション・レート制限・リトライ・トークン自動リフレッシュ）
  - 日足・財務・カレンダー取得＋DuckDB への冪等保存関数

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得（SSRF対策、gzip上限、XML hardening）
  - テキスト前処理、URL 正規化、記事ID生成（SHA-256）、raw_news 保存、銘柄抽出と紐付け

- スキーマ管理（kabusys.data.schema）
  - DuckDB のテーブル定義（Raw / Processed / Feature / Execution 層）
  - 初期化関数 init_schema(db_path)

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（最終保存日からの差分算出 + バックフィル）
  - run_daily_etl で日次 ETL（カレンダー→株価→財務→品質チェック）

- 研究（kabusys.research）
  - ファクター計算（mom/vol/value 等）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ
  - z-score 正規化ユーティリティ

- 特徴量・シグナル生成（kabusys.strategy）
  - build_features: 生ファクターをマージしてユニバースフィルタ→Zスコア正規化→features テーブルへ保存（冪等）
  - generate_signals: features + ai_scores を統合して final_score を算出、BUY/SELL シグナルを signals テーブルへ保存（冪等）
  - Bear レジーム抑制、エグジット（ストップロス等）判定搭載

- 監査（kabusys.data.audit）
  - シグナル→order_request→実行のトレーサビリティを残す監査テーブル（UUID・冪等性を重視）

セットアップ手順
----------------

前提
- Python 3.10 以上（型注釈で | 演算子等を使用）
- Git
- ネットワークアクセス（J-Quants / RSS 取得）

1. リポジトリをクローン
   - git clone <repository-url>
   - cd <repository>

2. 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

4. 環境変数 / .env の準備
   - プロジェクトルートに .env を配置すると自動読み込みされます（.env.local は上書き）。
   - 自動ロードを無効にする: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

   推奨の .env（例）
   - JQUANTS_REFRESH_TOKEN=あなたの_jquants_refresh_token_
   - KABU_API_PASSWORD=あなたの_kabu_api_password_
   - SLACK_BOT_TOKEN=あなたの_slack_bot_token_
   - SLACK_CHANNEL_ID=channel_id
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - KABUSYS_ENV=development
   - LOG_LEVEL=INFO

   注意: Settings クラスは必須環境変数が未設定だと ValueError を投げます（例: JQUANTS_REFRESH_TOKEN 等）。

5. データベース初期化
   - Python REPL / スクリプト内で:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

使い方（主要な操作の例）
-----------------------

- DuckDB スキーマ初期化
  - from kabusys.data.schema import init_schema
    conn = init_schema("data/kabusys.duckdb")

- 日次 ETL 実行（J-Quants から差分取得・保存・品質チェック）
  - from kabusys.data.pipeline import run_daily_etl
    result = run_daily_etl(conn)  # target_date を指定可能
    print(result.to_dict())

- 特徴量ビルド
  - from kabusys.strategy import build_features
    from datetime import date
    n = build_features(conn, date(2024, 1, 12))
    print(f"features upserted: {n}")

- シグナル生成
  - from kabusys.strategy import generate_signals
    from datetime import date
    total = generate_signals(conn, date(2024, 1, 12))
    print(f"signals generated: {total}")

- ニュース収集（RSS）
  - from kabusys.data.news_collector import run_news_collection
    results = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
    print(results)

- J-Quants の個別取得（テスト用）
  - from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
    token = get_id_token()
    rows = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))

実装上のポイント（短く）
-----------------------
- .env 自動読み込みはプロジェクトルート（.git / pyproject.toml）基準で行われます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を指定して無効化可能。
- J-Quants クライアントは 120 req/min のレート制限、最大3回の指数バックオフリトライ、401 時のトークン自動リフレッシュを備えています。
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE / DO NOTHING）を意識して設計されています。
- RSS 収集では SSRF・XML Bomb・過大レスポンス等の防御処理を実装しています。

ディレクトリ構成
-----------------
（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                        # 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py              # J-Quants API client + save_* funcs
      - news_collector.py              # RSS 収集・前処理・保存
      - schema.py                      # DuckDB スキーマ定義・init_schema
      - stats.py                       # zscore_normalize 等
      - pipeline.py                    # ETL パイプライン（run_daily_etl 等）
      - calendar_management.py         # market_calendar 管理・営業日判定
      - audit.py                       # 監査ログ DDL（signal_events, order_requests, executions）
      - features.py                    # data 層の features 再エクスポート
    - research/
      - __init__.py
      - factor_research.py             # mom/vol/value 等のファクター計算
      - feature_exploration.py         # forward returns / IC / summary
    - strategy/
      - __init__.py
      - feature_engineering.py         # build_features
      - signal_generator.py            # generate_signals
    - execution/                        # 実行関連モジュール（placeholder）
    - monitoring/                       # 監視（placeholder: __all__ に含む）

補足・注意点
------------
- 本 README はコードベースの主要 API と運用上の手順をまとめたものです。実運用の前に設定値（特に認証トークン・パス）と DuckDB のバックアップ方針を十分に確認してください。
- セキュリティ: .env にトークン等の秘密情報を平文で置く場合はアクセス権限に注意してください。CI/CD や運用ではシークレット管理ツールの利用を推奨します。
- 本パッケージをサービス化する際は、ETL・カレンダー更新・ニュース収集・戦略実行などをそれぞれ定期ジョブ（cron / scheduler）で運用することを想定しています。

必要ならば README に含めるサンプルスクリプト（起動用 CLI ラッパー例）や .env.example のテンプレート、さらなる運用手順（Dockerfile / systemd ユニットの例）を追加します。どの内容を追加しましょうか？