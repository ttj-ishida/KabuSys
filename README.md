# KabuSys

日本株向けの自動売買基盤ライブラリ（KabuSys）。データ取得（J-Quants）、ETL、特徴量作成、シグナル生成、ニュース収集、監査トレースまで含むモジュール群を提供します。

- パッケージ名: kabusys
- バージョン: 0.1.0

---

## 概要

KabuSys は以下の責務を持つ Python モジュール群です。

- J-Quants API からの株価・財務・市場カレンダー取得（レートリミット・リトライ・トークン自動更新対応）
- DuckDB を用いたローカルデータベーススキーマ定義・初期化
- ETL パイプライン（日次差分取得、バックフィル、品質チェック）
- ファクター計算（モメンタム / ボラティリティ / バリュー 等）
- 特徴量の正規化・保存（features テーブル）
- 戦略シグナル生成（final_score 計算、BUY/SELL シグナルの判定と signals テーブル保存）
- RSS ベースのニュース収集・銘柄紐付け（raw_news / news_symbols）
- マーケットカレンダーの管理（営業日 / SQ 日判定など）
- 監査ログ（signal/events → order_requests → executions のトレーサビリティ）

設計上のポイント：
- ルックアヘッドバイアスの回避（target_date 時点のデータのみ使用）
- 冪等性（DB 保存は ON CONFLICT を用いた更新/挿入）
- 外部依存を極力抑え、標準ライブラリ + 必要最小限のライブラリで実装

---

## 機能一覧

主なモジュール／機能（抜粋）

- kabusys.config
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - 環境変数 getter (`settings`)
- kabusys.data
  - jquants_client: API クライアント（取得 / 保存ユーティリティ）
  - schema: DuckDB スキーマ定義 / init_schema
  - pipeline: 日次 ETL（run_daily_etl 等）
  - news_collector: RSS 取得・保存・銘柄抽出
  - calendar_management: 営業日判定 / カレンダー更新ジョブ
  - stats: zscore_normalize（特徴量正規化）
  - audit: 監査ログテーブル DDL
- kabusys.research
  - factor_research: calc_momentum / calc_volatility / calc_value
  - feature_exploration: forward returns / IC / factor summary
- kabusys.strategy
  - feature_engineering.build_features: features テーブル作成
  - signal_generator.generate_signals: signals テーブル作成（BUY/SELL）
- kabusys.execution / kabusys.monitoring
  - 発注 / モニタリング用プレースホルダ（拡張ポイント）

---

## 必要条件（推奨）

- Python 3.9+（型ヒントに union 型などを使用）
- 必要 Python パッケージ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API, RSS 等）

（実際の requirements.txt / pyproject.toml はプロジェクトに応じて用意してください）

---

## 環境変数

必須（Settings が ValueError を投げる）:

- JQUANTS_REFRESH_TOKEN — J-Quants の refresh token
- KABU_API_PASSWORD — kabu ステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — 通知先チャンネル ID

任意 / デフォルトあり:

- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動ロードを無効化
- KABUSYS は .env / .env.local をプロジェクトルート（.git or pyproject.toml）から検出して自動読み込みします（.env.local は上書き）。テスト時は自動ロードを無効化可能。

データベースパス（デフォルト）:

- DUCKDB_PATH — data/kabusys.duckdb
- SQLITE_PATH — data/monitoring.db

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンして、仮想環境を作成・有効化

   python -m venv .venv
   source .venv/bin/activate   # Linux/macOS
   .venv\Scripts\activate      # Windows

2. 必要パッケージをインストール

   pip install --upgrade pip
   pip install duckdb defusedxml

   （プロジェクトに pyproject.toml / requirements.txt があればそちらを使ってください）

3. 環境変数を設定
   - プロジェクトルートに .env を作成するのが簡単です。例:

   # .env
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

   自動読み込みは既定で有効です。テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して手動制御してください。

4. データベース初期化（DuckDB）

   Python REPL またはスクリプトで：

   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)  # デフォルト: data/kabusys.duckdb

   これにより必要なテーブルとインデックスが作成されます（冪等）。

---

## 使い方（主要 API の例）

以下は基本的なワークフロー例（Python スニペット）。

1. DB 初期化

   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)

2. 日次 ETL 実行（市場カレンダー・株価・財務の差分取得 → 保存 → 品質チェック）

   from kabusys.data.pipeline import run_daily_etl

   result = run_daily_etl(conn)
   print(result.to_dict())

3. 特徴量（features）作成

   from kabusys.strategy import build_features
   from datetime import date

   cnt = build_features(conn, target_date=date(2024, 1, 5))
   print(f"features upserted: {cnt}")

4. シグナル生成

   from kabusys.strategy import generate_signals
   from datetime import date

   n = generate_signals(conn, target_date=date.today())
   print(f"signals generated: {n}")

   - generate_signals は weights（辞書）や threshold を引数で渡せます。
   - Bear レジーム検出時は BUY を抑制します。

5. ニュース収集ジョブ（RSS → raw_news, news_symbols）

   from kabusys.data.news_collector import run_news_collection

   # known_codes は銘柄抽出用（4桁コードのセット）
   results = run_news_collection(conn, known_codes=set(["7203", "6758"]))
   print(results)

6. カレンダー関連ユーティリティ

   from kabusys.data.calendar_management import next_trading_day, is_trading_day

   is_open = is_trading_day(conn, date.today())
   nxt = next_trading_day(conn, date.today())

注意点：
- ほとんどの関数は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取ります。init_schema の返す接続をそのまま利用できます。
- ETL/取得は外部 API に依存するため、実行には有効な J-Quants トークンが必要です。

---

## 開発・拡張ポイント

- 発注（execution）層は分離設計。証券会社 API（kabu ステーション等）とのコネクタを実装して execution モジュールを拡張することで実運用へ繋げられます。
- AI スコア（ai_scores）用のパイプライン（外部モデル）を追加し、signal_generator の weights を調整して活用できます。
- quality モジュール（パイプライン内で参照）を強化してデータ品質監査を自動化できます。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
- data/
  - __init__.py
  - jquants_client.py
  - news_collector.py
  - schema.py
  - pipeline.py
  - stats.py
  - calendar_management.py
  - audit.py
  - features.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- strategy/
  - __init__.py
  - feature_engineering.py
  - signal_generator.py
- execution/
  - __init__.py
- monitoring/
  - (監視関連モジュール用のプレースホルダ)

各ファイルにはモジュールレベルのドキュメント文字列（設計方針・処理フロー）が含まれており、参照しながら拡張できます。

---

## ログ・デバッグ

- ログレベルは環境変数 LOG_LEVEL で制御できます（デフォルト INFO）。
- 詳細なデバッグを行う場合は LOG_LEVEL=DEBUG を設定してください。

---

## ライセンス・その他

- 本 README はコードの構造と API をまとめた簡易ドキュメントです。実際の配布時は LICENSE・CONTRIBUTING・pyproject.toml 等を整備してください。

---

何か特定の使い方（例: ETL の cron スケジューリング、kabu ステーションとの発注フロー、Slack 通知サンプル）について README に追記したい場合は、用途を教えてください。さらに具体的な利用例やスクリプトを追加します。