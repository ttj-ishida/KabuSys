# KabuSys — 日本株自動売買基盤

KabuSys は日本株のデータ収集、ファクター計算、特徴量エンジニアリング、シグナル生成、ETL、ニュース収集、マーケットカレンダー管理などを行う自動売買基盤向けのライブラリ群です。DuckDB をデータ層に用い、J-Quants API から市場データ・財務データ・カレンダーを取得します。戦略ロジックと発注層は分離されており、研究環境（research）と実運用（execution）に対応する設計です。

## 主な機能一覧
- 環境設定管理
  - .env / .env.local の自動ロード（プロジェクトルート検出）
  - 必須設定の取得とバリデーション
- データ取得（J-Quants）
  - 株価日足（OHLCV）取得（ページネーション対応、トークン自動リフレッシュ）
  - 財務データ取得（四半期BS/PL）
  - JPX マーケットカレンダー取得
  - レート制限・リトライ・フェイルセーフ実装
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義とインデックス
  - 初期化（init_schema）・接続ユーティリティ
- ETL パイプライン
  - 差分更新（backfill 対応）、品質チェックフック
  - 日次 ETL（calendar / prices / financials）を統合
- 研究 / ファクター計算
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン、IC（Spearman）やファクター統計
  - Z スコア正規化ユーティリティ
- 特徴量エンジニアリング
  - 生ファクターのユニバースフィルタ適用、Zスコア正規化、features テーブルへの冪等保存
- シグナル生成
  - features と ai_scores を統合して final_score を計算
  - Bear レジームで BUY 抑制、SELL（ストップロス等）判定
  - signals テーブルへの日付単位置換（冪等）
- ニュース収集
  - RSS フィードから記事収集、前処理、raw_news 保存、銘柄コード抽出
  - SSRF 対策、XML デコード安全化（defusedxml）
- マーケットカレンダー管理
  - DB優先の営業日判定、next/prev_trading_day、期間内営業日取得
- 監査ログ（audit）
  - シグナル→発注→約定のトレーサビリティを保存する監査テーブル群

---

## 要求環境
- Python >= 3.10（型注釈に `X | None` を使用）
- 必要パッケージ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API）を使用する場合は J-Quants のリフレッシュトークンが必要

（実プロジェクトでは requirements.txt / pyproject.toml を用意してください）

---

## セットアップ手順（開発ローカル）
1. リポジトリをクローンして仮想環境を作成
   ```bash
   git clone <repo-url>
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb defusedxml
   # またはプロジェクトの pyproject.toml / requirements.txt があればそれを使う
   ```

2. 環境変数を設定（.env / .env.local）
   - プロジェクトルートに `.env` として保存すると自動でロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能）。
   - 必須項目（例）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=CXXXXXXXX
     ```
   - 任意 / 既定値:
     ```
     KABUSYS_ENV=development      # development | paper_trading | live
     LOG_LEVEL=INFO
     KABUSYS_DISABLE_AUTO_ENV_LOAD=0
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABU_API_BASE_URL=http://localhost:18080/kabusapi
     ```

3. データベーススキーマを初期化
   - Python REPL やスクリプトから：
     ```python
     from kabusys.data.schema import init_schema, get_connection
     conn = init_schema("data/kabusys.duckdb")  # ファイルがなければ親ディレクトリを自動作成
     # またはメモリDB
     # conn = init_schema(":memory:")
     ```

---

## 使い方（代表的なワークフロー例）

1. 日次 ETL を実行（市場カレンダー → 株価 → 財務 → 品質チェック）
   ```python
   from datetime import date
   import duckdb
   from kabusys.data.schema import init_schema
   from kabusys.data.pipeline import run_daily_etl

   conn = init_schema("data/kabusys.duckdb")
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```

2. 特徴量のビルド（features テーブルへの保存）
   ```python
   from datetime import date
   from kabusys.strategy import build_features
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   n = build_features(conn, target_date=date(2025, 1, 31))
   print(f"upserted features for {n} codes")
   ```

3. シグナル生成（features / ai_scores / positions を参照して signals に保存）
   ```python
   from datetime import date
   from kabusys.strategy import generate_signals
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   total = generate_signals(conn, target_date=date(2025, 1, 31))
   print(f"signals written: {total}")
   ```

4. ニュース収集ジョブ（RSS 収集・raw_news 保存・銘柄紐付け）
   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   known_codes = {"7203", "6758", "9432"}  # 既知の銘柄コードセット
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   print(results)
   ```

5. カレンダー更新バッチ
   ```python
   from kabusys.data.calendar_management import calendar_update_job
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   saved = calendar_update_job(conn)
   print(f"saved calendar entries: {saved}")
   ```

---

## 主要モジュール / エントリポイント
- kabusys.config
  - settings: 必須環境変数取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）
  - 自動 .env 読み込み（.git または pyproject.toml を基準にプロジェクトルートを検出）
- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
- kabusys.data.schema
  - init_schema, get_connection
- kabusys.data.pipeline
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
- kabusys.data.news_collector
  - fetch_rss, save_raw_news, run_news_collection
- kabusys.data.calendar_management
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.strategy
  - build_features, generate_signals

---

## ディレクトリ構成（抜粋）
プロジェクトの主要なソース構成は以下の通りです。

```
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
   ├─ execution/        # 発注・証券会社連携の実装場所（空ディレクトリとして定義）
   └─ monitoring/       # 監視・メトリクス関連（将来的な実装）
```

---

## 環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API 用パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack チャネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG | INFO | WARNING | ERROR | CRITICAL
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動読み込みを無効化

---

## 開発上の注意
- DuckDB の SQL を多用するため、スキーマ設計の変更は既存データと互換性に注意してください。
- J-Quants API を利用する箇所はレート制限やリトライロジックを備えていますが、実運用では API キーやネットワークの監視を行ってください。
- ニュース収集は外部 RSS を扱うため、SSRF 対策や XML パース処理のセキュリティ実装を踏まえています。ライブラリ依存（defusedxml）は必須です。
- 本リポジトリは戦略ロジック（モデル定義）や execution（実際の発注処理）を分離しているため、実際の発注実装は各ブローカー API に合わせて実装してください。

---

## ライセンス・貢献
（ここにプロジェクトのライセンスや貢献方法、コードスタイル等を追加してください）

---

必要であれば、README にサンプル .env.example、CI やデプロイ手順、Dockerfile、実運用での運用手順（監視・ロギング・リトライポリシー）なども追記します。どの項目を優先して追加しますか？