# KabuSys

日本株自動売買プラットフォーム用ライブラリ（KabuSys）。  
データ収集（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなどを含むモジュール群を提供します。

## プロジェクト概要
- DuckDB をストレージとして用い、J-Quants API から株価・財務・カレンダーなどのデータを取得・保存する ETL パイプラインを備えています。
- 研究（research）で算出された生ファクターを加工して特徴量（features）を作成し、score を統合して売買シグナル（signals）を生成します。
- ニュース（RSS）収集・前処理・銘柄紐付け機能、マーケットカレンダー管理、監査ログ（order/exec トレース）をサポートします。
- 発注層（execution）とは分離された設計で、戦略層は発注 API に依存しない形でシグナルを出力します。

## 主な機能一覧
- データ取得・保存
  - J-Quants クライアント（fetch / save）：株価日足、財務諸表、マーケットカレンダー
  - DuckDB スキーマの初期化（冪等）
- ETL
  - 差分更新（バックフィル対応）、品質チェック統合、日次 ETL run_daily_etl
- 研究・特徴量
  - モメンタム / ボラティリティ / バリュー等のファクター計算（research/factor_research）
  - Z スコア正規化ユーティリティ（data.stats）
  - 特徴量作成（strategy/feature_engineering.build_features）
- シグナル生成
  - features と ai_scores を統合して final_score を算出、BUY/SELL シグナルを生成（strategy/signal_generator.generate_signals）
  - Bear レジーム抑制、エグジット判定（ストップロス等）
- ニュース収集
  - RSS フェッチ、安全対策（SSRF/gzip/サイズ上限/XML ハンドリング）と raw_news 保存、銘柄抽出（data/news_collector）
- カレンダー管理
  - JPX カレンダー更新ジョブ、営業日 / 前後営業日計算（data/calendar_management）
- 監査・トレーサビリティ
  - signal_events / order_requests / executions 等の監査テーブル群（data/audit）

## 前提・依存関係
- Python 3.10+（typing の Union | を利用）
- 必須パッケージ（例）
  - duckdb
  - defusedxml
- 実際のプロジェクトでは requirements.txt / pyproject.toml に依存パッケージを定義してください。

## 環境変数（主なもの）
以下はコード中で参照される主な環境変数です（.env に定義可能）。

- JQUANTS_REFRESH_TOKEN: J‑Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境 (development / paper_trading / live)（デフォルト: development）
- LOG_LEVEL: ログレベル (DEBUG/INFO/...)（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: 自動 .env ロードを無効化

config モジュールはプロジェクトルート（.git または pyproject.toml の存在）を探索して `.env` / `.env.local` を自動で読み込みます。

## セットアップ手順（開発環境）
1. ソースを取得
   - git clone などでプロジェクトを取得してください。

2. 仮想環境作成とパッケージインストール
   - 例（venv + pip）:
     ```
     python -m venv .venv
     source .venv/bin/activate
     pip install -U pip
     pip install duckdb defusedxml
     ```
   - 実際は pyproject.toml / requirements.txt に合わせてインストールしてください。

3. 環境変数（.env）を作成
   - プロジェクトルートに `.env` を作成し、必要項目を設定してください。例:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
   - テスト時に自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

## 使い方（簡単なコード例）
下記は基本的な操作の例です。プロダクションジョブや CLI は別途用意してください。

- DuckDB スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema
  db_path = "data/kabusys.duckdb"
  conn = init_schema(db_path)
  ```

- 日次 ETL（J-Quants からデータ取得 → 保存 → 品質チェック）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl, get_connection

  conn = get_connection("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量（features）構築
  ```python
  from datetime import date
  import duckdb
  from kabusys.strategy import build_features

  conn = duckdb.connect("data/kabusys.duckdb")
  count = build_features(conn, date.today())
  print(f"features upserted: {count}")
  ```

- シグナル生成
  ```python
  from datetime import date
  import duckdb
  from kabusys.strategy import generate_signals

  conn = duckdb.connect("data/kabusys.duckdb")
  cnt = generate_signals(conn, date.today(), threshold=0.6)
  print(f"signals generated: {cnt}")
  ```

- ニュース収集ジョブ
  ```python
  import duckdb
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES, extract_stock_codes

  conn = duckdb.connect("data/kabusys.duckdb")
  # known_codes は銘柄コードセット（例: {"7203", "6758", ...}）
  res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=None)
  print(res)
  ```

- カレンダー更新（夜間バッチ）
  ```python
  import duckdb
  from kabusys.data.calendar_management import calendar_update_job

  conn = duckdb.connect("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"market calendar saved: {saved}")
  ```

## 推奨ワークフロー（日常運用の一例）
1. 毎朝（または夜間）calendar_update_job でカレンダーを更新する
2. run_daily_etl を実行して当日（営業日）までの差分を取り込む
3. build_features で特徴量テーブルを再生成
4. generate_signals で当日のシグナルを作成
5. signals を元に execution 層で発注を実行（発注処理は本プロジェクトの execution パッケージまたは別実装）

## 注意点・設計上の特徴
- J-Quants API との通信はレートリミット（120 req/min）やリトライ（指数バックオフ）、401 時の自動トークンリフレッシュを備えています。
- ETL / 保存は冪等性を重視（ON CONFLICT を使った upsert）しています。
- ルックアヘッドバイアス対策：特徴量・シグナル生成は target_date 時点で利用可能なデータのみを使用することを意識した設計です。
- ニュース収集は SSRF や XML Bomb、Gzip Bomb、サイズオーバーなどの対策を実装しています。

## ディレクトリ構成
主要ファイル／モジュール一覧（src/kabusys 以下）

- src/kabusys/
  - __init__.py  (パッケージ定義、version)
  - config.py    (環境変数 / 設定管理)
  - data/
    - __init__.py
    - jquants_client.py        (J-Quants API クライアント、save / fetch / retry / rate limit)
    - news_collector.py       (RSS 収集・前処理・DB 保存)
    - schema.py               (DuckDB スキーマ定義と init_schema)
    - stats.py                (zscore_normalize 等統計ユーティリティ)
    - pipeline.py             (ETL パイプライン: run_daily_etl 等)
    - features.py             (zscore_normalize の公開再エクスポート)
    - calendar_management.py  (market_calendar 管理、営業日判定)
    - audit.py                (監査ログスキーマ)
    - execution/              (発注関連モジュール（雛形）)
  - research/
    - __init__.py
    - factor_research.py      (mom/vol/value のファクター計算)
    - feature_exploration.py  (forward returns, IC, summary, rank)
  - strategy/
    - __init__.py
    - feature_engineering.py  (features の構築処理)
    - signal_generator.py     (final_score 計算と signals テーブル書き込み)
  - monitoring/               (監視・メトリクス等: 設計領域)
  - execution/                (発注実装のためのプレースホルダー)

（上記はソース内の docstring とファイル名に基づく抜粋です）

## 開発・テストのヒント
- config モジュールはプロジェクトルートを自動検出して `.env` を読み込みます。単体テスト等で自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB はテスト時に ":memory:" を指定してインメモリ DB を使用できます（init_schema(":memory:")）。
- network IO 部分（jquants_client._request、news_collector._urlopen など）はモックしやすいように設計されています。

## ライセンス・貢献
- 本 README はコードベースの概要を説明するためのドキュメントです。実運用ではセキュリティ（トークン管理、ネットワーク設定）、監査、バックテスト、フォールバック処理を入念に検討してください。
- 貢献（Pull Request / Issue）は歓迎します。PR 前に設計意図や互換性に関して議論してください。

--- 

問題があれば、README の追加項目（CLI 例、詳細な .env.example、CI / デプロイ手順など）を追記します。どの内容を充実させたいか教えてください。