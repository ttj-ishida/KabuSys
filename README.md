# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）の README。  
本リポジトリはデータ取得・ETL・特徴量生成・シグナル生成・ニュース収集などの主要コンポーネントを提供します。

---

## プロジェクト概要

KabuSys は日本株の量的投資ワークフローを支援するライブラリ群です。主な目的は以下です。

- J-Quants API からの市場データ（OHLCV・財務・カレンダー）の取得と DuckDB への保存（冪等）
- データ品質チェック・ETL パイプラインの実装（差分更新・バックフィル対応）
- 研究環境で算出した生ファクターを正規化・統合して特徴量テーブルを作成
- 正規化済み特徴量と AI スコアを統合し、売買シグナルを生成
- RSS ベースのニュース収集と銘柄紐付け
- 発注・約定・監査ログのスキーマを備えた Execution / Audit レイヤ

設計方針として、ルックアヘッドバイアスを避けること、DuckDB ベースでの一貫したデータ管理、冪等性（ON CONFLICT / トランザクション）を重視しています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（ページネーション・リトライ・レート制限・トークン自動リフレッシュ）
  - schema: DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
  - pipeline: 日次 ETL（差分更新・バックフィル・品質チェック）
  - news_collector: RSS 取得・前処理・raw_news 保存・銘柄抽出
  - calendar_management: 市場カレンダー管理（営業日判定・次/前営業日取得）
  - stats: Z スコア正規化等の統計ユーティリティ
- research/
  - factor_research: Momentum / Volatility / Value 等のファクター計算（prices_daily / raw_financials 利用）
  - feature_exploration: 将来リターン計算・IC 計算・ファクターサマリ
- strategy/
  - feature_engineering: 生ファクタを正規化し features テーブルへ保存
  - signal_generator: features + ai_scores から final_score を算出し signals に書き込む
- config: 環境変数管理（.env/.env.local 自動ロード、必須値チェック）
- audit / execution / monitoring（スキーマや監査ログ、発注系の骨組み）

---

## セットアップ手順

1. Python 環境を用意（推奨: 3.9+）

2. リポジトリをクローンしてインストール（開発モード）
   ```bash
   git clone <this-repo-url>
   cd <repo>
   pip install -e .
   ```

3. 必要な依存ライブラリ（例）
   - duckdb
   - defusedxml
   - （標準ライブラリのみで実装されている部分も多いですが、上記は必須）

   例:
   ```bash
   pip install duckdb defusedxml
   ```

4. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（自動ロードはデフォルトで有効）。
   - 自動ロードを無効にする場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必須環境変数（config.Settings に基づく）
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
     - SLACK_BOT_TOKEN — Slack 通知用トークン（必須）
     - SLACK_CHANNEL_ID — Slack チャネルID（必須）
   - 任意 / デフォルト値を持つ環境変数
     - KABUSYS_ENV — 実行環境: `development` | `paper_trading` | `live`（デフォルト: development）
     - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL。デフォルト: INFO）
     - KABU_API_BASE_URL — kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）

   例 `.env`（最低限の例）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=yyyyy
   SLACK_BOT_TOKEN=xxxxx
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

---

## 使い方（基本的なワークフロー）

以下は Python からの簡単な利用例です。実行前に必ず環境変数を設定してください。

1. DuckDB スキーマ初期化
   ```python
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")  # ファイル DB を初期化して接続を返す
   ```

2. 日次 ETL 実行（J-Quants から差分取得して保存）
   ```python
   from kabusys.data.pipeline import run_daily_etl

   result = run_daily_etl(conn)  # target_date を渡さなければ今日の日付で実行
   print(result.to_dict())
   ```

3. 特徴量構築（features テーブル作成）
   ```python
   from kabusys.strategy import build_features
   from datetime import date

   n = build_features(conn, target_date=date(2024, 1, 10))
   print(f"features updated: {n}")
   ```

4. シグナル生成（signals テーブルへ書き込む）
   ```python
   from kabusys.strategy import generate_signals
   from datetime import date

   total = generate_signals(conn, target_date=date(2024, 1, 10))
   print(f"signals written: {total}")
   ```

5. ニュース収集（RSS -> raw_news）
   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203", "6758"})
   print(results)
   ```

6. 研究用ユーティリティ
   - ファクター計算:
     ```python
     from kabusys.research import calc_momentum, calc_volatility, calc_value
     recs = calc_momentum(conn, target_date=date(2024,1,10))
     ```
   - 将来リターン / IC:
     ```python
     from kabusys.research import calc_forward_returns, calc_ic
     fwd = calc_forward_returns(conn, target_date=date(2024,1,10))
     ```

ログやエラーは設定した LOG_LEVEL に従って出力されます。運用時は KABUSYS_ENV を `live` や `paper_trading` に変更してください。

---

## よくある操作・注意点

- 自動 .env 読み込み:
  - プロジェクトルート（.git または pyproject.toml がある場所）を起点に `.env` と `.env.local` を自動で読み込みます。
  - 読み込み優先度: OS 環境 > .env.local > .env。OS 環境変数は上書きされません。
- テスト時:
  - 自動環境読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 冪等性:
  - J-Quants から保存する関数は ON CONFLICT / DO UPDATE を利用しており、何度実行しても整合性が保たれます。
- ルックアヘッドバイアス対策:
  - すべての戦略・ファクター計算・シグナル生成は target_date 時点までのデータのみを参照するよう設計されています。

---

## ディレクトリ構成（主要ファイルの説明）

（src/kabusys 以下）

- __init__.py
  - パッケージのエクスポート定義（data, strategy, execution, monitoring）
- config.py
  - 環境変数の自動ロード（.env / .env.local）、必須チェック（Settings）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得 + 保存ユーティリティ）
  - news_collector.py — RSS 収集・前処理・raw_news / news_symbols 保存
  - schema.py — DuckDB スキーマ定義と init_schema / get_connection
  - pipeline.py — ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - features.py — zscore_normalize の再エクスポート
  - stats.py — zscore_normalize などの統計ユーティリティ
  - calendar_management.py — 市場カレンダー管理・営業日判定
  - audit.py — 監査ログ用スキーマ定義（signal_events, order_requests, executions 等）
  - (その他: quality 等の補助モジュールが想定される)
- research/
  - __init__.py
  - factor_research.py — momentum / volatility / value のファクター計算
  - feature_exploration.py — 将来リターン・IC・統計サマリー
- strategy/
  - __init__.py
  - feature_engineering.py — features テーブル作成ロジック
  - signal_generator.py — final_score 計算と signals 生成
- execution/
  - __init__.py
  - （発注・ブローカー連携の実装を想定）
- monitoring/
  - （監視・アラート・Slack 連携などを想定）

---

## 開発者向けメモ

- DuckDB の挙動（DATE/TIMESTAMP 型やクエリ）に依存する部分が多いため、ローカルでの DB 初期化と小さなサンプルデータでの単体テストを推奨します。
- network 周り（RSS / J-Quants）のエラーは再試行ロジックやログを利用して監視してください。
- Signal / Execution 層は監査トレーサビリティを重視しており、ID（UUID）連鎖でフローを追跡可能にする設計です。

---

必要があれば README に含める例（.env.example、cron ジョブ例、CI 実行例、より詳しい API 使用法など）を追記できます。どの項目を詳しく書き足しましょうか？