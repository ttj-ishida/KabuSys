# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリ。  
DuckDB を使ったデータレイク構成、J-Quants API からのデータ取得、RSS ベースのニュース収集、特徴量計算（ファクター群）、ETL パイプライン、品質チェック、監査ログ等の機能群を備えます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のデータ取得・前処理・特徴量生成・監査・ETL を一貫して行うための内部ライブラリ群です。設計方針として以下を重視しています：

- DuckDB を中心としたローカルデータベースによるデータ保存（冪等性を考慮した INSERT/update）
- J-Quants API との堅牢な連携（レート制御、リトライ、トークンリフレッシュ）
- RSS ベースのニュース収集における安全対策（SSRF、XML 攻撃対策、応答サイズ制限）
- Research 層（ファクター計算 / IC 検証等）は本番発注系に一切アクセスしない
- 品質チェック（欠損・スパイク・重複・日付不整合）を明示的に検出・報告
- 監査ログ（signal → order → execution のトレーサビリティ）

---

## 主な機能一覧

- 環境/設定管理（kabusys.config）
  - .env/.env.local の自動読み込み（無効化可）
  - 必須環境変数のチェック、環境モード（development/paper_trading/live）判定
- データ取得（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務データ、JPX カレンダーの取得（ページネーション対応）
  - レートリミッタ、リトライ、トークン自動リフレッシュ実装
  - DuckDB への冪等保存ユーティリティ（save_*）
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、前処理、raw_news 保存、銘柄コード抽出と紐付け
  - SSRF / XML Bomb / gzip bomb 等の防御
- スキーマ初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化
- ETL パイプライン（kabusys.data.pipeline）
  - 日次差分 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）
  - バックフィル機能、ETL 結果の集約（ETLResult）
- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク（前日比閾値）、重複、日付不整合の検出
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等、監査用テーブルの初期化・管理
- 研究用モジュール（kabusys.research）
  - momentum / volatility / value 等のファクター計算（prices_daily / raw_financials のみ参照）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ
- 統計ユーティリティ（kabusys.data.stats）
  - Zスコア正規化（クロスセクション）

---

## セットアップ手順

1. Python（推奨 3.9+）を用意してください。

2. 必要なパッケージをインストールします。プロジェクトに pyproject.toml / requirements.txt が無い場合、最低限以下をインストールしてください：

   pip install duckdb defusedxml

   （他にログ処理や Slack 連携用ライブラリを追加することがありますが、現状コードベースで明示的依存しているのは上記です）

3. ソースを配置して editable install（任意）：

   pip install -e .

4. 環境変数を設定します。プロジェクトルートに `.env` または `.env.local` を作成することで自動読み込みされます（自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

   最低限設定が必要な変数（kabusys.config.Settings より）:

   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
   - SLACK_BOT_TOKEN: Slack 通知を使う場合の Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite path（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

   例 (.env):

   ```
   JQUANTS_REFRESH_TOKEN=xxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマを初期化します（Python REPL やスクリプトで実行）：

   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")
   ```

   監査用 DB を分離して運用する場合：

   ```python
   from kabusys.data import audit
   audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（代表的な例）

- 日次 ETL 実行（単純なスクリプト例）:

  ```python
  from datetime import date
  import logging
  from kabusys.data import schema, pipeline
  # ログ設定
  logging.basicConfig(level=logging.INFO)
  # DB 初期化（既に初期化済みなら既存ファイルを使う）
  conn = schema.init_schema("data/kabusys.duckdb")
  # 日次 ETL を実行（target_date を指定しなければ今日）
  result = pipeline.run_daily_etl(conn)
  print(result.to_dict())
  ```

- ファクター計算（Research）例:

  ```python
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

  conn = duckdb.connect("data/kabusys.duckdb")
  target = date(2024, 1, 31)
  mom = calc_momentum(conn, target)
  vol = calc_volatility(conn, target)
  val = calc_value(conn, target)
  fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
  # 例: mom の mom_1m と fwd の fwd_1d で IC を計算
  ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
  print("IC:", ic)
  ```

- ニュース収集と銘柄紐付け（run_news_collection は既存の銘柄リストを受け取れます）:

  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9432"}  # 事前に取得または管理している銘柄コードセット
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  ```

- Zスコア正規化ユーティリティ:

  ```python
  from kabusys.data.stats import zscore_normalize
  records = [{"code":"7203","mom":0.1},{"code":"6758","mom":0.2}]
  normalized = zscore_normalize(records, ["mom"])
  ```

---

## 開発・テスト時のコツ

- 自動で .env をロードする機能は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます（テスト時に環境依存を排除するのに便利）。
- J-Quants API 呼び出し部分はネットワーク依存・レート制限があるため、単体テストでは `kabusys.data.jquants_client._request` や `fetch_*` をモックすることを推奨します。
- news_collector 内の `_urlopen` を差し替えることでネットワークの挙動を制御できます（テスト用フックが意図的に用意されています）。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - pipeline.py
      - quality.py
      - calendar_management.py
      - audit.py
      - etl.py
      - stats.py
      - features.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

主要なモジュール説明：
- kabusys.config: 環境変数・設定管理
- kabusys.data: データ取得 / 保存 / ETL / 品質チェック / スキーマ定義
- kabusys.research: ファクター計算・研究用ユーティリティ
- kabusys.strategy / execution / monitoring: 戦略実行・発注・監視に関するプレースホルダ（拡張領域）

---

## 注意点 / 運用上の留意事項

- J-Quants の API レート制限（120 req/min）に従うため、`jquants_client` にレートリミットとリトライ実装があります。クリティカルな運用では監視と監査ログを必ず有効にしてください。
- DuckDB のスキーマは多数のチェック制約を含みます。ETL は冪等を前提としていますが、外部から直接 DB を操作する場合は注意が必要です。
- ニュース収集では外部 URL の検証や応答サイズ制御を行っていますが、運用環境ではさらなる監視や例外ハンドリングを設けてください。
- 本ライブラリは発注（実際の約定）周りの実装（kabu API 呼び出しの詳細やリスク管理）は含めることができますが、production（live）で運用する場合は十分なテスト・レビューが必須です。

---

必要であれば README に以下を追加できます：
- 実行可能な CLI / サービス起動手順（systemd / cron 例）
- より詳細な .env.example
- テーブル定義ドキュメント（DataSchema.md 相当）
- 戦略設計ドキュメント（StrategyModel.md 相当）

ご希望の内容（例: .env.example の追加、ETL の cron 化サンプル、Slack 通知の設定方法など）があれば教えてください。README を拡張して提供します。