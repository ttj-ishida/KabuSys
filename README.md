# KabuSys

日本株向け自動売買プラットフォーム（ライブラリ）  
このリポジトリは、データ取得（J-Quants）→ ETL → 特徴量作成 → シグナル生成 → 発注監査までを想定したモジュール群を提供します。研究（research）と本番（execution）を分離し、DuckDB を中心に冪等性・トレーサビリティ・品質チェックを重視して設計されています。

---

## 概要

KabuSys は以下の層を備えた日本株自動売買システムの核となるコンポーネント群です。

- データ層（J-Quants API クライアント、RSS ニュース収集、DuckDB スキーマ定義、ETL パイプライン）
- 研究層（ファクター計算、特徴量探索）
- 戦略層（特徴量正規化、シグナル生成）
- 実行層（発注・約定・ポジション・監査テーブルの定義 — 実際のブローカー接続部分は別実装を想定）

設計上のポイント：
- DuckDB をデータベースとして利用（オンプレ／ローカルでの高速集計に最適）
- API 呼び出しはレートリミット・リトライ・トークンリフレッシュ対応
- ETL / DB 保存は冪等（ON CONFLICT / トランザクション）で安全
- ルックアヘッドバイアス回避のため、常に target_date 時点のデータのみを利用

---

## 主な機能一覧

- jquants_client
  - J-Quants から日足（OHLCV）、財務データ、マーケットカレンダーを取得（ページネーション対応）
  - レートリミッティング、リトライ、トークン自動リフレッシュ対応
  - DuckDB への冪等保存（raw_prices / raw_financials / market_calendar 等）

- data.schema
  - DuckDB 用のスキーマ初期化（Raw / Processed / Feature / Execution 層）
  - init_schema() で DB ファイルを作成・テーブル生成

- data.pipeline
  - 差分取得（last date から差分）を行う ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - 品質チェック（quality モジュール経由）と結果収集

- data.news_collector
  - RSS フィード取得・前処理・raw_news 保存、記事と銘柄の紐付け（ニュース → 銘柄抽出）
  - SSRF/サイズ/XML インジェクション対策を組み込んだ実装

- research
  - calc_momentum / calc_volatility / calc_value：prices_daily / raw_financials を参照してファクターを計算
  - calc_forward_returns / calc_ic / factor_summary / rank：特徴量解析支援関数

- strategy
  - build_features(conn, target_date)：research で計算した生ファクターを正規化・合成して features テーブルへ
  - generate_signals(conn, target_date, threshold, weights)：features と ai_scores を統合して BUY/SELL シグナルを生成し signals テーブルに保存

- data.calendar_management / data.audit / data.features / data.stats
  - カレンダー操作・監査ログのDDL・Zスコア正規化等のユーティリティ

---

## セットアップ手順（開発用）

前提
- Python 3.10 以上（PEP 604 の union 型（|）を使用しているため）
- Git が使える環境
- DuckDB を利用するためのディスク空き

1. リポジトリをクローン
   ```
   git clone <REPO_URL>
   cd <REPO_DIR>
   ```

2. 仮想環境を作成して有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール  
   最低限必要な外部依存（例）:
   - duckdb
   - defusedxml
   - （logging/urllib 等は標準ライブラリ）

   例:
   ```
   pip install duckdb defusedxml
   ```

   ※ 実運用では追加の依存（Slack 通知や kabuステーション API クライアント等）が必要になる場合があります。

4. 環境変数（.env）を用意  
   プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（読み込みは .git または pyproject.toml を基準に探索）。
   自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   必須環境変数
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID

   注意: Settings クラスが環境変数のバリデーションを行います（KABUSYS_ENV は development / paper_trading / live のいずれか、LOG_LEVEL は DEBUG/INFO/...）。

---

## 使い方（簡単なコード例）

以下は Python REPL / スクリプトからの基本的な使い方例です。

1. DuckDB スキーマ初期化
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ファイルパスを指定（:memory: でインメモリ）
   ```

2. 日次 ETL の実行
   ```python
   from kabusys.data.pipeline import run_daily_etl
   from datetime import date

   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```

3. 特徴量のビルド
   ```python
   from kabusys.strategy import build_features
   from datetime import date

   n = build_features(conn, target_date=date.today())
   print(f"features upserted: {n}")
   ```

4. シグナル生成
   ```python
   from kabusys.strategy import generate_signals
   from datetime import date

   total = generate_signals(conn, target_date=date.today(), threshold=0.6)
   print(f"signals written: {total}")
   ```

5. ニュース収集（RSS）
   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

   known_codes = {"7203", "6758", "9432"}  # 例: 有効銘柄コードセット
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   print(results)
   ```

6. カレンダー更新ジョブ
   ```python
   from kabusys.data.calendar_management import calendar_update_job
   saved = calendar_update_job(conn)
   print(f"calendar saved: {saved}")
   ```

注意:
- ETL 実行やシグナル生成はトランザクションを多用します。運用時はバックアップや排他制御を検討してください。
- AI スコア（ai_scores）や positions テーブルは別プロセス／スクリプトで更新される想定です。generate_signals は ai_scores が未登録でも中立値で処理します。

---

## 主要 API サマリ

- kabusys.config.settings
  - 各種環境設定にアクセス（例: settings.jquants_refresh_token、settings.duckdb_path、settings.env）

- kabusys.data.schema
  - init_schema(db_path)
  - get_connection(db_path)

- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date, ...)
  - run_prices_etl / run_financials_etl / run_calendar_etl

- kabusys.research
  - calc_momentum / calc_volatility / calc_value
  - calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize（data.stats からエクスポート）

- kabusys.strategy
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold, weights)

- kabusys.data.news_collector
  - fetch_rss(url, source)
  - save_raw_news(conn, articles)
  - run_news_collection(conn, sources, known_codes)

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要モジュール（抜粋）です。

- kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント + 保存ユーティリティ
    - news_collector.py            — RSS ニュース収集・前処理・保存
    - schema.py                    — DuckDB スキーマ定義・初期化
    - pipeline.py                  — ETL パイプライン（差分取得 / run_daily_etl）
    - calendar_management.py       — カレンダー管理ユーティリティ
    - audit.py                     — 監査ログ用 DDL（signal_events / order_requests / executions 等）
    - stats.py                     — z-score 正規化など統計ユーティリティ
    - features.py                  — features 用の公開インターフェース（zscore_normalize）
  - research/
    - __init__.py
    - factor_research.py           — momentum/value/volatility の計算
    - feature_exploration.py       — forward returns / IC / summary 等
  - strategy/
    - __init__.py
    - feature_engineering.py       — build_features 実装
    - signal_generator.py          — generate_signals 実装
  - execution/
    - __init__.py                  — （発注層のエントリ、別実装を想定）
  - monitoring/                    — モニタリング関連（未掲載のファイルを想定）

（この README はコード内の docstring / コメントを元に要約しています）

---

## 運用上の注意点

- 環境（KABUSYS_ENV）が `live` の場合は外部 API への発注等に注意してください。テスト時は `paper_trading` / `development` を利用してください。
- `.env.local` は `.env` を上書きする目的で使えます（OS 環境変数は保護されます）。
- 自動 .env 読み込みを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で有用）。
- DuckDB ファイルはデフォルト `data/kabusys.duckdb`。別パスを settings.duckdb_path で指定できます。
- ニュース収集や外部 HTTP は SSRF/サイズ/XML 攻撃対策を実装していますが、運用でさらにプロキシやネットワーク制限をかけることを推奨します。
- 監査ログ（audit）テーブルは削除せず、監査として永続化する運用を想定しています。

---

## 付録（トラブルシューティング）

- TypeError: union types (Path | None) が原因でエラーが出る場合は Python のバージョンを確認してください（3.10+ が必要）。
- .env が読み込まれない場合はプロジェクトルートの判定（.git や pyproject.toml）と `KABUSYS_DISABLE_AUTO_ENV_LOAD` を確認してください。
- DuckDB の接続・権限周りで問題が出る場合はファイルパスの親ディレクトリが存在するか確認してください（init_schema は親ディレクトリを自動作成します）。

---

必要に応じて、README にサンプルスクリプト（cron/airflow ジョブ定義、systemd unit、docker-compose など）や CI/CD・テスト手順（単体テスト／モック）を追記できます。どの情報を追加したいか教えてください。