# KabuSys

日本株の自動売買 / データプラットフォーム用ライブラリ。  
ETL、ニュース収集・NLP、ファクター計算、監査ログ、J-Quants クライアントなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けのデータプラットフォームと自動売買パイプラインの基盤ライブラリです。主な目的は次のとおりです。

- J-Quants API から株価・財務・カレンダー等を差分取得して DuckDB に保存する ETL（差分取得 / 冪等保存 / 品質チェック）
- RSS ベースのニュース収集と前処理、および LLM を使ったニュースセンチメントスコアリング
- マーケットレジーム判定（ETF の MA 乖離 + マクロニュースセンチメントの合成）
- 研究用ファクター計算・特徴量探索ユーティリティ
- 発注〜約定に向けた監査ログ（監査テーブル・初期化）や監査用 DB 初期化ユーティリティ
- J-Quants API クライアント（認証・リトライ・レートリミット管理）とデータ保存関数

設計方針の例:
- ルックアヘッドバイアスを避ける（関数は内部で date.today() や datetime.today() に直接依存しない）
- 各種操作は冪等に（ON CONFLICT / トランザクション）実装
- 外部 API 呼び出しはリトライ + バックオフを実装して堅牢化

---

## 主な機能一覧

- 環境設定読み込み（.env / .env.local 自動読み込み、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
- J-Quants クライアント
  - get_id_token / fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - DuckDB への save_*（raw_prices, raw_financials, market_calendar）で冪等保存
- ETL パイプライン
  - 日次 ETL（run_daily_etl）: カレンダー → 株価 → 財務 → 品質チェック
  - 個別 ETL ジョブ（run_prices_etl, run_financials_etl, run_calendar_etl）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- マーケットカレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job）
- ニュース収集（RSS 取得・前処理・SSRF 防御・トラッキングパラメータ削除）
- ニュース NLP（gpt-4o-mini を利用した銘柄ごとのセンチメントスコアリング）
- レジーム判定（ETF 1321 の MA200 乖離とマクロニューススコアの合成）
- 研究用モジュール（モメンタム・ボラティリティ・バリュー計算、将来リターン、IC、統計サマリ）
- 監査ログスキーマ（監査テーブルの初期化・インデックス作成・専用 DB 初期化）

---

## セットアップ手順

前提:
- Python 3.10+（typing の一部機能を利用）
- システムに適切なネットワーク / DB 保存先の書き込み権限

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境の作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

3. 必要パッケージのインストール（例）
   requirements.txt を用意している場合:
   ```bash
   pip install -r requirements.txt
   ```
   最低限の依存ライブラリ（コードで使用されているもの）:
   - duckdb
   - openai
   - defusedxml

   例:
   ```bash
   pip install duckdb openai defusedxml
   ```

4. 環境変数の設定
   - プロジェクトルートに `.env`（または `.env.local`）を作成すると自動読み込みされます（優先順: OS env > .env.local > .env）。
   - 自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数例（.env）
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

   # kabuステーション (外部モジュールが利用する場合)
   KABU_API_PASSWORD=your_kabu_api_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # OpenAI
   OPENAI_API_KEY=sk-...

   # Slack (通知等で使用)
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=Cxxxxxx

   # ローカル DB パス
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 実行環境
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（主要なユースケース）

以下は代表的な API の呼び出し例です。実行前に必ず必要な環境変数（特に OPENAI_API_KEY / JQUANTS_REFRESH_TOKEN）を設定してください。

- DuckDB 接続を作って日次 ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュースのセンチメントを算出して ai_scores に書き込む
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 19))  # 書き込み件数を返す
  print("written:", written)
  ```

- 市場レジームを判定して market_regime に書き込む
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 19))
  ```

- 監査ログ用 DB を初期化する
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # conn を使って order_requests, signal_events, executions テーブルへ書けます
  ```

- J-Quants API を直接使ってデータ取得
  ```python
  from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
  token = get_id_token()  # 環境変数 JQUANTS_REFRESH_TOKEN を参照
  rows = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

- マーケットカレンダーの判定ユーティリティ
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  print(is_trading_day(conn, date(2026, 1, 1)))
  print(next_trading_day(conn, date(2026, 1, 1)))
  ```

注意点:
- AI 関連関数（score_news / score_regime）は OpenAI の API キー（OPENAI_API_KEY）を必要とします。api_key 引数でも渡せます。
- ETL は DuckDB 内のテーブルスキーマが前提です。初期スキーマ作成スクリプトがある場合は先に実行してください（本 README にスキーマ DDL は含めていませんが、data.audit モジュールの init_audit_schema などは提供されています）。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード（使う場合）
- KABU_API_BASE_URL — kabuステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（AI モジュールで使用）
- SLACK_BOT_TOKEN (必須) — Slack 通知を使う場合の Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（モニタリング等）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化する（1）

.env の読み込み順序:
- OS 環境変数 > .env.local > .env
- プロジェクトルートは .git または pyproject.toml を基準に自動検出

---

## ディレクトリ構成（主なファイル）

プロジェクトの主要なソースは `src/kabusys` 配下にあります。代表的なファイル・モジュールは次の通りです。

- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py          # ニュースの LLM スコアリング
  - regime_detector.py   # 市場レジーム判定
- src/kabusys/data/
  - __init__.py
  - jquants_client.py    # J-Quants API クライアント + DuckDB 保存
  - pipeline.py          # ETL パイプライン / run_daily_etl 等
  - etl.py               # ETLResult 再エクスポート
  - news_collector.py    # RSS 収集と前処理
  - calendar_management.py
  - stats.py             # zscore_normalize 等
  - quality.py           # データ品質チェック
  - audit.py             # 監査ログ DDL / 初期化
- src/kabusys/research/
  - __init__.py
  - factor_research.py   # モメンタム / ボラティリティ / バリュー
  - feature_exploration.py  # 将来リターン / IC / 統計サマリ

（上記以外にも strategy / execution / monitoring 等のパッケージが __init__ に列挙されていますが、ここに挙げたのがコアデータ処理・研究・AI モジュール群です）

---

## 追加の注意事項・運用上のヒント

- セキュリティ
  - RSS 収集では SSRF 対策や gzip サイズ制限、トラッキングパラメータ削除などが組み込まれています。外部 URL の取り扱いには注意してください。
  - OpenAI や J-Quants の API キーは秘匿情報のため Git 管理しないでください。
- 冪等性
  - ETL / 保存関数は ON CONFLICT で上書きする設計です。部分失敗時のデータ保護を考慮した実装がされています。
- ロギング
  - LOG_LEVEL で制御し、運用環境では INFO〜WARNING、デバッグ時は DEBUG を推奨します。
- テスト
  - 外部 API 呼び出し部はモックしやすい形（_call_openai_api の差し替えや _urlopen のモック）で実装されています。ユニットテスト作成が容易です。

---

必要であれば、README に以下を追加できます:
- 開発用のテスト実行方法（pytest）や CI 設定
- DuckDB の初期スキーマ定義（DDL）とマイグレーション手順
- サンプル .env.example ファイル（テンプレート）
- 各テーブルのカラム定義ドキュメント

どれを追加しますか？