# KabuSys

日本株向けの自動売買プラットフォーム（ライブラリ）です。  
データ収集（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、監査・実行用スキーマなどを含むモジュール群を提供します。

主に DuckDB をデータストアとして利用し、研究（research）と運用（strategy / execution）を分離した設計になっています。

---

## 目次
- プロジェクト概要
- 機能一覧
- 前提条件
- セットアップ手順
- 簡単な使い方（コード例）
- 環境変数（設定項目）
- ディレクトリ構成
- 補足（設計上の注意点）

---

## プロジェクト概要
KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API からのデータ取得（株価・財務・カレンダー）
- DuckDB を用いた Raw / Processed / Feature / Execution 層のスキーマ定義と初期化
- ETL（差分取得、保存、品質チェック）
- 研究用ファクター（momentum, volatility, value 等）の計算
- 特徴量の正規化・合成（features テーブル登録）
- 戦略による最終スコア計算と売買シグナル生成（signals テーブル）
- RSS ベースのニュース収集と銘柄抽出（SSRF 対策、トラッキング除去）
- 監査ログ・トレーサビリティのためのテーブル群

設計方針として、ルックアヘッドバイアスを避ける、冪等性（ON CONFLICT）を保つ、安全性（SSRF、XML 脆弱性対策）を重視しています。

---

## 機能一覧
主な機能は以下の通りです。

- data/jquants_client:
  - J-Quants API へのクライアント（レート制限・リトライ・トークン自動再取得対応）
  - fetch_* / save_* 系関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar など）
- data/schema:
  - DuckDB スキーマの定義と初期化（init_schema(), get_connection()）
  - Raw / Processed / Feature / Execution 層のテーブルを定義
- data/pipeline:
  - 日次 ETL の統合ジョブ（run_daily_etl）
  - 個別 ETL（run_prices_etl, run_financials_etl, run_calendar_etl）
- data/news_collector:
  - RSS フィード取得・前処理・raw_news への保存
  - 記事 → 銘柄コード紐付け（extract_stock_codes）
  - SSRF・XML 攻撃・Gzip BOM 対策等を実装
- research:
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 研究用ユーティリティ（calc_forward_returns, calc_ic, factor_summary, rank）
- strategy:
  - build_features: 研究で生成した raw ファクターを統合・Zスコア正規化して features テーブルへ保存
  - generate_signals: features と ai_scores を用いて final_score を計算し signals テーブルへ保存（BUY / SELL 生成、エグジット判定含む）
- data/stats:
  - zscore_normalize: クロスセクショナルな Z スコア正規化ユーティリティ
- config:
  - .env / 環境変数読み込みのヘルパー、Settings クラス（必須変数のラップ、環境別判定、ログレベル等）

---

## 前提条件
- Python 3.10 以上（コード中での型ヒント（|）やアノテーションを使用）
- 必要な外部ライブラリ（例、最低限）:
  - duckdb
  - defusedxml

（プロジェクトに別途 requirements.txt があればそちらを優先してください）

---

## セットアップ手順（開発環境）
1. リポジトリをクローン／取得する
2. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージのインストール
   - pip install duckdb defusedxml
   - （プロジェクトがパッケージ配布されていれば）pip install -e .
4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml の位置）から .env / .env.local を自動読み込みします（自動ロードはデフォルト ON）。
   - 自動ロードを無効化したい場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 必須環境変数は README 内の「環境変数」を参照して設定してください。
5. DuckDB スキーマ初期化
   - 以下のように初期化します（デフォルト DB パスは data/kabusys.duckdb）。
     - from kabusys.data.schema import init_schema
       conn = init_schema("data/kabusys.duckdb")

---

## 簡単な使い方（サンプルコード）

- DuckDB スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL を実行（J-Quants トークンは環境変数経由）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- 特徴量作成（features テーブルへの書き込み）
  ```python
  from datetime import date
  from kabusys.strategy import build_features
  build_features(conn, target_date=date(2025, 3, 1))
  ```

- シグナル生成
  ```python
  from datetime import date
  from kabusys.strategy import generate_signals
  count = generate_signals(conn, target_date=date(2025, 3, 1))
  print("signals:", count)
  ```

- RSS ニュース収集と保存
  ```python
  from kabusys.data.news_collector import run_news_collection
  known_codes = {"7203", "6758", "9432"}  # 例: 有効銘柄コードセット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- J-Quants から日足を直接取得して保存（テスト／ユーティリティ）
  ```python
  from kabusys.data import jquants_client as jq
  records = jq.fetch_daily_quotes(date_from=date(2025,1,1), date_to=date(2025,3,1))
  saved = jq.save_daily_quotes(conn, records)
  ```

---

## 環境変数（主な設定項目）
config.Settings で参照される環境変数の一覧（必須は明示）:

- 必須
  - JQUANTS_REFRESH_TOKEN : J-Quants の refresh token（get_id_token 用）
  - KABU_API_PASSWORD     : kabuステーション API パスワード（execution 層で使用）
  - SLACK_BOT_TOKEN       : Slack 通知用 BOT トークン
  - SLACK_CHANNEL_ID      : Slack チャンネル ID

- 任意（デフォルトあり）
  - KABUSYS_ENV           : 環境 ("development" / "paper_trading" / "live") - デフォルト "development"
  - LOG_LEVEL             : ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL") - デフォルト "INFO"
  - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト "data/kabusys.duckdb"）
  - SQLITE_PATH           : sqlite 用パス（監視用等、デフォルト "data/monitoring.db"）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 をセットすると .env 自動読み込みを無効化

.env の例（.env.example を参照して作成してください）
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## ディレクトリ構成
提供している主なモジュール・ファイルの構成（抜粋）:

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
      - (execution 層の実装ファイル)
    - monitoring/
      - (監視・記録用モジュール)

README に含れるファイル群のうち、主要な実装と API は上記のとおりです。  
（実際のリポジトリにはさらにモジュールや補助ユーティリティが含まれる想定です。）

---

## 補足・設計上の注意
- DuckDB スキーマは init_schema() により冪等に作成されます。既存データは保持されます。
- jquants_client は API レート制限（120 req/min）に合わせた内部 RateLimiter、リトライ、401 トークン自動更新を備えています。
- news_collector は SSRF 対策、XML の安全パーサ（defusedxml）、受信サイズ上限（10 MB）など安全性を考慮しています。
- research と strategy は「ルックアヘッドバイアスを防ぐ」設計になっており、target_date 時点以前のデータのみ参照します。
- strategy.generate_signals はデフォルト重み・閾値を持ち、ユーザ定義の重みをマージして合計 1.0 に再スケールします。不正値はスキップされます。
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml を起点）を探索して行います。テスト時などに無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

必要であれば、各モジュールの使い方（より詳細な API 例）、テスト方法、CI 設定、運用時の注意（バックテストと本番の分離、paper_trading 環境の使い方）などの節を追加できます。どの部分を詳述したいか教えてください。