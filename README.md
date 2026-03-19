# KabuSys

KabuSys は日本株向けの自動売買システム（データ基盤・特徴量生成・戦略シグナル生成・監査用スキーマ等）を提供する Python パッケージです。J-Quants API から市場データ・財務データ・市場カレンダーを取得して DuckDB に保存し、研究で作成した生ファクターを正規化・合成して戦略シグナルを生成します。ニュース収集・銘柄抽出や監査ログのためのスキーマも含まれます。

バージョン: 0.1.0

---

## 主な機能一覧

- データ取得 / 保存
  - J-Quants API クライアント（jquants_client）
    - 株価日足、財務データ、市場カレンダーの取得（ページネーション対応・リトライ・トークン自動更新）
    - DuckDB へ冪等に保存する save_* 関数
  - ETL パイプライン（data.pipeline）
    - 差分更新、バックフィル、品質チェックを含む日次 ETL
  - 市場カレンダー更新ジョブ（data.calendar_management）

- データスキーマ
  - DuckDB 用のスキーマ初期化（data.schema.init_schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義（raw_prices, prices_daily, features, signals, orders, executions, positions 等）

- ニュース収集
  - RSS フィード取得と前処理（data.news_collector）
  - URL 正規化・SSRF 対策・記事 ID 生成・銘柄コード抽出・DB 保存（raw_news, news_symbols）

- 研究 / 特徴量
  - ファクター計算（research.factor_research）
    - Momentum / Volatility / Value 等の定量ファクターを計算
  - 特徴量探索ユーティリティ（research.feature_exploration）
    - 将来リターン計算、IC（Information Coefficient）、統計サマリー
  - Z スコア正規化ユーティリティ（data.stats / data.features）

- 戦略
  - 特徴量の正規化・合成・features テーブルへの書き込み（strategy.feature_engineering.build_features）
  - features と ai_scores を統合して BUY/SELL シグナルを生成し signals テーブルへ書き込む（strategy.signal_generator.generate_signals）

- 監査 / トレーサビリティ
  - シグナル→発注→約定の監査ログ用スキーマ（data.audit）

---

## セットアップ手順

前提: Python 3.9+（型アノテーションと pathlib の使用を踏まえた想定）とネットワークアクセス（J-Quants API、RSS フィード）を利用できる環境。

1. リポジトリのクローン / ソースを取得
   - 例: git clone ...（パッケージは src/kabusys に配置）

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate

3. 必要なパッケージをインストール
   - 必須の依存（例）
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

   （メタ情報がないため、プロジェクトの requirements.txt / pyproject.toml を参照してください。追加の依存がある場合はそちらに従ってください。）

4. 環境変数の設定
   - プロジェクトルートに `.env` を作成するか、OS 環境変数で設定します。自動ロードは config.py により .env → .env.local の順で行われ、既存の OS 環境変数は保護されます。
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API のパスワード（発注機能を使う場合）
     - SLACK_BOT_TOKEN — Slack 通知を使う場合の Bot トークン
     - SLACK_CHANNEL_ID — Slack チャンネル ID
   - 任意/デフォルト:
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/...（デフォルト: INFO）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）

   - 例（.env）
     JQUANTS_REFRESH_TOKEN=xxxxxxxx
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトから schema.init_schema() を実行して DB を準備します。
   - 例:
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")

---

## 使い方（主要な操作例）

以下は代表的な利用例です。必要に応じてスクリプト化してバッチ or Cron で実行してください。

1. DuckDB の初期化（1回）
   ```python
   from kabusys.data import schema

   conn = schema.init_schema("data/kabusys.duckdb")
   ```

2. 日次 ETL の実行
   - J-Quants から差分取得して保存、品質チェックまで含めて実行します。
   ```python
   from datetime import date
   import duckdb
   from kabusys.data import pipeline, schema

   conn = schema.init_schema("data/kabusys.duckdb")
   result = pipeline.run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```

3. 特徴量の構築（features テーブルへの保存）
   - research の生ファクターを呼び出して正規化・フィルタリングし、features テーブルへ UPSERT します。
   ```python
   from datetime import date
   from kabusys.strategy import build_features
   from kabusys.data import schema

   conn = schema.get_connection("data/kabusys.duckdb")
   count = build_features(conn, target_date=date(2025, 1, 2))
   print(f"features upserted: {count}")
   ```

4. シグナル生成（signals テーブルへ）
   - features と ai_scores、positions を参照して BUY / SELL シグナルを生成します。
   ```python
   from datetime import date
   from kabusys.strategy import generate_signals
   from kabusys.data import schema

   conn = schema.get_connection("data/kabusys.duckdb")
   total = generate_signals(conn, target_date=date(2025, 1, 2))
   print(f"signals written: {total}")
   ```

5. ニュース収集ジョブの実行
   - RSS を取得して raw_news に保存し、既知銘柄が与えられていれば news_symbols に紐付けます。
   ```python
   from kabusys.data.news_collector import run_news_collection
   from kabusys.data import schema

   conn = schema.get_connection("data/kabusys.duckdb")
   known_codes = {"7203", "6758", "2432"}  # 例: 有効銘柄コードセット
   res = run_news_collection(conn, known_codes=known_codes)
   print(res)
   ```

6. 市場カレンダー更新ジョブ（夜間バッチ）
   ```python
   from kabusys.data.calendar_management import calendar_update_job
   from kabusys.data import schema

   conn = schema.get_connection("data/kabusys.duckdb")
   saved = calendar_update_job(conn)
   print(f"calendar saved: {saved}")
   ```

注意:
- 各処理は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取る設計です。スクリプト実行時は同一 DB ファイルへ接続してください。
- J-Quants API 呼び出しは rate limit・リトライ・401 自動更新などを考慮して実装されています。API トークンとネットワーク環境を準備してください。

---

## ディレクトリ構成（概要）

以下は src/kabusys 以下の主要なモジュールと役割です（抜粋）。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動ロード（.env / .env.local）、設定取得用 Settings クラス
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（fetch_* / save_*）
    - news_collector.py
      - RSS 取得・前処理・DB 保存・銘柄抽出
    - schema.py
      - DuckDB スキーマ定義と init_schema / get_connection
    - stats.py
      - zscore_normalize（クロスセクション正規化）
    - pipeline.py
      - ETL パイプライン（run_daily_etl、run_prices_etl 等）
    - calendar_management.py
      - カレンダー更新・営業日判定ユーティリティ
    - audit.py
      - 発注〜約定の監査ログスキーマ
    - features.py
      - data.stats の公開ラッパー
  - research/
    - __init__.py
    - factor_research.py
      - momentum / volatility / value 等のファクター計算（prices_daily / raw_financials を参照）
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py
      - 生ファクターを正規化・フィルタし features テーブルへ保存
    - signal_generator.py
      - features / ai_scores を統合して BUY/SELL シグナルを生成
  - execution/
    - __init__.py
    - （発注・execution 層の実装箇所を想定）
  - monitoring/
    - （監視・アラート周りの実装箇所を想定）

---

## 注意事項 / 運用上のヒント

- 環境変数管理
  - .env/.env.local の自動ロードは config.py によりプロジェクトルート（.git または pyproject.toml）を起点に探索されます。テスト等で自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- DuckDB のバックアップ / 容量
  - DuckDB ファイルは定期的にバックアップしてください。raw 層は大容量になり得ます。

- API レート制限・鍵管理
  - J-Quants のレート制限（120 req/min）を守る必要があります。トークン管理は厳重に行ってください。

- ルックアヘッドバイアスの防止
  - ファクター計算・シグナル生成は target_date 時点のデータのみを使用するよう設計されていますが、運用時にもデータの取得日時（fetched_at）や ETL の実行タイミングに注意してください。

- テスト容易化
  - 多くの関数は id_token の注入や URLopen の差し替え（モック）に対応できるよう設計されています。ユニットテストでは外部 API 呼び出しをモックしてください。

---

もし README に追加してほしい内容（CLI の提供、具体的なデプロイ手順、CI 設定、より詳細な API 使用例やサンプルデータの準備方法など）があれば教えてください。必要に応じてサンプルスクリプトや .env.example のテンプレートも作成します。