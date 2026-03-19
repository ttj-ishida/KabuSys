# KabuSys

KabuSys は日本株向けの自動売買／データプラットフォーム用ライブラリです。  
DuckDB を用いたデータ層、J-Quants からのデータ取得クライアント、ETL パイプライン、ニュース収集、ファクター計算（リサーチ用ユーティリティ）、監査ログなどを含みます。

主な設計方針：
- データ取得は冪等（ON CONFLICT / DO UPDATE）で保存
- Look-ahead bias を防ぐために取得時刻（fetched_at）を記録
- API レート制御・リトライ（J-Quants クライアント）
- DuckDB を中心とした軽量なデータレイヤ
- Research モジュールは発注 API にアクセスしない（安全）

---

## 機能一覧

- 環境設定管理（.env 自動ロード、必須環境変数チェック）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロード無効化可
- J-Quants API クライアント（jquants_client）
  - 日足（OHLCV）、四半期財務、JPX カレンダーの取得
  - レート制限（120 req/min）、リトライ、401 時のトークン自動リフレッシュ
  - DuckDB への保存ユーティリティ（冪等保存）
- ETL パイプライン（data.pipeline）
  - 差分取得（最終取得日からの差分＋バックフィル）
  - 日次 ETL 統合 run_daily_etl
  - 品質チェックの実行（data.quality）
- データスキーマの初期化（data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - init_schema(db_path) で DuckDB を初期化
- ニュース収集（data.news_collector）
  - RSS フィード取得、前処理、raw_news への保存、銘柄紐付け
  - SSRF 対策、XML の安全パース、受信サイズ制限、記事ID のハッシュ化
- カレンダー管理（data.calendar_management）
  - 営業日判定、next/prev_trading_day、カレンダー更新ジョブ
- 監査ログ（data.audit）
  - signal_events / order_requests / executions 等の監査テーブル・初期化
- リサーチ用ファクター計算（research）
  - momentum / volatility / value 等のファクター算出（DuckDB 参照）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、Zスコア正規化
- 統計ユーティリティ（data.stats）
  - zscore_normalize（外部ライブラリ依存なし）

注意：strategy、execution、monitoring パッケージはプレースホルダ（将来的な実装）を想定。

---

## セットアップ手順

前提
- Python 3.10 以上（`Path | None` や `X | Y` 型ヒントの使用のため）
- OS による環境依存ライブラリは特に不要（ただし duckdb はネイティブ拡張を含む場合があります）

1. 仮想環境作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate    # macOS / Linux
   .venv\Scripts\activate       # Windows
   ```

2. 必要パッケージをインストール
   （プロジェクトに pyproject.toml/requirements がある場合はそちらを利用してください）
   ```bash
   pip install duckdb defusedxml
   ```
   - 他に logging 等 Python 標準で賄えるもののみ使用しています。
   - packaging が用意されていれば `pip install -e .` で開発インストールできます。

3. ソースの参照方法
   - 開発中でパッケージ化していない場合は、プロジェクトルート（src を含む）を PYTHONPATH に追加するか、仮想環境にインストールしてください。
   - 例:
     ```bash
     export PYTHONPATH=$(pwd)/src:$PYTHONPATH
     ```

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すれば無効化可）。
   - 必須環境変数（config.Settings が参照、未設定時はエラー）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意 / 既定値:
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — default: INFO
     - KABU_API_BASE_URL — default: http://localhost:18080/kabusapi
     - DUCKDB_PATH — default: data/kabusys.duckdb
     - SQLITE_PATH — default: data/monitoring.db

   サンプル .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（コード例）

以下はライブラリを直接インポートして利用する基本例です。実行前に必要な環境変数と DuckDB の初期化を行ってください。

1. DuckDB スキーマの初期化
   ```python
   from kabusys.data import schema

   conn = schema.init_schema("data/kabusys.duckdb")
   ```

2. 日次 ETL を実行する
   ```python
   from kabusys.data.pipeline import run_daily_etl
   from datetime import date

   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```

3. ニュース収集ジョブを実行する
   ```python
   from kabusys.data.news_collector import run_news_collection

   # known_codes は銘柄抽出に使う有効コード集合（任意）
   known_codes = {"7203", "6758", "9984"}
   stats = run_news_collection(conn, known_codes=known_codes)
   print(stats)  # {source_name: 新規保存数}
   ```

4. リサーチ系ファクター計算（例: モメンタム）
   ```python
   from kabusys.research.factor_research import calc_momentum
   from datetime import date

   records = calc_momentum(conn, target_date=date(2024, 1, 10))
   # 必要に応じて zscore 正規化
   from kabusys.data.stats import zscore_normalize
   normed = zscore_normalize(records, columns=["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
   ```

5. J-Quants クライアントから生データを直接取得して保存
   ```python
   from kabusys.data import jquants_client as jq
   from datetime import date

   records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
   saved = jq.save_daily_quotes(conn, records)
   ```

注意点：
- research モジュールは DuckDB 上の prices_daily / raw_financials のみ参照し、発注 API にはアクセスしません。
- jquants_client は API レート制限とリトライ処理を内部で行います。
- run_daily_etl は品質チェック（data.quality）を行い、QualityIssue のリストを返します。重大な問題（severity="error"）があれば対処してください。

---

## ディレクトリ構成（抜粋）

以下は主要モジュールと役割の一覧です（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py
    - 環境変数の読み込み・必須チェック（Settings）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（fetch_*/save_*）
    - news_collector.py
      - RSS 収集、前処理、raw_news 保存、銘柄抽出
    - schema.py
      - DuckDB スキーマ定義と init_schema / get_connection
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - pipeline.py
      - ETL（run_prices_etl / run_financials_etl / run_calendar_etl / run_daily_etl）
    - features.py
      - features API（zscore_normalize 再公開）
    - calendar_management.py
      - market_calendar の管理、営業日判定
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py
      - 監査ログ用スキーマ（signal_events / order_requests / executions）
    - etl.py
      - ETLResult の再公開
  - research/
    - __init__.py (再エクスポート)
    - feature_exploration.py
      - 将来リターン calc_forward_returns、IC calc_ic、summary 等
    - factor_research.py
      - momentum, value, volatility ファクター計算
  - strategy/
    - __init__.py (プレースホルダ)
  - execution/
    - __init__.py (プレースホルダ)
  - monitoring/
    - __init__.py (プレースホルダ)

---

## 運用上の注意 / ベストプラクティス

- 環境分離
  - KABUSYS_ENV を使い、development / paper_trading / live を切り替えられます。実運用（live）では特に十分な検証を行ってください。
- シークレット管理
  - .env ファイルをリポジトリに含めないでください。トークン・パスワード類はシークレットマネージャや環境変数で管理してください。
- ETL の監視
  - run_daily_etl の結果（ETLResult）や data.quality が返す QualityIssue を監視し、エラー発生時はアラートを上げてください。
- DuckDB バックアップ / サイズ管理
  - DuckDB ファイルは定期的にバックアップ、または分割（raw / audit など）を検討してください。
- テスト
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使うとテスト時に .env の自動ロードを止められます。jquants_client は id_token を外部から注入可能なのでモックが容易です。

---

もし README に入れたい具体的なコマンド例、サンプル .env.example、または CI / デプロイ手順（systemd タイマー、Airflow、cron）の例が必要であれば、用途に合わせて追記します。