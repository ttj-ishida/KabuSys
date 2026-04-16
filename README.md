KabuSys — 日本株自動売買システム
================================

このリポジトリは、日本株の自動売買・検証・監視を目的としたモジュール群です。戦略・ポートフォリオ構築、発注エンジン、監視・アラート、Research/AI ツール（ニュースセンチメントやレジーム判定）などを含みます。

主な特徴
--------
- ExecutionEngine（発注エンジン）と Monitoring（監視）を分離して実行可能
- Paper Trading モード（実口座と完全分離された SQLite DB を使用）
- DuckDB を用いたファクター／リサーチ用の高速集計処理
- OpenAI（gpt-4o-mini）を利用したニュースセンチメント / レジーム判定（任意）
- Streamlit による監視ダッシュボード表示
- 監視ログ（system_status / trade_logs / risk_logs / positions / dashboard）を SQLite に永続化
- ポートフォリオ構築（候補抽出・重み計算・ポジションサイズ算出・セクター制限など）は純粋関数で実装（DB 参照なし）

機能一覧
--------
- 実行（Execution）
  - ブローカークライアント（実口座 / モック）を切り替え可能（KABUSYS_ENV）
  - OrderManager / OrderRepository / Reconciler による発注・状態同期
  - リスク管理（RiskManager, RiskConfig）
- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/ディスク/プロセス/データ鮮度を監視し system_status に記録
  - TradeMonitor: 注文滞留／約定異常を検出して risk_logs に記録
  - RiskMonitor: ドローダウン・ポジション上限をチェックし dashboard を更新、必要なら kill.flag を書き込む
  - AlertManager: LINE Messaging API による通知（クールダウン機能付き）
  - MonitoringEngine: 各モニタを束ねてポーリング実行
  - Streamlit ダッシュボードで監視情報を可視化
- Research / AI
  - factor_research: Momentum / Volatility / Value ファクター計算（DuckDB）
  - feature_exploration: 将来リターン、IC、統計サマリーなど
  - ai.news_nlp: raw_news を LLM でセンチメント評価し ai_scores に書き込み（OpenAI 必須）
  - ai.regime_detector: ma200 + マクロニュースセンチメントを混合して市場レジーム判定
- ユーティリティ
  - process_priority: プロセス優先度・CPU affinity 設定（psutil 使用）
  - tools.paper_verification_report: Paper Trading の検証レポート生成（コマンドライン）

セットアップ手順
----------------
前提
- Python 3.10+
- system パッケージ（SQLite は標準で利用可）
- 推奨: 仮想環境（venv / poetry / pipenv 等）

依存パッケージ（例）
- duckdb
- psutil
- requests
- openai
- streamlit

インストール例（pip）
1. 仮想環境を作成・有効化:
   python -m venv .venv
   source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール（プロジェクトに requirements.txt がない場合は手動で）
   pip install duckdb psutil requests openai streamlit

環境変数 / .env
- プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- 主な環境変数:
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - OPENAI_API_KEY（AI 機能を使うなら必須）
  - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（AlertManager 用）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
  - SQLITE_PATH（monitoring 用 DB、デフォルト: data/monitoring.db）
  - DUCKDB_PATH（DuckDB ファイル、デフォルト: data/kabusys.duckdb）
  - PAPER_FILL_MODE: instant | partial | never | reject（paper 用振る舞い）
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔（秒）、デフォルト 60）
  - PID_FILE_PATH / KILL_FLAG_PATH 等（デフォルト data 以下）

使い方（主な実行コマンド）
------------------------

1) 監視プロセス起動
- 監視ループを起動（SystemMonitor を定期実行して monitoring.db に記録）
  python -m kabusys.run_monitoring
- 環境変数でポーリング間隔を上書き:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 監視は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用します。
- 停止: data/stop_requested.flag を作成するとループは終了します。

2) 実行（ExecutionEngine）起動
- 実口座 / Paper Trading を切り替えて起動:
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  KABUSYS_ENV=live python -m kabusys.run_execution
- Paper Trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます（本番 DB と完全分離）。
- 停止: data/stop_requested.flag を作成するか、data/kill.flag が作成された時に実行エンジンは停止されます。実行時の PID は data/execution.pid に保存されます。

3) Paper Trading 検証レポート
- コマンドライン:
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- オプション --db で DB パスを指定可能。環境変数 PAPER_TRADING_SQLITE_PATH でも指定できます。

4) Streamlit 監視ダッシュボード
- 起動:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- read-only モードで SQLite を開き、Overview / Positions / Orders / System タブを表示します。

5) AI モジュール（ニューススコア / レジーム判定）
- OpenAI API キーが必要（OPENAI_API_KEY）。
- モジュール関数を呼ぶ例（Python REPL / スクリプト内）:
  from kabusys.ai.news_nlp import score_news
  count = score_news(duckdb_conn, target_date, api_key="sk-...")

  from kabusys.ai.regime_detector import score_regime
  score_regime(duckdb_conn, target_date, api_key="sk-...")

注意点:
- API 失敗時は多くの部分でフェイルセーフ（スコア=0 やログ出力）で継続する実装になっていますが、API キー未設定時は ValueError を投げる関数もあります。
- OpenAI 呼び出しはレート制限 / リトライを組み込んでいますが、課金・レートに注意してください。

設定（Settings モジュール）
-------------------------
- kabusys.config.Settings により環境変数から設定を取得します。
- .env / .env.local はプロジェクトルート（.git または pyproject.toml のある場所）を基準に自動読み込み。
- 自動読み込みを無効にするには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- Settings で取得される主な設定:
  - jquants_refresh_token, kabu_api_password
  - kabu_api_base_url
  - line_channel_access_token, line_user_id
  - duckdb_path, sqlite_path, paper_sqlite_path
  - paper_fill_mode（instant|partial|never|reject）
  - pid_file_path, kill_flag_path, kill_flag_clear_on_start
  - cpu_threshold_pct, memory_threshold_pct, disk_threshold_pct
  - env, log_level, is_live/is_paper/is_dev

運用関連ファイル / フラグ
------------------------
- data/monitoring.db              — 監視ログ SQLite（デフォルト）
- data/paper_trading.db           — Paper Trading 用 SQLite（paper_trading 時）
- data/kabusys.duckdb             — DuckDB ファイル（リサーチ用）
- data/execution.pid              — 実行エンジンの PID（run_execution が書き込む）
- data/stop_requested.flag        — 起動中の run_monitoring/run_execution に停止を要求するフラグ
- data/kill.flag                  — KillSwitch が書き込む停止フラグ（ExecutionEngine に対する停止要求）
- kill.flag は KillSwitch によって書き込まれ、ExecutionEngine 起動時に Settings.kill_flag_clear_on_start が有効ならクリアされます。

ディレクトリ構成（主要ファイルのみ）
-----------------------------------
src/
  kabusys/
    __init__.py
    config.py                      -- 環境変数 / Settings
    run_monitoring.py              -- SystemMonitor ポーリングループ起動スクリプト
    run_execution.py               -- ExecutionEngine 起動スクリプト
    tools/
      paper_verification_report.py -- Paper Trading 検証レポート CLI
    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
    monitoring/
      monitoring_db.py
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      kill_switch.py
      alert_manager.py
      monitoring_engine.py
      streamlit_dashboard.py
    execution/
      order_manager.py
      reconciler.py
      ... (OrderRepository / broker_factory 等の実装)
    research/
      factor_research.py
      feature_exploration.py
    ai/
      news_nlp.py
      regime_detector.py
    utils/
      process_priority.py

設計上の注意・補足
-----------------
- Monitoring の DB スキーマは init_monitoring_db() で冪等に作成／マイグレーションされます。
- ポートフォリオ関連関数は純粋関数として設計され、ユニットテストが容易です（DB 参照なし）。
- process_priority の適用は psutil が必要で、プラットフォーム権限により失敗する場合があります（警告でスキップ）。
- AI 関連処理は LLM 出力のバリデーションを厳格に行い、部分失敗時でも既存データを消さないようにしています（例: ai_scores の DELETE/INSERT は対象コードのみ）。

トラブルシューティング
---------------------
- DuckDB / SQLite ファイルが見つからないエラー:
  - パスを確認（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）。
  - streamlit は読み取り専用で開いているため DB が存在しないとエラーになります。
- OpenAI 呼び出しで失敗が多い場合:
  - API キー, ネットワーク, レート上限を確認してください。ログにリトライ情報が残ります。
- プロセス優先度や CPU affinity 設定に失敗する場合は権限不足（非 root）または未サポート OS の可能性があります。ログに警告が出力されます。

ライセンス・貢献
----------------
プロジェクトのライセンスや貢献方法はリポジトリのルートに LICENSE / CONTRIBUTING.md を置くことを推奨します（本コードベースには含まれていません）。

以上。必要であれば、README に含める具体的なサンプル .env.example、requirements.txt、簡易起動スクリプト（systemd ユニットや supervisor 用）などのテンプレートも作成します。どれを優先しますか？