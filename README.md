# KabuSys

日本株向け自動売買基盤（データ取得・ETL・特徴量生成・シグナル生成・発注監査ログ等）のライブラリ群です。  
本リポジトリは主に以下の役割を担うモジュール群で構成されています。

- データ取得（J-Quants）・保存（DuckDB）
- ETL パイプライン（差分取得・品質チェック）
- 研究用ファクター計算（momentum / volatility / value 等）
- 特徴量正規化 → features テーブル作成
- シグナル生成（final_score 計算、BUY/SELL 判定）
- ニュース収集（RSS → raw_news / news_symbols）
- スキーマ / 監査ログ（DuckDB DDL）

以下はこのコードベースの README（日本語）です。

---

## 概要

KabuSys は日本株を対象に、データ取得から戦略信号生成までを行うためのモジュール群です。  
主要設計方針としては以下を重視しています。

- ルックアヘッドバイアスを防ぐ（target_date 時点のデータのみ使用）
- DuckDB をローカル DB に用いて高速・軽量にデータを保持
- API レート制御・リトライ等の堅牢性（J-Quants クライアント）
- ETL と品質チェックによりデータ品質を担保
- 冪等（Idempotent）な DB 書き込み（ON CONFLICT 等を使用）
- RSS ニュース収集時の SSRF / XML 攻撃対策（defusedxml 等）

---

## 主な機能一覧

- データ取得
  - J-Quants API クライアント（jquants_client）：日足・財務・マーケットカレンダー取得、トークン自動リフレッシュ、レートリミット・リトライ
- データ保存 / スキーマ
  - DuckDB スキーマ定義と初期化（data.schema.init_schema）
- ETL
  - 日次 ETL（data.pipeline.run_daily_etl）：市場カレンダー・株価・財務の差分取得と保存、品質チェック
  - 個別ジョブ（run_prices_etl, run_financials_etl, run_calendar_etl）
- 研究（research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC 計算、統計サマリー
- 特徴量（strategy.feature_engineering）
  - ファクターの正規化、ユニバースフィルタ、features テーブルへの upsert（build_features）
- シグナル（strategy.signal_generator）
  - features と ai_scores を統合して final_score を算出、BUY/SELL シグナルを生成（generate_signals）
- ニュース収集（data.news_collector）
  - RSS フィード取得、前処理、raw_news 保存、銘柄抽出と news_symbols への紐付け
- 監査ログ（data.audit）
  - シグナル→注文→約定のトレーサビリティを保つ監査テーブル（UUID 構造）

---

## 必要条件 / 依存関係

- Python 3.10 以上（PEP 604 の型記法や | None を使用）
- 主な外部パッケージ
  - duckdb
  - defusedxml
- 標準ライブラリのみで実装された部分も多いですが、上記パッケージは必須です。

例（pip）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

（プロジェクトに requirements.txt がある場合はそれを使用してください）

---

## 環境変数

以下の環境変数を設定してください（必須・任意の区別は Settings クラスのプロパティ説明参照）。

必須（Settings._require により未設定時に例外が出ます）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意（デフォルト値あり）:
- KABUSYS_ENV (development / paper_trading / live) — デフォルト: development
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL) — デフォルト: INFO
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db

自動 .env ロード:
- パッケージ起点でプロジェクトルート（.git または pyproject.toml を探索）を見つけた場合、ルートの `.env` と `.env.local` を自動で読み込みます。
- 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxx...
KABU_API_PASSWORD=pass
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境の作成と依存関係インストール
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install duckdb defusedxml
   ```

3. 環境変数の用意
   - ルートに `.env`（または `.env.local`）を作成して上記必須値を設定してください。
   - または環境に直接エクスポートしても構いません。

4. DuckDB スキーマ初期化
   - Python REPL もしくはスクリプトで初期化します。
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # パスは settings.duckdb_path を使うのも可
   conn.close()
   ```

---

## 使い方（主要 API の例）

以下は最も一般的なワークフロー例です。

1. DuckDB の初期化（一度だけ）
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

2. 日次 ETL 実行（市場カレンダー → 株価 → 財務 → 品質チェック）
   ```python
   from kabusys.data.pipeline import run_daily_etl
   result = run_daily_etl(conn)  # target_date を指定可能
   print(result.to_dict())
   ```

3. 特徴量生成（strategy.feature_engineering.build_features）
   ```python
   from datetime import date
   from kabusys.strategy import build_features
   n = build_features(conn, date(2024, 1, 15))
   print(f"features upserted: {n}")
   ```

4. シグナル生成（strategy.signal_generator.generate_signals）
   ```python
   from datetime import date
   from kabusys.strategy import generate_signals
   total = generate_signals(conn, date(2024, 1, 15))
   print(f"signals written: {total}")
   ```

5. ニュース収集ジョブ（RSS 取得 → raw_news 保存 → 銘柄紐付け）
   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   known_codes = {"7203", "6758", ...}  # 有効な銘柄コードセット
   result_map = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   print(result_map)
   ```

6. J-Quants 生 API 呼び出し（直接使用したい場合）
   ```python
   from kabusys.data.jquants_client import fetch_daily_quotes
   quotes = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
   ```

注意事項:
- 各関数は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取るので、同一接続でまとめて処理することでトランザクションの扱いが容易になります。
- settings（環境変数）を適切に設定しないと必須項目でエラーになります。

---

## よく使う関数 / モジュール一覧

- kabusys.config.settings — 環境設定の集中管理
- kabusys.data.schema.init_schema(db_path) — DuckDB スキーマ初期化
- kabusys.data.pipeline.run_daily_etl(...) — 日次 ETL 実行（推奨入口）
- kabusys.data.jquants_client.* — API 取得・保存ユーティリティ
- kabusys.data.news_collector.run_news_collection(...) — RSS ニュース収集ジョブ
- kabusys.research.* — 研究用ファクター計算・解析関数
- kabusys.strategy.build_features(conn, date) — features 作成
- kabusys.strategy.generate_signals(conn, date, ...) — signals 作成

---

## ディレクトリ構成（主なファイル）

概要的なツリー（src/kabusys 以下の主要ファイル）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - stats.py
      - pipeline.py
      - features.py
      - calendar_management.py
      - audit.py
      - (execution/ や quality モジュール等が想定される)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - strategy/
      - __init__.py
      - feature_engineering.py
      - signal_generator.py
    - execution/
      - __init__.py
    - monitoring/  (モニタリング関連は __all__ に含まれているが未列挙のファイルが存在する可能性あり)

各モジュールの責務はファイル先頭の docstring に詳述しています。実運用向けには data/schema.py で定義したテーブル構造を確認の上、DuckDB のスキーマを適切に管理してください。

---

## 運用上の注意 / 補足

- 本コードは「本番口座（live）」での使用を想定した設計要素を含みます。実際に発注を行う場合は入念なレビューと監査・テストを行ってください。
- J-Quants API はレート制限があります。本クライアントは固定間隔スロットリングとリトライを実装していますが、大量取得時は実行計画を調整してください。
- ニュース収集は外部 URL を扱うため SSRF / XML 攻撃対策（実装済み）に注意しつつ、さらに運用環境に応じた制限を設けてください。
- DuckDB ファイルは（デフォルト）`data/kabusys.duckdb` に保存されます。バックアップやアクセス権は運用ポリシーに従ってください。
- KABUSYS_ENV は `development` / `paper_trading` / `live` のいずれかで運用モードを切り替えます。`is_live`/`is_paper`/`is_dev` で参照できます。

---

必要であれば「導入例スクリプト」「.env.example」「運用ガイド（Cron/CI での ETL 実行方法）」などの追補資料を作成します。どの部分を優先的に整備したいか教えてください。