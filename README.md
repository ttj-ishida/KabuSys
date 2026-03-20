# KabuSys

日本株向けの自動売買基盤ライブラリ（ミニマム実装）。  
データ取得（J-Quants）、ETL、データスキーマ、特徴量計算、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなどを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は以下を目的とした内部ライブラリです。

- J-Quants API からの株価 / 財務 / カレンダー取得と DuckDB への冪等保存
- ETL パイプライン（差分取得 / バックフィル / 品質チェック）
- 研究用ファクター計算（momentum / volatility / value 等）
- 特徴量正規化・合成（feature layer）
- 戦略シグナル生成（final_score に基づく BUY/SELL の生成）
- ニュース収集（RSS）と銘柄紐付け（SSRF 対策・トラッキング除去）
- マーケットカレンダー管理（営業日判定 / next/prev / 範囲取得）
- DuckDB スキーマ定義と監査ログテーブル

設計方針は「ルックアヘッドバイアス回避」「冪等処理」「外部発注層への直接依存を持たない」「テストしやすさ」を重視しています。

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（レートリミット、リトライ、トークン自動リフレッシュ、ページネーション）
  - 生データ保存用の save_* 関数（raw_prices / raw_financials / market_calendar）を提供
- data/schema.py
  - DuckDB のスキーマ（Raw / Processed / Feature / Execution / Audit 等）の定義と初期化
  - init_schema(db_path) で DB を初期化
- data/pipeline.py
  - 日次 ETL 実行（run_daily_etl）
  - prices / financials / calendar の差分 ETL ヘルパ
- data/news_collector.py
  - RSS 収集、記事正規化（URL トラッキング除去）、raw_news への冪等保存、銘柄抽出・紐付け
  - SSRF 対策、gzip/サイズ制限、XML の安全パース
- data/calendar_management.py
  - market_calendar の更新ジョブ、営業日判定・次営業日取得・範囲取得等
- research/
  - factor_research.py: momentum / volatility / value 等のファクター計算（prices_daily / raw_financials を参照）
  - feature_exploration.py: 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ
- strategy/
  - feature_engineering.py: 生ファクターの正規化・ユニバースフィルタ・features テーブルへの書き込み
  - signal_generator.py: features + ai_scores を組み合わせた final_score 計算、BUY/SELL シグナル生成、signals テーブルへの保存
- その他
  - data/stats.py: zscore 正規化ユーティリティ
  - config.py: 環境変数読み込み（.env 自動ロード機能）、設定オブジェクト（settings）

---

## 要件

- Python 3.10+
- 必須パッケージ（一例）
  - duckdb
  - defusedxml

（プロジェクトに requirements.txt があればそちらを使用してください）

インストール例:
```
python -m pip install duckdb defusedxml
```

---

## セットアップ手順

1. リポジトリをチェックアウト / クローンする。

2. Python 仮想環境を作る（推奨）:
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール:
   ```
   pip install duckdb defusedxml
   ```

4. 環境変数を設定（.env をプロジェクトルートに置くと自動ロードされます）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD : kabuステーション API パスワード（発注機能使用時）
     - SLACK_BOT_TOKEN : Slack 通知を使う場合
     - SLACK_CHANNEL_ID : Slack 通知チャンネルID
   - 任意 / デフォルトあり:
     - KABUSYS_ENV : development / paper_trading / live（デフォルト development）
     - LOG_LEVEL : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
     - DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH : 監視用 SQLite 等（デフォルト data/monitoring.db）
   - 自動 .env ロードを無効にする場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   簡易例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=your_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマ初期化:
   Python REPL またはスクリプトで:
   ```
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```
   init_schema は必要なディレクトリを作成し、全テーブルを作成します（冪等）。

---

## 使い方（クイックスタート）

- DB 初期化（1回）:
  ```
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL 実行:
  ```
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  # conn は init_schema / get_connection で取得した DuckDB 接続
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量（features）を構築:
  ```
  from datetime import date
  from kabusys.strategy import build_features
  count = build_features(conn, target_date=date.today())
  print("features upserted:", count)
  ```

- シグナル生成:
  ```
  from datetime import date
  from kabusys.strategy import generate_signals
  total = generate_signals(conn, target_date=date.today(), threshold=0.6)
  print("signals written:", total)
  ```

- ニュース収集ジョブ（RSS から raw_news へ保存、既知銘柄で紐付け）:
  ```
  from kabusys.data.news_collector import run_news_collection
  # known_codes は銘柄コードセット（例: {"7203", "6758", ...}）
  results = run_news_collection(conn, sources=None, known_codes=known_codes)
  print(results)
  ```

- カレンダー更新ジョブ:
  ```
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print("market_calendar saved:", saved)
  ```

- 設定参照:
  ```
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)
  print(settings.env, settings.is_live)
  ```

注意:
- 各処理はデータの存在チェック・冪等性を備えているため、スケジューラで安全に定期実行できます。
- 発注・ブローカー連携部分は execution レイヤーが骨組みとして存在しますが、実際のブローカー API 実装は別途必要です。

---

## ディレクトリ構成

主要ファイルとモジュール（リポジトリ src/kabusys を基準）:

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
    - (その他: execution 用モジュールなど)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - execution/ (発注実装のためのプレースホルダ)
  - monitoring/ (監視・メトリクス用モジュール想定)

（上記は本 README に含まれる実装部分の要約です。詳細はソース内の docstring を参照してください。）

---

## 設計上の注意点・運用メモ

- 環境:
  - settings は .env を自動ロードします（プロジェクトルート判定: .git または pyproject.toml があるディレクトリ）。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。
- データベース:
  - DuckDB を採用。init_schema は冪等にテーブルを作成します。初期化後は get_connection を用いて接続を取得してください。
- ルックアヘッドバイアス対策:
  - ファクター計算 / シグナル生成は target_date 時点のデータのみを利用する設計です。fetched_at など取得時刻も保存してトレーサビリティを確保します。
- ニュース収集:
  - URL 正規化・トラッキング除去・SSRF 対策・XML の安全パースを行います。既知銘柄セットで銘柄抽出を行うことを推奨します。
- ログ:
  - LOG_LEVEL で出力レベルを制御してください。運用時は適切にローテーション/永続化を検討してください。

---

## 参考 / 追加情報

- 環境名（KABUSYS_ENV）には "development" / "paper_trading" / "live" のいずれかを指定してください。is_live / is_paper / is_dev プロパティで判定できます。
- strategy の重みや閾値は generate_signals の引数で上書きできます（辞書で部分指定し、自動で正規化されます）。
- J-Quants API レート制限（120 req/min）を尊重するため、内部で RateLimiter を使用しています。

---

この README はコードベースの主要な使い方と構成をまとめたものです。実装の詳細や拡張方法は各モジュールの docstring（ソース内コメント）を参照してください。必要であればセットアップ用スクリプト例や CI / デプロイ手順、requirements.txt の追記例も作成します。どの情報がさらに必要か教えてください。