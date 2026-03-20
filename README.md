# KabuSys

日本株自動売買システム用ライブラリ（KabuSys）。  
データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、カレンダー管理、監査トレーサビリティ等を含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は日本株アルゴリズム取引のための内部ライブラリ群です。主な目的は以下です。

- J-Quants API からの市場データ（株価、財務、マーケットカレンダー）取得と DuckDB への保存（冪等）
- ETL パイプラインによる差分取得・品質チェック
- 研究（research）で作成した生ファクターを用いた特徴量生成（features）
- 正規化済み特徴量 + AI スコアからの売買シグナル生成
- RSS ベースのニュース収集と銘柄紐付け
- マーケットカレンダー管理（営業日の判定や次営業日の取得）
- 発注・約定・監査ログ（スキーマの定義、トレーサビリティ）

設計上の特徴：
- DuckDB を中心としたローカル DB 管理（スキーマ初期化用 API を提供）
- 取得処理は冪等に設計（ON CONFLICT / INSERT ... DO UPDATE を使用）
- ルックアヘッドバイアス対策（取得時刻の追跡やtarget_date ベースでの計算）
- ネットワーク処理はレート制御・リトライを備える
- セキュリティ考慮（RSS の SSRF 対策、defusedxml を利用した XML パース）

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（取得・保存・認証・ページネーション・レート制御）
  - schema: DuckDB スキーマ定義と初期化（init_schema）
  - pipeline: ETL（日次差分 ETL、カレンダーETL、財務/価格 ETL）
  - news_collector: RSS 収集・前処理・DB 保存・銘柄抽出
  - calendar_management: 営業日判定・next/prev/trading days、calendar 更新ジョブ
  - stats: zscore_normalize 等の統計ユーティリティ
  - audit: 発注〜約定までの監査テーブル定義（トレーサビリティ）
- research/
  - factor_research: momentum / volatility / value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）や統計サマリ
- strategy/
  - feature_engineering.build_features: 生ファクターを正規化・合成して features テーブルに UPSERT
  - signal_generator.generate_signals: features + ai_scores を統合して BUY/SELL シグナルを作成
- execution/ monitoring/ （発注・監視レイヤーの骨組みを想定）

設定管理:
- kabusys.config.Settings: 環境変数経由の設定取得（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN 等）

---

## 要求環境

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml
（実運用では requirements.txt / pyproject.toml を参照してください）

---

## セットアップ手順

1. リポジトリをクローン（またはソースを入手）し、適切な Python 仮想環境を作成します。

   ```bash
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 依存ライブラリをインストールします（pyproject.toml / requirements.txt がある場合はそちらを使用してください）。例:

   ```bash
   pip install duckdb defusedxml
   # またはプロジェクトを編集可能モードでインストール
   pip install -e .
   ```

3. 環境変数を設定します。プロジェクトルートに `.env` / `.env.local` を置くと自動でロードされます（自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

   必要な環境変数（主なもの）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: 環境（development / paper_trading / live、デフォルト development）
   - LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

4. DuckDB スキーマを初期化します（初回のみ、db ファイルを作成します）:

   Python REPL またはスクリプト内で:

   ```python
   from kabusys.data.schema import init_schema
   init_schema("data/kabusys.duckdb")
   ```

   成功すると必要なテーブルがすべて作成されます。

---

## 使い方（代表例）

ここでは主要な操作の簡単なコード例を示します。各関数は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取ります。

1. DuckDB 接続の取得（既存 DB へ）:

   ```python
   import duckdb
   conn = duckdb.connect("data/kabusys.duckdb")
   ```

   もしくは上記 init_schema が返す接続をそのまま使えます。

2. 日次 ETL（株価・財務・カレンダー取得＋品質チェック）を実行:

   ```python
   from kabusys.data.pipeline import run_daily_etl
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")  # 初回のみ
   result = run_daily_etl(conn)  # target_date を指定可能
   print(result.to_dict())
   ```

3. 特徴量の構築（features テーブルへ保存）:

   ```python
   from kabusys.strategy import build_features
   from kabusys.data.schema import get_connection
   import datetime

   conn = get_connection("data/kabusys.duckdb")
   target = datetime.date(2026, 3, 20)
   count = build_features(conn, target)
   print(f"built features: {count}")
   ```

4. シグナル生成（signals テーブルへ保存）:

   ```python
   from kabusys.strategy import generate_signals
   from kabusys.data.schema import get_connection
   import datetime

   conn = get_connection("data/kabusys.duckdb")
   target = datetime.date.today()
   total_signals = generate_signals(conn, target, threshold=0.6)
   print(f"total signals: {total_signals}")
   ```

5. ニュース収集ジョブの実行:

   ```python
   from kabusys.data.news_collector import run_news_collection
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   known_codes = {"7203", "6758", "9984"}  # 例えば有効銘柄セット
   results = run_news_collection(conn, known_codes=known_codes)
   print(results)  # ソースごとの新規保存数
   ```

6. カレンダー更新ジョブ:

   ```python
   from kabusys.data.calendar_management import calendar_update_job
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   saved = calendar_update_job(conn)
   print(f"saved calendar records: {saved}")
   ```

注意:
- これらの API は内部でログや例外を出します。運用ではログの設定と例外ハンドリングを行ってください。
- J-Quants へのリクエストは rate limit を尊重します。大量の同時呼び出しは避けてください。

---

## 主要な API（抜粋）

- kabusys.config.settings: 環境設定をプロパティで取得
- kabusys.data.schema.init_schema(db_path)
- kabusys.data.schema.get_connection(db_path)
- kabusys.data.jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
- kabusys.data.jquants_client.save_daily_quotes / save_financial_statements / save_market_calendar
- kabusys.data.pipeline.run_daily_etl
- kabusys.strategy.build_features
- kabusys.strategy.generate_signals
- kabusys.data.news_collector.run_news_collection
- kabusys.data.calendar_management.calendar_update_job

---

## ディレクトリ構成

以下は主要なソースファイルの位置（抜粋）です。リポジトリルートに `src/kabusys/` 配下が配置されています。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - stats.py
      - pipeline.py
      - features.py
      - calendar_management.py
      - audit.py
      - (その他: quality.py 等が想定される)
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
      - (監視関連モジュール)
- pyproject.toml / setup.cfg / requirements.txt（存在する場合は依存情報を参照）

---

## 運用上の注意・ヒント

- 環境（KABUSYS_ENV）は "development", "paper_trading", "live" のいずれかを指定してください。live 時は特に発注・資金管理に注意してください。
- .env ファイルの自動ロードはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に行われます。テスト等で自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB のファイルパスは settings.duckdb_path で指定します。小さな実験は ":memory:" を使うことも可能です。
- J-Quants API 呼び出しはトークンの自動リフレッシュとリトライロジックを備えていますが、API 利用制限や課金体系を確認のうえ利用してください。
- ニュース RSS のフェッチでは SSRF や XML インジェクションに対する防御（リダイレクト検査、defusedxml、受信サイズ制限など）を実装しています。それでも外部入力なので運用上の監視を推奨します。

---

## 貢献・拡張

- strategy 層の重みや閾値、シグナル生成ロジックは generate_signals の引数や内部実装を調整することで変更可能です。
- execution 層は証券会社 API との接続を実装する余地があります（kabu ステーション連携など）。
- quality モジュール（品質チェック）が想定されており、追加チェックやアラートの統合を行ってください。
- テストを追加する際は config の自動 env ロードを無効にして（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）単体テストを行ってください。

---

必要であれば README に「コマンドラインツールの使い方」「デプロイ手順」「CI/CD 設定例」「詳細な設定項目（.env.example）」などを追加して作成します。どの部分を追加したいか教えてください。