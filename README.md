# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（KabuSys）。  
データ取得・ETL、ニュースNLP、レジーム判定、ファクター計算、監査ログなどを含むモジュール群を提供します。

注意: このリポジトリはライブラリ/モジュール群の一部です。実際の運用時は各種 API キーや外部サービス設定が必要です。

## 概要（Project Overview）

KabuSys は日本株を対象としたデータ基盤とリサーチ／トレード補助のためのライブラリセットです。主な目的は次の通りです。

- J-Quants API からの株価・財務・カレンダー等データの差分取得と DuckDB への保存（ETL）
- RSS ニュース収集と OpenAI を用いた銘柄別／マクロセンチメント評価（ニュースNLP）
- ETF（1321）200日MA とマクロセンチメントを組み合わせた市場レジーム判定
- ファクター計算（モメンタム・バリュー・ボラティリティ等）およびリサーチ支援ユーティリティ
- 監査ログ（signal → order → execution をトレースする監査テーブル）の初期化
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計方針として、ルックアヘッドバイアスの回避、冪等性、API リトライ/スロットリング、フェイルセーフを重視しています。

## 主な機能一覧（Features）

- data/
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch_* / save_*）とレート制御・トークン自動リフレッシュ
  - 市場カレンダー管理（営業日判定、next/prev trading day）
  - ニュース収集（RSS -> raw_news、URL 正規化、SSRF 対策）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ定義・初期化（signal_events / order_requests / executions）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - ニュース NLP（銘柄別センチメント score_news）
  - マクロと MA を組み合わせた市場レジーム判定（score_regime）
  - OpenAI 呼び出しに対するリトライ・パース耐性の実装
- research/
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索（forward returns / IC / summary / rank）
- config
  - .env 自動読み込み（プロジェクトルート検出）と Settings オブジェクト
  - 必須環境変数取得（_require）・環境モード判定（development / paper_trading / live）

## セットアップ手順（Setup）

前提:
- Python 3.10 以上（Union 型記法や | 演算子を使用）
- DuckDB, openai, defusedxml 等のライブラリが必要

1. リポジトリをクローンし、開発用仮想環境を作成・有効化します。

   ```
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

2. 必要パッケージをインストールします（プロジェクトに requirements.txt がある場合はそちらを利用してください）。最低限必要なライブラリ例:

   ```
   pip install duckdb openai defusedxml
   ```

   実運用ではさらに HTTP クライアント、Slack クライアント等が必要になる場合があります。

3. パッケージの開発インストール（任意）:

   ```
   pip install -e .
   ```

4. 環境変数の設定:
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 例（.env）:

     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_station_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（モジュールの使用範囲に応じて OPENAI_API_KEY も必要）

## 使い方（Usage）

以下はライブラリ API を直接利用する例です。実行前に適切に環境変数を設定してください。

- DuckDB 接続を準備して ETL を実行する

  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP（銘柄別センチメント）を実行する

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY は環境変数に設定するか、api_key パラメータを渡す
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("ai_scores written:", n_written)
  ```

- 市場レジーム判定を実行する

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DuckDB を初期化する

  ```python
  from kabusys.data.audit import init_audit_db

  conn_audit = init_audit_db("data/audit_duck.db")
  # 必要に応じて conn_audit を使って order/request/execution を挿入
  ```

- 市場カレンダー更新ジョブ（夜間バッチ）を実行する

  ```python
  from kabusys.data.calendar_management import calendar_update_job
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  saved = calendar_update_job(conn, lookahead_days=90)
  print("saved calendar records:", saved)
  ```

注意点:
- OpenAI API 呼び出しを含む機能（news_nlp, regime_detector）は OPENAI_API_KEY を環境変数に設定するか、各関数の api_key 引数で渡す必要があります。
- J-Quants 呼び出しは JQUANTS_REFRESH_TOKEN に依存します。
- ETL は DuckDB 上に期待するスキーマ（raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, prices_daily など）が存在することを前提とします。プロジェクトのスキーマ初期化コード（data.schema 等）が別ファイルに用意されている場合はそれを利用してください。

## 設定（Config・.env の自動読み込み）

- config.Settings を通して設定値へアクセスできます。

  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)
  ```

- .env 自動読み込み:
  - プロジェクトルート（.git または pyproject.toml を探索）から `.env` → `.env.local` の順で読み込みます。
  - OS 環境変数が優先され、.env.local は .env を上書きします（ただし OS の環境変数は上書きされません）。
  - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

## ディレクトリ構成（Directory structure）

主要モジュール一覧（src/kabusys）:

- kabusys/__init__.py
  - パッケージのバージョンと公開モジュール一覧
- kabusys/config.py
  - 環境変数と Settings オブジェクト
- kabusys/ai/
  - __init__.py（score_news をエクスポート）
  - news_nlp.py（銘柄別ニュースセンチメント -> ai_scores）
  - regime_detector.py（1321 MA + マクロセンチメント -> market_regime）
- kabusys/data/
  - __init__.py
  - calendar_management.py（市場カレンダー、営業日判定、calendar_update_job）
  - etl.py（ETL 結果クラスのエクスポート）
  - pipeline.py（run_daily_etl 等 ETL パイプライン）
  - stats.py（zscore_normalize 等）
  - quality.py（データ品質チェック）
  - audit.py（監査ログテーブル定義・初期化）
  - jquants_client.py（J-Quants API クライアント、fetch/save 実装、レート制御）
  - news_collector.py（RSS フィード取得、前処理、SSRF 対策等）
- kabusys/research/
  - __init__.py（research ヘルパーの再エクスポート）
  - factor_research.py（calc_momentum, calc_value, calc_volatility）
  - feature_exploration.py（calc_forward_returns, calc_ic, factor_summary, rank）
- その他: テスト用・ドキュメント・スクリプト等はプロジェクトルートに配置される想定

（実際のリポジトリでは追加のモジュールや CLI スクリプトが含まれる可能性があります）

## 開発メモ / 実運用上の注意

- ルックアヘッドバイアス対策:
  - 各モジュールは date や target_date を明示的に受け取り、内部で現在時刻を参照しない方針です。バッチやバックテスト時は target_date を正しく指定してください。
- 冪等性:
  - J-Quants 保存関数やニュース保存は ON CONFLICT / INSERT DO UPDATE / DO NOTHING により冪等化されています。
- リトライ・スロットリング:
  - J-Quants クライアントは 120 req/min の制限に合わせたスロットリングとエクスポネンシャルバックオフを実装しています。
  - OpenAI 呼び出しも 429/ネットワーク/5xx を対象にリトライロジックがあります。
- セキュリティ:
  - news_collector は URL 正規化とトラッキング除去、SSRF 対策、受信サイズ制限、defusedxml の使用などを含みます。
- ロギングと監視:
  - 各モジュールは logger を用いた詳細なログ出力を行います。運用時は LOG_LEVEL を調整してください。
- テスト時:
  - self-contained なユニットテストでは外部 API 呼び出しをモックすること（例: kabusys.ai.news_nlp._call_openai_api 等）を推奨します。
  - 自動 .env ロードを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定。

---

この README はコードベース（src/kabusys 以下）の概要と利用例をまとめたものです。実運用・デプロイ時はプロジェクトの上位ドキュメント（README、運用手順書、StrategyModel.md、DataPlatform.md 等）を参照してください。必要であればサンプル .env.example やスキーマ初期化スクリプトの追加も作成できます。