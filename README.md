# KabuSys

KabuSys は日本株向けの自動売買プラットフォームのリファレンス実装です。  
J-Quants 等から市場データを取得して DuckDB に蓄積し、リサーチ／特徴量生成／シグナル生成／発注監査までのワークフローを提供します。  
設計方針として「ルックアヘッドバイアス回避」「冪等性」「オフラインでの研究再現性」を重視しています。

主な用途例:
- 市場データの差分ETL（J-Quants API）
- ファクター（モメンタム／バリュー／ボラティリティ等）の計算
- 特徴量正規化・合成（features テーブルの構築）
- 最終スコアに基づく売買シグナル生成（signals テーブル）
- RSS によるニュース収集・銘柄紐付け
- DuckDB スキーマ管理と監査ログ

---

## 機能一覧

- 環境設定
  - .env / OS 環境変数から設定を読み込む（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化可）
  - 必須環境変数を明示（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN など）
- データ層（kabusys.data）
  - J-Quants API クライアント（認証リフレッシュ、レート制限、リトライ、ページネーション対応）
  - DuckDB スキーマ定義・初期化（init_schema）
  - ETL パイプライン（差分取得、バックフィル、品質チェック呼び出し）
  - ニュース収集（RSS -> raw_news 保存、銘柄抽出）
  - マーケットカレンダー管理（営業日判定、次/前営業日、カレンダー更新ジョブ）
  - 汎用統計ユーティリティ（Zスコア正規化）
- リサーチ（kabusys.research）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン、IC（スピアマン）、ファクターサマリ等の解析ユーティリティ
- 戦略（kabusys.strategy）
  - 特徴量エンジニアリング（build_features: 生ファクターの正規化・フィルタ・UPSERT）
  - シグナル生成（generate_signals: final_score 計算、Bear フィルタ、BUY/SELL 生成・保存）
- ニュース収集セキュリティ
  - SSRF 対策、gzip サイズ制限、XMLパースの安全化（defusedxml）
- 監査（audit）
  - signal/events → order_requests → executions などの監査テーブル定義（トレーサビリティ）

注: execution 層（実際の証券会社 API 発注）はインターフェースを想定しており、実運用では証券会社側の安全対策・リスク管理が必須です。

---

## 必要条件・セットアップ

前提
- Python 3.10 以上（コード内で PEP 604 の | 型ヒント等を使用）
- DuckDB（Python パッケージ duckdb）
- defusedxml（RSS の安全パース用）
- ネットワークアクセス（J-Quants API 等）

推奨手順（UNIX 系の例）

1. リポジトリをクローン
   ```bash
   git clone <repository-url>
   cd <repository-dir>
   ```

2. 仮想環境を作成して有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   python -m pip install -U pip
   ```

3. 依存ライブラリをインストール（最低限）
   ```bash
   pip install duckdb defusedxml
   # 開発時は editable install する場合:
   pip install -e .
   ```

4. 環境変数を設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動的に読み込まれます（優先順位: OS 環境 > .env.local > .env）。
   - 自動読み込みを無効にする場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必須の環境変数（例）
     ```
     JQUANTS_REFRESH_TOKEN=xxx
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABU_API_PASSWORD=...
     # 任意: DB パスなど
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development   # (development|paper_trading|live)
     LOG_LEVEL=INFO
     ```

5. DuckDB スキーマの初期化（例）
   Python REPL またはスクリプトから:
   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)
   ```

---

## 使い方（主要ユースケースの例）

以下は最小限の操作例です。実運用ではログ・エラーハンドリングやバックアップ等を適宜追加してください。

- 日次 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）
  ```python
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量の構築（build_features）
  ```python
  from datetime import date
  from kabusys.data.schema import get_connection
  from kabusys.strategy import build_features

  conn = get_connection("data/kabusys.duckdb")
  count = build_features(conn, target_date=date.today())
  print(f"features upserted: {count}")
  ```

- シグナル生成（generate_signals）
  ```python
  from datetime import date
  from kabusys.data.schema import get_connection
  from kabusys.strategy import generate_signals

  conn = get_connection("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date.today())
  print(f"signals written: {total}")
  ```

- ニュース収集ジョブ（RSS 収集 → raw_news 保存 → 銘柄紐付け）
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コード集合
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: saved_count, ...}
  ```

- カレンダー更新（夜間バッチ）
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")
  ```

注意点:
- run_daily_etl / run_prices_etl などは id_token を引数で注入可能（テスト用）。デフォルトは settings.jquants_refresh_token を使用して自動的に ID トークンを取得します。
- production（live）環境での発注は execution 層の実装・外部ブローカー連携・リスク制御を必ず行ってください。

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（必須：発注連携時）
- KABU_API_BASE_URL: kabuステーションのベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用トークン（必須：通知機能を使う場合）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須：通知機能を使う場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動ロードを無効化

設定値は kabusys.config.settings 経由で参照できます（例: settings.jquants_refresh_token）。

---

## ディレクトリ構成

主要なファイル・ディレクトリの概要（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                -- 環境変数/設定管理
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント（取得/保存ユーティリティ）
    - schema.py              -- DuckDB スキーマ定義・init_schema / get_connection
    - pipeline.py            -- ETL パイプライン（run_daily_etl, run_prices_etl 等）
    - news_collector.py      -- RSS 収集と raw_news/news_symbols 保存
    - calendar_management.py -- カレンダー管理・営業日ユーティリティ
    - features.py            -- zscore_normalize の再エクスポート
    - stats.py               -- 統計ユーティリティ（Zスコア正規化）
    - audit.py               -- 監査ログ用テーブル DDL
    - (その他: quality, monitoring など想定)
  - research/
    - __init__.py
    - factor_research.py     -- モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py -- IC/forward returns/summary 等
  - strategy/
    - __init__.py
    - feature_engineering.py -- features テーブルの構築（build_features）
    - signal_generator.py    -- signals 生成（generate_signals）
  - execution/
    - __init__.py            -- 発注層（ブリッジ実装を想定）
  - monitoring/              -- 監視・アラート関連（モジュール想定）

（実際のリポジトリでは上記に加えてテストコード・ドキュメント・スクリプトが存在する可能性があります）

---

## 補足・設計上の注意

- 冪等性
  - ETL の保存処理は基本的に ON CONFLICT/UPSERT を用いて重複を排除する設計です。
- ルックアヘッドバイアス対策
  - 特徴量・シグナル計算は target_date 時点で利用可能なデータのみを使用するよう設計されています（fetched_at を記録）。
- 局所的なエラーハンドリング
  - ETL は各ステップを独立して実行し、1 ステップの失敗で全体を停止させない設計です。結果は ETLResult で集約されます。
- セキュリティ
  - RSS の処理は SSRF・XML Bomb・gzip 膨張に対する対策が組み込まれています。
  - J-Quants API ではレート制御とリトライ、401 時のトークン自動リフレッシュを実装しています。
- 本番運用
  - 実際の発注（execution 層）を行う場合は、リスク管理・二重化防止・監査ログ保存の実装と十分なテストを必須としてください。

---

必要であれば以下の追加ドキュメントを作成できます:
- API リファレンス（各モジュールの公開関数一覧）
- 運用手順書（デプロイ・夜間バッチ・監視設定）
- テストガイド（単体テスト・統合テストの実行方法）
- .env.example（サンプル環境変数ファイル）

ご希望の追加情報があれば教えてください。README のサンプル .env.example や具体的な運用スクリプトも作成できます。