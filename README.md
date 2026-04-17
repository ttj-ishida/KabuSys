# KabuSys — README

概要
- KabuSys は日本株向けの自動売買・調査・監視ライブラリ群です。本リポジトリは発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築ロジック、リサーチ/ファクター計算、AI（ニュース NLP / レジーム検出）を含みます。
- コードは純粋関数（ポートフォリオ計算等）と、SQLite / DuckDB を使った永続化・集計、外部 API（kabuステーション、J-Quants、OpenAI）との連携部で構成されています。

主な機能
- Execution
  - 発注管理（OrderManager）、リコンサイル（Reconciler）、リスク管理（RiskManager）による注文ライフサイクル制御
  - 本番（live）と Paper Trading（paper_trading）モードの分離（paper_trading は専用 SQLite を使用）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、プロセス生存、データ鮮度を記録・監視
  - TradeMonitor: 注文滞留、約定価格異常の検出
  - RiskMonitor: ドローダウン、ポジション上限の監視とリスクログ記録
  - KillSwitch / AlertManager: 条件に応じた停止フラグの書き込みと LINE 通知
  - Streamlit ダッシュボード（監視情報の可視化）
- Portfolio construction
  - 候補選定、等金額/スコア加重、ポジションサイズ計算、セクターキャップ、レジーム乗数
- Research
  - ファクター計算（モメンタム、バリュー、ボラティリティ）、将来リターン計算、IC（Information Coefficient）算出、統計サマリー
- AI
  - ニュースを OpenAI（gpt-4o-mini）でセンチメントスコア化して ai_scores に保存
  - マクロニュース + ETF MA200 による市場レジーム判定
- ツール
  - paper_verification_report: Paper Trading の検証レポート出力（稼働率、注文成功率、レイテンシ等）

要件（推奨）
- Python 3.10+
- 主な Python ライブラリ（抜粋）:
  - duckdb, psutil, requests, openai, streamlit
  - sqlite3（標準モジュール）
- 実行環境は OS によってプロセス優先度設定挙動が異なります（Linux / macOS / Windows に対応）。

セットアップ手順（開発用・起動前）
1. 仮想環境・依存関係
   - 仮想環境を作成・有効化して依存パッケージをインストールしてください。requirements.txt は無い想定なので最低限:
     - pip install duckdb psutil requests openai streamlit
2. プロジェクトルート
   - .git または pyproject.toml があるディレクトリをプロジェクトルートとして自動検出します（config モジュール）。
3. 環境変数 / .env
   - 必須:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - AI 機能を使う場合:
     - OPENAI_API_KEY
   - オプション:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE: instant / partial / never / reject（デフォルト: instant）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（AlertManager 用）
     - LOG_LEVEL（INFO 等）
     - MONITOR_POLL_INTERVAL（監視ポーリング秒、デフォルト: 60）
   - .env の自動読み込み:
     - プロジェクトルートの .env を自動で読み込みます（.env.local は上書き）。
     - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

使い方（主要スクリプト）
- 監視ループ（Monitoring）
  - 実行:
    - python -m kabusys.run_monitoring
  - 注意:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト 60）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path (Settings.sqlite_path) を使用します。
    - 停止: プロジェクトルート/data/stop_requested.flag を作成するとループが次回に検知して停止します。
- 発注エンジン（ExecutionEngine）
  - 実行:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - 特記事項:
    - paper_trading モードでは MockBrokerClient を使用し、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ完全に分離して記録します。
    - 起動時に data/stop_requested.flag が存在すれば起動しません。
    - 実行中に停止するには data/stop_requested.flag を作成します。実行中の PID は data/execution.pid（デフォルト）に記録されます。
- Paper Trading 検証レポート
  - 実行:
    - python -m kabusys.tools.paper_verification_report
    - オプション:
      - --from YYYY-MM-DD
      - --to YYYY-MM-DD
      - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数で代替可）
  - 出力: 稼働率・注文成功率・送信率・レイテンシ等をレポートして PASS/FAIL 判定を行います。
- Streamlit ダッシュボード（監視）
  - 実行:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 説明: read-only で SQLite を開き、Overview / Positions / Orders / System を表示します。
- AI 機能（プログラム呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - ai_scores テーブルへニュースセンチメントを書き込みます。OPENAI_API_KEY 要。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - market_regime テーブルへレジーム判定を永続化します。OPENAI_API_KEY 要。

停止 / キルフラグ等
- stop_requested.flag: data/stop_requested.flag を作成すると run_monitoring / run_execution のループが停止します（監視スクリプトは存在をチェック）。
- kill.flag: KillSwitch が条件を検出すると data/kill.flag に理由を書き込み、ExecutionEngine に停止を指示できます（Settings.kill_flag_path でパス変更可）。
- PID ファイル: data/execution.pid（既定）。SystemMonitor は PID の Stale 検出機能を持ち、存在するがプロセスが無ければ削除してアラートを記録します。

設定の注意
- Settings クラス（kabusys.config）を通じて環境変数を参照します。未設定の必須キーはエラーになります。
- PAPER_FILL_MODE は instant/partial/never/reject のいずれかである必要があります。
- KABUSYS_ENV は development / paper_trading / live のいずれかである必要があります。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py — 環境変数・.env 読み込み、Settings
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト（paper_trading 用分離ロジック含む）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - ai/
    - news_nlp.py — ニュースを LLM でスコアリングして ai_scores に書き込む
    - regime_detector.py — MA200 + マクロニュースでレジーム判定
    - __init__.py
  - monitoring/
    - monitoring_db.py — SQLite テーブル初期化・CRUD ラッパー（MonitoringDB）
    - system_monitor.py — システム状態・データ鮮度チェック
    - trade_monitor.py — 注文滞留・約定異常チェック
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - monitoring_engine.py — 各 Monitor を束ねる Engine
    - kill_switch.py — kill.flag 書き込みユーティリティ
    - alert_manager.py — LINE Push API 通知、クールダウン管理
    - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
    - __init__.py
  - execution/
    - reconciler.py — 起動時の注文・ポジション突合
    - order_manager.py — 発注 API の高レベル操作
    - order_repository.py, order_record.py, その他（発注関連）
  - portfolio/
    - portfolio_builder.py — 候補選定、重み算出
    - position_sizing.py — 株数計算、丸め、集約キャップ
    - risk_adjustment.py — セクターキャップ、レジーム乗数
    - __init__.py
  - research/
    - factor_research.py — momentum/value/volatility 計算
    - feature_exploration.py — 将来リターン、IC、統計サマリー
    - __init__.py
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ラッパー
    - __init__.py
  - monitoring, ai, portfolio, research の各モジュール群（前述）
- データ関連（実行時に使用／生成）
  - data/monitoring.db（デフォルト SQLite）
  - data/paper_trading.db（paper_trading用）
  - data/kabusys.duckdb（DuckDB ファイル）
  - data/stop_requested.flag, data/kill.flag, data/execution.pid

開発上のヒント
- .env / .env.local で設定を管理。自動ロードを止めたいテスト等では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- MonitoringDB.init_monitoring_db を起動前に呼ぶことでテーブルと最小限のマイグレーション（カラム追加）を保証します。
- AI 系処理は API 呼び出しに依存するため、テストでは _call_openai_api をモックする設計になっています。
- Streamlit ダッシュボードは monitoring DB を read-only URI で開いています。監視実行前に DB が作成されている必要があります。

免責・注意事項
- 本リポジトリは自動売買ロジックを含みます。実運用時は各種リスク（API 仕様、注文挙動、資金管理、障害時の取り扱い）を十分に検証してください。
- Paper Trading と Live は DB を分離していますが、設定ミスにより誤った DB に接続しないよう .env を慎重に管理してください。

以上。必要であれば README に載せる例の .env テンプレートや systemd / supervisor 用の起動ユニット例、requirements.txt の候補を追加して作成できます。必要であれば教えてください。