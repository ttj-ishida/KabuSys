# KabuSys

日本株向けの自動売買・データ基盤ライブラリ群です。  
主にデータ取得（J-Quants）、ETL、データ品質チェック、ニュースセンチメント（LLM）、市場レジーム判定、ファクター計算、監査ログなどを含むバックエンドユーティリティを提供します。

---

## 概要

KabuSys は以下の目的で設計された内部ツール／ライブラリです。

- J-Quants API を用いた株価・財務・マーケットカレンダーの差分取得と DuckDB への冪等保存（ETL）
- ニュース収集（RSS）と LLM を用いた銘柄別センチメント評価（AI スコアリング）
- ETF を用いた市場レジーム判定（マクロニュース + MA200 乖離）
- ファクター（モメンタム・バリュー・ボラティリティ等）の計算と特徴量解析ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order → execution のトレーサビリティ）用スキーマ初期化ユーティリティ

設計上の特徴:
- Look‑ahead バイアス対策（内部で datetime.today()/date.today() を直接参照しない箇所が多数）
- DuckDB を中心とした軽量なデータストア
- OpenAI（gpt-4o-mini 想定）を用いた JSON mode ベースの堅牢な API 呼び出し（リトライ・バリデーション実装）
- 冪等性とトランザクション処理を重視した実装

---

## 機能一覧（主なモジュール）

- kabusys.config
  - 環境変数の自動ロード（`.env`, `.env.local`）、設定アクセス（settings オブジェクト）
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得・保存・認証・rate limiting）
  - pipeline / etl: 日次 ETL 実行（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - calendar_management: JPX カレンダー管理・営業日判定ユーティリティ
  - news_collector: RSS 収集・前処理（SSRF/サイズ制限/トラッキング除去等）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログ（signal / order_request / executions）スキーマ初期化・DB作成
  - stats: zscore_normalize など汎用統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: ニュースから銘柄別センチメントを生成して ai_scores に書き込む
  - regime_detector.score_regime: ETF(1321) の MA200 乖離とマクロニュース LLM スコアを合成して market_regime を生成
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- ほかユーティリティ類（ファイル内ドキュメント参照）

---

## 必要条件・依存関係

（プロジェクトで想定される最低要件）
- Python 3.10+
- 必要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続（J-Quants, OpenAI 等外部 API）

実際のインストールはプロジェクトの pyproject.toml / requirements.txt を参照してください。

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN  
  - J-Quants のリフレッシュトークン（kabusys.data.jquants_client.get_id_token で使用）
- KABU_API_PASSWORD  
  - kabuステーション API 用パスワード（設定上必要な場合）

OpenAI:
- OPENAI_API_KEY  
  - news_nlp / regime_detector が OpenAI を呼ぶ場合に必要（関数引数での注入も可能）

任意（デフォルト値あり）:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PID_FILE_PATH / KILL_FLAG_PATH / その他しきい値環境変数

オートロード無効化（テスト等）:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

note: config モジュールはプロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を自動読み込みします。

---

## セットアップ手順（例）

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo>

2. 仮想環境作成・有効化
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール
   pip install -U pip
   pip install duckdb openai defusedxml

   （開発時はプロジェクト直下で editable インストール）
   pip install -e .

4. 環境変数の準備
   プロジェクトルートに `.env`（または `.env.local`）を作成し、必要な環境変数を設定してください。例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_password
   DUCKDB_PATH=data/kabusys.duckdb
   LOG_LEVEL=INFO
   KABUSYS_ENV=development
   ```

5. DuckDB ファイル用ディレクトリ作成（必要に応じて）
   mkdir -p data

6. 監査 DB（必要時）初期化
   Python REPL またはスクリプトで:
   ```py
   import duckdb
   from kabusys.config import settings
   from kabusys.data.audit import init_audit_db

   # ファイル DB を初期化して接続を取得
   conn = init_audit_db(settings.duckdb_path)
   # 以後 conn を使って監査テーブルにアクセスできます
   ```

---

## 使い方（代表的な例）

以下はモジュール API を直接呼ぶ簡単な例です。実運用ではジョブスケジューラ（cron, systemd, Airflow 等）から呼び出したり、独自のラッパー CLI を作成して利用してください。

- DuckDB 接続作成の例:
  ```py
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行（run_daily_etl）
  ```py
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  res = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(res.to_dict())
  ```

- ニュースのスコア生成（AI）
  ```py
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OpenAI API key は環境変数 OPENAI_API_KEY か api_key 引数で渡す
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム判定
  ```py
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- カレンダー・営業日ユーティリティ
  ```py
  from datetime import date
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

- ファクター計算（研究用）
  ```py
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  records = calc_momentum(conn, target_date=date(2026,3,20))
  ```

注意:
- OpenAI 呼出しを伴う関数は API 呼出し失敗時にフェイルセーフ（スコア 0.0 または該当銘柄スキップ）する設計です。
- 各種関数は DuckDB 接続（DuckDBPyConnection）を受け取ります。スキーマ作成は別途スクリプト等で行ってください（audit.init_audit_schema などの補助関数あり）。

---

## よく使う設定・トラブルシューティング

- 自動的に `.env` を読み込む処理は config モジュールが行います。テスト時などで自動読み込みを抑止したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI のレート制限と J-Quants のレート制限（120 req/min）に注意してください。クライアント実装にはリトライ・バックオフ・スロットリングが含まれますが、運用側でも呼び出し頻度を管理してください。
- DuckDB のファイルパスに書き込み権限があるか確認してください（デフォルトは data/kabusys.duckdb）。
- news_collector は SSRF 対策・レスポンスサイズ制限等の安全対策を含んでいますが、RSS ソースの信頼性や文字コードに注意してください。
- J-Quants の認証が 401 を返す場合は内部でトークンリフレッシュを試みますが、refresh token が不正・期限切れだと get_id_token が失敗します。

---

## ディレクトリ構成（抜粋）

実際のリポジトリは src/kabusys 配下にモジュール群があります。以下は主なファイル・モジュールの一覧（現在のコードベースに基づく抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - calendar_management.py
    - news_collector.py
    - quality.py
    - stats.py
    - audit.py
    - pipeline.py (ETLResult 等)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/__init__.py
  - その他（strategy / execution / monitoring 等の名前が __all__ にあるが未掲載のファイルは実装次第追加）

各ファイル内に詳細な docstring（処理フロー・設計方針・戻り値/例外）が記載されています。API を利用する際は各モジュールの docstring を参照してください。

---

## 開発メモ

- テスト時は OpenAI / J-Quants への実際の HTTP 呼び出しをモックすることを想定しています（各モジュールで _call_openai_api や _urlopen を差し替え可能）。
- DuckDB の executemany に空リストを渡すと例外となるバージョンがあるため、空チェックを行う実装が随所にあります。
- 監査スキーマ初期化は idempotent（再実行可能）です。init_audit_db が便利です。

---

必要であれば README に以下を追加できます:
- CLI / systemd ユニット例
- 詳細なスキーマ（DDL）
- CI / テスト実行方法
- デプロイ・運用手順（監視・ログローテーション等）

要望があれば追加で記載します。