# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）。  
ETL（J-Quants からのデータ取得・保存）、ニュース収集・NLP スコアリング、研究用ファクター計算、監査ログスキーマなどを提供します。

主な設計方針の要点:
- DuckDB を中心としたローカルデータプラットフォーム
- J-Quants / OpenAI 等の外部 API を利用（API キーは環境変数で管理）
- ルックアヘッドバイアスを避ける設計（内部で date.today() を直接参照しない等）
- フェイルセーフ（API 失敗時に例外を投げず継続する箇所あり）
- 冪等性（DB 書き込みは ON CONFLICT / トランザクションで整備）

---

## 機能一覧

- data（データ基盤）
  - J-Quants API クライアント（fetch / save）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - カレンダー管理（営業日判定、next/prev trading day、calendar_update_job）
  - ニュース収集（RSS → raw_news 保存、SSRF 対策、前処理）
  - データ品質チェック（欠損、重複、スパイク、日付不整合）
  - 監査ログ（signal / order_request / executions テーブル定義と初期化）
  - 監査 DB 初期化ユーティリティ（init_audit_db, init_audit_schema）

- ai（AI / NLP）
  - ニュースごとのセンチメントスコアリング（score_news）
  - 市場レジーム判定（score_regime：ETF 1321 の MA200 乖離とマクロニュースを合成）

- research（研究用）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算・IC 計算・統計サマリー等

- utils / config
  - 環境変数管理（.env 自動ロード、Settings クラスで型付きアクセス）
  - 汎用統計ユーティリティ（zscore_normalize）

---

## セットアップ手順

前提: Python 3.10 以上推奨（ソースでの型アノテーションに依存）

1. リポジトリをクローン
   - 例: git clone <repo-url>

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - 必要最低限のライブラリ:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml
   - （プロジェクトに pyproject.toml/requirements.txt があればそれに従ってください）
   - 開発中にパッケージとして使う場合:
     - pip install -e .

4. 環境変数（.env）を準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（起動時に読み込み）。  
   - 自動読み込みを無効化する場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
     - OPENAI_API_KEY=<your_openai_api_key>  （score_news / score_regime で使用）
     - KABU_API_PASSWORD=<kabu_station_password>  （kabu API 関連）
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=INFO
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag

   - settings で参照可能なキーは `kabusys.config.Settings` のプロパティを参照してください。

---

## 使い方（主要な例）

以下はライブラリを Python スクリプトや REPL から利用する際の簡単な例です。

- DuckDB 接続の準備
  - from kabusys.config import settings
    import duckdb
    conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する（J-Quants トークンは settings.jquants_refresh_token を使用）
  - from datetime import date
    from kabusys.data.pipeline import run_daily_etl
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- 単体の株価 ETL（差分）
  - from kabusys.data.pipeline import run_prices_etl
    fetched, saved = run_prices_etl(conn, target_date=date(2026,3,20))
    print(fetched, saved)

- ニューススコアリング（OpenAI API キーを引数で渡すことも可）
  - from kabusys.ai.news_nlp import score_news
    from datetime import date
    n_written = score_news(conn, target_date=date(2026,3,20))
    print("written:", n_written)

- 市場レジーム評価（regime）
  - from kabusys.ai.regime_detector import score_regime
    from datetime import date
    score_regime(conn, target_date=date(2026,3,20))

- 監査 DB の初期化（監査専用 DB を作る）
  - from kabusys.data.audit import init_audit_db
    conn_audit = init_audit_db("data/audit.duckdb")
    # これで signal_events / order_requests / executions 等が作成される

- 研究用ファクター計算
  - from kabusys.research.factor_research import calc_momentum
    from datetime import date
    momentum = calc_momentum(conn, target_date=date(2026,3,20))
    # momentum は dict のリスト（各銘柄のファクター）

注意:
- score_news / score_regime は OpenAI API に呼び出しを行います。API キーが未設定の場合は ValueError を送出します。
- ETL や save_* 関数は DuckDB のスキーマ（raw_prices, raw_financials, market_calendar 等）に依存します。スキーマ作成やマイグレーションはプロジェクトの別スクリプト／初期化手順に従ってください。

---

## 環境変数と設定の挙動（補足）

- `.env` 自動読み込みのルール
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に `.env` と `.env.local` を読み込みます。
  - 読み込み順序（優先度低 → 高）: OS 環境変数 > .env > .env.local（.env.local が上書き）
  - テストや手動制御のため、`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動読み込みを無効化します。

- Settings（kabusys.config.settings）
  - settings.jquants_refresh_token 等のプロパティで必要な環境変数を型付きで取得できます。
  - KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれかで、ログレベルや動作モードの切り替えに使用できます。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py
    - .env 自動読み込み、Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースセンチメント（score_news）
    - regime_detector.py  — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント / save_* 関数
    - pipeline.py         — ETL パイプライン（run_daily_etl 等）
    - etl.py              — ETLResult 再エクスポート
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - news_collector.py   — RSS ニュース収集（fetch_rss 等）
    - quality.py          — データ品質チェック
    - stats.py            — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py            — 監査ログスキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py      — ファクター計算（momentum / value / volatility）
    - feature_exploration.py  — 将来リターン・IC・summary 等
  - research/*.py
  - その他: strategy, execution, monitoring（パッケージ公開用に __all__ を定義）

各モジュールは docstring に設計方針や処理フロー、フェイルセーフの挙動を明記していますので、詳細実装や仕様は各ファイルの先頭コメントを参照してください。

---

## 注意事項 / 運用上のヒント

- OpenAI / J-Quants 等の外部 API 呼び出しはレートリミット・課金に注意してください。score_news などはバッチ処理のためバッチサイズやリトライの設定を確認して運用してください。
- ETL と研究用途は分離して利用すること（研究モジュールは本番発注などを行いません）。
- DuckDB ファイルはバックアップを取り、運用 DB の位置（DUCKDB_PATH）に注意してください。
- 監査ログ（audit）を有効にするとシグナル→発注→約定のトレースが可能になります。運用時は必ず監査テーブルを初期化してください。

---

必要であれば、README にサンプルの .env.example、より詳細なスキーマ定義や CLI（実行スクリプト）利用方法、CI を含めた展開手順を追加できます。どの部分を優先して詳述しましょうか？