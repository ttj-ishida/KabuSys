KabuSys — 日本株自動売買システム
=================================

このリポジトリは日本株向けの自動売買フレームワークです。  
戦略・ポートフォリオ構築、Execution（発注エンジン）、監視（Monitoring）、AI（ニュースNLP / レジーム判定）、および Research（ファクター計算）等のコンポーネントを含みます。設計方針として「本番/ペーパートレードの分離」「ルックアヘッドバイアス回避」「外部 API 呼び出しのフェイルセーフ化」を重視しています。

主な特徴
--------
- ExecutionEngine（発注エンジン）と OrderManager による状態管理とリコンシリエーション（再起動後の自動復旧）。
- Paper Trading モード（KABUSYS_ENV=paper_trading）では MockBrokerClient を使い本番 DB と分離（data/paper_trading.db）。
- Monitoring（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager）による常時監視と自動停止処理（フラグファイル方式）。
- Monitoring 用 SQLite（デフォルト data/monitoring.db）と分析用 DuckDB（data/kabusys.duckdb）を併用。
- ニュースを LLM（OpenAI）でスコアリングするニュースNLP（ai.news_nlp）と、ETF + マクロニュースを用いた市場レジーム判定（ai.regime_detector）。
- Research（ファクター計算、IC 計測、特徴量探索）および Portfolio 構築モジュール（銘柄選定・重み付け・ポジションサイズ計算・セクターキャップ適用）。
- Streamlit ダッシュボードで監視データの可視化（src/kabusys/monitoring/streamlit_dashboard.py）。
- 一連のツール（例: Paper Trading 検証レポート生成スクリプト）。

セットアップ手順
----------------
前提:
- Python 3.9+（ソースは型ヒントに Python 3.9+ 機能を使用）
- SQLite（標準ライブラリに同梱）、DuckDB（Python パッケージ）、psutil、requests、openai、streamlit 等

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール
   - pip install duckdb psutil requests openai streamlit

   ※プロジェクトに requirements.txt があれば pip install -r requirements.txt を使用してください。

3. 環境変数の準備
   プロジェクトルートに .env または .env.local を置くことで自動的に読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化します）。

   代表的な環境変数（必要に応じて設定してください）:
   - JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須な箇所で使用）
   - KABU_API_PASSWORD — kabuステーション API パスワード
   - KABU_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
   - OPENAI_API_KEY — OpenAI API キー（ai モジュールで使用）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — AlertManager（LINE）用
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
   - KABUSYS_ENV — 起動環境（development | paper_trading | live）（デフォルト development）
   - LOG_LEVEL — ログレベル（DEBUG | INFO | ...）
   - MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）
   - PID_FILE_PATH / KILL_FLAG_PATH / PID/flag ファイルに関する設定
   - PAPER_FILL_MODE — Paper Trading の fill 動作（instant | partial | never | reject）

   例 (.env):
   ```
   KABUSYS_ENV=development
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

4. データディレクトリの準備
   - デフォルトでは data/ 以下を使用します。必要に応じて作成してください:
     - mkdir -p data

5. DB 初期化
   実行スクリプト（run_monitoring/run_execution）が起動時に必要なテーブルを作成します（init_monitoring_db が冪等に実行されます）。手動で初期化する必要は通常ありません。

使い方
------
- 監視デーモンを起動（Monitoring）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書きできます（例: MONITOR_POLL_INTERVAL=30）。
  - 監視は本番の sqlite_path を常に参照します（KABUSYS_ENV の値に依らず）。

- ExecutionEngine（発注エンジン）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し data/paper_trading.db に記録して本番 DB と分離します。
  - 起動時に data/stop_requested.flag が存在する場合は起動を行いません。停止は kill.flag（KillSwitch）や stop_requested.flag によって行います。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH に指定がない場合の DB パス上書き）
  - 例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用で SQLite を開くため、MonitoringEngine が稼働してデータが入っていることを前提とします。

- AI / Research / Portfolio の利用（プログラム的）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key="...") — DuckDB 接続と日付を渡して実行
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key="...")
  - ファクター計算:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
    - 各関数に DuckDB 接続と target_date を渡して計算します。
  - ポートフォリオ構築:
    - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier

運用時の注意
-------------
- Execution と Monitoring は PID / flag ファイルにより相互監視・停止を行います:
  - data/execution.pid — ExecutionEngine の PID（存在しない場合は process_ok=False とみなされます）
  - data/kill.flag — KillSwitch が書き込む停止理由（存在する場合は ExecutionEngine 停止対象）
  - data/stop_requested.flag — run_* スクリプトが監視している停止フラグ（存在するとループを終了）
- Monitoring は監視ログ（system_status / risk_logs / trade_logs / positions / dashboard）を SQLite に永続化します。init_monitoring_db() でテーブルとマイグレーション処理を行います。
- OpenAI や外部 API 呼び出しはリトライやフェイルセーフの仕組みを持っていますが、API キーやレート制限、コストには留意してください。
- Paper Trading モードでは本番注文を出しませんが、ロジックやリスク評価は同様に動作します。

主なスクリプトとエントリポイント
------------------------------
- python -m kabusys.run_monitoring
  - SystemMonitor のポーリングループを起動。MONITOR_POLL_INTERVAL で間隔制御。
- python -m kabusys.run_execution
  - ExecutionEngine を起動（KABUSYS_ENV により paper_trading を選択可）。
- streamlit run src/kabusys/monitoring/streamlit_dashboard.py
  - 監視ダッシュボード表示。
- python -m kabusys.tools.paper_verification_report
  - Paper Trading 検証レポート生成。

設定ファイルの自動読み込み
-------------------------
- src/kabusys/config.py はプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して .env / .env.local を自動でロードします（OS 環境変数を上書きしない仕組み）。
- 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py
- run_monitoring.py            — Monitoring ポーリングループ起動スクリプト
- run_execution.py             — ExecutionEngine 起動スクリプト
- data/                        — （別モジュール）データパイプライン / stats 等（DuckDB 用）
- execution/
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - execution_engine.py (主要ロジックは省略)
  - broker_factory.py (Mock/実ブローカー選択)
  - ...
- monitoring/
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - monitoring_engine.py
  - streamlit_dashboard.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- ai/
  - news_nlp.py
  - regime_detector.py
- tools/
  - paper_verification_report.py
- utils/
  - process_priority.py
  - ...

（上記は主要ファイルを抜粋した構成です。実際のコードベースには他のモジュールや詳細実装が含まれます。）

開発・デバッグのヒント
---------------------
- ログ出力は各モジュールで標準 logging を使用しています。LOG_LEVEL を設定して冗長さを調整してください。
- Monitoring の DB スキーマは init_monitoring_db() にまとまっています。スキーマ変更時はマイグレーション処理を追加してください（いくつかのカラム追加は既にマイグレーションを行います）。
- OpenAI など外部 API 呼び出しはユニットテストで _call_openai_api をモックする設計になっています（テスト容易性を考慮）。

ライセンス・貢献
----------------
この README ではライセンスやコントリビューション手順は含めていません。Git リポジトリ内の LICENSE / CONTRIBUTING ファイルを参照してください（無い場合は運用チームに確認してください）。

最後に
------
この README はコードベースの主要点をまとめた簡易ガイドです。詳細な設計意図やアルゴリズムの背景（PortfolioConstruction.md / StrategyModel.md 等の設計ドキュメント）がリポジトリ内にある場合、それらも参照してください。質問や追記したい点があれば教えてください。