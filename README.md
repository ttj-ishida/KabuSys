# KabuSys

日本株向けの自動売買データ基盤・戦略モジュール群です。  
DuckDB を利用したデータレイヤ、J-Quants API を介したデータ取得、ニュース収集、特徴量生成・正規化、シグナル生成、監査用スキーマなどを含む設計になっています。

---

## プロジェクト概要

KabuSys は以下の目的を持つライブラリ／ミニプラットフォームです。

- J-Quants API から株価・財務・マーケットカレンダーを取得して DuckDB に保存する ETL パイプライン
- RSS ベースのニュース収集と記事→銘柄の紐付け
- 研究（research）で計算した生ファクターを正規化・合成して strategy 用の特徴量を作成
- 生成した特徴量と AI スコアを統合して売買シグナル（BUY/SELL）を作成
- 発注・約定・ポジション等を記録する実行（execution）/監査（audit）用のスキーマ
- 冪等性・レート制御・リトライ・SSRF 対策等の実運用を意識した実装

設計方針として、ルックアヘッドバイアス防止・DB 側での冪等保存・外部発注層への直接依存回避などが採用されています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（ページネーション・レート制御・自動トークンリフレッシュ・保存メソッド）
  - schema: DuckDB スキーマ定義と初期化（raw / processed / feature / execution 層）
  - pipeline: 日次差分 ETL（run_daily_etl、run_prices_etl、run_financials_etl、run_calendar_etl）
  - news_collector: RSS 収集・前処理・DB 保存・銘柄抽出（SSRF 対策・gzip/サイズ制限対応）
  - calendar_management: マーケットカレンダー管理・営業日判定ユーティリティ
  - stats: Z スコア正規化等の統計ユーティリティ
- research/
  - factor_research: momentum / volatility / value 等のファクター計算
  - feature_exploration: 将来リターン計算（forward returns）、IC（Information Coefficient）、サマリー
- strategy/
  - feature_engineering: research の生ファクターを取り込み Z スコア正規化・フィルタ・features テーブルへの保存
  - signal_generator: features + ai_scores を統合して final_score を計算、BUY/SELL シグナルを signals テーブルへ書き込む
- config: .env / 環境変数管理（自動 .env ロード、必須チェック）
- execution / monitoring / audit: 実行/監査/監視用のスキーマ・空のパッケージプレースホルダ（コードベースに応じて拡張）

主な設計上の特徴：
- DB 側での冪等性（INSERT … ON CONFLICT 等）により再実行可能
- J-Quants のレート制御（120 req/min）やリトライ/トークンリフレッシュを実装
- RSS の SSRF/サイズ/Gzip 対策、トラッキングパラメータ除去
- 各処理は target_date 時点のデータのみを使用しルックアヘッドを防止

---

## セットアップ手順

前提：
- Python 3.9 以上（型注釈の Union | を使用しているため）を推奨
- DuckDB を利用します（pip パッケージ duckdb）
- defusedxml（RSS の安全なパース）等が必要

1. 仮想環境の作成（任意）:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（最低限）:
   - pip install duckdb defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください。）

3. 環境変数の設定:
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（但し KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可能）。
   - 最低限必要な環境変数（config.Settings が必須とするもの）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション等の API パスワード（実行層で使用）
     - SLACK_BOT_TOKEN: Slack 通知用トークン
     - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

   - 任意 / デフォルト設定:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
     - KABU_API_BASE_URL: デフォルト "http://localhost:18080/kabusapi"
     - DUCKDB_PATH: デフォルト "data/kabusys.duckdb"
     - SQLITE_PATH: デフォルト "data/monitoring.db"

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN="xxxxxx"
   KABU_API_PASSWORD="secret"
   SLACK_BOT_TOKEN="xoxb-..."
   SLACK_CHANNEL_ID="C12345678"
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   DUCKDB_PATH=data/kabusys.duckdb
   ```

4. データベース初期化:
   - Python REPL やスクリプトで DuckDB を初期化します。例:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
   - ":memory:" を渡すとインメモリ DB になります（テスト等で便利）。

---

## 使い方（代表的なワークフロー）

下記は代表的な利用例です。各関数は DuckDB の接続オブジェクトを受け取り操作します。

1. DuckDB の初期化
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

2. 日次 ETL（J-Quants から市場データを差分取得して保存）
   ```python
   from kabusys.data.pipeline import run_daily_etl
   from datetime import date

   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```

3. マーケットカレンダー更新（夜間バッチ）
   ```python
   from kabusys.data.calendar_management import calendar_update_job
   saved = calendar_update_job(conn)
   print("saved:", saved)
   ```

4. ニュース収集ジョブ
   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   print(results)
   ```

5. 特徴量構築（strategy.feature_engineering）
   ```python
   from kabusys.strategy import build_features
   from datetime import date
   count = build_features(conn, target_date=date.today())
   print(f"features upserted: {count}")
   ```

6. シグナル生成（strategy.signal_generator）
   ```python
   from kabusys.strategy import generate_signals
   from datetime import date
   total_signals = generate_signals(conn, target_date=date.today(), threshold=0.6)
   print("signals written:", total_signals)
   ```

7. J-Quants からの生データ取得（低レベル）
   ```python
   from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
   records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
   saved = save_daily_quotes(conn, records)
   ```

注意点：
- 多くの書き込み関数はトランザクションを用いて日付単位で置換（冪等性）しています。
- シグナル生成は features/ai_scores/positions テーブルを参照し、Bear レジーム時は BUY を抑制する等のポリシーを実装済みです。
- ETL はデフォルトで差分取得とバックフィル（直近 n 日）を行い、API 後出し修正を吸収する挙動です。

---

## 環境変数（主要）

- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（Settings.jquants_refresh_token）
  - KABU_API_PASSWORD: kabu API パスワード（Settings.kabu_api_password）
  - SLACK_BOT_TOKEN: Slack Bot トークン（Settings.slack_bot_token）
  - SLACK_CHANNEL_ID: Slack チャンネル ID（Settings.slack_channel_id）

- 任意
  - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
  - LOG_LEVEL: ログレベル（INFO など、Settings.log_level）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると自動 .env ロードを無効化
  - KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）

config.Settings は、.env/.env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読込します。テストなどで自動読み込みを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を使ってください。

---

## ディレクトリ構成（主要ファイル）

以下はコードベースの主要なファイル・モジュール一覧（src/kabusys 以下）です。

- src/kabusys/
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
    - audit（DDLの続き / 監査用テーブル定義）...
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
  - monitoring/  (プレースホルダ)

（README はコードベースの抜粋に基づいてまとめたもので、実際のリポジトリでは追加ファイルやドキュメントが存在することがあります。）

---

## 実運用上の注意・ベストプラクティス

- クリティカルな環境（live）で運用する際は、KABUSYS_ENV を `live` に設定し、ログ・監査・アラート（Slack など）を整備してください。
- J-Quants API トークンや kabu API の資格情報は安全に管理し、CI/CD に平文で置かないでください。
- DuckDB ファイルは定期バックアップを検討してください（クラッシュや消失に備えるため）。
- テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定し、意図しない環境読み込みを止めると良いです。
- ニュースの RSS 取得は外部ネットワークに依存するため、フェイルセーフ（ソースごとの個別エラーハンドリング）を組み込んでいますが、常時監視をおすすめします。

---

もし README にサンプルスクリプト、CI 用のセットアップやより詳細な API リファレンスを追加したい場合は、どの部分を拡張するか教えてください。