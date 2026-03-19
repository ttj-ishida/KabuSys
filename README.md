# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（ミニマル実装）。  
データ取得・ETL、特徴量計算、戦略シグナル生成、ニュース収集、監査ログなどの主要機能を提供します。

---

## プロジェクト概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API からの市場データ・財務データ取得と DuckDB への永続化（差分取得・冪等保存）
- データ品質チェック、マーケットカレンダー管理
- 研究用ファクター計算（モメンタム / ボラティリティ / バリュー 等）とクロスセクション正規化
- 戦略用特徴量の構築（features テーブル）とシグナル生成（signals テーブル）
- RSS ベースのニュース収集と銘柄紐付け
- 発注／約定／監査ログのためのスキーマ（実行レイヤの枠組みを提供）

設計上のポイント:
- ルックアヘッドバイアスを避ける（target_date 時点のデータのみ参照）
- DuckDB を主要なローカル DB として使用（ON CONFLICT による冪等性）
- 外部 API 呼び出し部分はリトライ／レート制御・トークン自動リフレッシュを実装
- research 層は本番口座・発注 API に依存しない（安全な分析）

---

## 主な機能一覧

- 環境設定管理（.env の自動読み込み / 必須環境変数の取得）
- J-Quants API クライアント（ページネーション・レート制限・リトライ・トークンリフレッシュ）
- DuckDB スキーマ初期化（init_schema）
- 日次 ETL（run_daily_etl）:
  - 市場カレンダー、株価日足、財務データの差分取得・保存
  - オプションの品質チェック
- ファクター計算（research.calc_momentum / calc_volatility / calc_value）
- 特徴量構築（strategy.build_features）
- シグナル生成（strategy.generate_signals）
- ニュース収集（data.news_collector.fetch_rss / run_news_collection）と銘柄抽出
- 統計ユーティリティ（zscore_normalize 等）
- マーケットカレンダー操作ユーティリティ（is_trading_day, next_trading_day 等）
- 監査ログスキーマ（signal_events / order_requests / executions など）

---

## 必要条件 / 依存

- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - defusedxml

インストール例（pip）:
```bash
python -m pip install "duckdb" "defusedxml"
# 開発パッケージを使う場合はプロジェクトの setup / pyproject に従ってインストール
```

---

## 環境変数（.env）

プロジェクトルートの `.env` / `.env.local`（存在すれば）を自動で読み込みます（CWD 依存ではなくパッケージ位置からプロジェクトルートを探索）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数（必須は明記）:

- J-Quants / データ
  - JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- kabuステーション API
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- Slack（通知等）
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
- データベース / パス
  - DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- 動作モード / ログ
  - KABUSYS_ENV (任意, allowed: development / paper_trading / live, デフォルト: development)
  - LOG_LEVEL (任意, DEBUG/INFO/WARNING/ERROR/CRITICAL, デフォルト: INFO)

注意: Settings は `kabusys.config.settings` から参照可能で、未設定の必須値は取得時に ValueError を投げます。

---

## セットアップ手順（ローカルでの最小構成）

1. リポジトリをクローン / 取得
2. Python 3.10+ の仮想環境を作成して有効化
3. 必要パッケージをインストール:
   ```bash
   pip install duckdb defusedxml
   ```
4. プロジェクトルートに `.env` を作成し必要な環境変数を設定（または環境変数としてエクスポート）。
   例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456
   KABUS_API_PASSWORD=yourpass
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```
5. DuckDB スキーマの初期化:
   - Python REPL またはスクリプトで:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
   - これにより必要なテーブルがすべて作成されます（冪等）。

---

## 使い方（簡単なコード例）

- DuckDB スキーマ初期化:
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL（J-Quants からデータ取得して保存）:
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ファクター → features テーブル構築:
  ```python
  from datetime import date
  from kabusys.strategy import build_features

  n = build_features(conn, target_date=date.today())
  print(f"features upserted: {n}")
  ```

- シグナル生成:
  ```python
  from datetime import date
  from kabusys.strategy import generate_signals

  total = generate_signals(conn, target_date=date.today(), threshold=0.6)
  print(f"signals written: {total}")
  ```

- ニュース収集（RSS）と保存:
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  # known_codes は銘柄抽出に使う既知の銘柄コードセット（例: {"7203", "6758", ...}）
  res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=set())
  print(res)  # {source_name: saved_count}
  ```

---

## 主要 API（モジュール / 代表関数）

- kabusys.config
  - settings: 環境変数ベースの設定オブジェクト
- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - get_id_token (トークン取得)
- kabusys.data.schema
  - init_schema(db_path), get_connection(db_path)
- kabusys.data.pipeline
  - run_daily_etl(conn, target_date, ...)
  - run_prices_etl / run_financials_etl / run_calendar_etl
- kabusys.data.news_collector
  - fetch_rss(url, source), save_raw_news, run_news_collection
- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
- kabusys.strategy
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold, weights)

---

## ディレクトリ構成

主要ファイルのツリー（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - execution/ (発注関連はプレースホルダ)
      - __init__.py
    - strategy/
      - __init__.py
      - feature_engineering.py
      - signal_generator.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - pipeline.py
      - features.py
      - stats.py
      - calendar_management.py
      - audit.py
    - monitoring/ (監視ロジックのためのファイル群想定)
    - その他モジュール...

各ファイルは以下の責務を持ちます（一部）:
- data/schema.py: DuckDB スキーマ定義と init_schema
- data/jquants_client.py: J-Quants API 統合（取得・保存・トークン管理）
- data/pipeline.py: 日次 ETL パイプライン
- data/news_collector.py: RSS 収集・前処理・DB 保存
- research/*: 研究用ファクター計算と統計解析
- strategy/*: 特徴量構築とシグナル生成ロジック
- config.py: .env 読み込み・環境設定アクセス

---

## 運用上の注意点

- 本ライブラリは発注ロジック（ブローカーへの実際の注文送信）を含まない場合があります。実運用では execution 層とブローカー API の実装・検証が必要です。
- 環境変数やトークンは安全に管理してください（.env を共有リポジトリに置かない等）。
- DuckDB ファイルのバックアップと権限管理を適切に行ってください。
- ニュース収集では外部 URL を取得するため SSRF 対策やサイズ制限が組み込まれていますが、運用時の監視を推奨します。
- J-Quants の API レート制限（120 req/min）に準拠する設計です。大量同時処理を行う場合は注意してください。

---

## 参考 / 補足

- 自動で .env を読み込みますが、読み込みを無効にしたいユニットテスト等では環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- ロギングレベルは `LOG_LEVEL` で調整できます。
- システムモード（development / paper_trading / live）は `KABUSYS_ENV` で指定します。`settings.is_live` / `is_paper` / `is_dev` で参照可能です。

---

必要であれば README に含めるサンプル .env.example、CLI ランナー（cron 用）や運用手順（バックフィル手順、モニタリング）に関する追記も作成します。どの部分を詳しく追記しますか？