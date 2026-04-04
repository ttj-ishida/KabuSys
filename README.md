# KabuSys — 日本株自動売買プラットフォーム（README）

本リポジトリは日本株のデータパイプライン、リサーチ、AI を使ったニュース解析、監査ログ、及び監視／実行基盤を含む自動売買補助ライブラリ群です。DuckDB を主なデータ格納に用い、J-Quants / OpenAI / kabuステーション 等の外部 API と連携するモジュールを提供します。

---

## 主要なポイント（プロジェクト概要）
- 株価・財務・カレンダーを J-Quants から差分取得して DuckDB に保存する ETL パイプライン。
- ニュース収集（RSS）→ OpenAI による銘柄別センチメント算出 → ai_scores テーブルへ保存する NLP パイプライン。
- ETF（1321）の 200 日移動平均乖離とマクロニュースセンチメントを合成して「市場レジーム」を判定する機能。
- 監査（audit）スキーマ：戦略→シグナル→発注→約定 をトレース可能にする監査テーブルの作成・初期化。
- データ品質チェック（欠損・スパイク・重複・日付不整合等）。
- 汎用リサーチ機能（モメンタム / バリュー / ボラティリティ計算、将来リターン・IC 計算、Z スコア正規化 等）。

---

## 機能一覧
- data
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（取得 / 保存関数）
  - ニュース収集（RSS → raw_news）
  - カレンダー管理（営業日判定、next/prev/get_trading_days）
  - 品質チェック（check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks）
  - 監査ログテーブル作成・初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai
  - news_nlp.score_news: ニュースを銘柄別に LLM で評価して ai_scores に書き込む
  - regime_detector.score_regime: ETF とマクロニュースを用い市場レジームを判定して market_regime に書き込む
- research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## 要件（概要）
- Python 3.10+
- 主要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API, OpenAI, RSS フィード 等）

必要パッケージはプロジェクトの requirements.txt / pyproject.toml によって管理してください（本 README では代表的なライブラリを挙げています）。

---

## セットアップ手順

1. Python 環境準備
   - 推奨: 仮想環境を作成
     - python -m venv .venv
     - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. インストール
   - pip install -e . もしくは必要パッケージを直接インストール
     - pip install duckdb openai defusedxml

3. 環境変数 / .env の用意
   - プロジェクトルート（.git または pyproject.toml がある階層）に `.env` / `.env.local` を配置すると自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>  ← 必須（ETL）
     - OPENAI_API_KEY=<your_openai_api_key>               ← 必須（AI スコアリング）
     - KABU_API_PASSWORD=<password>                       ← kabuステーション連携用
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (通知用)
     - DUCKDB_PATH (例: data/kabusys.duckdb)
     - SQLITE_PATH (監視 DB など)
     - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START / CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
     - KABUSYS_ENV ∈ {development, paper_trading, live}（デフォルト development）
     - LOG_LEVEL ∈ {DEBUG, INFO, WARNING, ERROR, CRITICAL}（デフォルト INFO）

   - .env サンプル（例）
     ```
     JQUANTS_REFRESH_TOKEN=xxxx...
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

4. データディレクトリ作成
   - DuckDB 等のパス（例 data/）が存在しない場合は作成してください。

---

## 使い方（代表的な呼び出し例）

以下は Python REPL やスクリプトからの利用例です。

- DuckDB に接続して ETL を実行（日次 ETL）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（OpenAI API 必須）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # target_date に対して前日15:00 JST ～ 当日08:30 JST の記事を評価
  n = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {n} codes")
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査 DB 初期化（監査専用 DB を作る場合）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- 研究用ファクター計算
  ```python
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  mom = calc_momentum(conn, date(2026,3,20))
  val = calc_value(conn, date(2026,3,20))
  vol = calc_volatility(conn, date(2026,3,20))
  ```

注意:
- AI 系関数（score_news / score_regime）は OpenAI API キーが必須です（api_key 引数で注入可能、None の場合は環境変数 OPENAI_API_KEY を参照）。
- 多くの関数は lookahead bias を避けるため target_date を外部から与える設計です。内部で安易に date.today() を参照しない実装になっています（一部 ETL エントリポイントは省略時に今日を使います）。

---

## データベース初期化の注意点
- 監査スキーマの初期化: init_audit_schema / init_audit_db を利用。init_audit_db は親ディレクトリを自動作成します。
- J-Quants 保存関数（save_*）は冪等（ON CONFLICT DO UPDATE）設計です。
- DuckDB の executemany は空リスト渡し不可の箇所があるため、空リストチェックが行われています。

---

## 自動環境変数読み込み
- モジュール kabusys.config はプロジェクトルート（.git または pyproject.toml を探索）を検出し、`.env` → `.env.local` の順で読み込みます。
- 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定することで自動読み込みを無効化できます（テスト用途など）。

---

## ディレクトリ構成（主要ファイル）
（ソースは src/kabusys 以下に存在）

- src/kabusys/
  - __init__.py (パッケージ初期化、__version__)
  - config.py (環境変数・設定読み込みと Settings クラス)
  - ai/
    - __init__.py
    - news_nlp.py (ニュース → LLM センチメント → ai_scores 書込み)
    - regime_detector.py (ETF MA + マクロセンチメントを合成して market_regime 書込み)
  - data/
    - __init__.py
    - jquants_client.py (J-Quants API クライアント、取得＆DuckDB 保存)
    - pipeline.py (ETL パイプライン、run_daily_etl 等)
    - etl.py (ETLResult の再エクスポート)
    - news_collector.py (RSS 取得・前処理・raw_news 保存)
    - calendar_management.py (営業日ロジック、calendar_update_job)
    - quality.py (データ品質チェック)
    - audit.py (監査ログ DDL / 初期化)
    - stats.py (zscore_normalize 等汎用統計)
  - research/
    - __init__.py
    - factor_research.py (momentum/value/volatility 計算)
    - feature_exploration.py (forward returns / IC / summary / rank)
  - research/*（各種分析ユーティリティ）

---

## 運用上の注意 / ベストプラクティス
- 本リポジトリの AI 呼び出しは外部 API（OpenAI）に依存するため、API 使用量とレートを考慮してください。モデルは gpt-4o-mini を利用する想定です。
- J-Quants API はレート制限（120 req/min）に合わせた RateLimiter を実装済みですが、追加の運用監視を推奨します。
- ETL / AI 処理は外部 API 失敗時にフェイルセーフ（スキップや neutral 値フォールバック）するよう実装されていますが、結果の監査とログ出力を必ず確認してください。
- 本番（live）運用時は KABUSYS_ENV を `live` に設定してください。paper_trading 環境も考慮されています。

---

## 開発 / 貢献
- コードは型注釈およびロギングを重視して書かれています。ユニットテストを追加する際は、OpenAI / HTTP 呼び出し等をモックして行ってください（score_news, regime_detector などは内部の API 呼び出しを差し替え可能に設計されています）。
- .env.local は開発マシン固有の機密値や上書き設定に利用してください（`.env` より優先で読み込まれます）。

---

もし README に追加してほしい情報（例: 実際の SQL スキーマ定義の抜粋、より具体的な運用手順、CI/CD の設定例、デプロイ手順など）があれば教えてください。README を目的に合わせて拡張します。