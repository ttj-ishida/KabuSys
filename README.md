# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ。  
データ収集（J-Quants）、ETL、特徴量作成、シグナル生成、ニュース収集、カレンダー管理、監査ログなどを一貫して提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株自動売買システム向けの内部ライブラリ群です。  
主な目的は次の通りです。

- J-Quants API からの株価・財務・カレンダー収集（レート制御・リトライ・トークン自動更新）
- DuckDB を用いたデータ保管（Raw / Processed / Feature / Execution レイヤ）
- 研究向けファクター計算（モメンタム、ボラティリティ、バリュー等）
- 特徴量正規化・合成（戦略入力用 features テーブル）
- シグナル生成ロジック（final_score に基づく BUY / SELL 判定）
- RSS を使ったニュース収集と記事→銘柄紐付け
- JPX カレンダー管理（営業日判定、先読み更新）
- ETL パイプライン（差分更新・バックフィル・品質チェック）
- 監査ログ（signal → order → execution のトレーサビリティ）

設計方針として「ルックアヘッドバイアス防止」「冪等性」「外部依存を最小化」などを重視しています。

---

## 機能一覧（主要モジュール）

- kabusys.config
  - 環境変数/設定の読み込み（.env/.env.local 自動ロード、必須キーチェック）
- kabusys.data
  - jquants_client: J-Quants API クライアント（レートリミット・リトライ・トークン管理）
  - schema: DuckDB スキーマ定義・初期化
  - pipeline: 日次 ETL（prices / financials / calendar）およびユーティリティ
  - news_collector: RSS 収集、前処理、DB 保存、銘柄抽出
  - calendar_management: 営業日判定、カレンダー更新ジョブ
  - stats / features: 統計・正規化ユーティリティ
  - audit: 監査ログテーブル定義（signal / order_request / executions）
- kabusys.research
  - factor_research: モメンタム・ボラティリティ・バリュー計算
  - feature_exploration: 将来リターン計算、IC、統計サマリー
- kabusys.strategy
  - feature_engineering.build_features: ファクター統合・Zスコア正規化・features テーブルへの保存
  - signal_generator.generate_signals: final_score 計算、BUY/SELL シグナル作成、signals テーブル保存
- kabusys.execution / monitoring
  - （実装箇所はライブラリ構成に準備）

各モジュールは DuckDB 接続を受け取り、システム外（ブローカ API 等）への副作用を持たない設計が基本です。

---

## セットアップ手順

前提:
- Python 3.9+（コードは型ヒントに Python 3.10+ 構文を使う個所があるため、3.10 推奨）
- DuckDB（Python パッケージとして duckdb を使用）
- インターネットアクセス（J-Quants / RSS 取得）

1. リポジトリをクローンして作業ディレクトリへ
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール  
   必要な最低依存（例）:
   ```bash
   pip install duckdb defusedxml
   ```
   ※ 実プロジェクトでは requirements.txt / pyproject.toml を用意している想定です。追加の依存があればそちらを参照してください。

4. 環境変数設定  
   プロジェクトルート（.git または pyproject.toml がある場所）に `.env`（および必要に応じ `.env.local`）を用意します。主要な環境変数:

   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
   - KABU_API_BASE_URL (任意) — デフォルト "http://localhost:18080/kabusapi"
   - SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot Token
   - SLACK_CHANNEL_ID (必須) — Slack 送信先チャンネル ID
   - DUCKDB_PATH (任意) — デフォルト "data/kabusys.duckdb"
   - SQLITE_PATH (任意) — デフォルト "data/monitoring.db"
   - KABUSYS_ENV (任意) — "development" | "paper_trading" | "live"（デフォルト "development"）
   - LOG_LEVEL (任意) — "DEBUG","INFO",...（デフォルト "INFO"）

   自動読み込みはデフォルトで有効です。自動読み込みを無効にする場合は環境変数を設定:
   ```bash
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

5. スキーマ初期化（DuckDB ファイルを準備）
   - デフォルトの DB ファイルは `data/kabusys.duckdb`（settings.duckdb_path）
   - 初回はスキーマを作成する必要があります（例は次の「使い方」参照）

---

## 使い方（簡単な例）

以下は最小限の利用例です。各例は Python スクリプトまたは REPL から実行できます。

- スキーマ初期化（DuckDB）
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL の実行（J-Quants から差分取得して保存）
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量の構築（features テーブルの作成）
  ```python
  from kabusys.data.schema import get_connection
  from kabusys.strategy import build_features
  from datetime import date

  conn = get_connection("data/kabusys.duckdb")
  count = build_features(conn, target_date=date.today())
  print(f"features updated for {count} codes")
  ```

- シグナル生成
  ```python
  from kabusys.data.schema import get_connection
  from kabusys.strategy import generate_signals
  from datetime import date

  conn = get_connection("data/kabusys.duckdb")
  total_signals = generate_signals(conn, target_date=date.today())
  print(f"signals written: {total_signals}")
  ```

- RSS ニュース収集ジョブ（既知銘柄セットを渡して銘柄紐付け）
  ```python
  from kabusys.data.schema import get_connection
  from kabusys.data.news_collector import run_news_collection

  conn = get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- カレンダーの夜間更新ジョブ
  ```python
  from kabusys.data.schema import get_connection
  from kabusys.data.calendar_management import calendar_update_job

  conn = get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"market_calendar saved: {saved}")
  ```

注意点:
- settings に定義された必須環境変数が未設定だと ValueError が発生します。
- jquants_client のリクエストはレート制御とリトライが組み込まれています。
- 各 DB 保存関数は冪等（ON CONFLICT）で設計されています。

---

## ディレクトリ構成

主要なファイル・モジュール構成（src 直下）:

- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント (fetch/save)
    - news_collector.py              — RSS 収集・保存・銘柄抽出
    - schema.py                      — DuckDB スキーマ / init_schema
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - stats.py                       — 統計ユーティリティ（zscore_normalize）
    - features.py                    — features の再エクスポート
    - calendar_management.py         — JPX カレンダー管理
    - audit.py                       — 監査ログテーブル定義
    - quality.py?                    — 品質チェック（pipeline から参照想定）
  - research/
    - __init__.py
    - factor_research.py             — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py         — 将来リターン / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py         — ファクター合成・正規化・features 保存
    - signal_generator.py            — final_score 計算・signals 保存
  - execution/ (エントリ用空モジュール／発注関連)
  - monitoring/ (監視・メトリクス用モジュール)

（実際のリポジトリにはさらに補助モジュール・テスト等が含まれる可能性があります）

---

## 開発・拡張メモ

- 環境変数の自動ロードは .git / pyproject.toml を基準にプロジェクトルートを検出して行います。テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効化できます。
- DuckDB スキーマは init_schema() で一括作成されます。既存テーブルがある場合は安全にスキップされます（冪等）。
- research と strategy 層は発注ロジックに依存しないため、ローカルでの研究やバックテストに利用できます。
- news_collector は SSRF・XML Bomb・巨大レスポンス対策を実装していますが、信頼できる実行環境で動かしてください。

---

## トラブルシューティング

- 環境変数未設定による起動エラー: settings のプロパティ（例 JQUANTS_REFRESH_TOKEN）取得時に ValueError が投げられます。.env.example を参考に .env を作成してください。
- DuckDB に接続できない／書き込みできない: DUCKDB_PATH の親ディレクトリが存在しないときは init_schema が自動作成しますが、権限やパス名に注意してください。
- J-Quants API エラー: jquants_client は 401 時のトークン自動更新や 429/5xx のリトライを行います。多量のリクエストを短時間に送らないでください（120 req/min 制限）。

---

## ライセンス / コントリビューション

この README はコードベースからの自動生成ドキュメントの例です。実プロジェクトに適用する場合は LICENSE・CONTRIBUTING ガイドを追加してください。

---

README のサンプルはここまでです。必要であれば README に以下を追加します：
- .env.example の具体例
- requirements.txt / pyproject.toml のサンプル
- よくある質問（FAQ）
- 実運用時の監視・ロギング設定例

どのセクションを拡張しますか？