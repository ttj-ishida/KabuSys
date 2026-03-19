# KabuSys

日本株向けの自動売買/データプラットフォーム用ライブラリ（モジュール群）。  
データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなどの基盤処理を提供します。

主な目的は「ルックアヘッドバイアスを避けつつ、DuckDB を使った冪等なデータパイプラインと戦略パイプラインを提供すること」です。

バージョン: 0.1.0

---

## 主な機能

- データ取得（J-Quants API クライアント）
  - 日足（OHLCV）・財務（四半期）・マーケットカレンダーの取得
  - レート制限、リトライ、トークン自動リフレッシュ対応
- ETL パイプライン
  - 差分取得（バックフィル考慮）と冪等保存（DuckDB の ON CONFLICT 相当）
  - 品質チェック（欠損・スパイク等を検出）
  - 日次 ETL の実行 `run_daily_etl`
- スキーマ管理
  - DuckDB 用スキーマ初期化 (`init_schema`) と接続取得
  - Raw / Processed / Feature / Execution 層のテーブル定義
- 研究・ファクター計算（research）
  - Momentum / Volatility / Value のファクター計算関数
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ
- 特徴量エンジニアリング（strategy.feature_engineering）
  - 生ファクターの正規化（Zスコア）、ユニバースフィルタ、features テーブルへの書き込み
- シグナル生成（strategy.signal_generator）
  - 正規化済みファクター＋AIスコアを統合して final_score を算出し BUY/SELL シグナルを生成
  - Bear レジーム抑制、エグジット（ストップロス等）判定、signals テーブルへの保存
- ニュース収集（data.news_collector）
  - RSS フィード取得、前処理、raw_news への冪等保存、記事⇄銘柄の紐付け
  - SSRF 対策、XML 脆弱性対策、レスポンスサイズ制限等を実装
- マーケットカレンダー管理（data.calendar_management）
  - JPX カレンダーの更新、営業日判定、next/prev_trading_day 等のユーティリティ
- 監査ログ（data.audit）
  - signal → order → execution のトレーサビリティを担保する監査テーブル群

---

## 必要環境

- Python 3.10 以上（型注釈に `X | None` を使用）
- 必須 Python パッケージ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API, RSS 等）

（プロジェクト配布時に requirements.txt / pyproject.toml を提供することを想定）

---

## セットアップ手順

1. リポジトリをクローン / プロジェクトディレクトリへ移動

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (UNIX)
   - .venv\Scripts\activate     (Windows)

3. 必要なパッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトに pyproject.toml / requirements.txt があればそれを使用）

4. 環境変数を設定
   - プロジェクトルートに `.env` / `.env.local` を作成すると、パッケージ読み込み時に自動で読み込まれます（自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 必須の環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD      — kabuステーション API パスワード（execution 層で使用）
     - SLACK_BOT_TOKEN        — Slack 通知に使う Bot トークン
     - SLACK_CHANNEL_ID       — Slack 送信先チャンネル ID
   - 任意:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト `development`
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト `INFO`
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
     - SQLITE_PATH — 監視系 SQLite（デフォルト `data/monitoring.db`）

   例 .env:
     JQUANTS_REFRESH_TOKEN=xxxxx
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

5. DuckDB スキーマ初期化
   - Python から呼ぶ例:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
   - これにより必要なテーブル群とインデックスが作成されます（冪等）。

---

## 使い方（代表的な API）

以下は簡単な利用例（実行は Python REPL / スクリプトで）。

- 設定参照
  from kabusys.config import settings
  token = settings.jquants_refresh_token

- スキーマ初期化 / 接続取得
  from kabusys.data.schema import init_schema, get_connection
  conn = init_schema("data/kabusys.duckdb")  # 初回
  # conn = get_connection("data/kabusys.duckdb")  # 既存 DB へ接続

- 日次 ETL 実行
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)
  print(result.to_dict())

- 特徴量構築（features テーブルの生成）
  from kabusys.strategy import build_features
  from datetime import date
  n = build_features(conn, date(2025, 1, 1))
  print(f"features upserted: {n}")

- シグナル生成
  from kabusys.strategy import generate_signals
  from datetime import date
  total = generate_signals(conn, date(2025, 1, 1))
  print(f"signals written: {total}")

- ニュース収集ジョブ
  from kabusys.data.news_collector import run_news_collection
  # known_codes: (銘柄抽出に用いる有効コード集合) を渡すと銘柄紐付けを行う
  res = run_news_collection(conn, known_codes={'7203','6758'}, timeout=30)
  print(res)

- カレンダー更新ジョブ（夜間バッチ）
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")

- 監査ログ・発注フローは data.audit のテーブル群を利用して実装してください（高レベルの発注実装は execution 層で補完する想定）。

---

## よくあるトラブルシュート

- ValueError: 環境変数が未設定
  - settings のプロパティは必須 env が未設定だと ValueError を投げます。`.env` を作成し必要項目を埋めてください。

- 自動 .env 読み込みを無効化したい（テスト等）
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動読み込みをスキップします。

- DuckDB に接続できない / パーミッションエラー
  - `init_schema` を呼ぶ前に DB の親ディレクトリが作成されますが、ファイルパスに誤りがないか、実行ユーザーに書き込み権限があるか確認してください。

- RSS 取得で XML パースエラーやサイズ超過が出る
  - `data.news_collector` は安全重視の実装（サイズ上限、gzip 検査、defusedxml）です。フィードが大きすぎる・不正な XML の場合は取得がスキップされます。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                        — 環境変数 / 設定管理
- data/
  - __init__.py
  - jquants_client.py               — J-Quants API クライアント
  - news_collector.py               — RSS ニュース収集
  - schema.py                       — DuckDB スキーマ定義・初期化
  - stats.py                        — 統計ユーティリティ（zscore_normalize 等）
  - features.py                     — features API 再エクスポート
  - pipeline.py                     — ETL パイプライン（run_daily_etl 等）
  - calendar_management.py          — カレンダー管理（営業日判定 / 更新ジョブ）
  - audit.py                         — 監査ログの DDL（signal/order/execution）
- research/
  - __init__.py
  - factor_research.py              — ファクター計算 (momentum/volatility/value)
  - feature_exploration.py          — 研究用ユーティリティ (forward returns / IC / summary)
- strategy/
  - __init__.py
  - feature_engineering.py          — 特徴量構築 (build_features)
  - signal_generator.py             — シグナル生成 (generate_signals)
- execution/                         — 発注・ブローカー連携のためのプレースホルダ
- monitoring/                        — 監視・メトリクス（将来的な実装領域）

（README 末尾のファイル一覧は開発段階のため今後拡張される想定です）

---

## 開発上の注意 / 設計方針の要点

- ルックアヘッドバイアスの排除:
  - 全ての計算・シグナルは target_date 時点の利用可能データのみを参照する設計。
  - データ取得時に fetched_at を記録し、いつデータが得られたかを追跡可能にする。
- 冪等性:
  - DuckDB への保存は ON CONFLICT（UPDATE/DO NOTHING）やトランザクションで原子性・冪等性を担保。
- セキュリティ / 安全性:
  - news_collector: SSRF 対策、XML の安全パーサ、レスポンスサイズ制限を実装。
  - jquants_client: レート制限、リトライ、トークン自動リフレッシュを実装。
- テストしやすさ:
  - エントリポイントは引数でトークン注入可能（id_token など）、あるいは自動読み込み無効化フラグがあるため単体テストを書きやすい。

---

フィードバックや追加してほしい使い方（例: CLI スクリプト、Dockerfile、CI 設定）があれば教えてください。README をその要望に合わせて拡張します。