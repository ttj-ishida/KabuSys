# KabuSys

日本株向けの自動売買基盤ライブラリ（リサーチ / データパイプライン / 戦略 / 発注監査までを含むモジュール群）

このリポジトリは、J-Quants 等から市場データを収集して DuckDB に蓄積し、ファクター計算 → 特徴量作成 → シグナル生成 → 発注／監査のワークフローを支援するための共通ライブラリ群を提供します。研究環境（research）と本番実行（execution）の双方で利用できるように設計されています。

主な設計方針：
- ルックアヘッドバイアス排除（target_date 時点のデータのみを使用）
- 冪等性（DB 書き込みは ON CONFLICT / トランザクションで安全）
- 外部依存は最小限（DuckDB をコアに使用）
- 安全重視（RSS の SSRF 対策、J-Quants API のレート制御・リトライ・トークン自動更新 等）

---

## 機能一覧

- データ収集
  - J-Quants クライアント（株価日足、財務数値、マーケットカレンダー）
    - レートリミット (120 req/min) の順守
    - リトライ / トークン自動リフレッシュ
  - RSS ニュース収集（トラッキングパラメータ除去、SSRF 防止、gzip/サイズ制限）
- ETL / パイプライン
  - 差分更新・バックフィル対応の日次 ETL（市場カレンダー・株価・財務）
  - 品質チェック呼び出し（quality モジュールに依存）
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution レイヤのテーブル定義
  - 初期化関数（init_schema）
- 研究（research）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 特徴量探索（将来リターン計算、IC 計算、統計サマリ）
  - 汎用統計ユーティリティ（Z スコア正規化等）
- 戦略（strategy）
  - 特徴量作成（build_features: research で計算した raw factor を正規化 → features テーブルへ）
  - シグナル生成（generate_signals: features + AI スコア統合 → BUY/SELL シグナルを signals テーブルへ）
  - Bear レジーム抑制、エグジット条件（ストップロス等）を実装
- 発注 / 監査
  - 監査テーブル群（signal_events / order_requests / executions など）を定義
- ユーティリティ
  - マーケットカレンダー管理（営業日判定、next/prev trading day）
  - 環境変数管理（.env 自動読み込み、必須チェック）

---

## 動作環境・前提

- Python 3.10+
  - 型ヒントに `X | None` 等を使用しています（Python 3.10 以降が必要）
- 必要なパッケージ（代表例）
  - duckdb
  - defusedxml
- J-Quants API の利用にはリフレッシュトークン等の環境変数が必要

（実際のプロジェクトでは requirements.txt / pyproject.toml を用意してください）

---

## セットアップ手順

1. リポジトリのクローンとインストール（開発環境例）
   ```
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb defusedxml
   pip install -e .
   ```

2. 環境変数の設定
   - プロジェクトルートに `.env`（または `.env.local`）を配置すると自動で読み込まれます（デフォルト）。テスト等で自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 必須項目（例）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - オプション:
     - KABU_API_BASE_URL（既定: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（既定: data/kabusys.duckdb）
     - SQLITE_PATH（既定: data/monitoring.db）
     - KABUSYS_ENV（development / paper_trading / live、既定: development）
     - LOG_LEVEL（DEBUG / INFO / WARNING / ERROR / CRITICAL、既定: INFO）

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   SLACK_BOT_TOKEN=...
   SLACK_CHANNEL_ID=...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

3. DuckDB スキーマ初期化
   - Python REPL やスクリプトから:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ":memory:" も可
   ```

---

## 使い方（代表的なワークフロー）

以下はライブラリの主要 API を使った簡単なワークフロー例です。

- 日次 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）
  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量構築（research の生ファクターから features テーブルへ）
  ```python
  from datetime import date
  from kabusys.data.schema import get_connection, init_schema
  from kabusys.strategy import build_features

  conn = init_schema("data/kabusys.duckdb")
  n = build_features(conn, target_date=date(2024, 1, 31))
  print(f"features upserted: {n}")
  ```

- シグナル生成（features + ai_scores → signals）
  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.strategy import generate_signals

  conn = init_schema("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date(2024, 1, 31))
  print(f"signals written: {total}")
  ```

- ニュース収集
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.news_collector import run_news_collection

  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "6502"}  # 適宜登録済み銘柄セットを渡す
  stats = run_news_collection(conn, known_codes=known_codes)
  print(stats)
  ```

- 設定値の参照
  ```python
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  is_live = settings.is_live
  ```

---

## 重要な実装ノート / 動作上の注意

- 環境変数の必須チェックは `kabusys.config.Settings` のプロパティで行われます。未設定の場合は ValueError が発生します。
- DuckDB スキーマ初期化は冪等（既存テーブルはそのまま）です。運用開始時は必ず init_schema を実行してください。
- J-Quants API 呼び出しは内部でレート制御を行います。大量取得時は時間がかかります。
- RSS フェッチは SSRF 対策、受信サイズ制限、XML パース安全対策（defusedxml）を施しています。
- Strategy 層は発注 API（execution 層）には直接依存しません。signals テーブルへの書き込みは戦略の出力を永続化するためのものです。
- KABUSYS_ENV により実行モードを切り替えられます（development / paper_trading / live）。live 実行時は特に注意して環境変数や API エンドポイントを確認してください。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
  - 環境変数読み込み・Settings クラス
- data/
  - __init__.py
  - jquants_client.py        — J-Quants API クライアント（取得 + 保存ユーティリティ）
  - news_collector.py       — RSS 収集・前処理・DB 保存
  - schema.py               — DuckDB スキーマ定義・初期化（init_schema, get_connection）
  - pipeline.py             — ETL パイプライン（run_daily_etl 等）
  - stats.py                — 統計ユーティリティ（zscore_normalize 等）
  - features.py             — data.stats の再エクスポート
  - calendar_management.py  — market_calendar 管理・営業日判定・更新ジョブ
  - audit.py                — 発注 / 監査向けテーブル定義
  - (その他: quality モジュールなどが期待されるが本スニペットは一部)
- research/
  - __init__.py
  - factor_research.py      — モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py  — 将来リターン / IC / サマリ等
- strategy/
  - __init__.py
  - feature_engineering.py  — build_features（正規化・ユニバースフィルタ・features テーブル更新）
  - signal_generator.py     — generate_signals（final_score 計算・BUY/SELL 生成）
- execution/
  - __init__.py
  - （発注実行に関する実装を置く想定）
- monitoring/
  - （監視・メトリクス収集用モジュールを置く想定）

---

## 開発・寄与

- コードスタイル、テスト、CI の設定はプロジェクトのポリシーに従ってください。
- API トークンやシークレットはリポジトリに含めないこと。
- DuckDB のスキーマ変更を加える場合は後方互換性と既存データへの移行手順を明記してください。

---

もし README に追記したい具体的な運用手順（例えば cron/airflow に組み込む例、Slack 通知の使い方、kabuステーション連携手順など）があれば教えてください。必要に応じてサンプルスクリプトや運用チェックリストを追加します。