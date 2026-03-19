# KabuSys

KabuSys は日本株向けの自動売買基盤のプロジェクトです。データ収集（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、発注・監査用のスキーマを提供します。DuckDB を永続ストレージとして利用し、機能はモジュール単位で独立しているため、研究・バックテスト・本番運用まで同一コードベースで運用できます。

## 特徴（機能一覧）
- データ収集
  - J-Quants API クライアント（株価日足、財務、マーケットカレンダー）
  - レート制限遵守、リトライ・トークン自動リフレッシュ、ページネーション対応
- ETL（data.pipeline）
  - 差分取得（バックフィル対応）、保存（冪等）と品質チェック
  - 日次 ETL エントリポイント（run_daily_etl）
- データスキーマ（DuckDB）
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化（init_schema）
- 研究（research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Spearman）、統計サマリー
- 特徴量エンジニアリング（strategy.feature_engineering）
  - ファクター正規化（Z スコア）、ユニバースフィルタ、features テーブルへの UPSERT
- シグナル生成（strategy.signal_generator）
  - コンポーネントスコア（momentum/value/volatility/liquidity/news）を統合して final_score を算出
  - BUY/SELL のシグナル判定と signals テーブルへの保存（冪等）
- ニュース収集（data.news_collector）
  - RSS フィード取得、前処理、raw_news への冪等保存、銘柄コード抽出と紐付け
  - SSRF・XML 攻撃対策、応答サイズ制限
- マーケットカレンダー管理（data.calendar_management）
  - JPX カレンダーの差分更新、営業日判定ユーティリティ
- 発注・監査（data.audit / schema）
  - 発注・約定・ポジション・監査ログ用のテーブル設計（監査トレーサビリティ）

## 動作環境
- Python >= 3.10（PEP 604 の型ヒント `X | Y` を使用）
- 必須ライブラリ（例）
  - duckdb
  - defusedxml
  - （標準ライブラリ以外の依存はプロジェクトの requirements に従ってください）

## セットアップ手順

1. リポジトリをクローン
   - git clone …（省略）

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux / macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - または最小限:
     - pip install duckdb defusedxml

4. パッケージをインストール（開発モード）
   - pip install -e .

5. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動的に読み込まれます（ただし環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。
   - 必須環境変数（アプリ起動時に Settings で参照するもの）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション等のパスワード
     - SLACK_BOT_TOKEN: Slack 通知用トークン
     - SLACK_CHANNEL_ID: Slack チャンネル ID
   - 任意（デフォルト値あり）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/…
     - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN="xxxxxxxxxxxxxxxxxxxxxxxx"
   SLACK_BOT_TOKEN="xoxb-..."
   SLACK_CHANNEL_ID="C01234567"
   KABU_API_PASSWORD="secret"
   DUCKDB_PATH="data/kabusys.duckdb"
   KABUSYS_ENV="development"
   LOG_LEVEL="INFO"
   ```

6. DuckDB スキーマ初期化
   - Python REPL やスクリプトで実行:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     # or in-memory: init_schema(":memory:")
     ```
   - これにより必要なテーブルとインデックスが作成されます。

## 使い方（主要ワークフロー例）

以下はよく使う操作の例です。各関数は DuckDB 接続を受け取り動作します。

1. 日次 ETL（市場カレンダー・株価・財務の差分取得）
   ```python
   from datetime import date
   import duckdb
   from kabusys.data.schema import init_schema, get_connection
   from kabusys.data.pipeline import run_daily_etl

   conn = init_schema("data/kabusys.duckdb")
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```

2. 特徴量の構築（features テーブルへ保存）
   ```python
   from datetime import date
   from kabusys.strategy import build_features
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   count = build_features(conn, target_date=date(2025, 1, 15))
   print(f"upserted features: {count}")
   ```

3. シグナル生成（signals テーブルへ保存）
   ```python
   from datetime import date
   from kabusys.strategy import generate_signals
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   total_signals = generate_signals(conn, target_date=date(2025, 1, 15))
   print(f"signals saved: {total_signals}")
   ```

4. ニュース収集ジョブ
   ```python
   from kabusys.data.news_collector import run_news_collection
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   known_codes = {"7203", "6758", "6501"}  # 既知の銘柄コードセット
   results = run_news_collection(conn, known_codes=known_codes)
   print(results)
   ```

5. カレンダー更新ジョブ（夜間バッチ）
   ```python
   from kabusys.data.calendar_management import calendar_update_job
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   saved = calendar_update_job(conn)
   print(f"calendar rows saved: {saved}")
   ```

6. J-Quants からデータを直接取得して保存（例）
   ```python
   from kabusys.data import jquants_client as jq
   from kabusys.data.schema import get_connection
   from datetime import date

   conn = get_connection("data/kabusys.duckdb")
   recs = jq.fetch_daily_quotes(date_from=date(2025,1,1), date_to=date(2025,1,15))
   saved = jq.save_daily_quotes(conn, recs)
   print(saved)
   ```

注意:
- すべての API 操作は冪等に設計されています（ON CONFLICT DO UPDATE / DO NOTHING 等）。
- target_date の扱いは「その日までに利用可能だったデータ」を意識した設計です（ルックアヘッドバイアス防止）。

## 主要モジュールとディレクトリ構成

プロジェクトの主要ファイル構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント + 保存機能
    - news_collector.py     # RSS ニュース収集・保存
    - schema.py             # DuckDB スキーマ定義・初期化
    - stats.py              # 統計ユーティリティ（Z スコア等）
    - pipeline.py           # ETL パイプライン（run_daily_etl 等）
    - calendar_management.py# カレンダー管理・更新ジョブ
    - audit.py              # 監査ログ用スキーマ
    - features.py           # data 側公開インターフェース（zscore の再エクスポート）
  - research/
    - __init__.py
    - factor_research.py    # ファクター計算（momentum/volatility/value）
    - feature_exploration.py# 将来リターン / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py# features の構築（正規化・フィルタ）
    - signal_generator.py   # final_score 計算・シグナル生成
  - execution/               # 発注関連（現状空のパッケージプレースホルダ）
  - monitoring/              # 監視/メトリクス用（プレースホルダ）

（上記はソースコード内のドキュメント基づいた主要機能の抜粋です。）

## 開発・運用メモ（設計上の注意）
- 型ヒントで Python 3.10+ の構文を利用しています。
- 環境変数は .env / .env.local をプロジェクトルートに置くと自動読み込みされます（ただしテストや特殊ケースでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化可能）。
- DuckDB スキーマ初期化は一度実行すれば良いですが、スキーマは冪等に作成されるため再実行しても安全です。
- J-Quants API のレート制限（120 req/min）やリトライポリシーがクライアントに組み込まれています。
- ニュース収集は SSRF、XML Bomb、巨大レスポンスなどを想定した防御を実装しています。
- strategy モジュールは発注層（execution）に依存せず、signals テーブルに書き出すことで発注パイプラインと疎結合になっています。

## サポート・貢献
- バグレポートや機能提案は Issue を作成してください。
- コントリビュートする場合はコードスタイル・テスト・ドキュメントを用意してください。

---

この README はコードベース内のドキュメント文字列（docstring）と設計コメントを基にまとめています。詳細な設計仕様（StrategyModel.md / DataPlatform.md / DataSchema.md 等）がプロジェクトに存在する想定ですので、運用前にそちらも参照してください。