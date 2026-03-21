# KabuSys

日本株向けの自動売買 / データプラットフォームモジュール群です。  
DuckDB をデータレイヤに使い、J‑Quants API や RSS ニュースを取り込み、特徴量作成 → シグナル生成 → 発注フローのためのスキーマ/ユーティリティを提供します。

主な設計方針
- ルックアヘッドバイアスを避ける（target_date 時点のデータのみ使用）
- DuckDB を用いた冪等な保存（ON CONFLICT / トランザクション）
- API 呼び出しはレートリミット・リトライ・トークン自動リフレッシュ対応
- ニュース収集で SSRF や XML 攻撃等を考慮した堅牢な実装

---

## 機能一覧
- データ収集 / ETL
  - J‑Quants API クライアント（株価 / 財務 / 市場カレンダー）
  - 差分更新・バックフィルをサポートする ETL パイプライン（run_daily_etl 等）
  - DuckDB スキーマ初期化（init_schema）
- データ層（DuckDB スキーマ）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - インデックスやトランザクションを用いた堅牢な保存ロジック
- 研究・特徴量
  - ファクター計算（momentum / volatility / value 等）
  - Z スコア正規化ユーティリティ
  - 将来リターン・IC 計算・統計サマリー（研究向け）
- 戦略ロジック
  - 特徴量->features テーブル構築（build_features）
  - features + ai_scores を統合して売買シグナル生成（generate_signals）
  - BUY/SELL の閾値や重みのカスタマイズを想定
- ニュース収集
  - RSS 取得・前処理・記事ID生成（トラッキング除去・SHA-256）
  - raw_news 保存・銘柄紐付け（news_symbols）
  - SSRF / XML インジェクション / サイズ上限対策を実装
- カレンダー管理
  - market_calendar を用いた営業日判定・次/前営業日取得
  - カレンダー更新ジョブ（calendar_update_job）
- 監査 / 発注追跡（audit）
  - signal_events / order_requests / executions などトレーサビリティ用テーブル

---

## 要求事項（推奨）
- Python 3.9+
- duckdb
- defusedxml
- （標準ライブラリ以外の依存は実装や環境に合わせて追加ください）
- ネットワーク接続（J‑Quants API、RSS）

（実際の requirements.txt はこのリポジトリに合わせて作成してください）

---

## セットアップ手順

1. リポジトリをクローン／作業ディレクトリへ移動
   ```
   git clone <this-repo-url>
   cd <this-repo>
   ```

2. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール（例）
   ```
   pip install duckdb defusedxml
   # 追加の HTTP / logging / テストライブラリがある場合はここでインストール
   ```

4. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を配置すると自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます）。
   - 必須環境変数（実行に必要なもの）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - オプション（デフォルト値あり）
     - KABUSYS_ENV (development|paper_trading|live) — デフォルト: development
     - LOG_LEVEL (DEBUG|INFO|...) — デフォルト: INFO
     - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db

   例: .env（最小）
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password_here
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマ初期化
   Python コンソールやスクリプトで init_schema を呼びます（デフォルトの DB パスは .env の DUCKDB_PATH を参照）。
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

---

## 使い方（基本的なワークフロー例）

1. DB 初期化（上記）
2. 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）
   ```python
   from datetime import date
   from kabusys.data.schema import init_schema
   from kabusys.data.pipeline import run_daily_etl

   conn = init_schema("data/kabusys.duckdb")
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```
3. 特徴量生成（features テーブルに書き込む）
   ```python
   from datetime import date
   from kabusys.strategy import build_features
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   count = build_features(conn, target_date=date.today())
   print("features upserted:", count)
   ```
4. シグナル生成
   ```python
   from datetime import date
   from kabusys.strategy import generate_signals
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   signals_count = generate_signals(conn, target_date=date.today(), threshold=0.6)
   print("signals generated:", signals_count)
   ```
5. ニュース収集（RSS）
   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   # known_codes: 有効な銘柄コードの集合（抽出に使用）
   stats = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203", "6758"})
   print(stats)
   ```

注: サンプルは同期的な呼び出し例です。本番ジョブはジョブスケジューラ(cron / airflow) や非同期ワーカーで実行することを想定しています。

---

## 主要 API / モジュール一覧（抜粋）

- kabusys.config
  - settings: 環境変数経由で設定取得
- kabusys.data
  - schema.init_schema / get_connection
  - jquants_client.fetch_... / save_...
  - pipeline.run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - news_collector.fetch_rss / save_raw_news / run_news_collection
  - statistics: zscore_normalize
  - calendar_management.is_trading_day / next_trading_day / prev_trading_day / calendar_update_job
- kabusys.research
  - calc_momentum / calc_volatility / calc_value
  - calc_forward_returns / calc_ic / factor_summary / rank
- kabusys.strategy
  - build_features
  - generate_signals

---

## ディレクトリ構成

（リポジトリの src/kabusys を基点とした主要ファイル・モジュール）

- src/
  - kabusys/
    - __init__.py
    - config.py                       # 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py             # J‑Quants API クライアント + 保存ロジック
      - news_collector.py             # RSS ニュース収集・保存・銘柄抽出
      - schema.py                     # DuckDB スキーマ定義・初期化
      - pipeline.py                   # ETL パイプライン
      - stats.py                      # 統計ユーティリティ（zscore）
      - calendar_management.py        # 市場カレンダー管理
      - audit.py                      # 発注トレーサビリティ用スキーマ
      - features.py                   # data 層の特徴量ユーティリティ公開
    - research/
      - __init__.py
      - factor_research.py            # ファクター計算（momentum/value/volatility）
      - feature_exploration.py        # 将来リターン / IC / 統計サマリー
    - strategy/
      - __init__.py
      - feature_engineering.py        # features テーブル構築（正規化・フィルタ）
      - signal_generator.py           # features→signals の生成ロジック
    - execution/                       # 発注・実行関連（パッケージ用意）
    - monitoring/                      # 監視 / メトリクス関連（パッケージ用意）

上記以外にもユーティリティや追加のモジュールが存在する場合があります。README は主要なものを抜粋しています。

---

## 開発・テストのヒント
- 自動環境変数ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用）。
- DuckDB を in-memory でテストするには db_path に ":memory:" を渡してください:
  ```python
  conn = init_schema(":memory:")
  ```
- RSS のネットワーク呼び出しは news_collector._urlopen をモックすることで簡単にテスト可能。
- J‑Quants API 呼び出しは id_token を外部から注入してテスト可能（jq.get_id_token をモック）。

---

## 注意事項 / 安全性
- 実際に発注／ライブ稼働する際は十分なリスク管理（発注量制限、ドローダウン制御、監査ログの監視）を行ってください。
- API トークンやパスワードは決してソース管理に置かないでください。.env を使うか安全なシークレット管理を利用してください。
- KABUSYS_ENV を `live` に設定すると実際の発注処理や live モードの挙動を切り替える想定です（環境ごとの挙動に注意）。

---

これで README の概要は以上です。必要であれば以下を追加します:
- requirements.txt の候補
- 実行例の CLI スクリプト（例: run_etl.py / run_strategy.py）
- .env.example ファイルテンプレート

追加希望があれば教えてください。