# KabuSys

日本株自動売買／データプラットフォーム（KabuSys）

KabuSys は日本株のデータ収集（ETL）・品質チェック・特徴量生成・AI によるニュース解析・市場レジーム判定・監査ログのためのユーティリティ群を提供する Python パッケージです。本リポジトリは主に以下用途を想定しています：データパイプラインの運用、リサーチ（ファクター計算、特徴量探索）、AI を用いたニュースセンチメント評価、及びトレーディング監査ログ基盤。

バージョン: 0.1.0

---

## 主な機能

- 環境設定管理
  - .env / .env.local を自動読み込み（必要に応じて無効化可能）
  - 必須環境変数チェック

- Data（ETL / DataPlatform）
  - J-Quants API クライアント（ページネーション、トークン自動更新、レート制御、リトライ）
  - 日次 ETL（株価日足 / 財務 / 市場カレンダー）
  - マーケットカレンダー管理（営業日判定、next/prev trading day 等）
  - ニュース収集（RSS、SSRF 対策、正規化、前処理）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログ／トレーサビリティ（signal → order_request → execution の追跡）
  - DuckDB への保存ユーティリティ

- AI
  - ニュース NLP（OpenAI を用いた銘柄別センチメント評価、JSON モード利用）
  - 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM センチメントの合成）

- Research
  - ファクター計算（モメンタム / ボラティリティ / バリュー 等）
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計サマリー
  - 汎用統計ユーティリティ（Zスコア正規化）

- ユーティリティ
  - DuckDB 用スキーマ初期化（監査ログ用）
  - 安全な RSS 取得、URL 正規化、記事 ID 生成
  - OpenAI / J-Quants 呼び出しに対する堅牢なリトライ・バックオフ

---

## セットアップ手順

前提:
- Python 3.9+ を推奨（ソースは typing の型注釈、標準ライブラリ機能に依存）
- DuckDB を利用（ローカルファイルまたは :memory:）

1. リポジトリをクローン / checkout
   - 例: git clone <repo-url>

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (macOS / Linux)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - 必要に応じて他のユーティリティも追加（例: pytest 等）

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを利用してください）

4. 環境変数を設定
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を作成してください。
   - 自動読み込み順序: OS環境 > .env.local > .env
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   主要な環境変数（少なくとも以下は設定が必要な箇所があります）:
   - JQUANTS_REFRESH_TOKEN : J-Quants 用リフレッシュトークン（ETL 実行に必要）
   - KABU_API_PASSWORD : kabu ステーション API パスワード（発注等で使用）
   - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID : 通知用（監視向け）
   - OPENAI_API_KEY : OpenAI 呼び出し（news_nlp / regime_detector）に必要

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=CXXXXXX
   ```

5. データベースの準備
   - デフォルトの DuckDB パスは data/kabusys.duckdb（Settings.duckdb_path）
   - 監査ログ専用 DB を初期化する例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - ETL 用の DuckDB 接続:
     ```python
     import duckdb
     from kabusys.config import settings
     conn = duckdb.connect(str(settings.duckdb_path))
     ```

---

## 使い方（主要なサンプル）

以下は簡単な利用例です。各 API は例外処理やログを行いますが、実運用ではログ設定やエラーハンドリングを適切に行ってください。

- 日次 ETL を実行する（株価・財務・カレンダーの差分取得、品質チェック）
  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())
  ```

- ニュースセンチメントスコアを生成する
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # OPENAI_API_KEY は環境変数か api_key 引数で渡す
  written = score_news(conn, target_date=date(2026,3,20), api_key=None)
  print("wrote", written, "scores")
  ```

- 市場レジームスコアを判定する
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))
  ```

- 研究用ファクター計算の例
  ```python
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  mom = calc_momentum(conn, date(2026,3,20))
  val = calc_value(conn, date(2026,3,20))
  vol = calc_volatility(conn, date(2026,3,20))
  ```

- 監査スキーマ初期化（既存接続にテーブルを追加）
  ```python
  from kabusys.data.audit import init_audit_schema
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

---

## 環境変数と設定の動作

- 自動ロード順:
  - OS 環境変数
  - プロジェクトルートの .env.local（存在する場合、.env の設定を上書き可能）
  - プロジェクトルートの .env（デフォルト）
- 自動ロードを無効化:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- プロジェクトルートは本モジュールのファイル位置から上に .git または pyproject.toml があるディレクトリとして探索します。見つからない場合は自動 .env ロードをスキップします。
- 必須の値（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN など）が未設定だと Settings のプロパティアクセスで ValueError を投げます。

---

## ディレクトリ構成（主要ファイルの概要）

（パッケージベース: src/kabusys/ 以下）

- __init__.py
  - パッケージメタ情報（__version__）と主要サブパッケージの公開配列

- config.py
  - 環境変数の自動読み込み・保護、Settings クラス（各種設定プロパティ）

- ai/
  - __init__.py: score_news の公開
  - news_nlp.py: ニュース記事を銘柄ごとに集約して OpenAI でスコアを取得し ai_scores に保存するロジック
  - regime_detector.py: ETF 1321 の MA とマクロニュース LLM を合成して market_regime テーブルに書き込む

- data/
  - __init__.py
  - jquants_client.py: J-Quants API からの取得・DuckDB への保存（fetch_* / save_*）
  - pipeline.py: run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl と ETLResult クラス
  - etl.py: ETLResult の再エクスポート
  - news_collector.py: RSS 取得・前処理・raw_news への保存ロジック（SSRF 対策・サイズ制限等）
  - calendar_management.py: market_calendar の管理、営業日判定やカレンダー更新ジョブ
  - quality.py: データ品質チェック（欠損、スパイク、重複、日付整合性）
  - stats.py: zscore_normalize 等の統計ユーティリティ
  - audit.py: 監査ログ用スキーマ（signal_events, order_requests, executions）の初期化ユーティリティ

- research/
  - __init__.py
  - factor_research.py: calc_momentum, calc_value, calc_volatility
  - feature_exploration.py: calc_forward_returns, calc_ic, factor_summary, rank

---

## 注意事項 / 運用上のポイント

- Look-ahead bias（未来情報の漏洩）防止設計:
  - 各処理は明示的に target_date を受け取り、内部で datetime.today() 等に依存しない設計になっています。
  - DB クエリは target_date 未満／以前の条件で取得するなど配慮されています。

- OpenAI API 呼び出し:
  - gpt-4o-mini を想定して JSON Mode を利用する実装です。API失敗時はフェイルセーフ（0.0 にフォールバック）する箇所があり、過度に例外を投げない設計になっています。
  - テスト容易性のため内部の _call_openai_api をモックする想定です。

- J-Quants API:
  - レート制限（120 req/min）に合わせた RateLimiter 実装、401 のトークン自動更新、ページネーション対応、リトライロジックあり。

- DuckDB のバージョン差異:
  - DuckDB の executemany の挙動や型バインドの違いを考慮した実装が散見されます。運用時は利用する DuckDB バージョンでの動作確認を行ってください。

---

必要であれば、README にサンプル .env.example、requirements.txt の推奨内容、運用フロー（cron / Airflow での ETL スケジュール例）、およびより詳細な API リファレンスを追加できます。どの項目を優先して追記しますか？