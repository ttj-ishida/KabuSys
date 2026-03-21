# KabuSys — 日本株自動売買プラットフォーム（README）

KabuSys は日本株向けのデータプラットフォームと戦略層を備えた自動売買基盤のコードベースです。DuckDB をデータストアに用い、J-Quants API / RSS ニュース等からデータを収集し、特徴量作成→シグナル生成→発注（実装層）へとつなぐことを目的としています。

主な設計方針
- ルックアヘッドバイアスの防止（計算は target_date 時点のデータのみ使用）
- 冪等性（DB への保存は ON CONFLICT / トランザクションで担保）
- テスト容易性（id_token 注入など）
- 外部サービス呼び出しはクライアント層に集約、戦略層は発注 API に依存しない

---

## 機能一覧（概要）

- 環境設定管理
  - .env / .env.local を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - 必須環境変数のチェック（settings オブジェクト）

- データ取得・保存（data/jquants_client, data/pipeline）
  - J-Quants API クライアント（トークン更新、レート制御、リトライ）
  - 日足（OHLCV）、財務データ、JPX カレンダーの取得・DuckDB へ保存
  - 差分更新・バックフィル対応の ETL パイプライン（run_daily_etl 等）
  - 市場カレンダー管理、営業日ユーティリティ

- データ品質・スキーマ（data/schema）
  - DuckDB のスキーマ初期化（Raw / Processed / Feature / Execution 層）
  - インデックス定義・DDL を含む init_schema()

- ニュース収集（data/news_collector）
  - RSS フィード取得（SSRF 防止・gzip 対応・XML パース安全化）
  - 記事正規化・ID 生成（正規化 URL の SHA-256 の先頭 32 文字）
  - raw_news / news_symbols への冪等保存

- 研究・ファクター計算（research/factor_research, feature_exploration）
  - Momentum / Volatility / Value などのファクター計算
  - 将来リターン計算、IC（Spearman）や統計サマリーのユーティリティ

- 特徴量生成・シグナル（strategy）
  - build_features: research の生ファクターを正規化・フィルタして features テーブルへ保存
  - generate_signals: features + ai_scores を統合して final_score を計算し BUY/SELL シグナルを生成

- 発注・監査（schema に定義）
  - signal_queue / orders / trades / positions 等の実行層テーブル構成（監査用テーブル含む）

---

## 必須環境変数（主なもの）

（settings.Settings を参照。実行前に .env を作成して設定してください）

- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu API（kabuステーション）パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
- KABUSYS_ENV — 環境: development / paper_trading / live（省略時 development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、省略時 INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite DB（デフォルト: data/monitoring.db）

注意: .env 自動ロード機能はプロジェクトルート（.git または pyproject.toml を探索）で動作します。自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   ```
   git clone <リポジトリURL>
   cd <repo>
   ```

2. Python 仮想環境を作成・有効化（例: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要ライブラリをインストール
   - 本コードベースで使われている主要ライブラリ:
     - duckdb
     - defusedxml
   - 例:
     ```
     pip install duckdb defusedxml
     ```
   ※ pyproject.toml / requirements.txt がある場合はそちらを利用してください。

4. 環境変数設定
   - プロジェクトルートに `.env`（および `.env.local`）を作成して必須変数を設定してください。
   - 例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxx
     KABU_API_PASSWORD=xxxxx
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで初期化します:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")  # ":memory:" を指定してインメモリも可
     conn.close()
     ```

---

## 使い方（主なワークフロー例）

以下は典型的なワークフロー（ETL → 特徴量生成 → シグナル生成）です。

1. ETL（データ収集）
   ```python
   from datetime import date
   from kabusys.data.schema import init_schema
   from kabusys.data.pipeline import run_daily_etl

   conn = init_schema("data/kabusys.duckdb")
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   conn.close()
   ```

2. 特徴量のビルド
   ```python
   from datetime import date
   from kabusys.data.schema import get_connection
   from kabusys.strategy import build_features

   conn = get_connection("data/kabusys.duckdb")
   count = build_features(conn, target_date=date(2024, 1, 12))
   print(f"features upserted: {count}")
   conn.close()
   ```

3. シグナル生成
   ```python
   from datetime import date
   from kabusys.data.schema import get_connection
   from kabusys.strategy import generate_signals

   conn = get_connection("data/kabusys.duckdb")
   total = generate_signals(conn, target_date=date(2024, 1, 12))
   print(f"signals written: {total}")
   conn.close()
   ```

4. ニュース収集（RSS）
   ```python
   from kabusys.data.schema import get_connection
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

   conn = get_connection("data/kabusys.duckdb")
   known_codes = {"7203", "6758", "9432"}  # 例: 有効銘柄コードセット
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   print(results)
   conn.close()
   ```

5. カレンダー更新ジョブ
   ```python
   from kabusys.data.schema import get_connection
   from kabusys.data.calendar_management import calendar_update_job

   conn = get_connection("data/kabusys.duckdb")
   saved = calendar_update_job(conn)
   print(f"calendar saved: {saved}")
   conn.close()
   ```

6. J-Quants API を直接呼ぶ（例: 日足取得）
   ```python
   from kabusys.data import jquants_client as jq

   # settings.jquants_refresh_token を設定していれば省略可能
   records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
   print(len(records))
   ```

注意点
- 全ての戦略計算は target_date 時点の DB のみを参照するため、実行時点の DB を正しく更新しておく必要があります。
- generate_signals は ai_scores テーブルの regime_score を参照して Bear レジーム判定等を行います。ai_scores が未登録でも動作します（デフォルト補完あり）。

---

## 主要モジュール / ディレクトリ構成

リポジトリの主要なファイル・ディレクトリ（src/kabusys 以下）

- kabusys/
  - __init__.py
  - config.py                 — 環境変数/設定ロード（.env 自動読み込み）
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント、保存ユーティリティ
    - news_collector.py        — RSS ニュース収集・DB 保存
    - schema.py                — DuckDB スキーマ定義・初期化
    - stats.py                 — Z スコア等の統計ユーティリティ
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py   — 市場カレンダー管理ユーティリティ
    - features.py              — features エクスポート（zscore_normalize の再公開）
    - audit.py                 — 監査ログ（signal_events / order_requests / executions）
    - (その他 execution / monitoring 用のプレースホルダ)
  - research/
    - __init__.py
    - factor_research.py       — Momentum / Volatility / Value ファクター計算
    - feature_exploration.py   — 将来リターン / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py   — features テーブルの作成（正規化・フィルタ）
    - signal_generator.py      — final_score 計算・signals 書き込み
  - execution/                 — 発注層の実装（現状プレースホルダ）
  - monitoring/                — 監視/アラートの実装（プレースホルダ）

（上記はコードベースに含まれる主なファイルの抜粋です）

---

## 開発・運用上の注意

- DB 初期化は init_schema() を必ず一度実行してください（DDL が作成されます）。
- J-Quants API のレート制御・リトライ・トークン更新のロジックは jquants_client に実装されています。API 呼び出し時のエラーやレスポンス仕様に注意してください。
- news_collector は外部の RSS を取得します。SSRF 対策・サイズ制限・XML パースの安全化を実装していますが、運用環境ではさらに監視を行ってください。
- 本番稼働時は KABUSYS_ENV を適切に設定し、安全な発注フロー（paper_trading / live の切り替え）を確保してください。
- ログレベルや Slack 通知等の運用設定は環境変数で管理します。

---

## 貢献 / 変更の提案

- バグ修正・機能追加の提案は Pull Request を作成してください。
- 大きな設計変更や外部 API 仕様に関する変更は issue で事前に議論してください。

---

必要であれば、README に実行スクリプト例・docker 化手順・CI 設定例・テスト実行方法なども追加できます。どの情報が必要か教えてください。