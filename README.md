# KabuSys — 日本株自動売買基盤

KabuSys は日本株向けのデータプラットフォームと策略層を備えた自動売買基盤のサンプル実装です。  
DuckDB をデータレイクとして利用し、J-Quants から市場データ・財務データ・カレンダーを取得して ETL、特徴量作成、シグナル生成、ニュース収集、監査ログなどを行うモジュール群を提供します。

主な目的：
- データ取得と品質管理（差分ETL・市場カレンダー管理）
- 研究→本番へ移行可能な特徴量／シグナル生成ロジック
- 冪等な DB 操作、API レート制御、トレーサビリティ設計

---

## 機能一覧

- データ取得（J-Quants API）
  - 日足（OHLCV）、財務データ、マーケットカレンダーの取得（ページネーション対応）
  - レートリミットとリトライ（401 自動リフレッシュ含む）
- ETL パイプライン
  - 差分取得（最終取得日からの差分）／バックフィル
  - 品質チェック（欠損・スパイク等の検出）
  - 日次バッチ（run_daily_etl）
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層を含むスキーマ初期化（init_schema）
- 研究・特徴量関連
  - momentum / volatility / value 等のファクター計算（research）
  - クロスセクション Z スコア正規化ユーティリティ
  - ファクター解析（forward returns / IC / summary）
- 特徴量生成・シグナル生成
  - build_features: ファクター統合→features テーブルへ保存
  - generate_signals: features + ai_scores から final_score を計算し signals テーブルへ保存
- ニュース収集（RSS）
  - RSS の安全な取得（SSRF 対策・gzip サイズ制限）
  - raw_news / news_symbols への冪等保存、銘柄コード抽出
- マーケットカレンダー管理
  - 営業日判定、next/prev_trading_day、calendar_update_job など
- 監査ログ（audit）
  - シグナル→発注→約定のトレース用テーブル設計

---

## 要求環境（推奨）

- Python >= 3.10（型ヒントで | 型を使用しているため）
- DuckDB（Python パッケージ）
- defusedxml（RSS パーシングの安全化）
- 標準ライブラリ（urllib 等）

推奨パッケージインストール例:
- duckdb
- defusedxml

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境を作成・有効化（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb defusedxml
   - （パッケージ化されている場合）pip install -e .
4. 環境変数の用意
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須の環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabu ステーション API パスワード（必須）
     - SLACK_BOT_TOKEN — Slack Bot トークン（必須）
     - SLACK_CHANNEL_ID — Slack チャネル ID（必須）
     - DUCKDB_PATH — DuckDB ファイルパス（省略時: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 sqlite パス（省略時: data/monitoring.db）
     - KABUSYS_ENV — 環境 (development / paper_trading / live)（省略時: development）
     - LOG_LEVEL — ログレベル (DEBUG/INFO/WARNING/ERROR/CRITICAL)（省略時: INFO）
   - 例 (.env):
     - JQUANTS_REFRESH_TOKEN=your_refresh_token
     - KABU_API_PASSWORD=your_kabu_password
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C01234567
     - DUCKDB_PATH=data/kabusys.duckdb
5. データベースの初期化
   - Python REPL やスクリプトで下記を実行してスキーマを作成します（parent ディレクトリがなければ自動作成）。
     - from kabusys.data import schema
     - conn = schema.init_schema(settings.duckdb_path)

---

## 使い方（主要な API と例）

下記は典型的なバッチ処理の例です。各例は duckdb 接続（kabusys.data.schema.init_schema が返すもの）を前提とします。

- スキーマ初期化
  - from kabusys.data import schema
  - conn = schema.init_schema("data/kabusys.duckdb")

- 日次 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn)  # target_date を指定することも可能
  - print(result.to_dict())

- 特徴量のビルド（features テーブル更新）
  - from kabusys.strategy import build_features
  - from datetime import date
  - count = build_features(conn, target_date=date(2025, 1, 6))
  - print(f"features upserted: {count}")

- シグナル生成（signals テーブル更新）
  - from kabusys.strategy import generate_signals
  - from datetime import date
  - total = generate_signals(conn, target_date=date(2025, 1, 6))
  - print(f"signals written: {total}")

- ニュース収集ジョブ（RSS 収集 → raw_news へ保存 → 銘柄紐付け）
  - from kabusys.data.news_collector import run_news_collection
  - results = run_news_collection(conn, known_codes={"7203", "6758"})
  - print(results)

- カレンダー夜間更新ジョブ
  - from kabusys.data.calendar_management import calendar_update_job
  - saved = calendar_update_job(conn)
  - print(f"calendar saved: {saved}")

- 補助ユーティリティ
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days（calendar_management）
  - calc_forward_returns / calc_ic / factor_summary（research.feature_exploration）
  - jquants_client.fetch_daily_quotes / save_daily_quotes（データ取得・保存用）

注意:
- 各 ETL 関数は冪等性を考慮して設計されています（ON CONFLICT や日付単位の置換を利用）。
- シグナル生成は戦略モデル（StrategyModel.md 相当の設計）に沿っており、Bear レジームやストップロス等のルールを含みます。
- ニュース取得は SSRF・XML Bomb 等への対策を実装しています（defusedxml、ホスト検査、受信サイズ上限など）。

---

## 主要モジュール概要

- kabusys.config — 環境変数管理（.env 自動ロード・必須キー検査）
- kabusys.data
  - jquants_client — J-Quants API クライアント（レート制御・リトライ・保存関数）
  - schema — DuckDB スキーマ定義と init_schema
  - pipeline — ETL パイプライン（run_daily_etl 等）
  - news_collector — RSS 収集と保存
  - calendar_management — マーケットカレンダー操作
  - stats / features — 統計ユーティリティ、Z スコア正規化
- kabusys.research — ファクター計算 / 特徴量探索ユーティリティ
- kabusys.strategy — build_features, generate_signals
- kabusys.execution — 発注／約定／ポジション管理用（パッケージ用意）
- kabusys.monitoring — 監視・アラート用（パッケージ用意）
- kabusys.audit — 監査ログ（signal_events / order_requests / executions）

---

## ディレクトリ構成（抜粋）

src/
  kabusys/
    __init__.py
    config.py
    data/
      __init__.py
      jquants_client.py
      schema.py
      pipeline.py
      news_collector.py
      calendar_management.py
      features.py
      stats.py
      audit.py
      ... (その他 data 関連ファイル)
    research/
      __init__.py
      factor_research.py
      feature_exploration.py
    strategy/
      __init__.py
      feature_engineering.py
      signal_generator.py
    execution/
      __init__.py
      ... (execution 層の実装)
    monitoring/
      ... (監視・Slack 通知等)
    ... その他モジュール

（README は実装ファイルの抜粋に基づいています）

---

## 開発・テスト

- 自動 .env 読み込みはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）
- 単体テスト・統合テストは開発環境で DuckDB の :memory: を用いると高速に実行できます
  - schema.init_schema(":memory:") を使ってテスト用 DB を初期化してください
- 外部 API 呼び出しは jquants_client._request/_urlopen 等をモックしてテストすることを推奨します

---

## 運用上の注意

- J-Quants の API レート制限を厳守（実装済みだが、運用負荷によっては追加制御が必要）
- 機密情報（トークン等）は .env.local 等で管理し、リポジトリに含めないでください
- production 運用時は KABUSYS_ENV を `live` に設定し、安全なログ管理と監査を行ってください
- 発注・実際の売買に移す際は execution 層とブローカーインテグレーションのテストと監査を厳密に行ってください（バックテスト・ペーパートレードの段階を推奨）

---

必要であれば README に含めるサンプル .env.example、より詳細な API 使用例、運用手順（デプロイ／Cron ジョブ設定／監視）なども作成します。どの情報を追加したいか教えてください。