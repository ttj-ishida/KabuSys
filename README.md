# KabuSys

KabuSys は日本株向けの自動売買プラットフォーム用ライブラリ群です。  
データ収集（J-Quants）、ETL、マーケットカレンダー管理、ニュース収集、ファクター計算、特徴量生成、シグナル生成、監査ログ/スキーマ管理など、戦略実行に必要な主要コンポーネントを提供します。

---

## 主要な特徴（機能一覧）

- 環境設定管理
  - .env / 環境変数から設定読み込み（自動ロード、上書きルール、保護キー）
- データ収集（J-Quants API クライアント）
  - 日次株価、財務データ、マーケットカレンダーのページネーション対応取得
  - レートリミット制御、リトライ（指数バックオフ）、トークン自動リフレッシュ
  - DuckDB への冪等保存（ON CONFLICT / upsert）
- ETL パイプライン
  - 差分更新（バックフィル対応）、品質チェックフック、日次 ETL 実行（run_daily_etl）
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution レイヤーのテーブル定義と初期化（init_schema）
  - インデックス定義、テーブル作成の冪等化
- ニュース収集（RSS）
  - RSS フィード取得、XML 安全パース（defusedxml）、SSRF 対策、URL 正規化、記事ID生成、銘柄抽出、DB へ冪等保存
- リサーチ用ファクター計算
  - Momentum / Volatility / Value 等のファクターを prices_daily / raw_financials から計算
  - 将来リターン計算 (forward returns)、IC（Spearman）計算、ファクター統計サマリ
- 特徴量エンジニアリング
  - 研究で生成された生ファクターを正規化・フィルタして `features` テーブルへ保存（冪等）
- シグナル生成
  - features と ai_scores を統合して final_score を算出、BUY/SELL シグナルを生成して `signals` テーブルへ保存（冪等）
  - Bear レジーム判定、売買ロジック（閾値・ストップロス等）
- カレンダー管理
  - JPX カレンダーの管理、営業日判定、前後営業日の取得、期間内の営業日リスト取得
- 監査ログ（Audit）
  - signal → order_request → executions のトレーサビリティを担保するテーブル群

---

## セットアップ手順

前提:
- Python 3.9+（コードは型ヒントに | を使用しているため 3.10 以上を推奨する場合もありますが、3.9 も可能です）
- DuckDB が必要（Python パッケージ duckdb）
- ネットワークアクセス（J-Quants API、RSS フィード）

1. リポジトリをクローン / 取得
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows (PowerShell/CMD に応じて)
   ```

3. 必要パッケージをインストール
   - 最低限必要な依存（例）
     - duckdb
     - defusedxml
   - 例:
     ```bash
     pip install duckdb defusedxml
     ```
   - パッケージ配布ファイルがある場合:
     ```bash
     pip install -e .
     ```

4. 環境変数 / .env の準備
   - ルートに `.env` または `.env.local` を置くと自動読み込みされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN (J-Quants リフレッシュトークン)
     - KABU_API_PASSWORD (kabu API パスワード)
     - SLACK_BOT_TOKEN (Slack 通知用 Bot トークン)
     - SLACK_CHANNEL_ID (通知先チャンネル ID)
   - デフォルト値を持つもの:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL — デフォルト: INFO
     - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
   - .env の簡単な例:
     ```
     JQUANTS_REFRESH_TOKEN=your_refresh_token_here
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     ```

5. データベース初期化（DuckDB スキーマ作成）
   - Python REPL またはスクリプトから:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")  # デフォルトパスを使う場合
     conn.close()
     ```

---

## 使い方（代表的なユースケース）

以下はライブラリを直接利用する際の基本的なコード例です。実運用ではログ設定やエラーハンドリングを追加してください。

- DB 初期化（最初に一度）
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL（市場カレンダー・株価・財務の差分取得と品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # target_date を指定可
  print(result.to_dict())
  ```

- 特徴量構築（research の生ファクターを正規化して features に保存）
  ```python
  from kabusys.strategy import build_features
  from kabusys.data.schema import get_connection
  from datetime import date

  conn = get_connection("data/kabusys.duckdb")
  count = build_features(conn, date(2025, 1, 31))
  print(f"features updated: {count}")
  ```

- シグナル生成
  ```python
  from kabusys.strategy import generate_signals
  from kabusys.data.schema import get_connection
  from datetime import date

  conn = get_connection("data/kabusys.duckdb")
  total_signals = generate_signals(conn, date(2025, 1, 31), threshold=0.6)
  print(f"signals written: {total_signals}")
  ```

- ニュース収集ジョブ（RSS を取得して raw_news に保存、既知銘柄リストで紐付け）
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 例: 銘柄コードセット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- J-Quants から日次株価を直接取得して保存
  ```python
  from kabusys.data import jquants_client as jq
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, records)
  print(saved)
  ```

---

## 環境変数 / 設定一覧（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API 用パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境 (development|paper_trading|live)（デフォルト: development）
- LOG_LEVEL: ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env の自動ロードを無効化

設定値は kabusys.config.settings 経由で取得できます。

---

## ディレクトリ構成

以下は主要ファイル／モジュールの概略ツリー（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                      -- 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py             -- J-Quants API クライアント（取得 & 保存）
    - news_collector.py             -- RSS ニュース収集・前処理・DB 保存
    - schema.py                     -- DuckDB スキーマ定義と初期化
    - stats.py                      -- 統計ユーティリティ（zscore_normalize 等）
    - pipeline.py                   -- ETL パイプライン（run_daily_etl 等）
    - features.py                   -- data.stats の公開ラッパ
    - calendar_management.py        -- カレンダー管理、営業日判定、更新ジョブ
    - audit.py                      -- 監査ログ用スキーマ
    - audit (続き...)               -- （監査用 DDL 等）
  - research/
    - __init__.py
    - factor_research.py            -- Momentum/Volatility/Value 計算
    - feature_exploration.py        -- forward returns, IC, summary, rank
  - strategy/
    - __init__.py
    - feature_engineering.py        -- features を作成して features テーブルへ保存
    - signal_generator.py           -- final_score 計算・BUY/SELL シグナル生成
  - execution/
    - __init__.py                   -- （将来的な発注ライブラリ連携用）
  - monitoring/                      -- 監視・通知周り（パッケージ初期化時参照はあるが実装ファイルは本ツリーに依存）

注: 上記はコードベースの一部を抜粋した構成です。実運用コードでは更に CLI や worker、webhook、監視モジュール等が追加されることがあります。

---

## 運用上の注意 / 設計方針（抜粋）

- ルックアヘッドバイアス防止:
  - ファクター・シグナル生成は target_date 時点までのデータのみを使用する設計。
  - J-Quants データ取得は fetched_at を UTC で保存し、いつデータが得られたかをトレース可能にする。
- 冪等性:
  - DuckDB への保存は ON CONFLICT（upsert）や INSERT ... DO NOTHING を利用し冪等化。
  - ETL・feature/build・signal/generate の操作は日付単位で置換（DELETE → INSERT）することで再実行を安全にしている。
- セキュリティ:
  - RSS パースは defusedxml を使用し XML 攻撃を緩和。
  - ニュース収集では SSRF 対策（スキーム検証、プライベートIP検査、リダイレクト検査）を実装。
  - J-Quants API ではレート制限とリトライを実装し API 利用制限に配慮。

---

## 開発 / 貢献

- コード規約、ドキュメント（StrategyModel.md、DataPlatform.md、DataSchema.md 等）に沿って実装が進められています。新しい機能追加やバグ修正の際はユニットテスト、静的解析、logging の適切な利用を心がけてください。
- 自動ロードされる .env の取り扱いに注意。CI やテスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して外部依存を切り離すことが可能です。

---

この README はコードベースの主要機能と基本的な使い方をまとめたものです。詳細な API 仕様や運用手順 (デプロイ、ジョブスケジューリング、監視設定など) は別途ドキュメント（StrategyModel.md、DataPlatform.md、DataSchema.md 等）を参照してください。必要であれば、README にサンプルのワークフロー（cron/airflow ジョブ例や slack 通知例）を追加しますのでお申し付けください。