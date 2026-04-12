KabuSys — README
=================

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした Python パッケージです。  
モジュール群は主に「取引実行（execution）」「ポートフォリオ構築（portfolio）」「因子・リサーチ（research）」「AI（ニュース NLP / レジーム判定）」「監視（monitoring）」で構成されています。  
設計方針としては、DuckDB / SQLite をデータ層に用い、外部 API（kabuステーション / J-Quants / OpenAI 等）との接続は設定に応じて切り替えられます。

主な機能
--------
- Execution
  - ブローカー抽象化を介した発注・状態管理（OrderManager, Reconciler 等）
  - Paper Trading モード（本番 DB と分離して data/paper_trading.db に記録）
  - リスク管理（RiskManager）と発注制御
- Monitoring
  - システム状態・データ鮮度監視（SystemMonitor）
  - 注文滞留・約定異常検出（TradeMonitor）
  - ドローダウン / ポジション上限監視（RiskMonitor）
  - Kill Switch（フラグファイル経由で ExecutionEngine を停止）
  - LINE による通知（AlertManager）
  - Streamlit ベースの監視ダッシュボード（streamlit_dashboard.py）
- Portfolio construction
  - 候補選定（select_candidates）
  - 重み計算（等配分・スコア重み）
  - ポジションサイズ計算（リスクベース・ユニット丸め・集約キャップ）
  - セクター制限・レジーム乗数
- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC 計測、統計サマリ
- AI（OpenAI 連携）
  - ニュース記事のセンチメントスコアリング（ai.news_nlp.score_news）
  - マクロ + MA200 による市場レジーム判定（ai.regime_detector.score_regime）
  - 両者は OpenAI（gpt-4o-mini 等）を利用（API キー必須）
- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

セットアップ
-----------
前提
- Python 3.10 以降（型注釈に対応する構文を使用）
- git, pip, virtualenv 等が使えること

手順（簡易）
1. リポジトリをクローン
   - git clone <repo_url>
   - cd <repo_root>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

4. データディレクトリ作成（任意）
   - mkdir -p data

環境変数・設定
- 自動ロード
  - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）にある .env / .env.local を自動で読み込みます。
  - OS 環境変数の優先度 > .env.local > .env
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- 主要な環境変数（Settings クラスで参照）
  - KABUSYS_ENV: 起動モード（development / paper_trading / live） — デフォルト: development
  - JQUANTS_REFRESH_TOKEN: J-Quants API（必須）
  - KABU_API_PASSWORD: kabuステーション API（必須）
  - OPENAI_API_KEY: OpenAI API（AI モジュールで必要）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH: Execution PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH: Kill flag（デフォルト: data/kill.flag）
  - PAPER_FILL_MODE: paper_trading の約定動作（instant / partial / never / reject、デフォルト: instant）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト: INFO）
  - MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト: 60。run_monitoring で上書き可能）

例: .env（簡易）
- KABUSYS_ENV=paper_trading
- OPENAI_API_KEY=sk-...
- KABU_API_PASSWORD=*****
- JQUANTS_REFRESH_TOKEN=*****

使い方
------
実行スクリプト（パッケージとして実行可能）

- ExecutionEngine を起動（本番または paper_trading）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient が使われ、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に保存されます。
  - 実行前に必要な環境変数（KABU_API_PASSWORD 等）を設定してください。
  - 実行時、プロセス優先度が High に設定されます（set_process_priority を使用）。

- Monitoring（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可（デフォルト 60 秒）。
  - 監視は常に本番用の sqlite_path を使用します（KABUSYS_ENV に依存しません）。

- Streamlit ダッシュボード（監視 UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開きます。MonitoringEngine を先に起動してください。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite パスを指定可能（デフォルトは env または data/paper_trading.db）

- AI 処理（プログラムから）
  - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key=None)  # api_key を渡すか OPENAI_API_KEY を設定
  - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=None)

- ライブラリ利用例
  - ポートフォリオ構築関数:
    - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes
  - リサーチ関数:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

注意点
- Paper Trading は本番の orders/monitoring DB と完全分離するため、PAPER_TRADING_SQLITE_PATH を適切に設定してください。
- run_execution / run_monitoring 起動時にプロセス優先度の設定を試みます。権限不足で失敗することがありますが警告に留めて処理は継続します。
- Monitoring の DB スキーマは init_monitoring_db() により自動作成・マイグレーションされます（実行スクリプト内で呼び出し済み）。
- OpenAI 連携は API の利用料金・レート制限等に注意してください。429 / 一時エラーは指数バックオフでリトライしますが、最終失敗時はフェイルセーフとしてスキップされます。
- .env のパースはシェル風のクォート・コメントにある程度対応しています。OS 環境変数は .env で保護され上書きされません（ただし .env.local は override）。

ディレクトリ構成（重要ファイルのみ）
-----------------------------------
src/
  kabusys/
    __init__.py                — パッケージ定義
    config.py                  — 環境変数 / 設定読み込み
    run_execution.py           — ExecutionEngine 起動スクリプト
    run_monitoring.py          — SystemMonitor ポーリング起動スクリプト

    execution/
      order_manager.py
      order_repository.py
      reconciler.py
      ...                      — 発注関連の実装群

    monitoring/
      monitoring_db.py         — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      kill_switch.py
      alert_manager.py
      monitoring_engine.py
      streamlit_dashboard.py

    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py

    research/
      factor_research.py
      feature_exploration.py

    ai/
      news_nlp.py               — ニュースセンチメント（OpenAI）
      regime_detector.py        — レジーム判定（MA200 + マクロセンチメント）
      __init__.py

    tools/
      paper_verification_report.py

    utils/
      process_priority.py       — プロセス優先度 / CPU affinity ユーティリティ

主なデータファイル（デフォルト）
- data/kabusys.duckdb     — DuckDB（時系列データ / raw_financials / raw_news 等）
- data/monitoring.db      — SQLite（監視ログ）
- data/paper_trading.db   — Paper Trading 用 SQLite（KABUSYS_ENV=paper_trading）
- data/execution.pid      — ExecutionEngine が作成する PID ファイル（存在でプロセス生存確認）
- data/kill.flag          — Kill Switch が作成するフラグファイル（Execution 停止要求）

開発者向けメモ
---------------
- Settings は実行時に .env / .env.local の自動読み込みを行います。テストで自動ロードを避ける場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB を読み書きするコードは接続オブジェクトを受け取る設計になっているため、テストで in-memory 接続やモックを差し替えやすくなっています。
- AI まわりの外部呼び出しは内部でラップしており、ユニットテスト時は _call_openai_api を patch して差し替え可能です。
- ロギングは各モジュールで標準 logging を使っています。デバッグには LOG_LEVEL=DEBUG を設定してください。

ライセンス・貢献
----------------
（ここにライセンス情報と貢献方法を記載してください。リポジトリに LICENSE ファイルがあればその内容を参照してください。）

問い合わせ
----------
バグ報告や機能追加リクエストは issue を立ててください。開発者向けの質問はリポジトリの README / ドキュメントを参照のうえ issue または PR をお願いします。

以上。必要であれば README に追記（セットアップ手順の詳細化、依存パッケージの確定、サンプル .env.example の挿入など）します。