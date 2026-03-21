# KabuSys

日本株向けの自動売買基盤ライブラリ（モジュール群）。  
データ収集（J-Quants）、ETL、DuckDBスキーマ、特徴量計算、シグナル生成、ニュース収集、監査ログなどを含んだワークフローを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の責務を持つモジュール群から構成される自動売買システム用ライブラリです。

- J-Quants からの市場データ取得（株価 / 財務 / カレンダー）
- DuckDB を用いたローカルデータベース（Raw / Processed / Feature / Execution 層）の管理
- ETL パイプライン（差分取得・保存・品質チェック）
- 研究用ファクター計算（モメンタム / ボラティリティ / バリュー 等）
- 特徴量の正規化と features テーブルへの保存
- features と AI スコアを組み合わせたシグナル生成（BUY / SELL）
- RSS ベースのニュース収集と記事→銘柄紐付け
- 発注・約定・ポジション監査用テーブル（監査ログ）

設計方針として、ルックアヘッドバイアスを避けること、DuckDB に対する冪等操作、ネットワーク呼び出しの堅牢化（レート制限・リトライ）、および明瞭な境界（research / data / strategy / execution）を重視しています。

---

## 主な機能一覧

- data.jquants_client
  - J-Quants API から日足・財務・カレンダーを取得し DuckDB に保存（ページネーション対応、トークン自動更新、レート制御、リトライ）
- data.schema
  - DuckDB スキーマの作成 / 初期化（Raw / Processed / Feature / Execution 層）
- data.pipeline
  - 日次 ETL（差分取得・保存・品質チェック）を一括実行
- data.news_collector
  - RSS から記事を取得して前処理→raw_news 保存、銘柄抽出・紐付け
- research.factor_research / feature_exploration
  - モメンタム / ボラティリティ / バリュー等のファクター計算、将来リターン・IC・統計サマリー
- strategy.feature_engineering
  - 生ファクターを正規化・クリップして features テーブルへ保存
- strategy.signal_generator
  - features / ai_scores / positions を読み final_score を算出し BUY/SELL シグナルを生成、signals テーブルに保存
- monitoring / execution（骨組み）
  - 発注・監視・監査用テーブル定義とインターフェース（実際のブローカー連携は execution 層で実装）

---

## 要件

- Python 3.10+
- 必須パッケージ（最低限）
  - duckdb
  - defusedxml
- 標準ライブラリの urllib 等を広く利用します。

（実行環境に応じて他の依存を追加する場合があります。pip 用の requirements.txt がある場合はそちらを参照してください。）

---

## セットアップ手順

1. リポジトリをクローン / ソースを入手

2. 仮想環境作成（推奨）
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .venv\Scripts\Activate.ps1
     ```

3. 依存パッケージをインストール（最低限）
   ```
   pip install duckdb defusedxml
   ```

   ※ 実運用ではロギング・Slack 通知・テスト用の追加パッケージや linters を導入してください。

4. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を作成すると、自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすれば無効化可）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD : kabuステーション API パスワード（execution 層使用時）
     - SLACK_BOT_TOKEN : Slack 通知に使用する Bot トークン
     - SLACK_CHANNEL_ID : Slack チャンネル ID
   - 任意（デフォルト値あり）:
     - KABUSYS_ENV : development / paper_trading / live （デフォルト: development）
     - LOG_LEVEL : DEBUG/INFO/...（デフォルト: INFO）
     - DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH : 監視用 SQLite パス（デフォルト: data/monitoring.db）

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで実行:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
   - ":memory:" を指定するとインメモリ DB を使用できます（テスト時など）。

---

## 使い方（代表的なワークフロー）

以下はライブラリ API を直接利用する簡易例です。実運用ではジョブスケジューラ（cron / Airflow 等）で日次バッチ化します。

1. DuckDB スキーマ初期化（既に初期化済みならスキップ）
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

2. 日次 ETL 実行（市場カレンダー・株価・財務の差分取得）
   ```python
   from kabusys.data.pipeline import run_daily_etl
   result = run_daily_etl(conn)  # target_date を指定可能
   print(result.to_dict())
   ```

3. 特徴量構築（features テーブルへ保存）
   ```python
   from datetime import date
   from kabusys.strategy import build_features
   count = build_features(conn, target_date=date(2024, 1, 15))
   print(f"features upserted: {count}")
   ```

4. シグナル生成（features / ai_scores / positions を参照）
   ```python
   from datetime import date
   from kabusys.strategy import generate_signals
   total = generate_signals(conn, target_date=date(2024, 1, 15))
   print(f"signals written: {total}")
   ```

5. ニュース収集ジョブ（RSS）
   ```python
   from kabusys.data.news_collector import run_news_collection
   # known_codes: 銘柄抽出に使う有効コードの集合（例: {"7203", "6758", ...}）
   stats = run_news_collection(conn, sources=None, known_codes=known_codes)
   print(stats)
   ```

6. カレンダー夜間更新ジョブ
   ```python
   from kabusys.data.calendar_management import calendar_update_job
   saved = calendar_update_job(conn)
   print(f"calendar saved: {saved}")
   ```

注意:
- run_daily_etl 内で market_calendar を先に取得し、target_date を営業日に調整します。
- 各関数は冪等設計（対象日で DELETE → INSERT の日付単位置換や ON CONFLICT）になっています。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須 for execution) : kabu API パスワード
- KABU_API_BASE_URL (任意) : kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須 for Slack) : Slack Bot トークン
- SLACK_CHANNEL_ID (必須 for Slack) : Slack チャンネル ID
- DUCKDB_PATH (任意) : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) : 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) : development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意) : ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD (任意) : 1 をセットすると自動で .env を読み込まない

---

## ディレクトリ構成

リポジトリ（src 配下のパッケージ構成を中心に簡易的に示します）:

- src/kabusys/
  - __init__.py
  - config.py                      -- 環境変数/設定管理
  - data/
    - __init__.py
    - jquants_client.py             -- J-Quants API クライアント（取得・保存）
    - news_collector.py             -- RSS ニュース収集／保存／銘柄抽出
    - schema.py                     -- DuckDB スキーマ定義・初期化
    - stats.py                      -- 統計ユーティリティ（z-score 等）
    - pipeline.py                   -- ETL パイプライン（差分更新 / run_daily_etl 等）
    - calendar_management.py        -- カレンダー管理 / 更新ジョブ
    - features.py                   -- features の再エクスポート
    - audit.py                      -- 監査ログ DDL（signal_events 等）
  - research/
    - __init__.py
    - factor_research.py            -- ファクター計算（mom / vol / value）
    - feature_exploration.py        -- IC / forward return / summary
  - strategy/
    - __init__.py
    - feature_engineering.py        -- 特徴量作成（正規化・フィルタ）
    - signal_generator.py           -- シグナル生成ロジック
  - execution/                      -- 発注/約定関連（骨組み）
  - monitoring/                     -- 監視 / 通知用（骨組み）

（上記は主要ファイルのみ抜粋しています。実際のリポジトリには追加のユーティリティや文書がある可能性があります。）

---

## 運用上の注意 / ベストプラクティス

- 本コードは市場データを使った投資判断支援のための基盤です。実運用する場合はリスク管理、十分なテスト、監査ポリシー、証券会社 API の仕様遵守を行ってください。
- 秘匿情報（API トークン等）は .env を利用する場合でも Git 管理下に置かないでください。運用環境では Vault 等のシークレット管理を推奨します。
- DuckDB ファイルはバックアップ・排他アクセスに注意してください。複数プロセスで同時に書き込みを行う用途では運用設計が必要です。
- J-Quants API のレート制限・利用規約を順守してください。クライアントはレート制御を入れていますが、過度な同時実行は避けてください。
- テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使うと .env 自動読み込みを無効化できます。

---

## 参考・補足

- DuckDB を使うことでローカルに高速な分析用 DB を保持できます。初期化は data/schema.init_schema() を必ず呼んでください。
- research モジュールは外部ライブラリに依存しない実装になっているため、軽量に統計解析が可能です。
- ニュース収集は RSS を前提にしており、SSRF/大容量レスポンス対策、XML インジェクション対策（defusedxml）などを実装しています。

---

必要に応じて README を追記（例: CLI サンプル、Airflow/Docker 化、追加の環境設定、詳細なテーブル定義リンク）できます。どの項目を詳しく追加したいか指示をください。