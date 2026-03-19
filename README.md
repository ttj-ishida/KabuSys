# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリです。  
J-Quants や RSS などからデータを収集し、DuckDB に保存・整形し、研究・戦略・発注の各層で利用できるユーティリティ群を提供します。

主な設計方針：
- DuckDB を中心としたローカルデータレイク（Raw / Processed / Feature / Execution 層）
- J-Quants API との堅牢な連携（レート制御・リトライ・トークン自動更新）
- ニュース収集の安全性（SSRF対策、XML攻撃対策、受信サイズ制限）
- ETL の冪等性（ON CONFLICT 句を利用した上書き）
- 研究用途のファクター計算（外部ライブラリに依存しない実装）

---

## 機能一覧

- データ取得 / 保存
  - J-Quants から株価日足、財務情報、マーケットカレンダー取得 (kabusys.data.jquants_client)
  - RSS ベースのニュース収集と銘柄紐付け (kabusys.data.news_collector)
  - DuckDB スキーマ定義・初期化 (kabusys.data.schema)
  - ETL パイプライン（差分取得・バックフィル・品質チェック） (kabusys.data.pipeline)

- データ品質管理
  - 欠損・重複・スパイク（急騰/急落）・日付不整合チェック (kabusys.data.quality)

- カレンダー管理
  - JPX カレンダー管理・営業日判定・次/前営業日取得 (kabusys.data.calendar_management)

- 監査ログ / トレーサビリティ
  - signal → order_request → execution までの監査テーブル (kabusys.data.audit)

- 研究・特徴量生成
  - モメンタム / ボラティリティ / バリュー等のファクター計算 (kabusys.research.factor_research)
  - 将来リターン計算・IC（Information Coefficient）計算・統計サマリ (kabusys.research.feature_exploration)
  - Zスコア正規化ユーティリティ (kabusys.data.stats)

- その他
  - 設定管理（.env 自動読み込み、環境切替） (kabusys.config)
  - 発注・戦略・監視用のプレースホルダモジュール群 (kabusys.strategy, kabusys.execution, kabusys.monitoring)

---

## 動作要件 / 依存

- Python 3.10+
- duckdb
- defusedxml

インストール例（最低限）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# 必要に応じて他パッケージを追加
```

リポジトリ側で requirements.txt がある場合はそれを使ってください。

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成して有効化し、依存をインストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb defusedxml
   ```

3. 環境変数ファイルを準備
   - プロジェクトルートの `.env` / `.env.local` を用意します（.env.example を参考に）。
   - 主要な環境変数（以下参照）を設定してください。パスワードやトークンは秘匿して管理してください。

   主要な環境変数:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack Bot トークン（必須）
   - SLACK_CHANNEL_ID: 通知先 Slack チャンネル ID（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite (監視用) のパス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: development|paper_trading|live（デフォルト development）
   - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）

   自動 .env 読込を無効化したいテスト等では:
   ```bash
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

4. DuckDB スキーマ初期化
   Python REPL またはスクリプトから：
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ディレクトリがなければ自動作成
   ```
   監査ログ専用 DB を初期化する場合:
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（よくある操作の例）

- 日次 ETL を実行（株価・財務・カレンダーの差分取得＋品質チェック）:
  ```python
  from kabusys.data.schema import get_connection, init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")  # 初回のみ init_schema、以降は get_connection でも可
  result = run_daily_etl(conn)  # デフォルトは今日
  print(result.to_dict())
  ```

- 特定期間までの市場カレンダーを更新（夜間バッチ）:
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.calendar_management import calendar_update_job

  conn = init_schema("data/kabusys.duckdb")
  saved = calendar_update_job(conn)  # デフォルト lookahead_days=90
  print("saved:", saved)
  ```

- RSS ニュース収集ジョブ（known_codes を渡すと銘柄抽出して紐付け）:
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.news_collector import run_news_collection

  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 例えば有効な銘柄コードセット
  stats = run_news_collection(conn, known_codes=known_codes)
  print(stats)  # {source_name: saved_count, ...}
  ```

- 研究用ファクター計算（例: モメンタム）:
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.research.factor_research import calc_momentum
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  recs = calc_momentum(conn, target_date=date(2025, 1, 31))
  # recs は [{"date": ..., "code": ..., "mom_1m": ..., ...}, ...]
  ```

- ファクターの Z スコア正規化:
  ```python
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(recs, ["mom_1m", "ma200_dev"])
  ```

---

## 主要 API / モジュール

- kabusys.config: 環境変数管理・自動 .env 読込（settings オブジェクト経由で利用）
- kabusys.data.jquants_client: J-Quants API クライアント（取得・保存ユーティリティ）
- kabusys.data.schema: DuckDB スキーマ DDL と init_schema/get_connection
- kabusys.data.pipeline: ETL 実行（run_daily_etl など）
- kabusys.data.news_collector: RSS 収集・前処理・DB 保存
- kabusys.data.quality: データ品質チェック
- kabusys.data.calendar_management: 営業日判定・カレンダー更新ジョブ
- kabusys.data.audit: 監査ログテーブルの初期化
- kabusys.research: ファクター計算・将来リターン・IC・統計サマリ
- kabusys.strategy / kabusys.execution / kabusys.monitoring: 戦略・発注・監視層のエントリポイント（実装はモジュール内）

---

## ディレクトリ構成（抜粋）

src/kabusys/
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
  - feature_exploration.py
  - factor_research.py
- strategy/
  - __init__.py
- execution/
  - __init__.py
- monitoring/
  - __init__.py

（上記は本 README に含まれる主なファイルを抜粋しています）

---

## 運用上の注意 / 補足

- 環境切替:
  - KABUSYS_ENV により development / paper_trading / live を切り替えます。live を有効にすると本番発注ロジックの利用等を想定した挙動になります（戦略層・発注層の実装次第）。
- セキュリティ:
  - .env やトークンは漏洩しないように CI/CD シークレットストア等で管理してください。
  - news_collector は SSRF 対策・XML 注入対策を盛り込んでいますが、公開環境での運用時はさらに監視ログ等を有効にしてください。
- 冪等性:
  - jquants_client の save_* / news_collector の save_* は冪等設計（ON CONFLICT / RETURNING）です。ETL を再実行してもデータが重複しません。
- テスト:
  - 設定自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト中の .env の副作用回避に有用）。

---

この README はコードベースに含まれるモジュール構成・ドキュメント文字列を元に作成しています。実運用する際は .env.example を整備し、CI/運用手順（バックアップ、監視、ロールバック）を追加してください。質問や README の追加項目（例: CLI の利用方法、Docker コンテナ化手順など）があれば教えてください。