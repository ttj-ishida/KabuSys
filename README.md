# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ（KabuSys）

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のデータ収集（J-Quants）、品質チェック、特徴量算出、ニュース NLP（OpenAI）を含む研究・実行基盤のためのモジュール群です。  
主な目的は以下です。

- J-Quants API からのデータ ETL（株価・財務・市場カレンダー）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）
- ニュースのセンチメント算出（OpenAI を用いたバッチ評価）
- 市場レジーム判定（ETF + マクロニュースを統合）
- 監査ログ（シグナル→発注→約定のトレース用スキーマ）

設計上、バックテスト等でのルックアヘッドバイアスを防止する実装思想が随所に盛り込まれています（datetime.today()/date.today() を直接参照しない、DB クエリの排他条件など）。

---

## 主な機能一覧

- data:
  - ETL パイプライン（run_daily_etl、個別 run_prices_etl/run_financials_etl/run_calendar_etl）
  - J-Quants クライアント（fetch / save 関数、レートリミット & リトライ）
  - カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - ニュース収集（RSS 収集、前処理、SSRF 対策）
  - データ品質チェック（missing, spike, duplicates, date consistency）
  - 監査ログ初期化（監査テーブル定義・init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai:
  - ニュース NLP：銘柄ごとのセンチメントスコア算出（score_news）
  - 市場レジーム判定（score_regime） — ETF(1321) の MA とマクロニュースを統合
- research:
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索（calc_forward_returns / calc_ic / factor_summary / rank）
- 設定管理:
  - .env 自動読み込み（プロジェクトルート基準、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - settings オブジェクト経由で環境変数アクセス

  

---

## セットアップ手順

前提: Python 3.10+（型注釈に union 型等を使用）。

1. リポジトリをクローンまたはプロジェクトを配置する。

2. 仮想環境を作成・有効化（推奨）。
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール（例）。
   - pip install duckdb openai defusedxml
   - （パッケージ化されている場合）pip install -e .

   メモ: 実行環境によっては追加のパッケージが必要になる可能性があります（例: requests 等）。テスト用に unittest.mock を使う設計になっています。

4. 環境変数を設定（`.env` / `.env.local` をプロジェクトルートに置くと自動読み込みされます）。
   - 必須:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API のパスワード（発注系を使う場合）
     - OPENAI_API_KEY: OpenAI API キー（ai モジュールを使う場合）
   - 任意（デフォルト値あり）:
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（監視用、デフォルト）
     - PAPER_FILL_MODE: instant|partial|never|reject（Paper Trading の稼働モード、デフォルト: instant）
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - PID_FILE_PATH / KILL_FLAG_PATH / CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
   - 自動読み込みを無効化する場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=yourpass
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

5. データベース格納先ディレクトリを作成（必要に応じて）。
   - mkdir -p data

---

## 使い方（簡易ガイド）

以下は代表的な操作の Python 例です。

- DuckDB 接続を作って日次 ETL を実行する:
  ```
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース NLP スコアを生成する（OpenAI API キーが設定されていること）:
  ```
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  n_written = score_news(conn, target_date=date(2026, 3, 20))  # 例
  print("書き込み銘柄数:", n_written)
  ```

- 市場レジームをスコアリングする:
  ```
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査用 DuckDB を初期化する:
  ```
  import duckdb
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # conn は監査テーブルが作成された DuckDB 接続
  ```

注意点:
- AI（OpenAI）呼び出しは API エラー時にフェイルセーフで 0 を返す等の挙動があります。料金・レートに注意してください。
- J-Quants API 呼び出しはレート制限（120 req/min）を遵守します。get_id_token は自動リフレッシュ対応。
- バックテスト等で使用する際は Look-ahead を防ぐ設計（関数は target_date 引数で日にちを固定）を利用してください。

---

## 主要 API（抜粋）

- kabusys.config.settings
  - settings.jquants_refresh_token, .kabu_api_password, .duckdb_path, .env, .log_level, .is_live など

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, id_token=None, ...)
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - ETLResult（処理結果の dataclass）

- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token

- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None)

- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None)

- kabusys.data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)

- kabusys.research
  - calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, rank

---

## 注意事項 / 運用に関するポイント

- 環境変数は .env / .env.local がプロジェクトルートに置かれていれば自動読み込みされます。ただしテストでは自動読み込みを無効化するため KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使えます。
- OpenAI は JSON Mode を利用する想定です。レスポンスのパースやバリデーションは厳格に行われますが、意図しないレスポンスはスキップされることがあります。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため、モジュール内で空チェックを行っています。
- ETL / API 呼び出しはネットワークエラーや 5xx に対して指数バックオフでリトライする実装です。
- Paper Trading 用の挙動（PAPER_FILL_MODE や paper_sqlite_path）が用意されています。実環境でライブ発注する際は十分なテストを行ってください。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント算出（score_news）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch / save / get_id_token）
    - pipeline.py — ETL パイプライン実装（run_daily_etl 等）
    - quality.py — データ品質チェック
    - stats.py — 統計ユーティリティ（zscore_normalize）
    - news_collector.py — RSS 収集、前処理、SSRF/セキュリティ対策
    - calendar_management.py — 市場カレンダー管理（is_trading_day など）
    - audit.py — 監査ログ（スキーマ定義・初期化）
    - etl.py — ETLResult 再エクスポート（補助）
  - research/
    - __init__.py
    - factor_research.py — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py — calc_forward_returns / calc_ic / factor_summary / rank

---

## ライセンス / 責任範囲

このリポジトリはデータ取得・処理・研究用のツール群を提供します。実際の発注・運用を行う際は自己責任でお願いします。API キーや証券会社接続情報は厳重に管理してください。ログや監査テーブルに個人情報を保存しないなど、運用ポリシーの順守を推奨します。

---

必要であれば README に含めるインストール用 requirements.txt の推奨内容や、より詳細な運用手順（cron / systemd での ETL スケジューリング、監視 alerting、バックテストでの利用注意等）も作成します。どの情報を追加しますか？