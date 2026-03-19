# KabuSys

日本株向けの自動売買システム基盤（ライブラリ）です。  
市場データ取得、ETL、特徴量作成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなど、戦略開発〜運用に必要な基盤機能を提供します。

---

目次
- プロジェクト概要
- 機能一覧
- 前提 / 推奨環境
- セットアップ手順
- 必要な環境変数
- 使い方（簡単な例）
  - DB 初期化
  - 日次 ETL 実行
  - 特徴量作成（features）
  - シグナル生成
  - ニュース収集
  - カレンダー更新ジョブ
- 開発／テスト時のヒント
- ディレクトリ構成（主要ファイルの説明）

---

## プロジェクト概要

KabuSys は日本株自動売買のための内部ライブラリ群です。J-Quants API からのデータ取得、DuckDB を使ったデータ基盤、特徴量計算（research 層）、戦略シグナル生成（strategy 層）、ニュース収集（RSS）などを含みます。設計上、ルックアヘッドバイアスを避けるために「target_date 時点のデータのみを使用」する方針が貫かれています。

---

## 機能一覧

主な機能（モジュール）:

- 環境変数・設定管理
  - .env 自動読み込み（プロジェクトルートの .env / .env.local）
  - 必須設定の検証

- Data 層（kabusys.data）
  - J-Quants API クライアント（レート制限、リトライ、トークン自動リフレッシュ）
  - DuckDB スキーマ定義・初期化（init_schema）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - ニュース収集（RSS 取得、前処理、DB 保存、銘柄抽出）
  - マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
  - 統計ユーティリティ（Z スコア正規化等）

- Research 層（kabusys.research）
  - ファクター計算（momentum / volatility / value）
  - ファクター評価ツール（forward returns, IC, summary）

- Strategy 層（kabusys.strategy）
  - 特徴量エンジニアリング（build_features）
  - シグナル生成（generate_signals）：複数コンポーネントスコアの統合、Bear レジーム抑制、BUY/SELL の冪等書き込み

- Execution / Audit（スキーマ・監査テーブル）
  - シグナル / 注文 / 約定 / ポジション / 監査ログ用スキーマを提供

設計上、発注 API など外部ブローカーへの送信ロジックは execution 層に分離され、strategy や data 層は直接発注に依存しないようになっています。

---

## 前提 / 推奨環境

- Python 3.10 以上（PEP 604 の型記法などを使用）
- 必要パッケージ例:
  - duckdb
  - defusedxml
- インターネット接続（J-Quants API / RSS フィードへアクセスする場合）

（プロジェクトに pyproject.toml/requirements.txt がある場合はそちらを参照してください）

---

## セットアップ手順

1. リポジトリをクローン（例）
   git clone <repo-url>
   cd <repo>

2. 仮想環境作成（任意）
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate

3. pip 更新・依存パッケージのインストール
   pip install -U pip
   pip install duckdb defusedxml

   プロジェクトがパッケージ化されている場合:
   pip install -e .

4. 環境変数の設定
   - プロジェクトルートに .env を置くか、OS 環境変数で設定します（下記参照）。

---

## 必要な環境変数

以下はコード上で参照される主な環境変数です（必須は README に注記）。

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード（execution 層で使用）
- KABU_API_BASE_URL — kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用の Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境 (development / paper_trading / live). デフォルト development
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）。デフォルト INFO

.env 自動読み込みについて:
- パッケージ import 時にプロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を自動読み込みします。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用等）。

---

## 使い方（簡単な例）

以下は Python スクリプト / ワンライナーで実行できる基本的な操作例です。実行前に上記の必須環境変数を設定してください。

- DB の初期化（DuckDB スキーマ作成）
  python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"

- 日次 ETL の実行（市場カレンダー・株価・財務の差分取得と品質チェック）
  python -c "from kabusys.data.schema import init_schema; from kabusys.data.pipeline import run_daily_etl; c=init_schema('data/kabusys.duckdb'); res=run_daily_etl(c); print(res.to_dict())"

- 指定日の特徴量作成（build_features）
  python -c "import datetime; from kabusys.data.schema import init_schema; from kabusys.strategy import build_features; conn=init_schema('data/kabusys.duckdb'); build_features(conn, datetime.date(2024,1,1))"

- 指定日のシグナル生成（generate_signals）
  python -c "import datetime; from kabusys.data.schema import init_schema; from kabusys.strategy import generate_signals; conn=init_schema('data/kabusys.duckdb'); generate_signals(conn, datetime.date(2024,1,1))"

- ニュース収集ジョブ（RSS 収集 → raw_news / news_symbols 登録）
  python -c "from kabusys.data.schema import init_schema; from kabusys.data.news_collector import run_news_collection; conn=init_schema('data/kabusys.duckdb'); print(run_news_collection(conn))"

- カレンダー更新ジョブ（夜間バッチ想定）
  python -c "from kabusys.data.schema import init_schema; from kabusys.data.calendar_management import calendar_update_job; conn=init_schema('data/kabusys.duckdb'); print(calendar_update_job(conn))"

注意:
- 上記は最小限の例です。実運用ではログ設定、例外ハンドリング、ジョブスケジューラ（cron / Airflow）との統合、監視などが必要です。
- J-Quants API へアクセスするには有効なトークン（JQUANTS_REFRESH_TOKEN）が必須です。

---

## 開発 / テスト時のヒント

- 環境変数の自動ロードを無効化：
  KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを行いません（ユニットテスト等で便利）。

- メモリ DB を使ったテスト：
  DuckDB をインメモリで使用するには db_path に ":memory:" を渡して init_schema(":memory:") を使います（ただしファイルベースの永続性はありません）。

- ネットワーク API 呼び出しをモック：
  - news_collector._urlopen や data.jquants_client._request をモックすると外部 API にアクセスせずにテストできます。

---

## ディレクトリ構成（主要ファイルと説明）

（src/kabusys 以下）

- __init__.py
  - パッケージのバージョン等を定義。公開サブパッケージ: data, strategy, execution, monitoring

- config.py
  - 環境変数の読み込み・管理、Settings クラス（必須キーの検証、環境切替など）
  - .env / .env.local の自動ロード機能

- data/
  - jquants_client.py
    - J-Quants API クライアント（レート制御、再試行、トークン取得、保存ユーティリティ）
  - schema.py
    - DuckDB のスキーマ定義と init_schema(), get_connection()
  - pipeline.py
    - ETL パイプライン（run_daily_etl 等）
  - news_collector.py
    - RSS フィード取得 → 前処理 → raw_news / news_symbols 保存
  - calendar_management.py
    - market_calendar の運用・営業日判定ユーティリティ
  - audit.py
    - 発注/約定/監査ログ用スキーマ（signal_events / order_requests / executions 等）
  - features.py
    - data.stats の公開インターフェース（zscore_normalize の再エクスポート）
  - stats.py
    - zscore_normalize などの統計ユーティリティ

- research/
  - factor_research.py
    - momentum / volatility / value 等のファクター計算（prices_daily / raw_financials を参照）
  - feature_exploration.py
    - forward returns, IC（スピアマン）計算、統計サマリー等
  - __init__.py
    - 主要関数を再エクスポート

- strategy/
  - feature_engineering.py
    - build_features: research 側のファクターを正規化し features テーブルへ保存
  - signal_generator.py
    - generate_signals: features と ai_scores を統合して final_score を算出、signals テーブルへ書き込み
  - __init__.py
    - build_features / generate_signals を公開

- execution/
  - （現状はパッケージとして存在。発注・ブローカー連携ロジックはこの層に実装する方針）

- research/（上記）

（ファイル構成はリポジトリの実際のツリーに従ってください）

---

以上が README の概要です。追加で「運用手順」「例: Airflow の DAG テンプレート」「単体テストの書き方」など詳細なドキュメントを作成したい場合は、対象のトピックを指定してください。