# KabuSys

日本株自動売買基盤（KabuSys）の軽量リポジトリ説明書

このリポジトリは日本株向けのデータプラットフォーム、特徴量作成、戦略シグナル生成およびETLパイプラインを中心としたモジュール群を提供します。J-Quants API からのデータ取得、DuckDB によるローカルデータベース保存、RSS ニュース収集、ファクター計算・正規化、戦略スコア計算とシグナルの生成を行うことができます。

---

## 主な特徴（機能一覧）

- 環境変数 / .env 自動ロードと設定管理
  - .env / .env.local をプロジェクトルートから自動読み込み（無効化可）
- データ取得・保存（J-Quants API クライアント）
  - 株価日足（OHLCV）、財務データ、JPX カレンダー取得（ページネーション対応）
  - レート制限・リトライ・トークン自動リフレッシュ対応
  - DuckDB への冪等保存（ON CONFLICT / DO UPDATE）
- ETL パイプライン
  - 差分更新（最終取得日に基づく差分取得 + バックフィル）
  - 市場カレンダー・株価・財務データの一括 ETL（run_daily_etl）
  - 品質チェックフレームワーク（quality モジュールを想定）
- ニュース収集
  - RSS フィード取得、URL 正規化、トラッキングパラメータ除去、SSRF 対策
  - raw_news / news_symbols テーブルへの冪等保存
- リサーチ／ファクター計算
  - モメンタム、ボラティリティ、バリュー等のファクター算出（prices_daily / raw_financials を利用）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
  - Z スコア正規化ユーティリティ
- 特徴量エンジニアリング（feature_engineering）
  - 研究で得た生ファクターを統合・正規化して features テーブルへ保存（冪等）
  - ユニバースフィルタ（最低株価・最低売買代金）適用
- シグナル生成（signal_generator）
  - features / ai_scores を組み合わせて銘柄ごとの final_score を算出
  - Bear レジーム検知による BUY 制御、エグジット判定（ストップロス等）
  - signals テーブルへの日付単位置換（冪等）
- DuckDB スキーマ定義 / 初期化（init_schema）

---

## 動作環境（推奨）

- Python 3.10 以上（型注釈に | 演算子等を使用）
- 必須ライブラリ（最低限）
  - duckdb
  - defusedxml
- 推奨：ネットワーク経由で J-Quants / RSS を利用するための標準ライブラリ（urllib 等）を使用

（プロジェクトによっては他の依存がある想定です。requirements.txt があればそれを使用してください）

---

## セットアップ手順

1. リポジトリをクローン / コピー

   git clone <repo-url>
   cd <repo-root>

2. 仮想環境の作成（推奨）

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージのインストール

   pip install --upgrade pip
   pip install duckdb defusedxml

   （プロジェクトに requirements.txt がある場合は `pip install -r requirements.txt`）

4. 環境変数設定
   - プロジェクトルートに `.env`（および `.env.local` 任意）を作成して必要なキーを設定します。
   - 自動ロードはデフォルトで有効：KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化できます。

   必要な主な環境変数（Settings が参照するキー）
   - JQUANTS_REFRESH_TOKEN … J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD … kabuステーション API 用パスワード（必須）
   - KABU_API_BASE_URL … kabuAPI のベース URL（省略時: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN … Slack 通知用トークン（必須）
   - SLACK_CHANNEL_ID … Slack チャネル ID（必須）
   - DUCKDB_PATH … DuckDB ファイルパス（省略時: data/kabusys.duckdb）
   - SQLITE_PATH … 監視用 SQLite パス（省略時: data/monitoring.db）
   - KABUSYS_ENV … 実行環境 (development | paper_trading | live)（省略時: development）
   - LOG_LEVEL … ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)（省略時: INFO）

   例 .env（簡易）
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=yyyy
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

5. データベース初期化（DuckDB スキーマ作成）

   Python REPL かスクリプトで以下を実行:

   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)

   これで必要なテーブルとインデックスが作成されます。

---

## 基本的な使い方（コード例）

- 日次 ETL の実行（カレンダー・株価・財務を取得し、品質チェックまで実施）

  from datetime import date
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- 特徴量（features）作成

  from datetime import date
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.strategy import build_features

  conn = init_schema(settings.duckdb_path)
  n = build_features(conn, target_date=date.today())
  print(f"features upserted: {n}")

- シグナル生成

  from datetime import date
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.strategy import generate_signals

  conn = init_schema(settings.duckdb_path)
  total = generate_signals(conn, target_date=date.today())
  print(f"signals written: {total}")

- ニュース収集（RSS）

  from kabusys.data.news_collector import run_news_collection
  # known_codes: 抽出対象の銘柄コードセット（例: {'7203','6758', ...}）
  saved_map = run_news_collection(conn, sources=None, known_codes=known_codes)
  print(saved_map)

メソッドは冪等性を考慮して設計されています（対象日で DELETE→INSERT の置換方式など）。

---

## 主要モジュール説明（短い要約）

- kabusys.config
  - .env と環境変数の読み込み・設定取得（Settings クラス）。自動ロードはプロジェクトルート（.git / pyproject.toml）基準。
- kabusys.data
  - jquants_client.py: J-Quants API クライアント（取得・保存ユーティリティ）。
  - schema.py: DuckDB のスキーマ定義と初期化（init_schema）。
  - pipeline.py: ETL パイプライン（run_daily_etl, run_prices_etl 等）。
  - news_collector.py: RSS フィード取得と raw_news への保存、銘柄抽出。
  - calendar_management.py: JPX カレンダー管理と営業日判定。
  - stats.py: zscore_normalize 等の統計ユーティリティ。
  - features.py: zscore_normalize の公開ラッパ。
  - audit.py: 監査ログ向けテーブル DDL（signal_events / order_requests / executions など）。
- kabusys.research
  - factor_research.py: モメンタム / ボラティリティ / バリュー等のファクター計算。
  - feature_exploration.py: 将来リターン計算、IC、統計サマリー等。
- kabusys.strategy
  - feature_engineering.py: 生ファクターを正規化して features テーブルへ保存。
  - signal_generator.py: features / ai_scores から final_score を計算し signals を生成。
- kabusys.execution / monitoring
  - 空の __init__ が存在（発注・モニタリング周りの実装を想定）。

---

## ディレクトリ構成（抜粋）

リポジトリの主要ファイル・ディレクトリ例:

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - pipeline.py
    - features.py
    - calendar_management.py
    - stats.py
    - audit.py
    - ...
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
  - monitoring/
    - (将来の監視モジュール)

各ファイルはドキュメント文字列で役割が詳述されており、モジュール単位での利用が可能です。

---

## 運用上の注意 / 実装上の重要点

- ルックアヘッドバイアス回避
  - feature_engineering / signal_generator / research モジュールは target_date 時点で利用可能なデータのみを参照する設計です。
- 冪等性
  - ETL / save_* / features / signals などは日付単位の置換（DELETE → INSERT や ON CONFLICT）で冪等に動作します。
- トークン管理
  - J-Quants の ID トークンは自動リフレッシュとモジュールレベルキャッシュで扱われます。401 時にリフレッシュを試みます。
- セキュリティ考慮
  - RSS の取得は SSRF 対策や gzip 解凍上限、XML パースの保護（defusedxml）を実装しています。
- DuckDB 初期化
  - init_schema は親ディレクトリが存在しない場合に自動作成します。":memory:" 指定でインメモリ DB を利用可能。

---

## 追加開発 / 予定

- execution 層の broker 接続実装（kabuステーション等）／注文送信・約定処理
- monitoring（Slack 通知・稼働ダッシュボード）
- 品質チェックモジュール（quality）とルール拡張
- AI スコア導入パイプラインの実装（ai_scores の生成）

---

この README はコードベースの現状説明と基本的なセットアップ・利用手順をまとめたものです。実際の運用時には J-Quants の利用規約や証券会社の API 制限、取引リスクを十分に理解したうえで利用してください。追加情報（examples、requirements.txt、運用手順書等）があれば README を更新してください。