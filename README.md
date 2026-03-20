# KabuSys

日本株向けの自動売買システム（ライブラリ）です。市場データ取得・ETL、特徴量計算、シグナル生成、ニュース収集、監査・実行レイヤー向けのスキーマやユーティリティを提供します。DuckDB を中心に据え、J-Quants API や RSS ニュースを取り込み、戦略（feature → signal）を独立して実行できる設計です。

バージョン: 0.1.0

---

## 概要（Project overview）

KabuSys は以下を目的としたコンポーネント群を含む Python パッケージです。

- J-Quants API からの市場データ（株価、財務、取引カレンダー）取得と DuckDB への安全な保存（冪等）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- 研究用ファクター計算・特徴量正規化（research モジュール）
- 戦略レイヤー：特徴量からシグナル（BUY/SELL）を生成（strategy モジュール）
- ニュース収集（RSS）と銘柄紐付け（news_collector）
- データスキーマ（DuckDB）の初期化・管理（data.schema）
- 発注・監査用テーブル定義およびユーティリティ（execution / audit 用スキーマ）
- 軽量な統計ユーティリティ（Z スコア正規化等）

設計上の主眼：
- ルックアヘッドバイアスの排除（target_date 時点のデータのみ使用）
- 冪等性（DB 書き込みは ON CONFLICT 等で重複回避）
- 外部依存を最小化（可能な限り標準ライブラリと duckdb のみ）
- テストしやすい設計（トークン注入、モックしやすい HTTP ハンドラ等）

---

## 機能一覧（Features）

- data/
  - jquants_client: J-Quants API クライアント（レート制限・リトライ・自動トークンリフレッシュ）
  - pipeline: 日次 ETL（prices / financials / calendar）の差分取得 + 保存 + 品質チェック
  - schema: DuckDB の完全スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
  - news_collector: RSS フィード収集、前処理、raw_news 保存、銘柄抽出・紐付け
  - calendar_management: JPX カレンダーの更新・営業日判定ユーティリティ
  - stats: zscore_normalize 等の統計ユーティリティ
- research/
  - factor_research: Momentum / Value / Volatility 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、統計サマリー
- strategy/
  - feature_engineering: 生ファクターを正規化・フィルタして features テーブルへ保存
  - signal_generator: features と ai_scores を統合し BUY/SELL シグナルを生成して signals テーブルへ保存
- execution / monitoring
  - 発注/監視向けのスキーマやエントリポイントを想定（execution/monitoring は API の公開ポイント）

主な高信頼設計要素：
- ETL のバックフィル（API の後出し修正を吸収）
- DB トランザクションでの原子性保証（BEGIN/COMMIT/ROLLBACK）
- RSS の SSRF 防止・XML 安全処理・受信サイズ制限
- J-Quants のページネーション・レート制御

---

## 必要条件（Requirements）

- Python 3.9+
- duckdb
- defusedxml (ニュース収集で使用)
- ネットワークアクセス（J-Quants API / RSS フィード）
- J-Quants の refresh token、Slack トークンなどの環境変数（下記参照）

パッケージ依存はプロジェクト側で管理してください（requirements.txt / pyproject.toml を参照・作成）。

---

## 環境変数（主な設定項目）

KabuSys は .env ファイル（プロジェクトルート）または環境変数から設定を読み込みます（自動ロード: OS 環境変数 > .env.local > .env）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants の refresh token
- KABU_API_PASSWORD — kabu API（kabuステーション）パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意（デフォルトあり）:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境（development|paper_trading|live、デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL、デフォルト: INFO）

注意: Settings クラスは未設定の必須変数で ValueError を投げます。.env.example を参照して .env を作成してください。

---

## セットアップ手順（Setup）

1. リポジトリをクローン
   - git clone <repo-url>

2. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - pip install -r requirements.txt
   または
   - pip install duckdb defusedxml

4. パッケージを開発モードでインストール（任意）
   - pip install -e .

5. 環境変数設定
   - プロジェクトルートに `.env` を作成して必須変数を記入するか、環境変数をエクスポートしてください。
   - 例 (.env):
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678

6. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで初期化します（デフォルトパスを使用する例）:

     from kabusys.data import schema
     from kabusys.config import settings
     conn = schema.init_schema(settings.duckdb_path)

   - ":memory:" を渡すとインメモリ DB が使えます（テスト用）。

---

## 使い方（Usage）

以下は代表的な利用例の抜粋です。各関数は duckdb の接続（DuckDBPyConnection）と日付を受け取る設計です。

1) スキーマ初期化（先述）

2) 日次 ETL（市場カレンダー・株価・財務を差分取得して保存）
   - シンプルな実行例:

     from datetime import date
     import duckdb
     from kabusys.data import pipeline, schema
     from kabusys.config import settings

     conn = schema.init_schema(settings.duckdb_path)
     result = pipeline.run_daily_etl(conn, target_date=date.today())
     print(result.to_dict())

   - ETLResult に取得件数や品質問題・エラー情報が含まれます。

3) 特徴量構築（features テーブルへ）
   - build_features は research の calc_* に依存しており、prices_daily/raw_financials が必要です。

     from datetime import date
     from kabusys.strategy import build_features
     from kabusys.data import schema
     from kabusys.config import settings

     conn = schema.get_connection(settings.duckdb_path)
     n = build_features(conn, target_date=date(2024, 1, 31))
     print(f"features built: {n}")

4) シグナル生成（signals テーブルへ）
   - generate_signals は features / ai_scores / positions を参照し、BUY/SELL を生成します。

     from kabusys.strategy import generate_signals

     conn = schema.get_connection(settings.duckdb_path)
     count = generate_signals(conn, target_date=date(2024, 1, 31))
     print(f"signals written: {count}")

   - weights や threshold を引数でオーバーライドできます。

5) ニュース収集ジョブ
   - run_news_collection で RSS ソースを一括取得・保存し、既知銘柄との紐付けを行います。

     from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
     from kabusys.data import schema

     conn = schema.get_connection(settings.duckdb_path)
     known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット
     res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
     print(res)

6) カレンダー更新（夜間バッチ）
   - calendar_update_job で market_calendar の差分更新を行います。

     from kabusys.data.calendar_management import calendar_update_job
     saved = calendar_update_job(conn)
     print(f"saved calendar rows: {saved}")

7) 低レベル API（J-Quants など）
   - jquants_client には fetch_*/save_* 系の関数があり、必要に応じて直接呼べます。

     from kabusys.data import jquants_client as jq
     records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
     saved = jq.save_daily_quotes(conn, records)

---

## 開発・テストのヒント

- 自動で .env を読み込む仕組みはプロジェクトルート（.git または pyproject.toml）を基準に探索します。テストで自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB のインメモリ接続（":memory:"）はユニットテストで便利です。
- jquants_client の HTTP 呼び出しや news_collector の _urlopen はテスト時にモック可能になるよう設計されています。
- ETL/pipeline の各ステップは例外を局所で捕捉して処理を継続するため、結果オブジェクト（ETLResult）で失敗状況を確認できます。

---

## ディレクトリ構成（Directory structure）

以下、主要なソース構成（src/kabusys 配下の抜粋）:

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
      - audit/ (監査関連モジュールや補助ファイルが入る想定)
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
      - (発注/実行関連モジュール — 実装は別途)
    - monitoring/
      - __init__.py
      - (監視・アラート関連 — 実装は別途)

なお、上記は現在のコードベースの主要ファイルを抜粋したもので、将来的にモジュールが増える想定です。

---

## 参考・補足

- ログレベルや環境の設定は Settings クラス（kabusys.config）で管理されます。無効な値を与えると ValueError が発生します。
- DB スキーマは DataPlatform.md / DataSchema.md 等の設計資料に準拠しています（コメントや CHECK、インデックスなどを含む）。
- セキュリティ対策: RSS の SSRF 対策、XML の defusedxml 使用、J-Quants のレート制御とトークン管理、DB への書き込みは基本的に冪等を意識しています。
- 本リポジトリは本番発注（live）での使用を想定していますが、paper_trading / development モードを切り替えて安全にテストしてください。

---

この README はコードベースの主要な使い方と構成をまとめたものです。追加の API ドキュメントや運用手順（cron / Airflow の設定例、Slack 通知の利用法、バックアップ方針等）は別途補完してください。