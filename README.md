# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォーム用ライブラリです。J-Quants API から市場データ・財務データ・カレンダーを取得して DuckDB に保存し、研究用ファクター計算、特徴量生成、シグナル作成、ニュース収集、監査ログなどの機能を提供します。

主な設計方針は「ルックアヘッドバイアス排除」「冪等性（Idempotency）」「ネットワーク/セキュリティ対策（SSRF対策等）」です。

---

## 機能一覧

- 環境変数/設定読み込み（.env 自動読み込み, 必須設定チェック）
- J-Quants API クライアント
  - 株価日足（OHLCV）の取得（ページネーション対応、レートリミッタ、リトライ）
  - 財務データ、マーケットカレンダーの取得
  - DuckDB へ冪等保存（ON CONFLICT 相当の更新）
- DuckDB スキーマ定義と初期化（raw / processed / feature / execution 層）
- ETL パイプライン（差分更新・バックフィル・品質チェック統合）
- 研究用ファクター計算（Momentum / Volatility / Value 等）
- 特徴量エンジニアリング（Z スコア正規化・ユニバースフィルタ）
- シグナル生成（複数コンポーネントの重み付き合算、Bear レジーム抑制、BUY/SELL 判定）
- ニュース収集（RSS フィード取得、SSRF対策、記事ID正規化、記事と銘柄の紐付け）
- 監査ログ（signal → order → execution のトレーサビリティ用テーブル群）
- マーケットカレンダー管理（営業日判定、next/prev 等ユーティリティ）

---

## 必要条件・依存関係

- Python 3.9+（型注釈で Union 演算子を使用するため）
- 必須パッケージ（主にコードから推定）
  - duckdb
  - defusedxml

（プロジェクトの packaging/requirements が別途ある場合はそちらを優先してください）

---

## 環境変数

以下の環境変数がコード内で参照されます。必須のものは設定がないと例外になります。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード（実行層で使用）
- SLACK_BOT_TOKEN — Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意（デフォルトあり）:
- KABU_API_BASE_URL — kabu API ベース URL（default: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（default: data/monitoring.db）
- KABUSYS_ENV — 環境 ("development" | "paper_trading" | "live")（default: development）
- LOG_LEVEL — ログレベル（"DEBUG","INFO",...）（default: INFO）

自動でプロジェクトルートの .env → .env.local を読み込みます。自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例 (.env):
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. Python 仮想環境の作成と有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（例）
   - pip install duckdb defusedxml

   実際のプロジェクトには requirements.txt / pyproject.toml がある想定なので、そこからインストールしてください。

3. 環境変数を設定
   - プロジェクトルートに `.env` を作成して必要なキーを設定するか、シェル環境で export/set してください。

4. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで以下を実行:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")  # ディレクトリは自動作成されます
     ```

---

## 使い方（簡単な例）

下記は主要なワークフロー（ETL → 特徴量生成 → シグナル作成）の例です。

- ETL（市場データの差分取得と保存）
  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量の構築（features テーブルへ保存）
  ```python
  from datetime import date
  from kabusys.strategy import build_features

  count = build_features(conn, target_date=date(2024, 1, 31))
  print(f"features upserted: {count}")
  ```

- シグナル生成（signals テーブルへ保存）
  ```python
  from datetime import date
  from kabusys.strategy import generate_signals

  total_signals = generate_signals(conn, target_date=date(2024, 1, 31))
  print(f"signals generated: {total_signals}")
  ```

- ニュース収集と銘柄紐付け
  ```python
  from kabusys.data.news_collector import run_news_collection

  # known_codes: 銘柄抽出に使用する有効な銘柄コードの集合
  res = run_news_collection(conn, known_codes={"7203","6758"})
  print(res)  # {source_name: saved_count, ...}
  ```

- カレンダー操作のユーティリティ
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  print(is_trading_day(conn, date.today()))
  print(next_trading_day(conn, date.today()))
  ```

ログや障害状況は logger に出力されます。必要に応じて logging.basicConfig() 等で設定してください。

---

## 主要 API（抜粋）

- kabusys.config.settings — 環境設定アクセス（settings.jquants_refresh_token 等）
- kabusys.data.schema.init_schema(db_path) — DuckDB の全スキーマを初期化して接続を返す
- kabusys.data.schema.get_connection(db_path) — 既存 DB への接続を返す
- kabusys.data.jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar — API 取得
- kabusys.data.jquants_client.save_daily_quotes / save_financial_statements / save_market_calendar — DuckDB 保存
- kabusys.data.pipeline.run_daily_etl(...) — 日次 ETL（calendar, prices, financials, quality checks）
- kabusys.research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic — 研究用関数
- kabusys.strategy.build_features(conn, target_date) — 特徴量構築
- kabusys.strategy.generate_signals(conn, target_date, threshold, weights) — シグナル生成
- kabusys.data.news_collector.run_news_collection(...) — RSS 収集ジョブ

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内の主要モジュール構成（src/kabusys 以下）です。

- kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - pipeline.py
    - stats.py
    - features.py
    - calendar_management.py
    - audit.py
    - (その他: quality, execution 関連モジュール等想定)
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
  - monitoring/  (パッケージ公開名に含まれるがコードは省略/別ファイルで提供)

各モジュールは責務が明確に分離されています（データ取得層 / データ処理層 / 研究層 / 戦略層 / 発注・監査層）。

---

## 運用上の注意

- DuckDB ファイルはデフォルトで project/data/kabusys.duckdb に保存されます。運用環境ではバックアップやディスク容量に注意してください。
- J-Quants API のレート制限・リトライはクライアントで制御していますが、実利用時はトークン管理・エラーハンドリングを十分に行ってください。
- ニュース収集では外部 RSS を解析するため、defusedxml による安全対策や SSRF 検査を実装しています。HTTP クライアントのタイムアウト等を適切に設定してください。
- 本リポジトリの一部は設計ドキュメント（DataPlatform.md, StrategyModel.md 等）に準拠しています。実運用向けには追加のリスク管理/注文執行（kabuステーション連携）実装が必要です。
- 自動環境読み込み機能が不要なテストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

この README はコードベースの主要機能と使い方を簡潔にまとめたものです。追加の使用例・API仕様書・運用手順（cron / systemd / コンテナ化など）はプロジェクトの運用要件に合わせて追記してください。質問や特定のモジュールの詳細説明が必要であれば教えてください。