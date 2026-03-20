# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
データ収集（J-Quants）、ETL、特徴量作成、シグナル生成、ニュース収集、マーケットカレンダー管理、DuckDB スキーマ・監査などを含むモジュール群で構成されています。

## 主な特徴
- J-Quants API と連携した差分取得・保存（レートリミット・リトライ・トークン自動更新対応）
- DuckDB を利用したローカルデータベース（Raw / Processed / Feature / Execution 層）
- 研究用ファクター計算（Momentum / Volatility / Value）
- 特徴量の Z スコア正規化と日付単位の冪等アップサート
- 戦略のシグナル生成（BUY / SELL 判定、Bear レジーム抑制、ストップロス）
- RSS ベースのニュース収集と記事→銘柄紐付け（SSRF 対策・トラッキング除去）
- マーケットカレンダー管理（営業日判定 / next/prev / 範囲取得）
- ETL 一括ジョブ（データ取得・保存・品質チェック）
- 監査ログ（signal → order → execution のトレーサビリティ）

## 必要条件
- Python 3.9+（型注釈等を考慮）
- pip, virtualenv 推奨
- ライブラリ例:
  - duckdb
  - defusedxml

（プロジェクト配布時の `pyproject.toml` / requirements に従ってインストールしてください）

## 環境変数（必須 / 推奨）
以下は Settings クラスが参照する主な環境変数です（.env ファイルで管理できます）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード（発注系を使う場合）
- SLACK_BOT_TOKEN — Slack 通知に使う Bot トークン
- SLACK_CHANNEL_ID — Slack 送信先チャンネル ID

任意（デフォルトあり）:
- KABUSYS_ENV — `development` / `paper_trading` / `live`（デフォルト: development）
- LOG_LEVEL — `DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用 DB など）（デフォルト: data/monitoring.db）

自動 .env ロードを無効化:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

.env 例（ルートに配置）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxx...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=hogehoge
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

## セットアップ手順（ローカル開発向け）
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb defusedxml
   - （プロジェクトのパッケージを editable install する場合）
     - pip install -e .

3. 環境変数を設定（.env をプロジェクトルートに置く）
   - 例: .env に必須変数を追加

4. DuckDB スキーマ初期化
   - Python スクリプトまたは REPL から:
     ```
     from kabusys.data.schema import init_schema, get_connection
     conn = init_schema("data/kabusys.duckdb")
     conn.close()
     ```
   - :memory: を使って一時 DB を作ることも可能:
     ```
     conn = init_schema(":memory:")
     ```

## 使い方（代表的な操作例）

- ETL（日次一括）
  ```
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  conn.close()
  ```

- 特徴量作成（features テーブルへ書き込み）
  ```
  from datetime import date
  from kabusys.data.schema import get_connection
  from kabusys.strategy import build_features

  conn = get_connection("data/kabusys.duckdb")
  count = build_features(conn, date(2025, 1, 31))
  print(f"upserted features: {count}")
  conn.close()
  ```

- シグナル生成（signals テーブルへ書き込み）
  ```
  from datetime import date
  from kabusys.data.schema import get_connection
  from kabusys.strategy import generate_signals

  conn = get_connection("data/kabusys.duckdb")
  total = generate_signals(conn, date(2025, 1, 31), threshold=0.6)
  print(f"signals written: {total}")
  conn.close()
  ```

- ニュース収集ジョブ（RSS）
  ```
  from kabusys.data.schema import get_connection
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  conn = get_connection("data/kabusys.duckdb")
  known_codes = {"7203","6758", ...}  # 既知銘柄コードセット
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  conn.close()
  ```

- カレンダー更新（夜間バッチ）
  ```
  from kabusys.data.schema import get_connection
  from kabusys.data.calendar_management import calendar_update_job

  conn = get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"calendar rows saved: {saved}")
  conn.close()
  ```

- J-Quants からのデータ取得（低レベル）
  ```
  from kabusys.data import jquants_client as jq
  rows = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,2,1))
  ```

## 注意点 / 設計上の注意
- 多くの処理は「target_date 時点のデータのみを使用する」ことでルックアヘッドバイアスを防止する設計です。
- DuckDB への書き込みは基本的に日付単位で置換（DELETE + bulk INSERT）し、トランザクションで原子性を確保します。
- J-Quants API はレート制限とリトライロジックを内蔵しています。認証トークンは自動更新されます。
- ニュース収集は SSRF（リダイレクト先含む）や XML 攻撃対策が組み込まれています。
- 環境変数の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を読み込みます。テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

## ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / Settings 管理
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py  — RSS ニュース収集
    - schema.py  — DuckDB スキーマ定義 / init_schema
    - stats.py  — zscore_normalize など統計ユーティリティ
    - pipeline.py  — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — カレンダー管理 / 更新ジョブ
    - features.py — data 層の公開 API（zscore_normalize の再エクスポート）
    - audit.py — 監査ログ DDL（途中まで定義）
  - research/
    - __init__.py
    - factor_research.py  — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — IC/将来リターン/統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py  — features テーブル生成（正規化等）
    - signal_generator.py     — signals テーブル生成（BUY/SELL 判定）
  - execution/  — 発注・execution 層（現状モジュール空）
  - monitoring/ — 監視用コード（SQLite など、実装箇所がある場合）

（README の目的上、主要なファイルのみ抜粋しています。実際のツリーは src/kabusys 以下の全ファイルを参照してください）

## 開発上のヒント
- DuckDB を使う関数は接続オブジェクトを引数で受け取るため、テストでは in-memory DB (`:memory:`) を使うと速くて便利です。
- settings はプロセス開始時に .env を自動読み込みします。テストで環境汚染を避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- ログレベルや KABUSYS_ENV を切り替えることで paper_trading / live の動作切り替えを想定できます（発注層と組み合わせて利用してください）。

---

必要であれば、以下を追加で用意できます：
- 実行用の小さな CLI スクリプト例（ETL の cron 化サンプル）
- .env.example のテンプレート
- ローカルでの簡易データセットを使った動作確認手順（サンプル CSV → DuckDB へのロード）