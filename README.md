# KabuSys

日本株向けの自動売買プラットフォーム向けライブラリ（KabuSys）。  
データ取得・ETL、特徴量計算、シグナル生成、ニュース収集、DuckDBベースのスキーマ・監査ロジックを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の役割を担うモジュール群を含む Python パッケージです。

- J-Quants API からの市場データ・財務データ・カレンダー取得（rate limit・リトライ・トークン自動更新対応）
- DuckDB を用いたデータスキーマ、ETL（差分更新・バックフィル）パイプライン
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）
- クロスセクション正規化（Zスコア）
- 戦略の特徴量作成（features テーブルへの upsert）
- シグナル生成（BUY/SELL 条件、Bear レジーム抑制、エグジット判定）
- ニュース（RSS）収集と銘柄紐付け（SSRF対策・XML安全パーサー採用）
- 監査ログ（signal→order→execution のトレース）と実行レイヤ用テーブル群
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）

設計方針として、ルックアヘッドバイアス回避、冪等性（ON CONFLICT を利用した保存）、外部 API へのアクセス制御（本番資金口座や発注 API へは直接依存しない）を重視しています。

---

## 主な機能一覧

- data/jquants_client: J-Quants API クライアント（ページネーション・レート制御・リトライ・トークン自動更新）
- data/schema: DuckDB のスキーマ定義と初期化（Raw/Processed/Feature/Execution 層）
- data/pipeline: 日次 ETL（差分取得・保存・品質チェック）
- data/news_collector: RSS 収集・前処理・DB 保存・銘柄抽出
- data/calendar_management: JPX カレンダー更新・営業日ユーティリティ
- research/*: ファクター計算・ファクター探索（IC, forward returns, summary）
- strategy/feature_engineering: features テーブルの構築（正規化・ユニバースフィルタ）
- strategy/signal_generator: features と ai_scores を統合してシグナル生成
- data/stats: zscore_normalize 等の統計ユーティリティ
- config: .env ファイル / 環境変数管理（自動ロード機能）

---

## 前提・依存

最小限の依存（コード内参照）:

- Python 3.10+（型アノテーションの union 等を使用）
- duckdb
- defusedxml

実行する環境に合わせて追加パッケージが必要になる可能性があります。requirements.txt がある場合はそれに従ってください。

---

## セットアップ手順

1. リポジトリをクローン（ローカル開発）
   - pip で公開されている場合は pip install で取得できますが、開発中はソースを編集できるように editable インストールを推奨します。

   例（ソースから開発インストール）:
   ```
   git clone <repo-url>
   cd <repo>
   pip install -e .
   ```

2. 必要パッケージをインストール
   ```
   pip install duckdb defusedxml
   ```

3. 環境変数設定
   - プロジェクトルートの `.env` / `.env.local` を用意します（config モジュールが自動で読み込みます）。
   - 必須の環境変数（Settings クラス参照）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - オプション / デフォルト:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG / INFO / ...（デフォルト INFO）
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（デフォルト）
   - 自動ロードを抑止したい場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

4. DuckDB スキーマ初期化
   - データベースファイルを配置したいパス（デフォルト: data/kabusys.duckdb）でスキーマを作成します。

   Python 例:
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")
   ```

   この関数は親ディレクトリを自動作成し、全テーブル・インデックスを作成します（冪等）。

---

## 使い方（主要ユースケース例）

以下は代表的な操作のサンプルコードです。

- 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）
  ```python
  from datetime import date
  from kabusys.data import schema, pipeline

  conn = schema.init_schema("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- JPX カレンダー夜間更新ジョブ
  ```python
  from kabusys.data import calendar_management, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  saved = calendar_management.calendar_update_job(conn)
  print("saved:", saved)
  ```

- ニュース収集（RSS）と銘柄紐付け
  ```python
  from kabusys.data import news_collector, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  # known_codes は既知の銘柄コード集合（例: 全上場銘柄の4桁コード）
  results = news_collector.run_news_collection(conn, known_codes={"7203","6758"})
  print(results)
  ```

- 特徴量構築（features テーブルの作成）
  ```python
  from datetime import date
  import duckdb
  from kabusys.strategy import build_features
  from kabusys.data import schema

  conn = schema.get_connection("data/kabusys.duckdb")
  n = build_features(conn, target_date=date(2024, 1, 10))
  print("features upserted:", n)
  ```

- シグナル生成（signals テーブルへ保存）
  ```python
  from datetime import date
  from kabusys.strategy import generate_signals
  from kabusys.data import schema

  conn = schema.get_connection("data/kabusys.duckdb")
  count = generate_signals(conn, target_date=date(2024, 1, 10))
  print("signals generated:", count)
  ```

- J-Quants から日足を直接取得して保存（低レベル）
  ```python
  from kabusys.data import jquants_client as jq
  from kabusys.data import schema
  conn = schema.get_connection("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,10))
  saved = jq.save_daily_quotes(conn, records)
  ```

---

## 設定（環境変数 / .env）

主な環境変数（Settings参照）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API のパスワード（execution 層で利用）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — 通知用 Slack Bot Token
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV — "development", "paper_trading", "live" のいずれか
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化する場合に 1 を設定

注意: config モジュールはプロジェクトルート（.git または pyproject.toml の親ディレクトリ）を探して `.env` / `.env.local` を自動読み込みします。テスト時に自動ロードを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

## ロギング / 実行モード

- KABUSYS_ENV により動作モードを切り替えます（development / paper_trading / live）。live ではより厳格なチェックや安全機構を有効にするコード・分岐が期待されます。
- LOG_LEVEL でログの詳細度を設定します（デフォルト INFO）。

---

## ディレクトリ構成

主要ファイル／ディレクトリの概観（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント & 保存ロジック
    - news_collector.py             — RSS 収集・保存・銘柄抽出
    - schema.py                     — DuckDB スキーマ定義・初期化
    - stats.py                      — 統計ユーティリティ（zscore_normalize）
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py        — カレンダー更新・営業日ユーティリティ
    - features.py                   — features インターフェース（再エクスポート）
    - audit.py                      — 監査ログ用スキーマ
    - (その他: quality.py 等は想定)
  - research/
    - __init__.py
    - factor_research.py            — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py        — forward returns, IC, summary, rank
  - strategy/
    - __init__.py
    - feature_engineering.py        — features を作る処理
    - signal_generator.py           — signals を生成
  - execution/                      — 発注実装（パッケージ化済み）
  - monitoring/                     — 監視・Slack 通知等（パッケージ化済み）
  - その他モジュール...

README の先頭にある __version__ は 0.1.0 です。

---

## 開発 / テストのヒント

- DuckDB をメモリで使うとテストが高速になります:
  ```python
  conn = schema.init_schema(":memory:")
  ```
- config モジュールはプロジェクトルート探索を行うため、テストから環境を完全に制御したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD をセットしてから必要な環境変数を os.environ に注入してください。
- 外部ネットワークアクセスを伴う関数（fetch_rss, fetch_daily_quotes 等）はネットワークをモックして単体テストを行うことを推奨します。

---

## コントリビューション

- バグ修正、改善提案、ドキュメント修正は歓迎します。
- プルリクエスト作成時は既存テスト（ある場合）を通すこと、API 互換を保つよう注意してください。

---

## ライセンス / 注意事項

- 本リポジトリに含まれる設計ドキュメント（DataPlatform.md, StrategyModel.md 等）に基づく実装例が含まれます。実運用で使う場合は、発注ロジック・リスク管理・監査要件を必ず内部で検証・承認してください。
- 金融取引に関わるコードは重大な資金リスクを伴います。実取引での使用は自己責任で行ってください。

---

もし README に追加したい具体的なコマンド例や、CI / デプロイ手順、あるいは .env.example のテンプレートを用意してほしい場合は教えてください。