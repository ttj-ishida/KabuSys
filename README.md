# KabuSys

日本株向けのデータプラットフォーム兼自動売買支援ライブラリ（DuckDBベース）。  
データ収集（J-Quants / RSS）、ETL、データ品質チェック、特徴量生成、ニュースNLP（OpenAI）、市場レジーム判定、監査ログ（発注トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の定量投資・自動売買を支える基盤モジュール群です。  
主に次を目的とします。

- J-Quants API から株価・財務・カレンダーを取得し DuckDB に保存する ETL
- RSS からのニュース収集とニュース → 銘柄紐付け
- OpenAI を用いたニュースセンチメント評価（銘柄単位 & マクロ）
- 市場レジーム判定（ETF ma200 とマクロセンチメントの合成）
- 研究用途のファクター計算（モメンタム・バリュー・ボラティリティ等）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 発注〜約定の監査ログ用テーブル定義と初期化ユーティリティ
- 環境変数による設定管理（.env 自動読込）

設計上、バックテスト時のルックアヘッドバイアス回避やフェイルセーフ（API失敗時のデフォルト挙動）に配慮しています。

---

## 主な機能一覧

- データ取得 / 保存
  - J-Quants クライアント（レート制御・再試行・トークンリフレッシュ）
  - DuckDB へ冪等保存（ON CONFLICT 対応）
  - RSS ニュース収集（SSRF対策・トラッキング除去）
- ETL
  - 日次 ETL（calendar / prices / financials）と品質チェックの統合実行
  - 差分取得とバックフィル対応
- データ品質
  - 欠損、重複、スパイク、日付整合性検査
- 研究（Research）
  - モメンタム、バリュー、ボラティリティ等のファクター計算
  - 将来リターン計算、IC（Spearman）や統計サマリ
  - z-score 正規化ユーティリティ
- AI（OpenAI）
  - 銘柄別ニュースセンチメントスコア生成（batch、JSON mode、リトライ）
  - マクロニュースを用いた市場レジーム判定（ETF 1321 の ma200乖離 + マクロセンチメント）
- 監査（Audit）
  - signal_events, order_requests, executions 等の監査テーブル定義と初期化
- 設定管理
  - .env（.env.local）自動読み込み（プロジェクトルート検出）
  - 必須環境変数チェックと型変換ユーティリティ

---

## 要件（主な依存）

- Python 3.10+
- duckdb
- openai
- defusedxml

（実際の開発環境では他に型チェック用やテスト用の依存があるかもしれません。pip インストール時に必要パッケージを指定してください）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. インストール
   - 開発中パッケージを editable インストールする例：
     ```
     pip install -U pip
     pip install -e ".[dev]"  # requirements の定義がある場合
     ```
   - 最低限の依存を個別に入れる場合：
     ```
     pip install duckdb openai defusedxml
     ```

4. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須項目（例）:
     ```
     # J-Quants
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

     # kabuステーション（API 連携がある場合）
     KABU_API_PASSWORD=your_kabu_password
     KABU_API_BASE_URL=http://localhost:18080/kabusapi

     # Slack 通知
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567

     # OpenAI
     OPENAI_API_KEY=sk-...

     # DB paths (任意)
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db

     # 実行環境
     KABUSYS_ENV=development  # development | paper_trading | live
     LOG_LEVEL=INFO
     ```
   - .env の例ファイルは `./.env.example` を参考に作成してください（config モジュール参照のメッセージあり）。

5. DuckDB ファイル用ディレクトリ作成（必要なら）
   ```
   mkdir -p data
   ```

---

## 使い方（主要 API/実行例）

以下は Python REPL やスクリプト中で利用する例です。すべての操作は DuckDB 接続（duckdb.connect）を渡して行います。

- ETL（日次パイプライン実行）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄別）をスコアリングして ai_scores に保存
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print("written:", n_written)
  ```

- 市場レジーム判定（market_regime テーブルへ書き込み）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 監査ログDB の初期化（監査用に専用 DB を作る）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- J-Quants トークン取得 / データフェッチ（直接利用）
  ```python
  from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
  token = get_id_token()  # 環境変数 JQUANTS_REFRESH_TOKEN を使用
  records = fetch_daily_quotes(id_token=token, date_from=date(2026,3,1), date_to=date(2026,3,20))
  ```

- カレンダー更新ジョブ（夜間バッチ相当）
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  calendar_update_job(conn)
  ```

- 設定値参照
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path, settings.env, settings.is_live)
  ```

注意:
- OpenAI を利用する機能は `OPENAI_API_KEY`（または関数引数）を必要とします。
- ETL / API 呼び出しは外部ネットワークへ接続するため、適切な認証情報とネットワーク設定が必要です。
- 自動で .env を読み込む仕組みはプロジェクトルート（.git または pyproject.toml を基準）を探索します。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注実装時に使用）
- KABU_API_BASE_URL: kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知設定
- OPENAI_API_KEY: OpenAI API キー（AI モジュール用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env 読込を無効化する（値が設定されていれば無効化）

---

## ロギング / 実行モード

- KABUSYS_ENV で実行モードを切替（development / paper_trading / live）。production 相当の動作検査や安全制御はこのフラグを参照して実装してください（ライブラリ側は is_live / is_paper / is_dev プロパティを提供）。
- LOG_LEVEL 環境変数でログレベルを制御。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py  — 環境変数・設定読み込み
- ai/
  - __init__.py
  - news_nlp.py        — 銘柄ニュースのセンチメントスコア（OpenAI）
  - regime_detector.py — マーケットレジーム判定（ETF + マクロ）
- data/
  - __init__.py
  - jquants_client.py  — J-Quants API クライアント（取得 & DuckDB 保存）
  - pipeline.py        — ETL パイプライン（run_daily_etl 等）
  - etl.py             — ETL 主要型の公開
  - calendar_management.py — 市場カレンダー管理
  - news_collector.py  — RSS 収集・保存（SSRF対策等）
  - quality.py         — データ品質チェック
  - stats.py           — 統計ユーティリティ（zscore）
  - audit.py           — 監査ログテーブル定義 / 初期化
- research/
  - __init__.py
  - factor_research.py — モメンタム等ファクター計算
  - feature_exploration.py — 将来リターン・IC・統計サマリ等

（上記は主要ファイルの一覧です。細かいユーティリティや追加モジュールが含まれます）

---

## テスト & 開発時のヒント

- 自動 .env 読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テストで意図的に環境変数を注入したい場合など）。
- OpenAI 呼び出しは内部で再試行やフェイルセーフが入っていますが、ユニットテストでは `unittest.mock.patch` などで `_call_openai_api` を差し替える設計になっています。
- DuckDB の executemany に空リストを渡すとエラーになるバージョン差分対策が各所に実装されています。ダミーデータで十分な事前確認を行ってください。

---

## ライセンス / 貢献

（ここにプロジェクトのライセンスや貢献ルールを記載してください）

---

README では主要な使い方とアーキテクチャ、セットアップをまとめました。追加で各モジュール（ETL、news_nlp、regime_detector、jquants_client 等）の詳細なドキュメントやサンプルスクリプトが必要であれば、目的別にサンプルを作成します。どの部分を優先してほしいか教えてください。