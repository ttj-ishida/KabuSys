# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースNLP（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（発注〜約定トレーサビリティ）などの機能を提供します。

---

## 主な概要

- データ取得: J-Quants API から株価（OHLCV）、財務、マーケットカレンダー等を差分取得して DuckDB に保存
- ETL パイプライン: 差分取得 / 保存 / 品質チェックを行う日次 ETL（run_daily_etl）
- データ品質: 欠損・スパイク・重複・日付整合性チェック
- ニュース処理: RSS 収集 → raw_news 保存、OpenAI による銘柄別センチメント（score_news）
- 市場レジーム判定: ETF（1321）の MA とマクロニュースの LLM センチメントを合成（score_regime）
- リサーチ: モメンタム / ボラティリティ / バリュー等のファクター計算、将来リターン・IC 計算、Zスコア正規化
- 監査ログ: signal → order_request → execution を辿れる監査 DB 初期化ユーティリティ

---

## 機能一覧

- kabusys.config
  - .env / .env.local の自動読み込み（プロジェクトルート検出）と Settings API
- kabusys.data
  - jquants_client: API 呼び出し、ページネーション、リトライ、レート制御、DuckDB への冪等保存
  - pipeline: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - quality: 各種データ品質チェック（欠損、スパイク、重複、日付不整合）
  - calendar_management: 営業日判定・次営業日取得・カレンダー更新ジョブ
  - news_collector: RSS の堅牢な取得・前処理・raw_news への保存ロジック
  - audit: 監査ログテーブルの DDL 初期化、監査用 DB 作成ユーティリティ
  - stats: zscore_normalize 等の統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI で評価して ai_scores に書き込む
  - regime_detector.score_regime: ETF MA と LLM によるマクロセンチメントを合成して market_regime に保存
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## 必要条件

- Python 3.10+（型ヒントに union 型や標準ライブラリの利用があるため推奨）
- 必要なパッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続（J-Quants / OpenAI / RSS）

パッケージ化・実行環境では pyproject.toml 等で依存管理してください（ここでは最低限を記載）。

---

## インストール（開発環境）

例:

1. 仮想環境の作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Linux/macOS) または .venv\Scripts\activate (Windows)

2. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

3. パッケージを editable install（開発用）
   - pip install -e .

（プロジェクトに pyproject.toml / setup.cfg がある想定で editable install が可能です）

---

## 環境変数 / 設定

settings（kabusys.config.Settings）で参照される主な環境変数:

必須:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD     : kabuステーション API のパスワード（発注連携がある場合）
- SLACK_BOT_TOKEN       : Slack 通知用ボットトークン（通知機能を使う場合）
- SLACK_CHANNEL_ID      : Slack チャンネル ID

任意 / デフォルトあり:
- KABUSYS_ENV           : development / paper_trading / live（デフォルト: development）
- LOG_LEVEL             : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL     : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : SQLite パス（監視用途など）
- OPENAI_API_KEY        : OpenAI API キー（news_nlp / regime_detector 実行時に参照）

.env 自動読み込み:
- パッケージはプロジェクトルート（.git または pyproject.toml を探索）から .env → .env.local の順に読み込みます。
- OS 環境変数が優先されます。
- 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ（例）

1. .env を作成（プロジェクトルート）
   - JQUANTS_REFRESH_TOKEN=...
   - OPENAI_API_KEY=...
   - SLACK_BOT_TOKEN=...
   - SLACK_CHANNEL_ID=...
   - DUCKDB_PATH=data/kabusys.duckdb

2. DuckDB の初期化（監査用 DB を作る例）
   ```python
   import duckdb
   from kabusys.config import settings
   from kabusys.data.audit import init_audit_db

   conn = init_audit_db(settings.duckdb_path)  # ファイルと親ディレクトリを自動作成
   ```

3. （ETL 用）一般的には run_daily_etl を起動するために DuckDB 接続を作る:
   ```python
   import duckdb
   from kabusys.config import settings
   from kabusys.data.pipeline import run_daily_etl
   from datetime import date

   conn = duckdb.connect(str(settings.duckdb_path))
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```

---

## 使い方（代表的な API）

- 日次 ETL 実行
  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  res = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(res.to_dict())
  ```

- ニュースセンチメントのスコアリング（OpenAI 必須）
  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.ai import score_news  # kabusys.ai.__init__ でエクスポート済み

  conn = duckdb.connect(str(settings.duckdb_path))
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key を渡すか OPENAI_API_KEY を環境変数に
  print("written:", n_written)
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  status = score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  print("status:", status)
  ```

- リサーチ API（ファクター算出など）
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from kabusys.data.stats import zscore_normalize

  conn = duckdb.connect(str(settings.duckdb_path))
  date0 = date(2026, 3, 20)
  mom = calc_momentum(conn, date0)
  vol = calc_volatility(conn, date0)
  val = calc_value(conn, date0)

  normalized = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
  ```

- 品質チェック
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues:
      print(i.check_name, i.severity, i.detail)
  ```

注意:
- OpenAI を使う関数は API キー（OPENAI_API_KEY）を必須とするか、関数引数で api_key を与える必要があります。
- run_daily_etl は内部で calendar_etl → prices_etl → financials_etl → 品質チェック の順に実行します。各ステップは個別に例外処理され、1ステップ失敗でも他は継続する設計です。

---

## ディレクトリ構成

主要ファイル・モジュールの一覧（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                # .env 読み込みと Settings
  - ai/
    - __init__.py
    - news_nlp.py            # ニュースセンチメント（score_news）
    - regime_detector.py     # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント（取得・保存）
    - pipeline.py            # ETL パイプライン（run_daily_etl 等）
    - etl.py                 # ETLResult のエクスポート
    - quality.py             # データ品質チェック
    - calendar_management.py # マーケットカレンダー管理・判定ロジック
    - news_collector.py      # RSS 収集・前処理
    - audit.py               # 監査ログ DDL / 初期化
    - stats.py               # zscore_normalize 等
  - research/
    - __init__.py
    - factor_research.py     # calc_momentum / calc_value / calc_volatility
    - feature_exploration.py # calc_forward_returns / calc_ic / factor_summary / rank
  - research (補助モジュール)
  - その他: strategy / execution / monitoring（パッケージ公開用メンバーとして __all__ に含めるが、今回抜粋コードでは上記が中心）

---

## 注意事項 / ベストプラクティス

- Look-ahead バイアス対策:
  - 多くの関数（ETL / AI モジュール / リサーチ）は内部で date.today() に依存しないよう設計されています。必ず target_date を明示して利用してください。
- 機密情報:
  - API キー・トークンは .env に保存する際はアクセス制御・シークレット管理を検討してください。
- テスト:
  - OpenAI 呼出しやネットワーク依存箇所はモック可能な設計になっています（内部の _call_openai_api 等を patch することでテスト可能）。
- レート制御・リトライ:
  - J-Quants クライアントはレート制限とリトライを持ちますが、運用時は API 利用制限の上位ポリシーに従ってください。
- DuckDB の互換性:
  - 一部コードでは DuckDB バージョンに依存する操作（executemany の空パラメータ等）に注意しています。実運用では DuckDB の推奨バージョンで動作確認してください。

---

もし README に追加したい例（CI 実行方法、cron ジョブ例、docker-compose、SQL スキーマ定義全文、.env.example サンプル等）があれば指定してください。それに合わせて追記します。