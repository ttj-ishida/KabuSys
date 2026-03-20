# KabuSys

日本株向けの自動売買システム用ライブラリ群。データ取得（J-Quants）、ETL、特徴量生成、戦略シグナル生成、ニュース収集、カレンダー管理、監査ログなどを含むモジュール化された実装を提供します。

---

## 概要

KabuSys は以下を目的とした内部ライブラリです。

- J-Quants API からの市場データ・財務データ・カレンダー取得と DuckDB への永続化（冪等）
- ETL（差分更新・バックフィル・品質チェック）ワークフロー
- 研究（research）で算出した生ファクターの正規化・合成（features）
- 戦略の最終スコア計算と BUY/SELL シグナル生成（signals）
- RSS ベースのニュース収集と銘柄紐付け
- JPX マーケットカレンダーの管理と営業日判定
- 発注・約定・ポジション管理用スキーマと監査ログ（監査トレーサビリティ）

設計上のポイント：
- ルックアヘッドバイアス対策（target_date 時点のデータのみを使用）
- DuckDB を中心に SQL + Python で解析可能（pandas 等には依存しないユーティリティあり）
- API 呼び出しはレート制御・リトライ・トークン自動更新を実装
- DB 保存は冪等（ON CONFLICT / upsert）を前提

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（レート制御・リトライ・ページネーション対応）
  - schema: DuckDB スキーマ定義 + init_schema()
  - pipeline: ETL パイプライン（run_daily_etl 等）
  - news_collector: RSS 取得・前処理・raw_news 保存・銘柄抽出
  - calendar_management: market_calendar の更新・営業日判定ユーティリティ
  - stats: zscore_normalize 等の統計ユーティリティ
- research/
  - factor_research: Momentum / Volatility / Value ファクター計算
  - feature_exploration: 将来リターン計算・IC（スピアマン）・サマリー
- strategy/
  - feature_engineering.build_features: ファクター正規化 → features テーブルへ UPSERT
  - signal_generator.generate_signals: features と ai_scores を統合して BUY/SELL を生成
- execution / monitoring:
  - 発注・監視層のプレースホルダ（スキーマ・監査テーブルあり）
- config:
  - 環境変数管理（.env 自動読み込み、必須値チェック、env 切替）

---

## 必要条件 / 依存ライブラリ

- Python 3.10 以上（型注釈に PEP 604 の `X | Y` を利用）
- 必須 Python パッケージ（代表例）:
  - duckdb
  - defusedxml
※ 実行環境に応じた追加パッケージが必要な場合があります（例: J-Quants 認証に関連する HTTP クライアントを自分で用意する等）。パッケージ管理はプロジェクト側で requirements.txt / pyproject を用意してください。

---

## セットアップ手順

1. リポジトリをクローンしてローカルに配置
   - 例: git clone <repo-url>

2. 仮想環境作成と依存インストール
   - python -m venv .venv
   - source .venv/bin/activate  # (Windows: .venv\Scripts\activate)
   - pip install -U pip
   - pip install duckdb defusedxml
   - （プロジェクトで pyproject.toml / requirements.txt がある場合はそれに従ってください）

3. 環境変数の準備
   - ルートに `.env` を作成（.env.example を参考に）
   - 必須の環境変数（config.Settings が要求するもの）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD     : kabu ステーション API のパスワード
     - SLACK_BOT_TOKEN       : Slack Bot 用トークン（通知を使う場合）
     - SLACK_CHANNEL_ID      : 通知先 Slack チャンネル ID
   - 任意 / デフォルトあり:
     - KABU_API_BASE_URL     : kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH           : DuckDB 保存先（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH           : 監視用 SQLite パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV           : development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL             : DEBUG/INFO/…（デフォルト: INFO）
   - テストや CI 等で自動環境読み込みを無効化したい場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると config の自動 .env ロードを無効化します。

4. データベース初期化
   - Python REPL やスクリプトで DuckDB スキーマを作成します:
     - from kabusys.config import settings
       from kabusys.data.schema import init_schema
       conn = init_schema(settings.duckdb_path)
   - メモリ DB を試す場合: init_schema(":memory:")

---

## 使い方（基本的な例）

以下は代表的な利用例です。すべて Python スクリプト / REPL 内で実行します。

- DuckDB 初期化と接続
  - from kabusys.config import settings
    from kabusys.data.schema import init_schema, get_connection
    conn = init_schema(settings.duckdb_path)  # 初回は init_schema
    # 既存 DB に接続するだけなら:
    conn = get_connection(settings.duckdb_path)

- 日次 ETL を実行（市場カレンダー・株価・財務の差分取得と品質チェック）
  - from kabusys.data.pipeline import run_daily_etl
    result = run_daily_etl(conn)  # target_date を指定可
    print(result.to_dict())

- カレンダー更新ジョブ（夜間バッチ）
  - from kabusys.data.calendar_management import calendar_update_job
    saved = calendar_update_job(conn)
    print("saved:", saved)

- ニュース収集ジョブ
  - from kabusys.data.news_collector import run_news_collection
    known_codes = {"7203", "6758", ...}  # 既知の銘柄コードセット
    results = run_news_collection(conn, known_codes=known_codes)
    print(results)

- 特徴量構築（strategy.feature_engineering）
  - from kabusys.strategy import build_features
    from datetime import date
    n = build_features(conn, target_date=date(2026, 3, 1))
    print(f"features for date written: {n}")

- シグナル生成（strategy.signal_generator）
  - from kabusys.strategy import generate_signals
    from datetime import date
    total = generate_signals(conn, target_date=date(2026, 3, 1))
    print("signals generated:", total)

- J-Quants から直接データを取得する（テストや手動取得）
  - from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
    quotes = fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,3,1))

注意:
- generate_signals / build_features は target_date に依存して、当該日以前のデータのみ参照するよう設計されています（ルックアヘッド回避）。
- jquants_client は API レート（120 req/min）を自動制御します。大量取得時は実行時間がかかります。

---

## ディレクトリ構成（主なファイル）

（リポジトリの src/kabusys 配下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py           — J-Quants API クライアント（fetch/save）
    - news_collector.py           — RSS ニュース収集・保存
    - schema.py                   — DuckDB スキーマ定義 / init_schema
    - pipeline.py                 — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py      — マーケットカレンダー管理
    - stats.py                    — zscore_normalize 等
    - features.py                 — data.stats の再エクスポート
    - audit.py                    — 監査ログ DDL（signal_events, order_requests, executions）
    - audit (一部未完のインデックス定義が含まれるファイル)
  - research/
    - __init__.py
    - factor_research.py          — ファクター計算（momentum/volatility/value）
    - feature_exploration.py      — 将来リターン・IC・統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py      — features テーブル作成（正規化・UPSERT）
    - signal_generator.py         — final_score 計算・signals 生成
  - execution/                     — 発注/実行層（パッケージ定義ファイル）
  - monitoring/                    — 監視用モジュール（パッケージ定義ファイル）

（上記は主要ファイルの一覧です。実際のプロジェクトでは tests/, docs/, scripts/ 等が追加されることがあります。）

---

## 追加メモ / 運用上の注意

- 環境変数の自動読み込み:
  - config.py はプロジェクトルート（.git または pyproject.toml を含む親ディレクトリ）を探索し `.env` / `.env.local` を自動で読み込みます。自動読み込みを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- セキュリティ:
  - `.env` に API トークン等を置く場合は Git 管理しない（.gitignore に追加）ことを徹底してください。
- API レート制御:
  - J-Quants のレート上限（120 req/min）に合わせた実装が組み込まれています。大量にページングを行う処理では時間がかかる点に注意してください。
- テスト:
  - jquants_client の HTTP 呼び出しや news_collector のネットワーク IO はモック可能な設計（トークン注入、_urlopen の差し替えなど）です。ユニットテストでは外部 API を直接叩かないようにしてください。

---

必要に応じて README へ実行スクリプト、CI 設定例、.env.example の雛形や具体的な SQL サンプル（スキーマ確認用）を追加できます。追加する内容の希望があれば教えてください。