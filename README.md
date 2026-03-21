# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（KabuSys）。  
データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、DuckDB スキーマ管理などを提供します。

---

## プロジェクト概要

KabuSys は以下の層を持つ設計です。

- データレイヤ（J-Quants からの株価・財務・カレンダー・ニュース取得、DuckDB 保存）
- 処理レイヤ（prices_daily / fundamentals 等の整形）
- 特徴量レイヤ（research モジュールによるファクター算出、z-score 正規化）
- 戦略レイヤ（features + ai_scores を統合して売買シグナルを生成）
- 実行／監査レイヤ（シグナル・オーダー・約定・ポジション等のスキーマ）

設計上の主な特徴：

- DuckDB をデータベースとして利用（ローカルファイルまたはインメモリ）
- J-Quants API 呼び出しはレート制限・リトライ・トークンリフレッシュ対応
- ETL・保存は冪等（ON CONFLICT / INSERT … DO UPDATE / DO NOTHING）で実装
- ルックアヘッドバイアス対策（target_date 時点のデータのみ使用）
- ニュース収集は RSS を正規化・前処理し、銘柄コード抽出を行う（SSRF 対策あり）

---

## 主な機能一覧

- 環境設定管理（.env / .env.local の自動読み込み、必須 env チェック）
- DuckDB スキーマ初期化 / 接続（data.schema.init_schema / get_connection）
- J-Quants API クライアント（データ取得、ページネーション対応、トークン自動リフレッシュ）
- ETL パイプライン（日次 ETL：カレンダー・株価・財務の差分取得、品質チェック呼び出し）
- 研究用ファクター計算（momentum / volatility / value）
- 特徴量エンジニアリング（正規化・ユニバースフィルタ・features テーブルへの upsert）
- シグナル生成（final_score 計算、BUY/SELL 判定、signals テーブルへの書き込み）
- ニュース収集（RSS フィード取得、記事正規化、raw_news / news_symbols 保存）
- マーケットカレンダー管理（営業日判定・next/prev_trading_day 等ユーティリティ）
- 統計ユーティリティ（z-score 正規化、IC 計算、要約統計）

---

## セットアップ手順

下記はローカル開発 / 実行に必要な最低手順例です。

1. リポジトリをクローン（省略）

2. Python 仮想環境を作成・有効化（例）
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 必要なパッケージをインストール  
   （このコードベースでは明示的な requirements.txt が無いので、少なくとも以下を入れてください）
   ```
   pip install duckdb defusedxml
   ```
   - 実行層（HTTP, logging 等）は標準ライブラリ中心で実装されていますが、実環境では追加パッケージがあるかもしれません。

4. 環境変数の設定  
   プロジェクトルート（.git や pyproject.toml がある場所）に `.env` / `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   主要な環境変数（必須）:
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
   - KABU_API_PASSWORD: kabu ステーション API パスワード（発注等で使用）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID: 通知先チャンネル ID

   任意:
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

   簡易 `.env.example`:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=CXXXXX
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. データベース初期化（DuckDB スキーマ作成）
   Python REPL やスクリプトで:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ファイルを作成してスキーマを構築
   conn.close()
   ```

---

## 使い方（主要 API と実行例）

以下は主要なユースケースと簡単なコード例です。すべて duckdb 接続オブジェクト（kabusys.data.schema.get_connection / init_schema の戻り値）を渡して実行します。

1. 日次 ETL の実行（株価・財務・カレンダー取得 + 品質チェック）
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.data.pipeline import run_daily_etl

   conn = init_schema("data/kabusys.duckdb")
   result = run_daily_etl(conn)  # target_date を指定可能
   print(result.to_dict())
   conn.close()
   ```

2. 特徴量の計算・保存（features テーブル作成済みが前提）
   ```python
   from kabusys.data.schema import get_connection
   from kabusys.strategy import build_features
   from datetime import date

   conn = get_connection("data/kabusys.duckdb")
   n = build_features(conn, date(2024, 1, 31))
   print(f"upserted features: {n}")
   conn.close()
   ```

3. シグナル生成（features + ai_scores を参照）
   ```python
   from kabusys.data.schema import get_connection
   from kabusys.strategy import generate_signals
   from datetime import date

   conn = get_connection("data/kabusys.duckdb")
   num = generate_signals(conn, date(2024, 1, 31))
   print(f"signals written: {num}")
   conn.close()
   ```

4. ニュース収集ジョブ（RSS 取得 → raw_news 保存 → news_symbols 紐付け）
   ```python
   from kabusys.data.schema import get_connection
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

   conn = get_connection("data/kabusys.duckdb")
   # known_codes を与えると本文から銘柄コードを抽出して紐付ける
   known_codes = {"7203", "6758", "9984"}
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   print(results)
   conn.close()
   ```

5. J-Quants 生データの直接取得（テストやバッチ）
   ```python
   from kabusys.data import jquants_client as jq
   from datetime import date

   quotes = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
   # 保存は save_daily_quotes(conn, quotes)
   ```

注意点:
- 多くの関数は target_date ベースで「当日の情報のみ」を参照・保存するよう設計されています（ルックアヘッドバイアス対策）。
- ETL・保存関数は冪等であるため再実行しても重複挿入されない設計です。

---

## 環境設定の自動読み込み

- パッケージ import 時にプロジェクトルート（.git または pyproject.toml）を探し、`.env` と `.env.local` を自動で読み込みます。
  - 読み込み順序: OS 環境変数 > .env.local > .env
  - `.env.local` は上書き（override=True）され、OS 環境変数は保護されます。
- 自動読み込みを無効化するには環境変数を設定:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

---

## ディレクトリ構成

（主要ファイルを抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py  — 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py        — J-Quants API クライアント
      - news_collector.py       — RSS ニュース収集
      - schema.py               — DuckDB スキーマ定義・init_schema
      - stats.py                — 統計ユーティリティ（zscore_normalize）
      - pipeline.py             — ETL パイプライン（run_daily_etl 等）
      - features.py             — data 層の特徴量ユーティリティ再エクスポート
      - calendar_management.py  — マーケットカレンダー管理ユーティリティ
      - audit.py                — 監査ログテーブル DDL（order_requests / executions 等）
      - pipeline.py             — ETL 実装（差分取得・保存）
      - ...（その他 data 周りモジュール）
    - research/
      - __init__.py
      - factor_research.py      — momentum/volatility/value 計算
      - feature_exploration.py  — IC / forward returns / summary
    - strategy/
      - __init__.py
      - feature_engineering.py  — features 作成（正規化・ユニバースフィルタ）
      - signal_generator.py     — final_score 計算 → signals 生成
    - execution/
      - __init__.py            — 発注・実行層（スタブ／実装分離）
    - monitoring/              — 監視・アラート系（モジュールは将来追加）
- data/                       — デフォルトのデータ格納先（DuckDB ファイル等）
- .env.example                — 環境変数テンプレート（ユーザ作成）

---

## 開発メモ / 注意事項

- DuckDB の SQL やスキーマは設計上の制約（DuckDB バージョン差異）を考慮して書かれています。環境により一部機能（外部キーの ON DELETE など）が制限される旨の注釈があります。
- J-Quants API のレート制限は 120 req/min。クライアントは固定間隔スロットリングと指数バックオフで対応します。
- RSS 収集は SSRF・XML Bomb 等の脅威を考慮して実装されています（スキーム検証・プライベートホストブロック・defusedxml）。
- ログレベルや実行環境（development/paper_trading/live）は環境変数で制御され、Settings クラスで検証されます。
- 本パッケージは発注実行と証券会社 API への送信部分を直接行わない設計です（execution 層を通じて抽象化することを想定）。

---

必要であれば、README に次の情報も追記できます：
- CI / テスト実行方法（ユニットテスト / モックのセットアップ）
- 追加のデプロイ手順（systemd / cron / Airflow / Prefect の例）
- サンプル .env.example をリポジトリに追加しての具体例

ご希望があれば、README をリポジトリ向けにさらに整形（例: badges、Usage スクリプト、FAQ など）して更新します。