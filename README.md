# KabuSys

バージョン: 0.1.0

KabuSys は日本株の自動売買プラットフォーム向けに設計されたモジュール群です。  
データ取り込み（J-Quants）→ ETL → 特徴量作成 → シグナル生成 → 発注/監査のワークフローを想定したライブラリ群を提供します。  
このリポジトリは主に以下を提供します：DuckDB によるデータスキーマ、J-Quants API クライアント、ニュース収集、ファクター計算、特徴量正規化、シグナル生成、ETL パイプライン等。

---

## 主な機能（機能一覧）

- 環境設定管理
  - .env / .env.local を自動読み込み（必要に応じて無効化可能）
  - 必須環境変数のラップ（Settings クラス）
- データ取得・保存（J-Quants クライアント）
  - 日足（OHLCV）、財務四半期データ、マーケットカレンダーの取得（ページネーション対応）
  - 取得データを DuckDB の raw テーブルに冪等（ON CONFLICT DO UPDATE）で保存
  - レート制限・リトライ・自動トークンリフレッシュ対応
- データスキーマ管理
  - DuckDB 用スキーマ定義・初期化（raw / processed / feature / execution 層）
  - 各種インデックス定義
- ETL パイプライン
  - 差分取得（最終取得日を参照）とバックフィル
  - 市場カレンダー先読み、品質チェックフローと結果集約
- 研究/ファクター群（research）
  - Momentum / Volatility / Value のファクター計算
  - 将来リターン計算、IC（Spearman rank）や統計サマリー
  - Z スコア正規化ユーティリティ
- 特徴量エンジニアリング（strategy.feature_engineering）
  - 生ファクターを統合 → ユニバースフィルタ → Z スコア正規化 → features テーブルへ UPSERT
- シグナル生成（strategy.signal_generator）
  - features と ai_scores を統合して final_score を算出
  - Bear レジーム判定、BUY/SELL シグナル生成、signals テーブルへ日付単位で置換（冪等）
- ニュース収集（data.news_collector）
  - RSS フィードのフェッチ、前処理、raw_news への冪等保存
  - 記事と銘柄コードの紐付け（抽出）機能
  - SSRF / XML Bomb / 大容量応答対策などセキュリティ設計
- 監査ログ（data.audit）
  - signal → order_request → execution までのトレーサビリティ用スキーマ（UUID ベースの監査）

---

## セットアップ手順

前提:
- Python 3.10+ を推奨（型ヒントで Union 型等を使用）
- DuckDB を使用（Python パッケージ duckdb）
- ネットワークアクセス（J-Quants、RSS）可能な環境

1. リポジトリをクローン／入手
   - 例: git clone <repo-url>

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (UNIX)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージをインストール
   - duckdb, defusedxml（RSS XML 安全解析のため）
   - 例（pip）:
     - pip install duckdb defusedxml

   ※ 本テンプレートでは requirements.txt は含まれていません。プロジェクトで追加の依存があれば適宜インストールしてください。

4. パッケージとしてインストール（任意）
   - プロジェクトルートに setup.cfg / pyproject.toml 等があれば:
     - pip install -e .

5. 環境変数（.env）を作成
   - プロジェクトルート（.git か pyproject.toml のあるディレクトリ）に `.env` または `.env.local` を置くと自動読み込みされます（不要なら KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 主なキー（Settings クラス参照）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
     - SLACK_BOT_TOKEN (必須)
     - SLACK_CHANNEL_ID (必須)
     - DUCKDB_PATH (任意、デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (任意、デフォルト: data/monitoring.db)
     - KABUSYS_ENV (development|paper_trading|live) デフォルト: development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) デフォルト: INFO

---

## 使い方（簡単なコード例）

以下はいくつかの主要操作の Python スニペット例です。DuckDB 接続は kabusys.data.schema のヘルパを使うと簡単です。

- DuckDB スキーマ初期化
  - from kabusys.data.schema import init_schema
  - conn = init_schema("data/kabusys.duckdb")

- 日次 ETL 実行（J-Quants から日足・財務・カレンダーを差分取得）
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn)  # target_date を省略すると今日

- 特徴量作成（features テーブルへ）
  - from kabusys.strategy import build_features
  - from datetime import date
  - n = build_features(conn, date(2024, 1, 31))

- シグナル生成（signals テーブルへ）
  - from kabusys.strategy import generate_signals
  - from datetime import date
  - total = generate_signals(conn, date(2024, 1, 31))

- ニュース収集ジョブ
  - from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  - results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})

- J-Quants から直接データを取得して保存
  - from kabusys.data import jquants_client as jq
  - records = jq.fetch_daily_quotes(date_from=..., date_to=...)
  - saved = jq.save_daily_quotes(conn, records)

Notes:
- 各 write 操作はほとんど冪等（ON CONFLICT / DO UPDATE / DO NOTHING）を意識して実装されています。重複実行や途中失敗からの再試行に耐えます。
- generate_signals/build_features は target_date 時点のデータのみを参照し、ルックアヘッドバイアスに配慮しています。

---

## ディレクトリ構成（概要）

（パッケージは src/kabusys 以下に配置）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数・設定読み込みロジック（.env 自動ロード、Settings クラス）
  - data/
    - __init__.py
    - schema.py
      - DuckDB スキーマ定義と init_schema / get_connection
    - jquants_client.py
      - J-Quants API クライアント（取得・保存ユーティリティ）
    - pipeline.py
      - ETL パイプライン（run_daily_etl 等）
    - stats.py
      - zscore_normalize などの統計ユーティリティ
    - news_collector.py
      - RSS フェッチ、前処理、raw_news 保存、銘柄抽出
    - calendar_management.py
      - market_calendar 管理、営業日判定ユーティリティ、calendar_update_job
    - audit.py
      - 監査ログスキーマ DDL
    - features.py
      - データ層の特徴量ユーティリティ再エクスポート
  - research/
    - __init__.py
    - factor_research.py
      - momentum / volatility / value ファクター計算
    - feature_exploration.py
      - 将来リターン、IC、統計サマリー
  - strategy/
    - __init__.py
      - build_features, generate_signals を公開
    - feature_engineering.py
      - 生ファクターを合成して features テーブルへ保存
    - signal_generator.py
      - features + ai_scores → final_score → signals 生成
  - execution/
    - (発注/実行関連モジュール群のためのプレースホルダ)
  - monitoring/
    - (監視・メトリクス系のモジュール用プレースホルダ)

---

## 注意事項 / トラブルシューティング

- 自動 .env ロードはデフォルトで有効です。テストなどで無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB ファイルの親ディレクトリが存在しない場合は init_schema() が自動で作成します。
- J-Quants API のレート制限（120 req/min）や認証トークンの取り扱いに注意してください。jquants_client はリトライ・レート制御・401 の自動リフレッシュを備えていますが、運用側でも適切な運用管理が必要です。
- news_collector は外部ネットワークアクセスを行います。SSRF 対策・XML パース例外等を実装していますが、フィードの内容によっては取得できない記事もあります。
- ログレベルは環境変数 `LOG_LEVEL`（デフォルト INFO）で制御します。
- KABUSYS_ENV により挙動（例えば実運用のフラグ）を切り替えられます（development / paper_trading / live）。

---

必要であれば README にサンプル .env.example、より詳細な API 仕様（各テーブルのカラム説明）、ETL 品質チェック仕様、運用手順（cron / scheduler 設定例）などの追記もできます。どの情報を追加したいか教えてください。