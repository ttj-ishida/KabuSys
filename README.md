# KabuSys

日本株向けの自動売買システム用ライブラリ。データ収集（J-Quants）、ETL、特徴量作成、シグナル生成、ニュース収集、監査用スキーマなどを提供します。

## 概要

KabuSys は以下のレイヤーで構成された投資システム向けの共通ライブラリです。

- Data Platform（J-Quants からの株価・財務・カレンダー取得、DuckDB スキーマ、ETL）
- Research（ファクター計算・特徴量探索・統計ユーティリティ）
- Strategy（特徴量合成 → シグナル生成）
- Execution / Monitoring（発注／監視向けスキーマ・ユーティリティ）
- News Collector（RSS からニュース収集・記事 → 銘柄紐付け）

設計上のポイント：
- DuckDB を中心に冪等（idempotent）な保存を実現（ON CONFLICT / トランザクション）
- ルックアヘッドバイアスを避ける形で target_date 時点のデータのみを利用
- API 呼び出しはレート制御・リトライ・トークン自動更新などの堅牢な実装
- 外部依存を必要最小限にし、テスト性を高めるインターフェース

---

## 主な機能一覧

- J-Quants クライアント
  - 日足（OHLCV）・財務データ・市場カレンダーのページネーション対応取得
  - レートリミット制御、リトライ、トークン自動リフレッシュ
  - DuckDB への冪等保存メソッド（save_daily_quotes 等）

- ETL パイプライン
  - 差分取得（最終取得日から自動算出）
  - calendar / prices / financials の日次 ETL（run_daily_etl）
  - 品質チェック呼び出しの統合（quality モジュール経由）

- データスキーマ（DuckDB）
  - raw / processed / feature / execution 層のテーブル定義（init_schema）
  - signals, orders, trades, positions, raw_news 等を含むフルスキーマ

- Research / Feature
  - モメンタム / ボラティリティ / バリュー等のファクター計算（calc_momentum / calc_volatility / calc_value）
  - 将来リターン計算、IC（スピアマンρ）、ファクター統計サマリ
  - Z スコア正規化ユーティリティ（zscore_normalize）

- Strategy
  - 特徴量生成（build_features）：research のファクターを正規化して features テーブルに保存
  - シグナル生成（generate_signals）：features・ai_scores・positions を用いて BUY/SELL シグナルを作成・保存

- News Collector
  - RSS 取得（SSRF/リダイレクト検査、gzip上限、XML攻撃対策）
  - テキスト前処理、記事IDの冪等化（URL 正規化 → SHA-256）、raw_news 保存、銘柄抽出・紐付け

---

## セットアップ手順

※プロジェクトに含まれる依存関係ファイルはここに記載されていません。実際のプロジェクトでは requirements.txt / pyproject.toml を用意してください。以下は一般的な手順例です。

1. リポジトリをクローン（例）
   - git clone <repo-url>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   または
   - pip install -e .

   例: DuckDB、defusedxml などが必要です。
   - pip install duckdb defusedxml

4. 環境変数の設定
   プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` または `.env.local` を置くと、自動的に読み込まれます（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

   必須（実行する機能により異なる）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API 用パスワード（execution を使う場合）
   - SLACK_BOT_TOKEN: Slack 通知を使う場合
   - SLACK_CHANNEL_ID: Slack チャンネルID

   任意/デフォルト:
   - KABUSYS_ENV: development|paper_trading|live（デフォルト: development）
   - LOG_LEVEL: DEBUG|INFO|...（デフォルト: INFO）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）

   .env の簡易例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. DB スキーマ初期化
   - Python から DuckDB 接続を作成し、スキーマを初期化します。

   例:
   ```
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

---

## 使い方（基本的なワークフロー）

以下は主要 API の簡単な使用例です。実行は Python スクリプトまたは REPL で行います。

1. DuckDB スキーマ初期化（初回のみ）
   ```
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

2. 日次 ETL を実行（市場カレンダー → 株価 → 財務）
   ```
   from kabusys.data.pipeline import run_daily_etl
   result = run_daily_etl(conn)
   print(result.to_dict())
   ```

3. 特徴量の作成（features テーブルへ UPSERT）
   ```
   from datetime import date
   from kabusys.strategy import build_features
   build_features(conn, date.today())
   ```

4. シグナル生成（signals テーブルへ UPSERT）
   ```
   from datetime import date
   from kabusys.strategy import generate_signals
   cnt = generate_signals(conn, date.today(), threshold=0.6)
   print("signals written:", cnt)
   ```

5. ニュース収集（RSS → raw_news + news_symbols）
   ```
   from kabusys.data.news_collector import run_news_collection
   known_codes = {"7203", "6758", ...}  # 運用上の銘柄コードセット
   results = run_news_collection(conn, known_codes=known_codes)
   print(results)
   ```

6. Research ユーティリティ（IC 計算やファクター探索）
   ```
   from kabusys.research import calc_forward_returns, calc_ic, factor_summary
   # prices_daily から計算した将来リターンやファクターを使って解析
   ```

注意点:
- 各関数は target_date 時点のデータのみを用いることを念頭に置いています（ルックアヘッド回避）。
- ETL / fetch 系はネットワーク・API エラーをログに残しつつ処理を続行する設計です。戻り値にエラー情報を含めていることが多いので確認してください。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須 for data fetch)
- KABU_API_PASSWORD (kabuAPI を使う場合)
- KABUSYS_ENV (development | paper_trading | live) — settings.env で検証
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (通知用)
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- SQLITE_PATH (監視 DB、デフォルト data/monitoring.db)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env を読み込む処理を無効化できます（テスト用途など）

設定は kabusys.config.settings を通して参照できます。

---

## ディレクトリ構成（抜粋）

プロジェクトの主なファイル・ディレクトリ構成（src 以下）:

- src/kabusys/
  - __init__.py
  - config.py                   # 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py         # J-Quants API クライアント（取得・保存）
    - schema.py                 # DuckDB スキーマ定義・初期化 (init_schema)
    - pipeline.py               # ETL パイプライン（run_daily_etl 等）
    - news_collector.py         # RSS 取得・保存・銘柄抽出
    - calendar_management.py    # 市場カレンダー管理ユーティリティ
    - features.py               # zscore_normalize の公開ラッパ
    - stats.py                  # 統計ユーティリティ（zscore_normalize）
    - audit.py                  # 監査ログ用スキーマ
    - execution/                # execution 関連（発注連携など）
  - research/
    - __init__.py
    - factor_research.py        # calc_momentum / calc_volatility / calc_value
    - feature_exploration.py    # calc_forward_returns / calc_ic / factor_summary
  - strategy/
    - __init__.py
    - feature_engineering.py    # build_features
    - signal_generator.py       # generate_signals
  - execution/                   # 発注統合層（未実装箇所あり）
  - monitoring/                  # 監視用ユーティリティ（SQLite など）
- pyproject.toml or setup.cfg    # （プロジェクト設定ファイルが存在する想定）
- .env.example                   # 環境変数のサンプル（想定）

---

## 開発・テスト時の注意

- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml）を起点に行われます。テスト環境で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB のパスを ":memory:" にするとインメモリ DB での単体テストが可能です（init_schema(":memory:")）。
- ネットワーク/外部 API に依存する部分（jquants_client.fetch_* や news_collector._urlopen 等）はモックしやすいよう引数注入や内部関数分離が行われています。

---

## 連絡・貢献

バグ報告や機能提案、プルリクエストはリポジトリの Issue / Pull Request を通して行ってください。コードの一貫性を保つため、既存の設計方針（ルックアヘッド回避、冪等性、トランザクション）の遵守をお願いします。

---

必要であれば README に実行コマンド / systemd タイマー / cron の例、詳細な .env.example、CI 用のテスト手順などを追加できます。どの情報を優先して追記しますか？