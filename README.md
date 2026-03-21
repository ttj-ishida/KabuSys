# KabuSys

KabuSys は日本株の自動売買プラットフォーム向けのライブラリ群です。  
J-Quants からの市場データ取得、DuckDB によるデータ永続化、ファクター計算（研究モジュール）、特徴量の正規化、シグナル生成、ニュース収集、ETL パイプライン、マーケットカレンダー管理、監査ログなどの主要機能を含みます。

主な目的は、ルックアヘッドバイアスを防ぎつつ堅牢にデータを収集・加工し、戦略レイヤーでのシグナル生成と発注レイヤーへの橋渡しを行うことです。

---

## 機能一覧

- データ取得・保存
  - J-Quants API クライアント（株価日足・財務情報・市場カレンダー）
  - 差分 ETL（日次パイプライン）とバックフィル対応
  - raw / processed / feature / execution 層を持つ DuckDB スキーマ定義と初期化

- データ前処理・統計
  - クロスセクション Z スコア正規化（data.stats）
  - 将来リターン・IC（情報係数）計算などの研究向けユーティリティ（research）

- ファクター & 特徴量
  - Momentum / Volatility / Value 等のファクター計算（research.factor_research）
  - 生ファクターの統合・ユニバースフィルタ・Z スコア正規化を行い `features` テーブルへ保存（strategy.feature_engineering）

- シグナル生成
  - 正規化済み特徴量と AI スコアを統合して final_score を算出、BUY / SELL シグナルを `signals` テーブルへ書込（strategy.signal_generator）
  - Bear レジーム判定やエグジット（ストップロス等）判定を実装

- ニュース収集
  - RSS から記事収集、前処理、記事ID生成（URL正規化＋SHA-256）、DuckDB へ冪等保存（news_collector）
  - 銘柄コード抽出と記事との紐付け

- マーケットカレンダー管理
  - JPX カレンダーの差分取得・保存、営業日判定・翌営業日/前営業日取得等のユーティリティ

- 監査ログ
  - signal → order_request → executions までのトレーサビリティを確保する監査テーブル定義（audit）

---

## 要件

- Python 3.10 以上（typing における `X | Y` 構文を使用）
- 必要な主要ライブラリ（例）
  - duckdb
  - defusedxml
- 標準ライブラリの urllib, datetime 等を使用

実際のプロジェクトでは requirements.txt を用意して依存管理してください。最低限のインストール例:

```bash
python -m pip install "duckdb" "defusedxml"
```

---

## セットアップ手順

1. リポジトリをクローン（例）

   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. Python 仮想環境を作成・有効化（推奨）

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate.bat  # Windows
   ```

3. 必要ライブラリをインストール

   ```bash
   pip install duckdb defusedxml
   ```

   ※プロジェクトに requirements.txt や pyproject.toml があればそちらを使用してください。

4. 環境変数設定

   - プロジェクトルートの `.env` または `.env.local` に環境変数を置くと自動で読み込まれます（自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD      : kabuステーション API のパスワード（必要な場合）
     - SLACK_BOT_TOKEN        : Slack 通知を使用する場合の Bot トークン
     - SLACK_CHANNEL_ID      : Slack 通知先チャンネル ID
   - その他:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト "development"
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
     - DUCKDB_PATH, SQLITE_PATH（デフォルト: data/kabusys.duckdb, data/monitoring.db）

   例 `.env`（実運用では秘密情報を公開しないでください）:

   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=xxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマの初期化

   Python REPL やスクリプトで以下を実行して DB を初期化します:

   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)
   conn.close()
   ```

   - db_path に ":memory:" を指定するとインメモリ DB を使用できます。

---

## 使い方（代表的な API）

以下は簡単な使用例です。プロダクションではスクリプトやジョブとして組み込んでください。

- 日次 ETL の実行（株価・財務・カレンダーを差分取得）

  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.schema import get_connection, init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema(settings.duckdb_path)  # 初回のみ
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  conn.close()
  ```

- 特徴量の構築（features テーブルへ保存）

  ```python
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.schema import get_connection
  from kabusys.strategy import build_features

  conn = get_connection(settings.duckdb_path)
  count = build_features(conn, target_date=date.today())
  print(f"built features: {count}")
  conn.close()
  ```

- シグナル生成

  ```python
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.schema import get_connection
  from kabusys.strategy import generate_signals

  conn = get_connection(settings.duckdb_path)
  written = generate_signals(conn, target_date=date.today())
  print(f"signals written: {written}")
  conn.close()
  ```

- ニュース収集ジョブ（RSS → raw_news）と銘柄抽出

  ```python
  from kabusys.data.schema import get_connection
  from kabusys.data import news_collector as nc

  conn = get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット
  results = nc.run_news_collection(conn, known_codes=known_codes)
  print(results)
  conn.close()
  ```

- J-Quants からのデータ取得例（直接呼び出し）

  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes
  quotes = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須であれば) — kabu API パスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID — Slack 通知用
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 sqlite DB（デフォルト data/monitoring.db）
- KABUSYS_ENV — environment: development | paper_trading | live（デフォルト development）
- LOG_LEVEL — ログレベル（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化する場合に 1 を設定

設定は .env / .env.local / OS 環境変数の順で読み込まれます (.env.local が .env を上書き)。

---

## ディレクトリ構成

以下は主要なファイル・モジュールの一覧（リポジトリの `src/kabusys/` 配下を抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py                — J-Quants API クライアント（取得・保存）
    - news_collector.py                — RSS ニュース収集・保存
    - schema.py                        — DuckDB スキーマ定義・初期化
    - stats.py                         — 統計ユーティリティ（zscore_normalize 等）
    - pipeline.py                      — ETL パイプライン（run_daily_etl 等）
    - features.py                      — data.stats の再エクスポート
    - calendar_management.py           — マーケットカレンダー管理
    - audit.py                         — 監査ログテーブル定義
    - (その他: quality 等の補助モジュール想定)
  - research/
    - __init__.py
    - factor_research.py               — ファクター計算（momentum/value/volatility）
    - feature_exploration.py           — IC / 将来リターン / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py           — 特徴量構築（build_features）
    - signal_generator.py              — シグナル生成（generate_signals）
  - execution/                         — 発注 / 実行関連（空の __init__ 等）
  - monitoring/                        — 監視、外部DB連携など（実装想定）

（上記は現状の主要ファイル一覧で、将来的に追加モジュールや CLI、ジョブスケジューラ等を含める想定です）

---

## 注意事項 / 設計上のポイント

- ルックアヘッドバイアス防止: strategy / research モジュールは target_date 時点で利用可能なデータのみを参照する設計です。
- 冪等性: DuckDB への保存処理は ON CONFLICT を用いた冪等実装が施されています。
- ETL の耐障害性: 各ステップは独立してエラーハンドリングされ、1つの失敗で全体が止まらないよう設計されています（結果オブジェクトにエラーと品質問題を収集）。
- セキュリティ: news_collector は SSRF 対策、XML の安全パーサー（defusedxml）を利用しています。
- API レート制御: J-Quants クライアントは固定間隔スロットリングとリトライ・トークン自動リフレッシュを行います。

---

## 貢献 / 開発

- コードスタイル、型付け、単体テストの追加を歓迎します。
- ローカル開発では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して .env の自動読み込みを抑止できます（テストで独自環境を設定したい場合に有用）。

---

ご不明点があれば、どの機能（ETL、feature 計算、signal 生成、news collection、schema 初期化など）について詳しくドキュメント化・例示すべきか教えてください。必要に応じてサンプルスクリプトや CI/CD の設定例も追加できます。