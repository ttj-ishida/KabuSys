# KabuSys

KabuSys は日本株向けの自動売買プラットフォームのコンポーネント群です。データ収集（J-Quants）、ETL、特徴量エンジニアリング、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなどを含む一連の機能を DuckDB を中心に実装しています。

現在のバージョン: 0.1.0

---

## 概要

このリポジトリは以下の責務を持つモジュールを提供します。

- データ取得／保存（J-Quants API クライアント、RSS ニュース収集）
- DuckDB に対するスキーマ定義と初期化
- ETL（差分取得、バックフィル、品質チェック）
- 研究用ファクター計算（momentum/value/volatility など）
- 特徴量正規化・合成（feature engineering）
- シグナル生成（final_score 計算、BUY/SELL 判定）
- マーケットカレンダー管理（営業日判定／次営業日取得等）
- 監査ログ（signal → order → execution のトレース）

設計方針のポイント：
- ルックアヘッドバイアスを避けるため、target_date 時点のデータのみを使用
- DuckDB を用いた冪等な保存（ON CONFLICT / トランザクション）
- 外部 API のレート制御・リトライ（J-Quants クライアント）
- セキュリティ対策（RSS 側の SSRF 対策、defusedxml 利用など）

---

## 主な機能一覧

- jquants_client
  - J-Quants から株価・財務・カレンダーを取得（ページネーション対応、トークン自動更新、レート制御、リトライ）
  - DuckDB への冪等保存（raw_prices / raw_financials / market_calendar）
- ETL（data.pipeline）
  - 差分取得 / バックフィル / カレンダー先読み / 品質チェックを統合した日次 ETL
- スキーマ管理（data.schema）
  - DuckDB のテーブル定義・インデックス作成・初期化（Raw / Processed / Feature / Execution 層）
- ニュース収集（data.news_collector）
  - RSS 取得・前処理・記事ID生成・raw_news への冪等保存・テキストから銘柄コード抽出
- 研究モジュール（research）
  - momentum / volatility / value 等ファクター実装、将来リターン計算、IC 計算、統計サマリー
- 特徴量エンジニアリング（strategy.feature_engineering）
  - 生ファクターを正規化・合成し features テーブルへ保存
- シグナル生成（strategy.signal_generator）
  - 正規化済みファクターと AI スコアを統合して final_score を計算し signals テーブルへ保存
- カレンダー管理（data.calendar_management）
  - 営業日判定、次／前営業日取得、カレンダー更新ジョブ
- 監査ログ（data.audit）
  - signal_events / order_requests / executions 等でトレーサビリティを確保

---

## セットアップ手順

前提
- Python 3.10+（typing のセレクターや PEP 604 などを利用）
- DuckDB（Python パッケージとしてインストール）
- ネットワークアクセス（J-Quants API / RSS へのアクセス）

推奨手順（例）

1. 仮想環境作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

2. 依存パッケージをインストール
   - このコードベースでは少なくとも以下が必要です：
     - duckdb
     - defusedxml
   - 例:
     ```
     pip install duckdb defusedxml
     ```
   - 実際のプロジェクトでは requirements.txt / pyproject.toml を用意している想定です。

3. 環境変数を設定
   - リポジトリルート（.git または pyproject.toml のある階層）に `.env` / `.env.local` を配置すると自動で読み込まれます（自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須の環境変数（Settings で _require されるもの）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - オプション:
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - KABUSYS_ENV (development, paper_trading, live) デフォルト development
     - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL) デフォルト INFO

   .env の例（参考）
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマ初期化
   - Python から schema.init_schema を呼んで DB を初期化します。
   ```
   python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
   ```

---

## 使い方（簡単な例）

以下は主要なユースケースの最小例です。実運用ではロギングやエラーハンドリング、バックグラウンドジョブやスケジューラを組み合わせます。

1. DuckDB の初期化
   ```python
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   ```

2. 日次 ETL 実行
   ```python
   from kabusys.data.pipeline import run_daily_etl
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   result = run_daily_etl(conn)
   print(result.to_dict())
   ```

3. 特徴量構築（feature engineering）
   ```python
   from datetime import date
   from kabusys.strategy import build_features
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   count = build_features(conn, date(2024, 1, 31))
   print(f"features built: {count}")
   ```

4. シグナル生成
   ```python
   from datetime import date
   from kabusys.strategy import generate_signals
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   total_signals = generate_signals(conn, date(2024, 1, 31))
   print(f"signals written: {total_signals}")
   ```

5. ニュース収集ジョブ
   ```python
   from kabusys.data.news_collector import run_news_collection
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   # known_codes は有効な銘柄コード集合（抽出用）
   res = run_news_collection(conn, known_codes={"7203","6758"})
   print(res)
   ```

6. カレンダー更新（夜間バッチ）
   ```python
   from kabusys.data.calendar_management import calendar_update_job
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   saved = calendar_update_job(conn)
   print(f"calendar updated: {saved}")
   ```

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (省略可, デフォルト http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (省略可, デフォルト data/kabusys.duckdb)
- SQLITE_PATH (省略可, デフォルト data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効化

注意: Settings クラスで不正な値や未設定があると ValueError が発生します。

---

## ディレクトリ構成（主要ファイル）

リポジトリは src/kabusys 以下に実装されています。主なファイル・モジュール:

- src/kabusys/__init__.py
- src/kabusys/config.py
  - 環境変数の自動読み込み・Settings
- src/kabusys/data/
  - jquants_client.py    — J-Quants API クライアント（取得・保存）
  - news_collector.py    — RSS ニュース収集・保存・銘柄抽出
  - schema.py            — DuckDB スキーマ定義と初期化（init_schema / get_connection）
  - stats.py             — zscore_normalize 等の統計ユーティリティ
  - pipeline.py          — ETL パイプライン（run_daily_etl 等）
  - calendar_management.py — マーケットカレンダー管理
  - features.py          — data.stats の再エクスポート
  - audit.py             — 監査ログ系テーブル定義
- src/kabusys/research/
  - factor_research.py   — momentum / value / volatility 等のファクター計算
  - feature_exploration.py — 将来リターン／IC／統計サマリー
- src/kabusys/strategy/
  - feature_engineering.py — ファクターの正規化／features への保存
  - signal_generator.py    — final_score 計算、BUY/SELL 判定、signals 保存
- src/kabusys/execution/
  - （発注／監視関連は別途実装想定）
- その他: monitoring / execution / 実行用 CLI 等は将来的な拡張箇所

---

## 開発・運用上の注意

- DuckDB テーブル定義では一部の外部キー制約や ON DELETE 動作が DuckDB のバージョン差で扱いにくいため、コメントに注意書きがあります。運用時は削除順序など運用ルールを守ってください。
- ニュース RSS の取得は外部ネットワークに依存するため、SSRF 対策やレスポンスサイズ上限（10MB）など安全対策を実装済みです。
- J-Quants API はレート制限（120 req/min）に合わせたスロットリング実装とリトライロジックがあります。証券会社 API（kabuステーション等）接続部分は別モジュールに切り出す想定です。
- 本コードは本番（live）運用向けのスイッチを環境変数 KABUSYS_ENV で持ちます。paper_trading／live の扱いに注意してください。

---

ご要望があれば、README にサンプル .env.example、requirements.txt の例、CI/CD や cron でのジョブ運用例、より詳しい API ドキュメント（各関数の引数・戻り値を網羅）等を追加できます。どの情報を優先して追加しますか？