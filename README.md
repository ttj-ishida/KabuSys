# KabuSys

KabuSys は日本株のデータ収集・ETL・特徴量生成・リサーチ用ユーティリティを中心とした自動売買プラットフォームのコアライブラリです。DuckDB をデータストアに使用し、J-Quants API や RSS フィードからデータを取得して冪等に保存・検査・加工できるよう設計されています。

主な設計方針:
- DuckDB を中心とした3層（Raw / Processed / Feature）データレイヤ
- J-Quants API のレート制御、リトライ、トークンリフレッシュ対応
- ETL は差分更新かつ冪等（ON CONFLICT）で安全に保存
- データ品質チェック・監査ログ（トレーサビリティ）を重視
- 研究（research）モジュールは本番口座や発注 API にアクセスしない

## 主な機能一覧
- data
  - jquants_client: J-Quants API からの株価・財務・カレンダー取得、DuckDB への保存関数（冪等）
  - pipeline: 日次 ETL（差分取得・保存・品質チェック）を提供
  - schema / audit: DuckDB スキーマ初期化、監査ログテーブルの初期化
  - news_collector: RSS からニュース収集、テキスト前処理、銘柄抽出、冪等保存
  - calendar_management: JPX カレンダー管理・営業日判定・夜間更新ジョブ
  - quality: 欠損・スパイク・重複・日付不整合の品質チェック
  - stats / features: Z スコア正規化などのユーティリティ
- research
  - factor_research: momentum / volatility / value 等のファクター計算（DuckDB を参照）
  - feature_exploration: 将来リターン計算、IC（スピアマン）計算、ファクター統計概要
- config
  - 環境変数管理（.env 自動読み込み、必須項目チェック、環境判定等）
- execution / strategy / monitoring
  - パッケージ構造を用意（発注・戦略・監視は別モジュールで実装予定）

## 必要条件
- Python 3.10 以上（型ヒントで | 演算子等を使用）
- 必要パッケージ（例）
  - duckdb
  - defusedxml

（プロジェクトの packaging に requirements ファイルがあればそちらを利用してください）

## セットアップ手順（開発環境）
1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境作成・有効化（任意）
   - macOS / Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 必要パッケージをインストール
   ```
   pip install --upgrade pip
   pip install duckdb defusedxml
   # 開発モードでインストールする場合（setup があるなら）
   pip install -e .
   ```

4. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を置くと、自動的に読み込まれます（ただしテスト等で無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 必須環境変数（config.Settings で必須とされるもの）
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API パスワード（発注関連で必要）
     - SLACK_BOT_TOKEN: Slack 通知等に使用
     - SLACK_CHANNEL_ID: Slack チャンネル ID
   - 任意／デフォルト値あり
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/…（デフォルト: INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると自動 .env ロードを無効化
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（デフォルト）
     - KABUS_API_BASE_URL: http://localhost:18080/kabusapi（デフォルト）

   例（.env）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

## 使い方（簡単な例）
以下は Python REPL / スクリプトからの利用例です。

1. DuckDB スキーマを初期化
   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   # settings.duckdb_path は Path オブジェクトを返します
   conn = init_schema(settings.duckdb_path)
   ```

2. 日次 ETL を実行（J-Quants トークンは settings から自動利用）
   ```python
   from kabusys.data.pipeline import run_daily_etl
   from kabusys.config import settings
   from kabusys.data.schema import get_connection

   conn = get_connection(settings.duckdb_path)
   result = run_daily_etl(conn)  # target_date を省略すると今日
   print(result.to_dict())
   ```

3. ニュース収集ジョブを実行（既知銘柄 set を渡して銘柄紐付けをする例）
   ```python
   from kabusys.data.news_collector import run_news_collection
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   known_codes = {"7203", "6758", "8035"}  # 事前に用意した銘柄セット
   res = run_news_collection(conn, known_codes=known_codes)
   print(res)  # {source_name: saved_count}
   ```

4. ファクター計算 / 研究（DuckDB 接続を渡す）
   ```python
   from kabusys.data.schema import get_connection
   from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

   conn = get_connection("data/kabusys.duckdb")
   from datetime import date
   target = date(2024, 1, 4)

   mom = calc_momentum(conn, target)
   vol = calc_volatility(conn, target)
   val = calc_value(conn, target)
   fwd = calc_forward_returns(conn, target, horizons=[1,5,21])

   # 例: mom と fwd を結合して IC を計算
   ic = calc_ic(mom, fwd, factor_col="ma200_dev", return_col="fwd_1d")
   print("IC:", ic)
   ```

5. J-Quants の API クライアントを直接使う（トークンは settings から利用される）
   ```python
   from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements

   # 全銘柄の直近日足を取得（ページネーション対応）
   records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
   ```

## 主要 API（概要）
- kabusys.config.settings: アプリ設定（環境変数読み取り）
- kabusys.data.schema.init_schema(db_path): DuckDB スキーマ初期化（返り値は接続）
- kabusys.data.schema.get_connection(db_path): 既存 DB への接続取得
- kabusys.data.jquants_client:
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token（自動リフレッシュや retry を扱う）
- kabusys.data.pipeline:
  - run_prices_etl / run_financials_etl / run_calendar_etl / run_daily_etl
- kabusys.data.news_collector:
  - fetch_rss / save_raw_news / run_news_collection / extract_stock_codes
- kabusys.data.quality:
  - run_all_checks（品質チェック群）
- kabusys.research:
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank
- kabusys.data.stats:
  - zscore_normalize

## 初期化・運用ワークフロー（例）
1. 一度だけ: DuckDB スキーマ初期化
   - init_schema(settings.duckdb_path)
2. 定期実行（cron / Airflow 等）
   - run_daily_etl を毎営業日夜間に実行（calendar lookup を含む）
   - calendar_update_job を夜間バッチで実行して先読みカレンダーを更新
   - news_collector.run_news_collection を定期的に実行
3. リサーチ・バックテスト
   - research モジュールでファクター算出 → zscore_normalize → シグナル生成
4. 発注（本番化時）
   - execution / strategy モジュールに実装を追加して監査テーブルを活用

## ディレクトリ構成
（プロジェクト内の主要ファイルを抜粋）
- src/
  - kabusys/
    - __init__.py
    - config.py
    - execution/
      - __init__.py
    - strategy/
      - __init__.py
    - monitoring/
      - __init__.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - pipeline.py
      - etl.py
      - audit.py
      - calendar_management.py
      - quality.py
      - stats.py
      - features.py
    - research/
      - __init__.py
      - feature_exploration.py
      - factor_research.py

各モジュールの役割は上の「主な機能一覧」を参照。

## 注意事項 / 実運用での留意点
- J-Quants の API レート制限・認証を厳守する（jquants_client は内部で制御済み）。
- .env に認証情報を置く場合はリポジトリに含めないこと（.gitignore を利用）。
- DuckDB ファイルはローカル I/O なのでバッックアップ方針を検討してください。
- news_collector は外部 RSS を処理するため SSRF/圧縮爆弾等に配慮した実装（制限・検証）を行っていますが、運用時にはネットワーク制御やタイムアウトの調整を行ってください。
- research モジュールは本番発注と切り離して動作することを前提にしています（Look-ahead を防ぐ設計）。

---

問題や拡張（例えば戦略実装やブローカ連携）を行う際は、この README を起点に各モジュールの docstring / ソースを参照してください。必要であれば README にサンプルスクリプトや運用例（Airflow DAG、systemd タイマー等）を追加できます。