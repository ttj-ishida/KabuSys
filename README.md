# KabuSys

日本株向けの自動売買基盤ライブラリ。データ取得・ETL、特徴量生成、シグナル生成、ニュース収集、カレンダー管理、発注監査など、トレーディングシステムの主要コンポーネントを提供します。

---

## 概要

KabuSys は以下を目的としたモジュール群です。

- J-Quants API からの株価・財務・マーケットカレンダー取得（差分取得・ページネーション対応・リトライ・レート制御）
- DuckDB を用いたデータ保管スキーマ（Raw / Processed / Feature / Execution 層）
- 研究用のファクター計算（モメンタム・ボラティリティ・バリュー等）と特徴量エンジニアリング
- 正規化済みファクターと AI スコアを統合したシグナル生成
- RSS ベースのニュース収集と銘柄抽出
- マーケットカレンダー（JPX）管理と営業日ロジック
- 発注／約定／監査ログ用テーブル定義（監査トレーサビリティ重視）

設計方針として、ルックアヘッドバイアス回避、冪等性（ON CONFLICT）、外部発注 API への直接依存排除（戦略層は execution 層に依存しない）を重視しています。

---

## 機能一覧

- データ取得・保存
  - J-Quants API クライアント（株価、財務、カレンダー）
  - 差分 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - DuckDB スキーマ初期化（init_schema）
- データ処理・研究
  - ファクター計算（calc_momentum / calc_volatility / calc_value）
  - クロスセクション Z スコア正規化（zscore_normalize）
  - 将来リターン計算・IC（Information Coefficient）等の特徴量探索ユーティリティ
- 戦略
  - 特徴量バッチ生成（build_features）
  - シグナル生成（generate_signals）— 複数コンポーネントを重み付き合算、Bear レジーム抑制、BUY/SELL の日付単位置換（冪等）
- ニュース
  - RSS 収集（fetch_rss）・raw_news 保存（save_raw_news）
  - 銘柄コード抽出（extract_stock_codes）・news_symbols 保存
  - SSRF/サイズ/XML Bomb 等のセキュリティ対策
- カレンダー
  - market_calendar による営業日判定／next/prev/get_trading_days
  - 夜間カレンダー更新ジョブ（calendar_update_job）
- 監査
  - signal_events / order_requests / executions など監査テーブルの定義（UUID ベースでトレース可能）
- 設定管理
  - .env / 環境変数読み込み、自動ロード（パッケージルート検出）と保護機構

---

## 前提条件

- Python 3.10+
- pip（仮想環境推奨）
- DuckDB（Python パッケージとして提供されます）
- ネットワークアクセス（J-Quants API / RSS）

主要依存パッケージ例（実際の requirements.txt に合わせてください）:
- duckdb
- defusedxml

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成・有効化します（例）:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要なパッケージをインストールします（例）:
   - pip install duckdb defusedxml
   - またはプロジェクトに requirements.txt があれば pip install -r requirements.txt

3. パッケージをインストール（編集可能な開発インストール）:
   - pip install -e .

4. 環境変数を作成します:
   - プロジェクトルートに `.env` または `.env.local` を設置することで自動で読み込まれます（自動ロードは config モジュールがプロジェクトルートを検出できる場合のみ動作）。
   - 自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須の環境変数（少なくともこれらを設定してください）:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード（発注機能を使う場合）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（通知を使う場合）
- SLACK_CHANNEL_ID — Slack チャネル ID（通知を使う場合）

任意（デフォルト値あり）:
- KABUSYS_ENV — environment: "development"（デフォルト） / "paper_trading" / "live"
- LOG_LEVEL — ログレベル（"DEBUG","INFO","WARNING","ERROR","CRITICAL"）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視系 DB（デフォルト: data/monitoring.db）
  
例 .env:
  JQUANTS_REFRESH_TOKEN=your_refresh_token_here
  KABU_API_PASSWORD=your_kabu_password
  SLACK_BOT_TOKEN=xoxb-...
  SLACK_CHANNEL_ID=C01234567
  DUCKDB_PATH=data/kabusys.duckdb

---

## データベース初期化

DuckDB スキーマを作成して接続を得るには次を実行します（Python REPL やスクリプト）:

- from kabusys.data.schema import init_schema
- conn = init_schema("data/kabusys.duckdb")

引数に ":memory:" を与えるとインメモリ DB を使えます（テスト時に便利）。

---

## 使い方（代表的な例）

以下は Python スクリプトまたは REPL での利用例です。

1) 日次 ETL（市場カレンダー・株価・財務データの差分取得・保存・品質チェック）:
- from kabusys.data.schema import init_schema
- from kabusys.data.pipeline import run_daily_etl
- conn = init_schema("data/kabusys.duckdb")
- result = run_daily_etl(conn)  # target_date を指定可能
- print(result.to_dict())

2) 特徴量（features）生成:
- from kabusys.strategy import build_features
- from kabusys.data.schema import init_schema
- from datetime import date
- conn = init_schema("data/kabusys.duckdb")
- n = build_features(conn, date(2024, 1, 31))
- print(f"built features for {n} codes")

3) シグナル生成:
- from kabusys.strategy import generate_signals
- from kabusys.data.schema import init_schema
- from datetime import date
- conn = init_schema("data/kabusys.duckdb")
- total = generate_signals(conn, date(2024, 1, 31))
- print(f"signals written: {total}")

generate_signals は重み（weights）や閾値（threshold）を引数で調整できます。

4) ニュース収集（RSS）と保存:
- from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
- from kabusys.data.schema import init_schema
- conn = init_schema("data/kabusys.duckdb")
- known_codes = {"7203","6758", ...}  # 抽出に利用する有効銘柄コード集合
- results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
- print(results)

5) カレンダー更新ジョブ:
- from kabusys.data.calendar_management import calendar_update_job
- conn = init_schema("data/kabusys.duckdb")
- saved = calendar_update_job(conn)
- print(f"saved calendar rows: {saved}")

注意点:
- J-Quants API 呼び出しは内部でトークン自動リフレッシュ、レート制限（120 req/min）、リトライを実装しています。
- ETL 系処理は冪等性を考慮しており、既存行は ON CONFLICT で更新されます。

---

## 開発・テスト

- 自動 .env ロードがテストに影響する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。
- jquants_client のネットワーク呼び出しは id_token 注入や関数レベルでのモックがしやすい設計です（テストで id_token を直接渡す）。
- news_collector の _urlopen などは unit test で差し替え（モック）可能です。

---

## ディレクトリ構成

主要ファイル・モジュール（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py                   — 環境変数 / .env ロード / Settings
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（fetch/save 系）
    - pipeline.py                — ETL パイプライン（run_daily_etl 等）
    - schema.py                  — DuckDB スキーマ定義・init_schema
    - stats.py                   — 汎用統計ユーティリティ（zscore_normalize）
    - features.py                — data.stats の再エクスポート
    - news_collector.py          — RSS 取得・前処理・保存 / 銘柄抽出
    - calendar_management.py     — market_calendar 管理・営業日ロジック
    - audit.py                   — 監査ログ（signal_events / order_requests / executions）
    - pipeline.py                — ETL のエントリポイント（重複記載: ETL 操作を含む）
    - ...（その他 raw/processed テーブル関連）
  - research/
    - __init__.py
    - factor_research.py         — モメンタム/ボラティリティ/バリュー等の計算
    - feature_exploration.py     — 将来リターン/IC/要約統計
  - strategy/
    - __init__.py
    - feature_engineering.py     — 生ファクター統合・正規化・features への保存
    - signal_generator.py        — final_score 計算・BUY/SELL 判定・signals 保存
  - execution/
    - __init__.py
    - (発注関連モジュールを配置する想定)
  - monitoring/
    - (監視・メトリクス・alert 用モジュールを配置する想定)

上記は主要なモジュール群で、各モジュールはドキュメンテーション文字列と設計方針を含んでいます。

---

## 注意事項 / 補足

- 本リポジトリは本番発注までの多くの要素（ブローカー API との連携、リスク管理の完全実装、運用監視）を想定していますが、運用前に十分な検証と安全対策（ブラックスワン対応、二重チェック、テスト口座など）を行ってください。
- 環境変数の不足は config.Settings のプロパティが ValueError を投げます。`.env.example` を参考に `.env` を作成してください。
- DuckDB の SQL 文は一部のデータベース固有機能に依存しています（例: ON CONFLICT の振る舞いなど）。DuckDB のバージョン互換性に注意してください。
- ログレベルや環境（KABUSYS_ENV）により挙動（paper_trading/live）が変わる箇所があります。設定値は Settings を通して参照されます。

---

ご不明点や README に追加したい具体的なコマンド例があればお知らせください。README をプロジェクトの実行スクリプト（Makefile / CLI）に合わせてさらに整備できます。