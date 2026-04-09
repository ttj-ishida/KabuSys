KabuSys
=======

日本株向けのデータ基盤・研究・AI評価・監査ログを備えた自動化支援ライブラリです。  
主に以下を提供します：

- J-Quants API からの差分ETL（株価日足・財務・市場カレンダー）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS）とニュースのNLPスコアリング（OpenAI）
- 市場レジーム判定（MA200乖離 + マクロニュースセンチメント）
- 研究用ファクター計算・特徴量探索ユーティリティ
- 監査ログ（シグナル→発注→約定トレーサビリティ）用スキーマ管理

プロジェクトの意図
-----------------
バックテストやアルゴリズム開発における「ルックアヘッドバイアス防止」「冪等性」「フェイルセーフ」を重視した設計になっています。DuckDB を中心に、ETL／品質管理／AI スコアリング／監査ログを統合的に扱えるようになっています。

主な機能一覧
-------------
- ETL（kabusys.data.pipeline）
  - run_daily_etl: 日次で市場カレンダー・株価・財務を差分取得して保存
  - 個別ジョブ: run_prices_etl / run_financials_etl / run_calendar_etl
- J-Quants クライアント（kabusys.data.jquants_client）
  - fetch / save のラッパー（401 リフレッシュ、レート制御、リトライ）
- データ品質チェック（kabusys.data.quality）
  - 欠損 / スパイク / 重複 / 日付不整合の検出と QualityIssue レポート
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得（SSRF 対策、トラッキングパラメータ除去、正規化）
- AI スコアリング（kabusys.ai）
  - score_news: 銘柄ごとのニュースセンチメントを ai_scores に保存
  - score_regime: ETF (1321) の MA200 乖離とマクロニュースを合成して market_regime を更新
- 研究ユーティリティ（kabusys.research）
  - calc_momentum, calc_value, calc_volatility（ファクター）
  - calc_forward_returns, calc_ic, factor_summary（特徴量探索・IC）
  - zscore_normalize（正規化）
- 監査ログ（kabusys.data.audit）
  - 監査スキーマ初期化 / 監査専用 DB 初期化（init_audit_schema / init_audit_db）

セットアップ手順
----------------

前提
- Python 3.10+（typing | union 型表記などを利用）
- system に duckdb ライブラリがインストールされること（pip でインストール可能）
- OpenAI API を使う場合は OpenAI API キーが必要

1. リポジトリをチェックアウト
   - 例: git clone ...

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - requirements.txt が無い場合は少なくとも次をインストールしてください:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   （プロジェクトに pyproject.toml / requirements.txt がある想定なら pip install -e . 等）

4. 環境変数設定
   - 環境変数は .env または OS 環境に設定できます。パッケージ起動時にプロジェクトルートの .env（続いて .env.local）が自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須: J-Quants リフレッシュトークン）
     - KABU_API_PASSWORD（必須: kabu ステーション API 用パスワード）
     - KABU_API_BASE_URL（省略可, デフォルト http://localhost:18080/kabusapi）
     - OPENAI_API_KEY（OpenAI を使う場合）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知等）
     - DUCKDB_PATH（DuckDB のパス, デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視用 SQLite path, default data/monitoring.db）
     - PAPER_FILL_MODE（paper trading の fill モード: instant|partial|never|reject）
     - PAPER_TRADING_SQLITE_PATH（paper trading DB path）
     - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START（監視用）
     - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT（監視閾値）
     - KABUSYS_ENV（development|paper_trading|live、デフォルト development）
     - LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）

   例 .env:
     JQUANTS_REFRESH_TOKEN=xxxxx
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development

5. データベース初期化（監査ログ）
   - 監査用 DB を作る場合:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

使い方（主要な例）
-----------------

基本的な DuckDB 接続作成例
- Python REPL やスクリプトで:
  import duckdb
  from kabusys.config import settings
  conn = duckdb.connect(str(settings.duckdb_path))

1) 日次 ETL を実行する
- run_daily_etl を使って市場カレンダー → 株価 → 財務 → 品質チェック を順に回します。
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  res = run_daily_etl(conn, target_date=date(2026,3,20))
  print(res.to_dict())

2) ニュースのスコアリング（OpenAI 必須）
- news_nlp.score_news は raw_news と news_symbols に基づき ai_scores を更新します。
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  n = score_news(conn, target_date=date(2026,3,20), api_key=None)  # api_key None → ENV を使う

3) 市場レジーム判定
- regime_detector.score_regime を使うと market_regime テーブルに当該日の判定を保存します。
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026,3,20), api_key=None)

4) 研究用ファクター計算
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date
  m = calc_momentum(conn, date(2026,3,20))
  v = calc_value(conn, date(2026,3,20))

5) 監査ログ（スキーマ適用）
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)

自動環境読み込みの挙動
- パッケージロード時にプロジェクトルート（.git または pyproject.toml を基準）から .env → .env.local の順で自動読み込みされます。
- 既に OS 環境にあるキーは .env で上書きされません（ただし .env.local は override=True で上書き可能）。
- 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 設定値は kabusys.config.settings 経由で参照できます。

注意事項 / 設計方針のポイント
--------------------------------
- ルックアヘッドバイアス防止:
  - 日付基準処理は内部で datetime.today() / date.today() を直接参照しない設計になっています（target_date を明示的に渡す）。
  - ETL や AI スコアリングは「対象日以前のデータのみ」を参照するよう配慮されています。
- 冪等性:
  - DB への保存は基本的に ON CONFLICT DO UPDATE または INSERT ... ON CONFLICT を用いて冪等に行います。
- フェイルセーフ:
  - AI API の一時エラー等はフェイルセーフ（デフォルトスコア 0 やスキップ）で継続し、例外で全処理を止めない設計です（必要箇所はログと戻り値で通知）。
- セキュリティ:
  - news_collector は SSRF 対策、XML パースの安全化（defusedxml）を行っています。
  - jquants_client はトークン自動リフレッシュ（401対応）とレート制御を内包しています。

ディレクトリ構成（主要ファイルと説明）
-------------------------------------

src/kabusys/
- __init__.py
  - パッケージのメタ情報（__version__ 等）
- config.py
  - 環境変数 / .env 読み込みと settings（設定アクセス）
- ai/
  - __init__.py
  - news_nlp.py
    - ニュースを集約して OpenAI で銘柄ごとのセンチメントを算出し ai_scores へ保存
  - regime_detector.py
    - ETF1321 の MA200 乖離 + マクロニュースセンチメントを合成し market_regime を更新
- data/
  - __init__.py
  - calendar_management.py
    - 営業日判定・next/prev/get_trading_days・calendar_update_job
  - pipeline.py
    - ETL の本体（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - etl.py
    - ETLResult の再エクスポート
  - jquants_client.py
    - J-Quants API 呼び出し・ページネーション・保存（save_*）の実装
  - news_collector.py
    - RSS フィード取得・正規化・前処理（SSRF 対策・トラッキング除去）
  - quality.py
    - データ品質チェック群（欠損・スパイク・重複・日付不整合）
  - stats.py
    - zscore_normalize 等の統計ユーティリティ
  - audit.py
    - 監査ログ用 DDL / 初期化ユーティリティ（init_audit_schema / init_audit_db）
- research/
  - __init__.py
  - factor_research.py
    - Momentum / Value / Volatility 等のファクター計算
  - feature_exploration.py
    - 将来リターン計算・IC・rank・factor_summary など

（注）この README はコードベースの抜粋に基づく概要です。実運用では pyproject.toml / requirements.txt を用意し、適切な依存関係の固定・テスト・CI を整備してください。

よくある使い方のサンプル（まとめ）
---------------------------------
- ETL を cron / Airflow / バッチで回す:
  - 日次で run_daily_etl を呼ぶ（target_date を明示）
- AI スコアリング:
  - raw_news を収集後、score_news を呼んで ai_scores を作成
  - 必要に応じて score_regime を呼んで market_regime を更新
- 研究ワークフロー:
  - ETL 後に calc_forward_returns / calc_momentum を呼んで IC 等を評価

サポート / 開発
----------------
- バグ報告・機能提案は issue を作成してください。
- 新規機能追加時はユニットテストを追加し、ルックアヘッドバイアスや冪等性の観点を必ず考慮してください。

以上。必要であれば README に載せる具体的な .env.example、コマンド例（systemd ユニット、cron、Dockerfile）や追加の使用例（ニュース収集から DB 保存までのフロー例）を追記します。どの部分を詳細化しますか？