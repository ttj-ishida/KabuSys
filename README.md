KabuSys
======

KabuSys は日本株向けの自動売買・データプラットフォーム用ライブラリです。
DuckDB を用いたデータレイヤ、J-Quants からのデータ取得、ニュース収集、特徴量エンジニアリング、
戦略シグナル生成、監査・実行レイヤ用のスキーマ/ユーティリティを提供します。

概要
----
- 日本株（J-Quants）をデータソースとし、データ取得（ETL）→ 前処理 → 特徴量作成 → シグナル生成
  → 発注/監査ログ までを想定したモジュール群。
- DuckDB を中心に「Raw / Processed / Feature / Execution」の多層スキーマを提供。
- ルックアヘッドバイアス対策や冪等性（ON CONFLICT / トランザクション）を念頭に設計。
- RSS ベースのニュース収集（SSRF 対策、トラッキングパラメータ除去）機能あり。
- J-Quants API クライアントはレートリミット・リトライ・トークン自動更新を実装。

主な機能
--------
- データ取得（J-Quants）
  - 株価日足、財務データ、JPX マーケットカレンダー取得＆保存（fetch / save 関数）
  - Rate limit とリトライロジック、トークンリフレッシュ対応
- DuckDB スキーマ管理
  - init_schema() によるテーブル作成（Raw / Processed / Feature / Execution）
- ETL パイプライン
  - 日次 ETL（run_daily_etl）：カレンダー・株価・財務の差分取得、品質チェック
- 特徴量・戦略
  - research モジュール: momentum / volatility / value 等のファクター計算
  - strategy.feature_engineering.build_features: Z スコア正規化・ユニバースフィルタ・features への保存
  - strategy.signal_generator.generate_signals: final_score 計算、BUY/SELL シグナル生成、signals へ保存
- ニュース収集
  - RSS フィード取得、記事前処理、raw_news 保存、銘柄コード抽出と紐付け
- カレンダー管理
  - 営業日判定・次営業日/前営業日・カレンダー更新ジョブ
- 監査ログ（audit）
  - シグナル→発注→約定を連鎖でトレースする監査テーブル定義

セットアップ（開発環境の例）
--------------------------
前提
- Python 3.10+（型ヒントで | を使用）
- duckdb, defusedxml などが必要（下記は最低限の例）

推奨手順（プロジェクトルートで実行）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（最低例）
   - pip install duckdb defusedxml

   ※プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください。

3. 環境変数（.env）を準備
   - プロジェクトルートに .env（または .env.local）を置くと自動読み込みされます（デフォルト）。
   - 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

例: .env（最低限）
    JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
    KABU_API_PASSWORD=your_kabu_api_password
    SLACK_BOT_TOKEN=xoxb-...
    SLACK_CHANNEL_ID=C01234567
    KABUSYS_ENV=development
    LOG_LEVEL=INFO

主要な環境変数（必須）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（Settings.jquants_refresh_token）
- KABU_API_PASSWORD: kabu API 用パスワード
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
- KABUSYS_ENV: development / paper_trading / live のいずれか
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL
- DUCKDB_PATH: デフォルト data/kabusys.duckdb（省略可）
- SQLITE_PATH: 監視 DB のパス（省略可）

使い方（簡易例）
----------------

1) DuckDB スキーマ初期化
    from kabusys.data.schema import init_schema
    conn = init_schema("data/kabusys.duckdb")

    - ":memory:" を渡すとインメモリ DB を使えます。

2) 日次 ETL（J-Quants からの差分取得）
    from kabusys.data.pipeline import run_daily_etl
    result = run_daily_etl(conn)  # target_date を指定しなければ今日

    - ETLResult オブジェクトが返る。result.to_dict() で内容を確認。
    - run_calendar_etl / run_prices_etl / run_financials_etl を個別に呼べます。

3) 特徴量作成（features テーブルの作成）
    from datetime import date
    from kabusys.strategy import build_features
    count = build_features(conn, target_date=date(2025, 1, 15))

    - DuckDB の prices_daily / raw_financials 等を参照して features を作成します。

4) シグナル生成
    from kabusys.strategy import generate_signals
    total_signals = generate_signals(conn, target_date=date(2025, 1, 15))

    - threshold や weights を引数に与えて挙動を変更可能。
    - ai_scores / positions テーブルを参照して Bear レジーム判定やエグジット判定を行います。

5) ニュース収集（RSS）
    from kabusys.data.news_collector import run_news_collection
    results = run_news_collection(conn, sources=None, known_codes={"7203","6758"})

    - デフォルトの RSS ソースは DEFAULT_RSS_SOURCES（Yahoo 等）。
    - save_raw_news / save_news_symbols は冪等で保存します。

6) カレンダー更新ジョブ
    from kabusys.data.calendar_management import calendar_update_job
    saved = calendar_update_job(conn)

コア API（抜粋）
----------------
- kabusys.config.settings: 環境変数アクセス（settings.jquants_refresh_token など）
- kabusys.data.schema.init_schema(db_path)
- kabusys.data.pipeline.run_daily_etl(...)
- kabusys.data.jquants_client.fetch_daily_quotes / save_daily_quotes / get_id_token
- kabusys.data.news_collector.fetch_rss / save_raw_news / run_news_collection
- kabusys.research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic
- kabusys.strategy.build_features / generate_signals

自動 .env 読み込みについて
--------------------------
- モジュール起動時にプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し、
  .env → .env.local の順で読み込みます（OS 環境変数が優先）。
- 自動ロードを無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（抜粋）
-----------------------
以下は主要ファイル／モジュールのツリー（src/kabusys 配下の主要ファイルを抜粋）。

src/
└─ kabusys/
   ├─ __init__.py
   ├─ config.py
   ├─ data/
   │  ├─ __init__.py
   │  ├─ jquants_client.py
   │  ├─ news_collector.py
   │  ├─ schema.py
   │  ├─ stats.py
   │  ├─ pipeline.py
   │  ├─ features.py
   │  ├─ calendar_management.py
   │  └─ audit.py
   ├─ research/
   │  ├─ __init__.py
   │  ├─ factor_research.py
   │  └─ feature_exploration.py
   ├─ strategy/
   │  ├─ __init__.py
   │  ├─ feature_engineering.py
   │  └─ signal_generator.py
   ├─ execution/
   │  └─ __init__.py
   └─ monitoring/   (パッケージ公開用に __all__ に含むが実体はプロジェクト内に追加される想定)

ドキュメント参照
---------------
ソース内には StrategyModel.md / DataPlatform.md / DataSchema.md 等の仕様に基づく
設計コメントが多く含まれています。実装を理解する際は該当ドキュメント（リポジトリ内）も参照してください。

開発・運用上の注意
------------------
- DuckDB のトランザクション（BEGIN/COMMIT/ROLLBACK）を多用しているため、例外時のロールバック処理に注意してください。
- J-Quants API はレート制限が厳しいため、過度な並列リクエストは避けてください（ライブラリ内で 120 req/min を想定）。
- features/signal 生成は target_date 時点のデータのみを参照するよう設計されており、ルックアヘッドバイアスに配慮しています。
- 本リポジトリのコードは発注ロジック（execution 層）との結合を分離する設計です。実運用で発注を行う場合はリスク管理・認証・冗長化を慎重に実装してください。

サポート / 貢献
----------------
- バグ報告や機能提案はリポジトリの Issue を利用してください。
- プルリクエストは各機能のテストケース（DuckDB を使った統合テスト等）を添えて送ってください。

以上が README の要点です。必要であれば「インストール手順の詳細（pip packaging/pyproject）」や「よく使う CLI スクリプト例」「サンプル .env.example」を追記できます。どれを追加しますか？