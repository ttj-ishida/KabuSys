# KabuSys

日本株向けの自動売買 & データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）・ETL・データ品質チェック・ニュース収集とNLPスコアリング・市場レジーム判定・監査ログ（発注→約定のトレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の定量投資・自動売買基盤向けに設計された Python モジュール群です。主な目的は次の通りです。

- J-Quants API からの株価・財務・カレンダーの差分取得（レート制限・リトライ対応）
- DuckDB を使った ETL パイプライン（差分取得・冪等保存・品質チェック）
- RSS ベースのニュース収集と LLM を使ったニュースセンチメント（銘柄別）算出
- ETF ベースの長期移動平均とマクロニュース（LLM）を組み合わせた市場レジーム判定
- 監査ログ（signal → order_request → execution）のスキーマ初期化ユーティリティ
- 研究用ユーティリティ（ファクター計算・将来リターン・IC・統計サマリー等）

設計上の特徴:
- ルックアヘッドバイアス回避（内部で date.today() を安易に参照しない設計）
- DuckDB を中心としたローカルデータ管理（高速かつ軽量）
- 冪等（ON CONFLICT）・トランザクションでの安全な DB 操作
- 外部 API 呼び出しに対する堅牢なリトライ・バックオフロジック
- テスト容易性を意識した設計（API呼び出し部分のモック差替えが可能）

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（fetch / save の両方）
  - レートリミット管理、401 自動リフレッシュ、ページネーション対応
- data/pipeline.py
  - run_daily_etl を中心とした日次 ETL（カレンダー・株価・財務・品質チェック）
  - 個別 ETL（prices / financials / calendar）呼び出し可能
- data/news_collector.py
  - RSS からニュースを収集して raw_news / news_symbols に保存
  - SSRF 対策、サイズ制限、トラッキングパラメータ除去
- ai/news_nlp.py
  - 銘柄別ニュース集約 → OpenAI（gpt-4o-mini）でセンチメントを取得し ai_scores に保存
  - バッチ・リトライ・レスポンス検証ロジック
- ai/regime_detector.py
  - ETF (1321) の MA200 乖離とマクロニュースセンチメントを合成して market_regime に書込
- research/*
  - ファクター計算（momentum / volatility / value）・特徴探索（forward returns, IC, summary）
- data/calendar_management.py
  - JPX カレンダー管理、営業日判定、next/prev trading day 等
- data/audit.py
  - 監査ログ（signal_events / order_requests / executions）スキーマ初期化ユーティリティ

---

## セットアップ手順

前提
- Python 3.10+（Union 型の | を使用するため）
- Git とネットワーク接続（J-Quants / OpenAI など外部APIを使う場合）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows (PowerShell)
   ```

3. 必要パッケージをインストール（例）
   - 主要依存（本コードベースで参照されているライブラリ）
     - duckdb
     - openai
     - defusedxml
   例:
   ```
   pip install duckdb openai defusedxml
   ```
   実運用では requirements.txt / pyproject.toml に基づくインストールを推奨します。

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を配置すると自動読み込みされます（kabusys.config が自動ロード）。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   必須と思われる環境変数（例）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - OPENAI_API_KEY: OpenAI の API キー（score_news / score_regime で使用）
   - KABU_API_PASSWORD: kabu ステーション API のパスワード（必要に応じて）
   - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用
   - DUCKDB_PATH (任意): デフォルト `data/kabusys.duckdb`
   - SQLITE_PATH (任意): 監視 DB など

   サンプル `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=secret_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB データベースの準備
   - 通常は ETL 実行時にテーブルが存在しないとエラーになる場合があるため、
     スキーマ初期化ユーティリティ（本リポジトリに schema 初期化コードがある前提）を用意してください。
   - 監査ログ専用 DB 初期化例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```

---

## 使い方（簡易ガイド）

以下は代表的な利用例です。実行は Python スクリプトや CLI ジョブから行ってください。

1. 日次 ETL を実行する
   ```python
   import duckdb
   from datetime import date
   from kabusys.data.pipeline import run_daily_etl

   conn = duckdb.connect("data/kabusys.duckdb")
   result = run_daily_etl(conn, target_date=date(2026, 3, 20))
   print(result.to_dict())
   ```

   - run_daily_etl はカレンダー → 株価 → 財務 → 品質チェックの順で実行します。
   - ETLResult に各フェーズの取得/保存数と品質検査結果・エラーが格納されます。

2. ニュースセンチメント（銘柄別）をスコアリングして保存
   ```python
   import duckdb
   from datetime import date
   from kabusys.ai.news_nlp import score_news

   conn = duckdb.connect("data/kabusys.duckdb")
   written = score_news(conn, target_date=date(2026, 3, 20))  # 書き込んだ銘柄数を返す
   print("wrote", written, "ai_scores")
   ```

   - OPENAI_API_KEY を環境変数で設定するか、api_key 引数を渡してください。
   - ロット処理・リトライロジックが組み込まれています。

3. 市場レジーム判定
   ```python
   import duckdb
   from datetime import date
   from kabusys.ai.regime_detector import score_regime

   conn = duckdb.connect("data/kabusys.duckdb")
   score_regime(conn, target_date=date(2026, 3, 20))
   ```

   - ETF 1321 の MA200 乖離とマクロニュースの LLM スコアを組み合わせ、market_regime に書き込みます。

4. 監査ログ（audit）スキーマの初期化
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # これで signal_events, order_requests, executions テーブルが作成されます
   ```

5. カレンダー関連ユーティリティ
   ```python
   from kabusys.data.calendar_management import is_trading_day, next_trading_day
   import duckdb
   from datetime import date

   conn = duckdb.connect("data/kabusys.duckdb")
   print(is_trading_day(conn, date(2026,3,20)))
   print(next_trading_day(conn, date(2026,3,20)))
   ```

注意点
- research パッケージの関数（calc_momentum 等）は DB の prices_daily / raw_financials を参照しますが、実運用の発注ロジックには直接影響を与えません（本番アクションは execution 層で行う想定）。
- OpenAI 呼び出しは費用が発生します。API キーとモデル設定に注意してください。

---

## 環境変数 / 設定の挙動

- kabusys.config.Settings によりアプリ設定にアクセスできます。
  例:
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  ```
- .env 自動ロード:
  - プロジェクトルート（.git または pyproject.toml を基準）に `.env` / `.env.local` があれば自動で読み込みます（OS 環境 > .env.local > .env の順）。
  - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
- 必須設定は Settings のプロパティでチェックされ、未設定時は ValueError を投げます（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD 等）。

---

## ディレクトリ構成（主なファイル）

（src 以下を基準）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py          # ニュース NLU / LLM 呼び出し & ai_scores 書込
    - regime_detector.py   # 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py    # J-Quants API クライアント（fetch/save）
    - pipeline.py          # ETL パイプライン（run_daily_etl など）
    - etl.py               # ETLResult 再エクスポート
    - news_collector.py    # RSS ニュース収集
    - calendar_management.py # 市場カレンダー管理・営業日判定
    - audit.py             # 監査ログ（schema init / init_audit_db）
    - quality.py           # データ品質チェック
    - stats.py             # 汎用統計ユーティリティ（zscore_normalize）
  - research/
    - __init__.py
    - factor_research.py   # ファクター計算（momentum/value/volatility）
    - feature_exploration.py # forward returns / IC / summary / rank
  - ai/..., research/... の各モジュールはそれぞれテスト可能な小さな関数単位で実装されています。

---

## 開発時の注意 / テストポイント

- 外部 API 呼び出し（OpenAI / J-Quants / HTTP）はモジュール内部で分離されており、テスト時は該当関数をモック（patch）することを推奨します（例: kabusys.ai.news_nlp._call_openai_api を patch）。
- DuckDB の executemany に空リストが渡せないバージョン依存の注意点がコード中にコメントされています。テスト時は今回の実装の注意点に従ってください。
- LLM 呼び出しのレスポンスは JSON Mode を前提に設計されていますが、JSON パースエラーに備えた復元処理を入れています。
- ニュース収集では SSRF・Gzip Bomb・大容量レスポンス等を防ぐためのチェックが組み込まれています。

---

## ライセンス / 貢献

（ライセンス情報や貢献方法があればここに記載してください）

---

必要であれば、この README をベースに「運用手順」「CI」「デプロイ」「スキーマ定義（DDL 集約）」「詳細な API 参照ドキュメント」などの追加ドキュメントを作成できます。どの項目を優先したいか教えてください。