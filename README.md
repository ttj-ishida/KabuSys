# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（部分実装）。  
データ収集（J-Quants）、データ処理（DuckDB）、特徴量作成、シグナル生成、ニュース収集、マーケットカレンダー管理などの基盤機能を提供します。

---

## 概要

KabuSys は日本株の量的・AI混合戦略を運用するための内部ライブラリ群です。  
主に以下の役割を持つモジュールで構成されています。

- データレイヤ（J-Quants からの取得、DuckDB スキーマ）
- ETL パイプライン（日次の差分取得／保存／品質チェック）
- 研究（factor 計算 / 特徴量探索）
- 戦略（特徴量正規化、シグナル生成）
- ニュース収集（RSS → raw_news）
- マーケットカレンダー管理
- 実行／監査用のスキーマ（signals / orders / executions / positions など）
- 設定管理（.env 自動ロード、環境フラグ）

本リポジトリは戦略ロジックと execution 層を分離し、発注 API への直接依存を持たない設計になっています（発注処理は別モジュール／レイヤで扱う想定です）。

---

## 主な機能

- J-Quants API クライアント（レート制限・リトライ・トークン自動更新）
- DuckDB スキーマ定義と初期化（冪等な DDL 実行）
- 日次 ETL（差分取得、バックフィル、品質チェック）
- ファクター計算（Momentum / Volatility / Value 等）
- 特徴量エンジニアリング（Zスコア正規化・ユニバースフィルタ）
- シグナル生成（コンポーネントスコア合成・BUY/SELL 生成・エグジット判定）
- RSS ベースのニュース収集（URL 正規化、SSRF 対策、記事→銘柄紐付け）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- 設定管理（.env 自動ロード、環境別フラグ、ログレベル）

---

## 前提 / 要件

- Python 3.10 以上（型ヒントで `X | None` を使用しているため）
- 依存パッケージ（最低限）
  - duckdb
  - defusedxml

開発環境では以下を想定しています（適宜 virtualenv を利用してください）。

例:
pip install duckdb defusedxml

（プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを使用してください）

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成・有効化します。

   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate

2. 必要パッケージをインストールします（最低限）:

   pip install duckdb defusedxml

   （プロジェクト依存を pip でまとめて管理している場合は requirements / pyproject に従ってください）

3. 環境変数を設定します。プロジェクトルートに `.env`（または `.env.local`）を配置できます。自動ロードはデフォルトで有効です（CWD ではなく package のファイル位置からプロジェクトルートを検出）。

   主要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意
   - SLACK_BOT_TOKEN=...
   - SLACK_CHANNEL_ID=...
   - DUCKDB_PATH=data/kabusys.duckdb  # デフォルト
   - SQLITE_PATH=data/monitoring.db
   - KABUSYS_ENV=development|paper_trading|live
   - LOG_LEVEL=INFO|DEBUG|...

   自動ロードを無効化したい場合:
   - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時など）。

4. DuckDB スキーマを初期化します（デフォルト db パスは `data/kabusys.duckdb`）:

   Python スクリプト例:

   from kabusys.data.schema import init_schema, settings
   conn = init_schema(settings.duckdb_path)

   これでテーブル群が作成されます（冪等）。

---

## 使い方（主な API の例）

以下に代表的な処理の呼び出し例を示します。実運用ではこれらをラッパースクリプトやジョブスケジューラ（cron / Airflow / systemd timer 等）から呼ぶ想定です。

- DuckDB 初期化

  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)

- 日次 ETL（J-Quants から差分取得して保存）

  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  # conn は init_schema または get_connection の戻り値
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- マーケットカレンダーの夜間更新ジョブ

  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print("saved", saved)

- ニュース収集（RSS → raw_news + news_symbols）

  from kabusys.data.news_collector import run_news_collection
  # known_codes: 有効な銘柄コードセット（例: DBから prices_daily のコード一覧など）
  results = run_news_collection(conn, known_codes=set(["7203", "6758", ...]))
  print(results)

- 特徴量作成

  from datetime import date
  from kabusys.strategy import build_features
  count = build_features(conn, target_date=date.today())
  print("features upserted:", count)

- シグナル生成

  from datetime import date
  from kabusys.strategy import generate_signals
  total_signals = generate_signals(conn, target_date=date.today())
  print("signals:", total_signals)

注意点:
- これらの関数は DuckDB 接続を直接受け取るため、トランザクションや接続管理は呼び出し側で行うことが可能です。
- run_daily_etl 等は内部で例外を捕捉して処理を継続する性質があるため、戻り値（ETLResult）でエラーや品質問題を確認してください。

---

## 環境変数（.env）および自動ロード

kabusys/config.py により、プロジェクトルート（.git または pyproject.toml を基準）にある `.env` / `.env.local` を自動で読み込みます（既存 OS 環境変数を上書きしない / .env.local は上書き可）。

主なキー:
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development / paper_trading / live)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)

自動ロードを無効にする:
- 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

未設定の必須キーにアクセスしようとすると ValueError が発生します（settings.jquants_refresh_token 等）。

---

## ディレクトリ構成

主要なファイルとモジュール（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py                  # 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py        # J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py        # RSS ニュース収集・保存
    - schema.py                # DuckDB スキーマ定義・初期化
    - stats.py                 # 統計ユーティリティ（zscore_normalize）
    - pipeline.py              # ETL パイプライン（run_daily_etl 等）
    - features.py              # data 層の特徴量ユーティリティ公開
    - calendar_management.py   # マーケットカレンダー管理
    - audit.py                 # 監査ログ関連スキーマ
    - ...                      # （quality モジュール等は参照されるがここには含まれていない可能性あり）
  - research/
    - __init__.py
    - factor_research.py       # モメンタム・ボラティリティ・バリュー計算
    - feature_exploration.py   # IC / forward returns / summary
  - strategy/
    - __init__.py
    - feature_engineering.py   # features テーブル作成ロジック
    - signal_generator.py      # シグナル生成ロジック
  - execution/                  # 発注／実行層（placeholder）
  - monitoring/                 # 監視・メトリクス（placeholder）

その他:
- data/ (デフォルトの DB ファイルや SQLite の格納先)
- .env / .env.local (プロジェクトルートで管理)

---

## 開発メモ / 設計上の注意

- ルックアヘッドバイアスを避けるため、全ての計算は target_date 時点のデータのみを参照する方針です。
- DuckDB への保存関数は冪等（ON CONFLICT / DO UPDATE / DO NOTHING）を採用しています。
- J-Quants クライアントはレート制限・リトライ（指数バックオフ）・401 時のトークンリフレッシュを実装しています。
- RSS 収集では SSRF 対策（リダイレクト検査・プライベートホストブロック）や XML パースの安全対策（defusedxml）を行っています。
- Python 3.10 の型構文（A | B）を使用しているため、3.10 未満では動作しません。

---

## 貢献 / ライセンス

この README はソースコードから抽出した設計意図と利用法をまとめたものです。  
詳細な運用ルール（StrategyModel.md / DataPlatform.md / DataSchema.md 等）はリポジトリ内の関連ドキュメントを参照してください。

ライセンスや貢献ガイドが別途ある場合はそちらに従ってください。

---

以上。必要であれば README に含める実行スクリプト例（systemd timer / cron / docker-compose など）や .env.example のテンプレートも作成できます。どの情報が欲しいか教えてください。