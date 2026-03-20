# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査・実行レイヤのスキーマ等を提供します。

---

## プロジェクト概要

KabuSys は以下の責務を分離して実装したモジュール群です。

- J-Quants API からのデータ取得（株価日足、財務、マーケットカレンダー）
- DuckDB を用いたデータ格納・スキーマ管理（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- 研究用ファクター計算 / 特徴量エンジニアリング（ルックアヘッド対策済み）
- 戦略のスコア計算と売買シグナル生成（BUY / SELL のルール実装）
- RSS ベースのニュース収集と銘柄紐付け（SSRF対策・トラッキング除去）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day など）
- 監査ログ（信号→発注→約定のトレース）および実行層のテーブル定義

設計方針として「ルックアヘッドの排除」「冪等性」「DBトランザクションを用いた原子性確保」「外部ライブラリへの依存最小化（ただし duckdb / defusedxml 等は利用）」を重視しています。

---

## 主な機能一覧

- data/jquants_client: J-Quants API クライアント（レート制御、リトライ、トークン自動リフレッシュ、ページネーション対応）
- data/schema: DuckDB のスキーマ定義と初期化（Raw/Processed/Feature/Execution 層）
- data/pipeline: ETL（run_daily_etl、個別 ETL: run_prices_etl / run_financials_etl / run_calendar_etl）
- data/news_collector: RSS 取得・前処理・raw_news 保存・銘柄抽出
- data/calendar_management: market_calendar の取得と営業日ユーティリティ（is_trading_day / next_trading_day / prev_trading_day 等）
- research: ファクター計算・探索ユーティリティ（calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary）
- strategy:
  - feature_engineering.build_features: research で計算した raw ファクターを正規化・フィルタリングして features テーブルへ保存
  - signal_generator.generate_signals: features と ai_scores を統合して final_score を計算、BUY/SELL シグナルを signals テーブルへ保存
- data/stats: zscore_normalize などの共通統計ユーティリティ
- config: .env / 環境変数読み込み、アプリ設定管理（settings オブジェクト）

---

## 必要条件（概略）

- Python 3.10+
- 必要パッケージ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード）
- DuckDB ファイル保存用のファイルシステム書き込み権限

（プロジェクトに requirements.txt がある場合はそちらを使ってください）

---

## セットアップ手順

1. リポジトリをクローン / ワークディレクトリに配置

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトの setup.py / pyproject.toml / requirements.txt がある場合はそれに従ってください）

4. 環境変数の設定
   - プロジェクトルートに `.env`（または `.env.local`）を配置することで自動で読み込まれます（自動ロードはデフォルトで有効）。
   - 必須環境変数（settings で必須とされるもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants の refresh token
     - KABU_API_PASSWORD — kabuステーション API パスワード
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID — Slack チャネル ID
   - 任意（デフォルトあり）:
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
   - 自動 env ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   サンプル .env（例）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

5. DuckDB スキーマ初期化
   - Python から:
     ```
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()
     ```
   - これにより必要なテーブル・インデックスが作成されます（既存の場合はスキップされるため冪等です）。

---

## 使い方（主要な実行例）

以降は Python スクリプトや REPL で実行できます。conn は duckdb 接続オブジェクトです（init_schema で作成した接続をそのまま使うか get_connection）。

1. ETL（日次 ETL）の実行
   ```
   from kabusys.data.schema import init_schema
   from kabusys.data.pipeline import run_daily_etl
   conn = init_schema("data/kabusys.duckdb")
   result = run_daily_etl(conn)  # target_date を指定可能
   print(result.to_dict())
   conn.close()
   ```

2. 特徴量のビルド（feature engineering）
   ```
   from kabusys.data.schema import get_connection
   from kabusys.strategy import build_features
   from datetime import date
   conn = get_connection("data/kabusys.duckdb")
   cnt = build_features(conn, date(2025, 1, 31))
   print(f"features upserted: {cnt}")
   conn.close()
   ```

3. シグナル生成
   ```
   from kabusys.data.schema import get_connection
   from kabusys.strategy import generate_signals
   from datetime import date
   conn = get_connection("data/kabusys.duckdb")
   total = generate_signals(conn, date(2025, 1, 31), threshold=0.6)
   print(f"signals generated: {total}")
   conn.close()
   ```

4. ニュース収集（一括）
   ```
   from kabusys.data.schema import get_connection
   from kabusys.data.news_collector import run_news_collection
   conn = get_connection("data/kabusys.duckdb")
   known_codes = {"7203", "6758", "9984"}  # 事前に有効銘柄を用意
   results = run_news_collection(conn, known_codes=known_codes)
   print(results)
   conn.close()
   ```

5. カレンダー更新ジョブ
   ```
   from kabusys.data.schema import get_connection
   from kabusys.data.calendar_management import calendar_update_job
   conn = get_connection("data/kabusys.duckdb")
   saved = calendar_update_job(conn)
   print("saved calendar entries:", saved)
   conn.close()
   ```

6. J-Quants からの生データ取得（低レベル）
   ```
   from kabusys.data import jquants_client as jq
   id_token = jq.get_id_token()  # settings.jquants_refresh_token を利用
   quotes = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2024,1,1), date_to=date(2024,1,31))
   ```

---

## 環境変数 / 設定（まとめ）

- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
- オプション / 既定値あり:
  - KABUSYS_ENV (development | paper_trading | live) — default: development
  - LOG_LEVEL — default: INFO
  - DUCKDB_PATH — default: data/kabusys.duckdb
  - SQLITE_PATH — default: data/monitoring.db
- 自動 .env 読込の制御:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化

設定は kabusys.config.settings からアクセスできます（例: settings.jquants_refresh_token）。

---

## ディレクトリ構成

主要なファイル・モジュール（抜粋）:

- src/
  - kabusys/
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
      - (その他 data 関連モジュール)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - strategy/
      - __init__.py
      - feature_engineering.py
      - signal_generator.py
    - execution/
      - __init__.py
    - monitoring/  (監視・アラート等の実装場所想定)
    - (他モジュール)

上記は主要な機能別ディレクトリ（data / research / strategy / execution / monitoring）で整理されています。

---

## 運用上の注意点

- DuckDB のスキーマ初期化は init_schema() を使ってください。既存スキーマがあれば冪等にスキップします。
- ETL は差分取得かつバックフィルをサポートしています（デフォルトで最終取得日の数日前を再取得して API の後出し修正に耐性を持ちます）。
- J-Quants API のレート制限（120 req/min）を内部で尊重していますが、複数プロセスからの同時実行は別途注意してください。
- RSS フィード取得は SSRF や XML アタック対策（スキーム検証・ホスト検査・defusedxml・受信サイズ制限）を実装していますが、運用での監視も必要です。
- 本ライブラリは発注 API（ブローカー）への接続層と分離されています。実際の発注は execution 層を実装してブリッジする必要があります。
- テスト時に自動で .env を読み込ませたくない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

## 貢献 / 変更点の追跡

- バージョンは kabusys.__version__（現状: 0.1.0）で管理しています。
- 重要な機能や仕様はリポジトリ内の各種設計ドキュメント（DataPlatform.md, StrategyModel.md 等）に従って実装されています（リポジトリ内に存在する場合は参照してください）。

---

何か特定の使い方（例: ETL の定期実行 cron 設定、kabuステーション連携、Slack通知設定、ローカルテスト用 DB スクリプトなど）について詳しいドキュメントが必要であれば、用途に合わせてサンプルや運用手順を追加します。