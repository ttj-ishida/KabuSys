# KabuSys

KabuSys は日本株向けの自動売買プラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、監査・スキーマ管理までを含むモジュール群を提供します。

---

## 主要な目的 / プロジェクト概要

- J-Quants API から株価・財務・カレンダー等のデータを取得し DuckDB に保存する ETL パイプライン
- 研究用に実装されたファクター計算（momentum / volatility / value 等）
- クロスセクション正規化（Z スコア）→ features テーブル化
- features と AI スコアを統合して売買シグナルを生成（BUY / SELL）
- RSS ベースのニュース収集と銘柄紐付け
- DuckDB ベースのスキーマ（Raw / Processed / Feature / Execution / Audit 層）
- 環境設定管理（.env 自動読み込みをサポート）

---

## 主な機能一覧

- data.jquants_client: J-Quants API クライアント（認証 / ページネーション / レートリミット / リトライ）
- data.pipeline: 差分取得ベースの ETL（prices, financials, market_calendar）および品質チェック
- data.schema: DuckDB のスキーマ定義と初期化（init_schema）
- data.news_collector: RSS 収集、前処理、raw_news 保存、銘柄抽出・紐付け
- data.calendar_management: 営業日判定・next/prev_trading_day 等のユーティリティ
- data.stats: zscore_normalize 等の統計ユーティリティ
- research.factor_research / feature_exploration: ファクター計算・リターン計算・IC/要約統計
- strategy.feature_engineering: 生ファクターを正規化・合成して features テーブルへ保存
- strategy.signal_generator: final_score 計算・BUY/SELL シグナル生成・signals テーブル保存
- config: 環境変数管理（.env 自動ロード、必須キーチェック）
- audit / execution / monitoring: 実行層 / 監査ログのスキーマ等（実装の一部を含む）

---

## 動作要件

- Python 3.10 以上（typing における | 記法等を使用）
- 必要なパッケージ（代表例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード等）
- J-Quants / Slack / kabu API の認証情報（環境変数）

実際の依存関係はプロジェクトの requirements.txt / pyproject.toml を参照してください。

---

## セットアップ手順

1. Python 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール
   - もし `requirements.txt` がある場合:
     - pip install -r requirements.txt
   - なければ最低限:
     - pip install duckdb defusedxml

3. レポジトリをインストール（開発モード）
   - pip install -e .

4. 環境変数を準備
   - プロジェクトルートに `.env` を作成（.env.local を優先して上書き可能）
   - 例（最低限必要なキー）:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - KABU_API_PASSWORD=your_kabu_password
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C...
     - DUCKDB_PATH=data/kabusys.duckdb
     - KABUSYS_ENV=development  # (development | paper_trading | live)
     - LOG_LEVEL=INFO
   - 注意: config モジュールはプロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を自動読み込みします。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. DuckDB スキーマの初期化
   - Python REPL またはスクリプトで:
     - from kabusys.data.schema import init_schema
     - conn = init_schema("data/kabusys.duckdb")

---

## 使い方（基本例）

以下は主要なワークフローのサンプルです。実運用ではジョブスケジューラ（cron / Airflow 等）から呼び出してください。

- DuckDB 初期化（1 回）
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL 実行（市場カレンダー → prices → financials）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量ビルド（features テーブルの作成）
  ```python
  from kabusys.strategy import build_features
  from datetime import date

  n = build_features(conn, target_date=date(2025, 1, 15))
  print(f"build_features: {n} 銘柄")
  ```

- シグナル生成（signals テーブルへ保存）
  ```python
  from kabusys.strategy import generate_signals
  from datetime import date

  total = generate_signals(conn, target_date=date(2025, 1, 15))
  print(f"generate_signals: {total} シグナル")
  ```

- ニュース収集と保存
  ```python
  from kabusys.data.news_collector import run_news_collection
  known_codes = {"7203", "6758", "9984"}  # 既知銘柄セット
  results = run_news_collection(conn, sources=None, known_codes=known_codes)
  print(results)  # {source_name: saved_count}
  ```

- J-Quants API を直接使う（トークン取得 / データ取得）
  ```python
  from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
  tok = get_id_token()  # settings.jquants_refresh_token を使用
  records = fetch_daily_quotes(id_token=tok, date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

---

## 環境設定（重要な env 変数）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知に使用（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化（1 をセット）

config.Settings クラスから各設定が取得できます（例: from kabusys.config import settings; settings.jquants_refresh_token）。

---

## 実運用上の注意点

- KABUSYS_ENV に応じて実行ポリシーを変えてください（paper_trading / live）。
- J-Quants の API レート制限（120 req/min）に対応するためクライアントでスロットリングを行います。
- ETL は差分更新を行い、既存レコードは idempotent に保存されます（ON CONFLICT DO UPDATE）。
- ニュース収集では SSRF や XML Bomb 対策（defusedxml、ホスト検査、受信サイズ制限）を実装しています。
- DuckDB のスキーマは init_schema により作成されます。運用開始前に必ず初期化してください。
- 本リポジトリ内の戦略ロジックは「研究/実運用の橋渡し」を念頭に実装されていますが、実際の資金運用前に十分なバックテストとリスク検証を行ってください。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下）

- __init__.py
- config.py  — 環境変数・設定管理
- data/
  - __init__.py
  - jquants_client.py        — J-Quants API クライアント（取得・保存ユーティリティ）
  - schema.py                — DuckDB スキーマ定義と init_schema
  - pipeline.py              — ETL パイプライン（run_daily_etl 等）
  - news_collector.py        — RSS 収集・raw_news 保存・銘柄抽出
  - calendar_management.py   — 営業日判定・カレンダー更新ジョブ
  - features.py              — データユーティリティ（zscore_normalize 再エクスポート）
  - stats.py                 — 統計ユーティリティ（z-score 正規化等）
  - audit.py                 — 監査ログ用スキーマ定義
  - (その他実装ファイル)
- research/
  - __init__.py
  - factor_research.py       — momentum/volatility/value 等のファクター計算
  - feature_exploration.py   — IC / 将来リターン / 統計サマリー
- strategy/
  - __init__.py
  - feature_engineering.py   — features テーブルの構築（Z スコア正規化等）
  - signal_generator.py      — final_score 計算と signals 生成
- execution/                  — 発注・実行層（空パッケージ / 実装拡張用）
- monitoring/                 — 監視用モジュール（拡張ポイント）

---

## 貢献 / 開発メモ

- テストや CI を追加する場合、config._find_project_root は .git / pyproject.toml を使ってルートを検出します。テスト時に .env 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- DuckDB のスキーマ変更は backward-compatible を意識してください（既存データの移行が必要な場合はマイグレーション手順を用意してください）。
- セキュリティ: .env に機密情報を含めるため、リポジトリにコミットしないでください。運用ではシークレットマネージャや環境変数管理を推奨します。

---

README の改善点や追記したい使い方（例: CLI スクリプト、cron / systemd ユニット例、Airflow DAG 例など）があれば教えてください。具体的な実行サンプルや運用手順を追記します。