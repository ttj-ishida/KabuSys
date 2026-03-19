# KabuSys

日本株向けの自動売買システム用ライブラリ（KabuSys）のリポジトリ内ドキュメントです。  
この README はソースコード（src/kabusys/**）を基に作成しています。

## プロジェクト概要

KabuSys は日本株のデータ取得・ETL・特徴量生成・シグナル生成・ニュース収集・監査ログ管理など、
自動売買パイプラインを構築するためのモジュール群を提供します。主に以下の役割を持つレイヤーで構成されています。

- Data layer: J-Quants API からのデータ取得、DuckDB での永続化、品質チェック、カレンダー管理、ニュース収集など
- Research / Feature layer: ファクター（Momentum / Volatility / Value 等）の計算、特徴量正規化
- Strategy layer: 正規化済み特徴量と AI スコアを統合して売買シグナルを生成
- Execution / Audit layer: シグナル・発注・約定・ポジション・監査ログのスキーマ定義（発注実装は別途）

設計上のポイント:
- DuckDB をデータストアに利用（オンディスクまたは :memory:）
- J-Quants API の利用を想定（トークン管理・レート制御・リトライ等を実装）
- ルックアヘッドバイアス防止のため、target_date 時点のデータのみを用いる方針
- 冪等性（idempotent）を意識した DB 保存処理（ON CONFLICT / トランザクション利用）
- 外部依存を最小化（pandas 等を使わず標準ライブラリ中心で実装）

## 主な機能一覧

- データ取得・保存
  - J-Quants から日次株価・財務データ・マーケットカレンダー取得（kabusys.data.jquants_client）
  - raw / processed / feature / execution 層の DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - 差分 ETL と日次 ETL ジョブ（kabusys.data.pipeline）
- データ品質・カレンダー
  - 市場カレンダー管理（営業日判定、next/prev trading day 等）（kabusys.data.calendar_management）
  - 品質チェック（quality モジュールを想定）と ETL 後の問題収集
- ニュース収集
  - RSS フィードの安全な取得・前処理・記事保存・銘柄抽出（kabusys.data.news_collector）
  - SSRF 対策、gzip 制限、XML の安全パース等の防御処理を実装
- リサーチ / 特徴量
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）（kabusys.research.factor_research）
  - Z スコア正規化ユーティリティ（kabusys.data.stats）
  - 特徴量ビルド（features テーブルへの正規化・UPSERT）（kabusys.strategy.feature_engineering）
  - 研究用の将来リターン計算・IC 計算・要約統計（kabusys.research.feature_exploration）
- シグナル生成
  - 正規化済み特徴量と AI スコアを統合して final_score を計算し、BUY/SELL シグナルを生成（kabusys.strategy.signal_generator）
  - Bear レジーム抑制やエグジット（ストップロス等）判定を実装
- 監査（Audit）
  - signal_events / order_requests / executions 等の監査テーブル DDL（kabusys.data.audit）

## 必要な環境変数（設定）

kabusys.config.Settings で参照される主な環境変数:

必須:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD : kabuステーション等の API パスワード
- SLACK_BOT_TOKEN : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID : Slack 通知先チャンネル ID

オプション（デフォルト値あり）:
- KABUSYS_ENV : 環境 (development / paper_trading / live)。デフォルト `development`
- LOG_LEVEL : ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）。デフォルト `INFO`
- KABU_API_BASE_URL : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite パス（デフォルト: data/monitoring.db）

自動 .env 読込:
- プロジェクトルート（.git または pyproject.toml を基準）にある `.env` と `.env.local` を自動で読み込みます。
- 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

## セットアップ手順

1. Python と依存パッケージ
   - 推奨: Python 3.9+（コードは型ヒントに沿っており、最新の Python を想定）
   - 必要な主なパッケージ（例）:
     - duckdb
     - defusedxml
   - pip でインストール例:
     ```bash
     python -m pip install duckdb defusedxml
     ```
   - （プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください）

2. リポジトリのクローン / ファイル配置
   - ソースが `src/` にあることを想定しています。パッケージをローカルで使う場合:
     ```bash
     git clone <repo-url>
     cd <repo>
     export PYTHONPATH=$(pwd)/src:$PYTHONPATH
     ```

3. 環境変数の準備
   - `.env` または環境変数で必須項目を設定します（例: JQUANTS_REFRESH_TOKEN 等）。
   - サンプル `.env`（一例）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

4. DuckDB スキーマ初期化
   - データベースファイルを作成し、テーブルを初期化します:
     ```bash
     python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
     ```
   - メモリ DB を使う場合は `":memory:"` を指定できます（テスト用途）:
     ```bash
     python -c "from kabusys.data.schema import init_schema; init_schema(':memory:')"
     ```

## 使い方（簡易例）

以下はライブラリを直接インポートして使う最小の利用例です。実運用ではジョブスケジューラ（cron / Airflow / Prefect 等）から呼び出します。

1. 日次 ETL を実行（市場カレンダー更新・株価・財務を取得）
   ```python
   from datetime import date
   import duckdb
   from kabusys.data.schema import get_connection, init_schema
   from kabusys.data.pipeline import run_daily_etl

   conn = init_schema('data/kabusys.duckdb')
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```

2. 特徴量をビルド（features テーブルに保存）
   ```python
   from datetime import date
   from kabusys.data.schema import get_connection, init_schema
   from kabusys.strategy import build_features

   conn = init_schema('data/kabusys.duckdb')
   count = build_features(conn, target_date=date.today())
   print(f"features upserted: {count}")
   ```

3. シグナル生成（signals テーブルへ保存）
   ```python
   from datetime import date
   from kabusys.data.schema import get_connection, init_schema
   from kabusys.strategy import generate_signals

   conn = init_schema('data/kabusys.duckdb')
   total = generate_signals(conn, target_date=date.today())
   print(f"signals generated: {total}")
   ```

4. ニュース収集ジョブの実行
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

   conn = init_schema('data/kabusys.duckdb')
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={'7203','6758'})
   print(results)
   ```

5. カレンダー更新ジョブ（夜間バッチ）
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.data.calendar_management import calendar_update_job

   conn = init_schema('data/kabusys.duckdb')
   saved = calendar_update_job(conn)
   print(f"calendar_saved: {saved}")
   ```

注意:
- 上記例は同期的な呼び出しです。実運用ではログ設定、エラー処理、リトライ、ジョブスケジューリング等を組み合わせてください。
- J-Quants API はレート制限やトークン管理が必要です。settings（環境変数）を必ず設定してください。

## ディレクトリ構成（主なファイル / モジュール）

リポジトリ内の `src/kabusys` 配下の主要モジュール（抜粋）:

- kabusys/
  - __init__.py
  - config.py
    - 環境変数・設定管理（自動 .env ロード、Settings クラス）
  - data/
    - __init__.py
    - jquants_client.py    : J-Quants API クライアント（取得・保存関数）
    - news_collector.py    : RSS ニュース収集・保存・銘柄抽出
    - schema.py            : DuckDB スキーマ定義と init_schema / get_connection
    - stats.py             : zscore_normalize 等の統計ユーティリティ
    - pipeline.py          : ETL パイプライン（run_daily_etl 等）
    - calendar_management.py : 市場カレンダー管理・更新ジョブ
    - audit.py             : 監査ログ DDL と初期化
    - features.py          : data.stats の再エクスポート
  - research/
    - __init__.py
    - factor_research.py   : Momentum/Volatility/Value 等のファクター計算
    - feature_exploration.py : 将来リターン / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py : features テーブル生成（正規化・ユニバースフィルタ等）
    - signal_generator.py    : final_score 計算と signals 生成
  - execution/
    - __init__.py（発注層のエントリ、実装は外部や後続実装を想定）
  - monitoring/（監視・運用用 DB / ロギング等は monitoring に配置想定）

（上記はソースから抽出した主要ファイル一覧です。実際のリポジトリには README・テスト・CI 設定等が別にある可能性があります。）

## 開発・運用上の注意点

- 環境分離: KABUSYS_ENV によって動作モード（development/paper_trading/live）を切り替えます。実環境（live）では必ず十分なテスト・モニタリングを行ってください。
- DB トランザクション: 多くの保存処理はトランザクションで原子性を担保していますが、バックアップやマイグレーションは慎重に実施してください。
- セキュリティ: RSS フィード取得や外部 API 呼び出しは SSRF / XML Bomb / 大容量レスポンス等に注意した実装になっています。設定・ホワイトリスト運用を推奨します。
- テスト: 外部 API をモックしてユニットテストを作成してください。モジュール内部で注入可能なパラメータ（id_token など）を活用するとテスト容易性が向上します。

---

ご不明な点や README に追加したい具体的な利用例（Airflow の DAG、Docker のサンプル、CI 設定など）があれば教えてください。必要に応じてサンプルコードや .env.example を作成します。