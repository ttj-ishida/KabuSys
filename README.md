README — KabuSys (日本語)
=========================

概要
----
KabuSys は日本株向けの自動売買基盤です。以下の主要機能を持ち、研究→シグナル生成→ポートフォリオ構築→発注／監視までのワークフローをサポートします。

- 発注エンジン（ExecutionEngine）：ブローカー抽象化、オーダー管理、リスク管理、起動時リコンシリエーション
- 監視（MonitoringEngine）：システム状態、注文滞留、ドローダウン等の定期チェック、kill flag 発動
- 監視永続化（MonitoringDB）：SQLite を用いたログ保存（system_status / trade_logs / positions / risk_logs / dashboard）
- ポートフォリオ構築ユーティリティ：候補抽出、等重・スコア重み付け、ポジションサイジング、セクター上限・レジーム調整
- リサーチ機能：DuckDB を用いたファクター計算（Momentum / Volatility / Value）・特徴量解析
- AI モジュール：ニュースを LLM（OpenAI）でスコアリング（ai.news_nlp）、マクロ + MA によるレジーム判定（ai.regime_detector）
- 運用ツール：Paper Trading 検証レポート生成スクリプト、Streamlit による監視ダッシュボード等

主な機能一覧
--------------
- Execution
  - Broker 抽象化（実アダプタ／Mock を切替）
  - OrderManager（作成・送信・同期）
  - RiskManager（ポジション・ドローダウン制約、レート制限）
  - Reconciler（起動時の自動リコンシリエーション）
- Monitoring
  - SystemMonitor：CPU/MEM/DISK、Execution プロセス生存、データ鮮度チェック
  - TradeMonitor：滞留注文・約定異常の検出
  - RiskMonitor：ドローダウン・ポジション数の監視とアラート記録
  - KillSwitch：条件成立で flag ファイルにより Execution 停止シグナルを送信
  - AlertManager：LINE Push による通知（クールダウン管理）
  - Streamlit ダッシュボード（read-only）
- Portfolio
  - 候補選定・重み計算・株数決定（単元丸め、aggregate cap）
- Research
  - DuckDB を用いたファクター計算・将来リターン・IC/統計サマリ
- AI
  - ニュースセンチメントスコア（OpenAI）
  - マクロセンチメント + MA による市場レジーム判定
- Tools
  - paper_verification_report：Paper Trading DB に対する検証レポート生成

セットアップ手順
----------------

1. 前提
   - Python 3.10 以上（型注釈: union 演算子 (A | B) を使用）
   - SQLite（標準）、DuckDB（Python パッケージ）、ネットワーク接続（OpenAI/LINE 利用時）

2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 最低限（例）:
     pip install duckdb psutil requests openai streamlit
   - 実際の運用に必要な追加パッケージがある場合は requirements.txt を用意して pip install -r requirements.txt

4. データディレクトリ作成
   - デフォルト DB / PID / フラグの保存先は data/ 以下です:
     mkdir -p data

5. 環境変数 (.env)
   - プロジェクトルートに .env / .env.local を置くと自動読み込みされます（既存 OS 環境 > .env.local > .env）。
   - 自動読み込みを無効にしたい場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 主要な環境変数（一部、括弧内はデフォルト）:
     - KABUSYS_ENV (development | paper_trading | live) — (default: development)
     - JQUANTS_REFRESH_TOKEN — 必須
     - KABU_API_PASSWORD — 必須
     - OPENAI_API_KEY — OpenAI を利用する場合必須
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知を使う場合
     - DUCKDB_PATH (data/kabusys.duckdb)
     - SQLITE_PATH (data/monitoring.db) — Monitoring 用 SQLite（監視は常に本番 sqlite_path を使用）
     - PAPER_TRADING_SQLITE_PATH (data/paper_trading.db) — paper_trading 用 DB（KABUSYS_ENV=paper_trading 時に使用）
     - PAPER_FILL_MODE ("instant" | "partial" | "never" | "reject") — Paper Trading の約定挙動（default: instant）
     - PID_FILE_PATH (data/execution.pid)
     - KILL_FLAG_PATH (data/kill.flag)
     - MONITOR_POLL_INTERVAL — 監視ループの秒間隔（run_monitoring で利用、デフォルト 60 秒）
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)

6. DB 初期化
   - 多くのスクリプトが起動時に init_monitoring_db() を呼ぶため、特別なマイグレーションは不要です。最初にスクリプトを起動すると必要テーブルが作成されます。

使い方
------

実行エントリ（モジュール実行）が用意されています。プロジェクトルート（src を PYTHONPATH に含むか -m で実行）で動かします。

- ExecutionEngine の起動（本番/ペーパー切替）
  - 本番（デフォルト）:
    KABUSYS_ENV=live python -m kabusys.run_execution
  - Paper Trading（MockBroker を使用し paper DB に記録）:
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 補足: 起動時にプロセス優先度を "high" に設定します。paper_trading の場合は data/paper_trading.db を使用して本番 DB と分離します。

- Monitoring のポーリングループ起動
  - デフォルト 60 秒間隔:
    python -m kabusys.run_monitoring
  - 間隔を環境変数で上書き:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 補足: Monitoring は KABUSYS_ENV に関わらず settings.sqlite_path（本番設定）を使用して監視ログを保存します。

- Streamlit ダッシュボード（監視ビュー）
  - 起動例:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは DB を read-only モードで開きます。MonitoringEngine を先に起動してデータを投入してください。

- Paper Trading 検証レポート
  - 単発レポート生成:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI モジュールの利用（プログラムから呼び出す）
  - ニューススコアリング（プログラム内）:
    from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date, api_key="sk-...")
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key="sk-...")

- その他
  - kill.flag（Settings.kill_flag_path）により ExecutionEngine に停止シグナルを送ります。KillSwitch.write は冪等で既存ファイルを上書きしません。
  - Execution 起動時は PID ファイルを data/execution.pid に書きます。SystemMonitor はこの PID を参照して process_ok を判定します。

設定の挙動（重要）
------------------
- .env 自動読み込み:
  - プロジェクトルート（.git または pyproject.toml を基準）から .env/.env.local を自動的に読み込む。
  - OS 環境変数は保護され、.env.local の override でも上書きされません（保護されたキーは書き換えない）。
  - 無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

- PAPER_FILL_MODE の有効値:
  - "instant", "partial", "never", "reject"（不正値なら起動時に ValueError）

- 監視 DB:
  - init_monitoring_db() は冪等でテーブルを作成します。既存 DB に対してマイグレーション（列追加）も行います（例: dashboard.peak_value, trade_logs.latency_ms を追加）。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py — パッケージ定義、バージョン
- config.py — Settings クラス（環境変数 / .env 処理、各種パス・設定）
- run_execution.py — ExecutionEngine 起動スクリプト（-m kabusys.run_execution）
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト（-m kabusys.run_monitoring）

サブパッケージ:
- kabusys/execution/
  - order_manager.py, order_repository.py, execution_engine.py, reconciler.py, broker_factory.py, broker_api.py, ...（発注関連）
- kabusys/monitoring/
  - monitoring_db.py — SQLite 永続化層
  - system_monitor.py, trade_monitor.py, risk_monitor.py — 各種モニター
  - monitoring_engine.py — 複数モニターの総合ポーリング
  - kill_switch.py, alert_manager.py, streamlit_dashboard.py — 補助機能
- kabusys/portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py — ポートフォリオ構築ロジック
- kabusys/research/
  - factor_research.py, feature_exploration.py — DuckDB を使ったファクター計算・解析
- kabusys/ai/
  - news_nlp.py, regime_detector.py — OpenAI を用いた NLP / レジーム判定
- kabusys/tools/
  - paper_verification_report.py — Paper Trading 検証レポート
- kabusys/utils/
  - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
- その他: data/（DB / PID / flag の保存先。実行時に生成）

開発・運用上の注意
------------------
- 本コードベースは外部 API（ブローカー・OpenAI・LINE）を扱います。API キー・パスワードは安全に管理してください。
- Paper Trading モードは本番 DB と分離されますが、設定ミスにより上書きしないよう環境変数を確認してください（SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）。
- AI モジュールは外部 API の応答に依存するため、失敗時はフェイルセーフ（スコアを 0 にする等）で動作する設計になっていますが、運用時はログと挙動を必ず確認してください。
- run_monitoring は常に settings.sqlite_path を使って監視ログを保存します（KABUSYS_ENV に依存しません）。
- process priority / CPU affinity の設定に失敗した場合は警告を出してスキップします（権限不足等）。

補足（例コマンドまとめ）
----------------------
- 仮想環境作成:
  python -m venv .venv && source .venv/bin/activate
- 必要パッケージインストール:
  pip install duckdb psutil requests openai streamlit
- Execution 起動（paper trading）:
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Monitoring 起動（30秒間隔）:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Streamlit ダッシュボード:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper verification:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス / 連絡
-----------------
（この README にライセンス情報や連絡先が必要なら追記してください）

以上。README に追加したい内容や、サンプル .env.example を作成してほしい場合は教えてください。