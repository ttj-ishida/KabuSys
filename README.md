# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、DuckDB を用いたデータ基盤、ファクター計算、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理など、量的運用に必要な共通機能をモジュール化して提供します。

バージョン: 0.1.0

---

## プロジェクト概要

このコードベースは以下の責務を持つモジュール群で構成されています。

- データ取得・保存（J-Quants API クライアント、raw → processed レイヤの永続化、ETL パイプライン）
- DuckDB スキーマ定義・初期化
- ファクター計算（Momentum / Volatility / Value 等）
- 特徴量エンジニアリング（Z スコア正規化、ユニバースフィルタ等）
- シグナル生成（最終スコア計算、BUY/SELL シグナルの作成）
- ニュース収集（RSS → raw_news、銘柄抽出）
- マーケットカレンダー管理（営業日判定・次営業日/前営業日取得）
- 監査ログ・実行レイヤ（テーブル定義を含む）
- 設定管理（環境変数 / .env ロード）

設計で特に重視している点:
- 冪等性（DB への保存は ON CONFLICT で既存を上書き/排除）
- ルックアヘッドバイアス防止（計算は target_date 時点のデータのみを使用）
- 外部依存を最小化（可能な限り標準ライブラリで実装）
- API レート制御・リトライ（J-Quants クライアント）

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（ページネーション・トークンリフレッシュ・レート制御・保存ユーティリティ）
  - pipeline: 日次 ETL（差分取得・バックフィル・品質チェック統合）
  - schema: DuckDB スキーマ定義と init_schema()
  - news_collector: RSS フィード収集、前処理、raw_news 保存、銘柄抽出
  - calendar_management: market_calendar の更新、is_trading_day / next_trading_day 等
  - stats: Z スコア正規化などの統計ユーティリティ
- research/
  - factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）などの解析ツール
- strategy/
  - feature_engineering.build_features: 生ファクターをマージ・フィルタ・正規化して features テーブルに保存
  - signal_generator.generate_signals: features と ai_scores を統合して BUY/SELL シグナルを作成
- config: .env / 環境変数ロードと設定ラッパー（Settings）
- execution / monitoring: 発注・監視関連のテーブル定義やプレースホルダ（実装は拡張想定）

---

## 必要な環境変数

config.Settings が利用する主要な環境変数（必須／任意）:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション等の API パスワード
- SLACK_BOT_TOKEN — Slack 通知に利用するボットトークン
- SLACK_CHANNEL_ID — 通知先 Slack チャンネル ID

任意（デフォルトあり）:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite DB（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）

自動 .env ロードを無効化する:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

（.env.example を作成してこれらを管理することを推奨します）

---

## セットアップ手順

想定環境: Python 3.9+（typing の Union | 等を使用しているため 3.10 以上が望ましい）

1. リポジトリをクローンして仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 必須: duckdb, defusedxml（news_collector が利用）
   - 例:
     - pip install duckdb defusedxml

   （プロジェクトに requirements.txt があればそれを使用してください）

3. 環境変数を設定
   - プロジェクトルートに .env を配置するか OS 環境変数を設定
   - 最低限、上記の必須環境変数を用意してください

4. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで:
     - from kabusys.data.schema import init_schema
     - conn = init_schema("data/kabusys.duckdb")
   - DUCKDB_PATH を設定している場合は settings.duckdb_path を使用できます

5. （任意）J-Quants API の ID トークンが必要な処理を行う場合は JQUANTS_REFRESH_TOKEN を準備

---

## 使い方（代表的な例）

以下は各種主要操作の最小の使用例です。

- DuckDB スキーマ初期化（コマンドライン）
  - python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"

- 日次 ETL を実行（J-Quants からの差分取得 → 保存）
  - ```python
    from datetime import date
    from kabusys.data.schema import init_schema
    from kabusys.data.pipeline import run_daily_etl

    conn = init_schema('data/kabusys.duckdb')
    result = run_daily_etl(conn, target_date=date.today())
    print(result.to_dict())
    ```

- 特徴量（features）を構築
  - build_features は DuckDB 接続と target_date を受け取り、features テーブルへ書き込みます。
  - ```python
    from datetime import date
    from kabusys.data.schema import init_schema
    from kabusys.strategy import build_features

    conn = init_schema('data/kabusys.duckdb')
    n = build_features(conn, target_date=date.today())
    print(f"built features for {n} symbols")
    ```

- シグナル生成
  - generate_signals は features / ai_scores / positions を参照して signals テーブルへ書き込みます。
  - ```python
    from datetime import date
    from kabusys.data.schema import init_schema
    from kabusys.strategy import generate_signals

    conn = init_schema('data/kabusys.duckdb')
    total = generate_signals(conn, target_date=date.today())
    print(f"generated {total} signals")
    ```

- RSS ニュース収集と DB 保存
  - ```python
    from kabusys.data.schema import init_schema
    from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

    conn = init_schema('data/kabusys.duckdb')
    known_codes = {'7203', '6758', '9984'}  # 既知の銘柄コードセット
    results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
    print(results)
    ```

- J-Quants データ取得（直接呼ぶ場合）
  - jquants_client.fetch_daily_quotes / fetch_financial_statements 等を利用できます。
  - これらは内部で ID トークンを自動取得・リフレッシュします（JQUANTS_REFRESH_TOKEN が必要）。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / .env ロードと Settings
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（取得・保存ユーティリティ）
    - schema.py                     — DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - news_collector.py             — RSS 収集・正規化・保存
    - stats.py                      — zscore_normalize 等の統計ユーティリティ
    - features.py                   — data.stats の公開ラッパ
    - calendar_management.py        — market_calendar 更新・営業日ユーティリティ
    - audit.py                      — 監査ログテーブル定義（signal_events 等）
    - (その他: quality.py 等想定)
  - research/
    - __init__.py
    - factor_research.py            — ファクター計算（mom/vol/value）
    - feature_exploration.py        — 将来リターン/IC/統計サマリなど
  - strategy/
    - __init__.py
    - feature_engineering.py        — build_features
    - signal_generator.py           — generate_signals
  - execution/                      — 発注・エグゼキューション関連（プレースホルダ）
  - monitoring/                     — 監視機能（プレースホルダ）

---

## 注意点 / 実運用時のヒント

- API レートやリトライは jquants_client に組み込まれていますが、大量の同時リクエストを行うクライアント側のコード設計に注意してください。
- DuckDB スキーマは init_schema で冪等的に作成されます。運用でテーブル定義を変更する場合はマイグレーション戦略を用意してください。
- シグナル生成では Bear レジーム判定・ストップロス等のルールが実装されています。重みや閾値は generate_signals の引数で調整できます。
- ニュース収集は RSS ベースであり、記事の ID は正規化した URL の SHA-256 の先頭を使うため、トラッキングパラメータが付いた URL でも冪等性が保たれます。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 .env ロードを無効化できます。

---

## 最後に

この README はコードベースの主要機能と基本的な使い方をまとめたものです。各モジュール（特に data/jquants_client.py, data/schema.py, strategy/*, research/*）のドキュメント文字列（docstring）に詳細と設計意図が記載されています。実装や運用ルールの追加・変更はドキュメントとコードの両方を更新してください。

質問や追加で README に入れたい項目があれば教えてください。