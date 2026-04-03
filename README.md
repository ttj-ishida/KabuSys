# KabuSys

日本株のデータプラットフォームと自動売買支援ライブラリ。  
DuckDB を用いたデータストア、J-Quants からの ETL、ニュースの NLP 評価（OpenAI）、市場レジーム判定、監査ログなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム／研究基盤向けのユーティリティ群です。主な目的は以下です。

- J-Quants API からの株価・財務・カレンダー等の差分 ETL
- ニュース記事収集・前処理・LLM による銘柄センチメント算出（gpt-4o-mini を利用）
- ETF とマクロニュースを組み合わせた市場レジーム判定
- ファクター計算（モメンタム・ボラティリティ・バリュー等）と特徴量解析ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）を保持する DuckDB スキーマ

設計上の特徴：
- Look-ahead bias を避ける日付扱い
- 冪等性（DB への保存は ON CONFLICT DO UPDATE 等で上書き）
- API 呼び出しはリトライ／バックオフ・レートリミッティングを実装
- OpenAI 呼び出しは JSON Mode を利用しレスポンスを検証

---

## 機能一覧

- データ収集 / ETL
  - J-Quants から日次株価（OHLCV）、財務諸表、JPX カレンダーを差分取得・保存
  - ETL の結果は ETLResult オブジェクトで返却

- データ品質管理
  - 欠損チェック、スパイク検出、重複チェック、日付整合性チェック
  - run_all_checks でまとめて実行

- ニュース NLP
  - RSS 収集、テキスト前処理、OpenAI による銘柄別センチメント評価（score_news）

- 市場レジーム判定
  - ETF（1321）の 200 日 MA 乖離と LLM マクロセンチメントを合成して日次レジーム判定（score_regime）

- 研究用ユーティリティ
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC 計算、Zスコア正規化等

- 監査ログ
  - signal_events / order_requests / executions テーブルとインデックスを初期化するユーティリティ

---

## 必須要件

- Python 3.9+
- 主要ライブラリ（例）
  - duckdb
  - openai
  - defusedxml

実際のプロジェクトでは pyproject.toml / requirements.txt に必要パッケージを明記してください。

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>
   - プロジェクトルートに `pyproject.toml` がある想定（自動 .env ロードに使用）

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （ローカル開発用）pip install -e .

4. 環境変数の設定
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
     - KABU_API_PASSWORD: kabu ステーション API パスワード（必要時）
     - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL

   - `.env` のパースはシェル形式（export KEY=val も可）、クォート・コメント等に対応しています。

5. DuckDB ファイルの準備
   - デフォルトでは data/kabusys.duckdb を使用します。ディレクトリは自動作成されますが、明示的に作る場合:
     - mkdir -p data

---

## 使い方（代表的な例）

※ 下記は簡易例です。状況に応じてエラー処理やロギングを追加してください。

- DuckDB 接続を開く（監査 DB 初期化）
  ```python
  import duckdb
  from kabusys.data.audit import init_audit_db

  # ファイル DB を作成して監査スキーマを初期化
  conn = init_audit_db("data/audit.duckdb")
  ```

- 日次 ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

  run_daily_etl は ETLResult を返します。ETL の内部でカレンダー取得→株価取得→財務取得→品質チェックの順に処理します。

- ニュースのセンチメントスコアを算出（OpenAI 必須）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env の OPENAI_API_KEY を使用
  print(f"scored {count} symbols")
  ```

- 市場レジーム判定（ETF 1321 の MA200 比 + マクロセンチメント）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY を環境変数で指定
  ```

- 研究用: モメンタム等の計算
  ```python
  from kabusys.research.factor_research import calc_momentum
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, date(2026, 3, 20))
  # records は date, code, mom_1m, mom_3m, mom_6m, ma200_dev を含む dict のリスト
  ```

- データ品質チェックを走らせる
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026, 3, 20))
  for i in issues:
      print(i)
  ```

注意:
- score_news / score_regime は OpenAI API キーを引数で渡すか、環境変数 OPENAI_API_KEY を参照します。未設定だと ValueError を送出します。
- J-Quants の API 呼び出しには JQUANTS_REFRESH_TOKEN が必要です（get_id_token を経由して id_token を取得）。

---

## 主要モジュールと API（抜粋）

- kabusys.config
  - settings: 環境変数読み出しラッパ（JQUANTS_REFRESH_TOKEN 等）

- kabusys.data
  - pipeline.run_daily_etl(conn, ...)
  - etl.ETLResult
  - jquants_client: fetch_* / save_* / get_id_token
  - news_collector.fetch_rss / preprocess_text
  - calendar_management: is_trading_day / next_trading_day / prev_trading_day / calendar_update_job
  - audit.init_audit_db / init_audit_schema
  - quality.run_all_checks

- kabusys.ai
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)

- kabusys.research
  - factor_research.calc_momentum / calc_volatility / calc_value
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank
  - data.stats.zscore_normalize

---

## ディレクトリ構成

（プロジェクトルートに `src/kabusys` 配下がある想定。抜粋）

- src/
  - kabusys/
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
      - quality.py
      - news_collector.py
      - calendar_management.py
      - stats.py
      - audit.py
      - ...（その他 ETL / client ユーティリティ）
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - research/（他ユーティリティ）
    - research/... 
    - monitoring/（監視・実行管理のためのモジュール群：README に未列挙の可能性あり）

上記は主要ファイルの抜粋です。各ファイルにはモジュール単位で docstring と設計方針が詳述されています。

---

## 開発時の注意点

- .env 自動読み込み
  - プロジェクトルートの `.env` / `.env.local` が自動で読み込まれます（優先順: OS 環境 > .env.local > .env）。
  - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利）。

- Look-ahead bias に対する配慮
  - 多くの関数は内部で `date.today()` や `datetime.today()` を参照しない設計です。バックテストでは明示的に target_date を渡してください。

- OpenAI / J-Quants の呼び出しはリトライ・バックオフ実装がありますが、API の呼び出し回数やコストには留意してください。

---

## よくある質問（簡易）

Q: OpenAI のレスポンスが想定外だった場合はどうなる？  
A: news_nlp / regime_detector ともにレスポンスパース失敗時はフェイルセーフでスコア 0 を採用するか、そのチャンクをスキップします。システム全体が例外で停止しないよう設計されています。

Q: DuckDB スキーマはどこに定義されている？  
A: 各機能モジュール（audit / pipeline / jquants_client の save_* 等）にて必要なテーブル作成ロジックを持つ想定です。audit モジュールは監査スキーマを初期化するユーティリティを提供します。

---

もし README に追記したい利用フロー（例: デプロイ手順、CI/CD、docker-compose、監視・再起動ポリシーなど）があれば教えてください。必要に応じてサンプル .env.example や便利なスクリプト例も作成します。