# KabuSys

日本株向けの自動売買システム基盤ライブラリ（KabuSys）。  
データ取得（J-Quants）、ETL、特徴量作成、シグナル生成、ニュース収集、監査ログなどの共通処理を提供します。

---

## プロジェクト概要

KabuSys は、J-Quants 等から取得した株価・財務・ニュース等のデータを DuckDB に蓄積し、研究→特徴量作成→シグナル生成→発注監査のワークフローをサポートするコンポーネント群です。  
主に以下の責務を持ちます:

- データ取得クライアント（J-Quants API）と保存ユーティリティ
- DuckDB スキーマ定義と初期化
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- 研究用ファクター計算（momentum / volatility / value 等）
- 特徴量正規化・合成（features テーブルへの UPSERT）
- シグナル生成（final_score 集計、BUY/SELL の判定）
- ニュース収集（RSS 取得・前処理・銘柄抽出）
- マーケットカレンダー管理と営業日ロジック
- 監査ログ（シグナル→発注→約定のトレーサビリティ）

設計上、ルックアヘッドバイアスの排除、冪等性（DB 保存の ON CONFLICT / UPSERT）、ネットワーク・XML の安全対策（SSRF、defusedxml 等）に配慮しています。

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API から日次株価・財務・マーケットカレンダーを取得（ページネーション対応）
  - レート制限、リトライ、トークン自動更新、DuckDB への冪等保存
- data/schema.py
  - DuckDB 用のスキーマ定義（Raw / Processed / Feature / Execution 層）
  - init_schema() による初期化
- data/pipeline.py
  - 日次 ETL 実行（run_daily_etl）および個別 ETL ジョブ
  - 差分取得・バックフィル・品質チェック連携
- data/news_collector.py
  - RSS フィード取得、前処理、raw_news 保存、銘柄抽出・紐付け
  - SSRF/サイズ上限/トラッキング除去などの安全対策
- data/calendar_management.py
  - 市場カレンダーの管理、営業日判定、next/prev_trading_day 等ユーティリティ
- data/audit.py
  - シグナル→発注→約定の監査テーブル定義（監査ログ）
- research/
  - factor_research.py : momentum/volatility/value 等のファクター計算
  - feature_exploration.py : 将来リターン計算、IC（スピアマン）計算、統計サマリー
- strategy/
  - feature_engineering.py : raw ファクターを統合して features テーブルへ保存
  - signal_generator.py : features + ai_scores を統合して BUY/SELL シグナルを生成
- config.py
  - 環境変数読み込みと Settings（必須トークン・DB パス・環境設定の集中管理）
  - 自動的にプロジェクトルートの .env / .env.local を読み込む仕組み

---

## 要件

- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - defusedxml
- ネットワーク接続（J-Quants API を利用する場合）
- 環境変数（下に一覧）

※ 実行環境に合わせて追加の依存がある場合があります。setup.py / pyproject.toml を参照してください。

---

## 環境変数（主要なもの）

以下はアプリケーションが参照する主な環境変数です（必須は README 中で明記）。

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意/デフォルトあり:
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development / paper_trading / live、デフォルト: development)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO)

自動 .env 読み込み:
- パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml の所在）を探索し、
  .env（上書きせず）→ .env.local（上書き）を読み込みます。
- 自動読み込みを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>

2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb defusedxml
   - （プロジェクトに pyproject.toml / requirements.txt があればそれを使用）

4. 環境変数を設定
   - プロジェクトルートに .env または .env.local を作成
   - 例 (.env.example を参考):
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb
     - KABUSYS_ENV=development

5. DuckDB スキーマ初期化
   - Python から実行:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()
     ```
   - ":memory:" を渡すとインメモリ DB を使えます（テスト用）。

---

## 使い方（代表的な操作例）

以下は最小限の Python スニペット例です。スクリプト化して定期実行（cron / Airflow 等）してください。

- DB 初期化（既出）
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  conn.close()
  ```

- 日次 ETL 実行
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())
  conn.close()
  ```

- 市場カレンダー更新（夜間ジョブ）
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.calendar_management import calendar_update_job

  conn = init_schema("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print("saved:", saved)
  conn.close()
  ```

- ニュース収集ジョブ
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.news_collector import run_news_collection

  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  conn.close()
  ```

- 特徴量作成（features テーブルに保存）
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.strategy import build_features
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  n = build_features(conn, target_date=date(2024, 1, 31))
  print("features upserted:", n)
  conn.close()
  ```

- シグナル生成（signals テーブルに保存）
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.strategy import generate_signals
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date(2024, 1, 31))
  print("signals generated:", total)
  conn.close()
  ```

- J-Quants API からのデータ取得（低レベル）
  ```python
  from kabusys.data import jquants_client as jq
  rows = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

---

## 注意点 / 運用メモ

- Python の型ヒントで | 演算子（PEP 604）を利用しているため Python 3.10 以上を推奨します。
- J-Quants API はレート制限（120 req/min）があります。jquants_client は内部でスロットリングしていますが、長時間の大量取得時には配慮してください。
- DuckDB のファイルパスは settings.duckdb_path で管理されます。複数ノードで共有する場合は DB 排他に注意してください。
- 自動 .env 読み込みはプロジェクトルート検出に依存します。CI やテストで不要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- signals → 発注 → 約定のフローは別モジュール（execution 層）で取り扱います。strategy 層はシグナル生成に専念し、発注は execution 層が担当する設計です。
- ログレベルは LOG_LEVEL 環境変数で制御できます（DEBUG/INFO/...）。

---

## ディレクトリ構成（主なファイル/パッケージ）

src/kabusys/
- __init__.py
- config.py — 環境変数 / 設定管理
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得 + 保存）
  - news_collector.py — RSS 収集・前処理・DB 保存
  - schema.py — DuckDB スキーマ定義 / init_schema
  - pipeline.py — ETL パイプライン（run_daily_etl 他）
  - calendar_management.py — マーケットカレンダー管理
  - audit.py — 監査ログ定義
  - stats.py — 統計ユーティリティ（zscore_normalize）
  - features.py — data.stats の再エクスポート
  - execution/ — 発注関連（パッケージ）
- research/
  - __init__.py
  - factor_research.py — momentum/volatility/value の計算
  - feature_exploration.py — forward returns / IC / summary
- strategy/
  - __init__.py
  - feature_engineering.py — features 作成（Z スコア正規化等）
  - signal_generator.py — final_score 計算と signals 生成
- execution/ — 発注実行層（初期化ファイルのみ）
- monitoring/ — 監視関連（未実装ファイル等）

---

## 貢献 / 開発

- 開発ブランチ戦略や PR のルールはリポジトリポリシーに従ってください。
- テスト、lint、型チェック（mypy）を導入することを推奨します（型ヒントが多く使用されています）。
- 機密情報（実運用トークン等）は CI の Secret 管理や環境変数で管理し、リポジトリに含めないでください。

---

必要であれば README にサンプル .env.example、より詳しい運用手順（cron / systemd / Airflow 設定例）、発注層の利用方法（kabu ステーション連携）などを追加します。どの情報を優先して追記しますか？