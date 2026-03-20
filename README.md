# KabuSys

日本株向けの自動売買プラットフォーム（骨格実装）。  
データ取得（J-Quants）、ETL、スキーマ管理、特徴量計算、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなどを含むモジュール群を備えています。研究（research）モジュールは戦略開発やファクター検証用のユーティリティを提供します。

---

## 主な目的（概要）
- J-Quants API 等から市場データ・財務データ・カレンダー・ニュースを取得し DuckDB に格納する。
- 取得データを加工して特徴量（features）を作成し、戦略に基づくシグナルを生成する。
- 発注や約定などの実行・監査ログを保持するためのスキーマを定義する（発注実装は別途）。
- 研究環境向けにファクター計算・IC計算などの分析ユーティリティを提供する。

---

## 機能一覧
- 環境変数/.env からの設定読み込み（自動ロード、上書き制御あり）
- J-Quants API クライアント
  - レート制御、リトライ、トークン自動リフレッシュ
  - 株価日足・財務データ・マーケットカレンダー取得
  - DuckDB へ冪等保存（ON CONFLICT / upsert）
- DuckDB スキーマ定義と初期化（raw / processed / feature / execution レイヤー）
- ETL パイプライン（差分取得・バックフィル・品質チェック呼び出し）
- マーケットカレンダー管理（営業日判定・next/prev trading day 等）
- ニュース収集（RSS）・テキスト前処理・銘柄コード抽出・DB保存
- 特徴量エンジニアリング（research の生ファクターを正規化して features テーブルへ保存）
- シグナル生成（features + AI スコア統合 → final_score → BUY/SELL 判定、エグジット判定）
- 研究ユーティリティ（将来リターン計算、IC、ファクター統計など）
- 監査ログスキーマ（signal → order_request → executions のトレース用テーブル群）

---

## 動作要件
- Python 3.10 以上（| を使った型注釈等のため）
- 必要な Python パッケージ（最低限）
  - duckdb
  - defusedxml
- 標準ライブラリで実装されている部分が多く、追加パッケージは最小限です。必要に応じて requirements を整備してください。

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成
   ```
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. 依存パッケージをインストール
   ```
   pip install duckdb defusedxml
   ```
   （実際のプロジェクトでは requirements.txt / pyproject.toml を用意して `pip install -e .` 等を推奨します）

3. 環境変数設定（.env）
   プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（設定を無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

   最小構成の例（.env.example のイメージ）:
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

4. DuckDB スキーマ初期化
   Python REPL かスクリプトから以下を実行して DB を初期化します（デフォルトパスは settings.duckdb_path）。
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)
   # これで必要なテーブルが作成されます
   conn.close()
   ```

---

## 使い方（主な操作例）

- 日次 ETL の実行（株価・財務・カレンダーを差分取得して保存）
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)  # target_date を指定することも可能
  print(result.to_dict())
  conn.close()
  ```

- 特徴量のビルド（features テーブルへ書き込み）
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.config import settings
  from kabusys.strategy import build_features
  from datetime import date

  conn = init_schema(settings.duckdb_path)
  n = build_features(conn, target_date=date.today())
  print(f"features upserted: {n}")
  conn.close()
  ```

- シグナル生成（features / ai_scores / positions を参照して signals を作成）
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.config import settings
  from kabusys.strategy import generate_signals
  from datetime import date

  conn = init_schema(settings.duckdb_path)
  total = generate_signals(conn, target_date=date.today(), threshold=0.6)
  print(f"signals written: {total}")
  conn.close()
  ```

- ニュース収集ジョブ（RSS 収集 → raw_news 保存 → news_symbols 紐付け）
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.config import settings
  from kabusys.data.news_collector import run_news_collection

  conn = init_schema(settings.duckdb_path)
  # known_codes は銘柄コードセット（抽出に用いる）
  results = run_news_collection(conn, known_codes={"7203","6758"})
  print(results)
  conn.close()
  ```

- マーケットカレンダー更新ジョブ
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")
  conn.close()
  ```

注意点:
- settings の必須プロパティ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）はアクセス時にチェックされ、未設定だと ValueError を送出します。ETL 実行などでこれらを必要とする場合は `.env` に設定してください。
- 自動で .env を読み込むため、CWD に依存せずプロジェクトルート（.git または pyproject.toml を探す）を起点として探索します。テスト等で自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 主な API（モジュール単位）
- kabusys.config
  - Settings クラスによる環境設定取得（例: settings.jquants_refresh_token）
- kabusys.data.jquants_client
  - get_id_token(), fetch_daily_quotes(), fetch_financial_statements(), fetch_market_calendar()
  - save_daily_quotes(), save_financial_statements(), save_market_calendar()
- kabusys.data.schema
  - init_schema(db_path), get_connection(db_path)
- kabusys.data.pipeline
  - run_daily_etl(), run_prices_etl(), run_financials_etl(), run_calendar_etl()
- kabusys.data.news_collector
  - fetch_rss(), save_raw_news(), run_news_collection(), extract_stock_codes()
- kabusys.data.calendar_management
  - is_trading_day(), next_trading_day(), prev_trading_day(), get_trading_days(), calendar_update_job()
- kabusys.data.stats
  - zscore_normalize()
- kabusys.research
  - calc_momentum(), calc_volatility(), calc_value(), calc_forward_returns(), calc_ic(), factor_summary()
- kabusys.strategy
  - build_features(), generate_signals()

---

## ディレクトリ構成（主なファイル）
（リポジトリの root に `src/kabusys/` 配下がある想定）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（取得・保存）
    - news_collector.py            — RSS ニュース収集 / 前処理 / DB 保存
    - schema.py                    — DuckDB スキーマ定義・初期化
    - pipeline.py                  — ETL パイプライン（差分取得・backfill）
    - features.py                  — features 用の軽量インターフェース
    - stats.py                     — 統計ユーティリティ（z-score 等）
    - calendar_management.py       — 市場カレンダー管理・更新ジョブ
    - audit.py                     — 監査ログ（signal/order/execution）
    - execution/                    — 発注関連のプレースホルダ（拡張領域）
  - research/
    - __init__.py
    - factor_research.py           — Momentum/Volatility/Value の生ファクター計算
    - feature_exploration.py       — 将来リターン・IC・ファクター統計
  - strategy/
    - __init__.py
    - feature_engineering.py       — 生ファクターの正規化・features 生成
    - signal_generator.py          — features + ai_scores → final_score → signals
  - monitoring/                     — 監視/モニタリング用コード（拡張領域）
  - execution/                      — 実際のブローカー接続/発注実装（拡張領域）

---

## 開発・貢献
- 新しい機能追加やバグ修正はモジュール単位でテストを追加してください。
- .env の自動読み込みを無効化してユニットテストを走らせるには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 外部 API を直接叩く箇所（jquants_client._request, news_collector._urlopen 等）はモックしやすい設計を意識しています。

---

## よくあるトラブルシューティング
- ValueError: "環境変数 'JQUANTS_REFRESH_TOKEN' が設定されていません。"  
  → .env に該当キーを追加するか、環境変数を設定してください。テスト時は不要なプロパティにアクセスしないようにしてください。
- DuckDB 接続/ファイルパスのエラー  
  → settings.duckdb_path のディレクトリが存在するか確認してください（init_schema は親ディレクトリを自動作成しますが、実行ユーザーの権限に注意）。
- RSS 取得で SSRF/プライベートホスト拒否  
  → ニュース収集は外部 URL のスキームとホストの安全性を厳格に検証します。社内リソースへのアクセスは許可されません。

---

必要に応じて README にサンプルスクリプト、CI 設定、依存関係ファイル（requirements.txt / pyproject.toml）、ライセンス情報、より詳しい運用手順（cron / サービス化）を追記してください。