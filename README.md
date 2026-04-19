README
======

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤のコードベースです。本リポジトリは以下の機能群を含みます。

- 発注実行エンジン（ExecutionEngine）の起動スクリプト
- 監視（Monitoring）コンポーネント（システム状態、注文・リスク監視、Kill Switch）
- ポートフォリオ構築（銘柄選定、重み付け、ポジションサイズ計算）
- リサーチ（ファクター計算、特徴量探索）
- AI を使ったニュースセンチメント / レジーム検知モジュール（OpenAI 経由）
- 運用・検証用ツール（ペーパー取引の検証レポート等）
- 環境設定ウィザード (.env 作成) と設定検証ユーティリティ

主な設計方針：
- 本番 / ペーパートレードを分離（KABUSYS_ENV による切り替え）
- DuckDB を分析用データベース、SQLite を監視 / 発注ログ用に利用
- .env による環境変数管理（.env は絶対にコミットしないこと）

機能一覧
--------
- 環境設定ウィザード（kabusys.config_setup）: 対話式で .env を生成・更新
- 設定検証 CLI（kabusys.validate_config）: .env / config/*.yaml 等の事前チェック
- Execution 起動スクリプト（kabusys.run_execution）:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し data/paper_trading.db を使用
  - プロセス優先度設定 / PID 管理 / 停止フラグ検出
- Monitoring 起動スクリプト（kabusys.run_monitoring）:
  - SystemMonitor を定期ポーリング（デフォルト 60 秒、MONITOR_POLL_INTERVAL で上書き可）
  - 監視ログは SQLite（monitoring.db）に永続化
- 監視エンジン（MonitoringEngine）:
  - SystemMonitor / TradeMonitor / RiskMonitor を束ね、AlertManager と KillSwitch により通知・停止指示
- 監視永続化層（monitoring_db）: system_status / trade_logs / positions / risk_logs / dashboard 等のテーブルを管理
- ポートフォリオ構築（kabusys.portfolio）:
  - 銘柄選定 / 等重配分・スコア加重 / ポジションサイズ計算 / セクター制限など純粋関数群
- リサーチ（kabusys.research）:
  - モメンタム、バリュー、ボラティリティなどのファクター計算、将来リターン、IC、統計サマリ
  - DuckDB を入力に SQL+Python で実行
- AI モジュール（kabusys.ai）:
  - news_nlp: OpenAI によりニュースを銘柄ごとにスコア化して ai_scores に書き込む
  - regime_detector: ETF MA とマクロニュースの LLM センチメントを合成して market_regime を作成
- 運用ツール:
  - tools.paper_verification_report: ペーパー取引 DB を対象に検証レポートを生成

前提 / 要件
-----------
- Python 3.9+（コードは型注釈を使用）
- 必要ライブラリ（代表例）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config/*.yaml の検証を行う場合に任意）
- SQLite（Python 標準ライブラリの sqlite3 を使用）
- ネットワークアクセス（kabuステーション API / OpenAI を利用する場合）

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

4. 環境変数 (.env) の作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - 生成された .env を編集して必要な値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）を設定してください。
   - .env は機密情報を含むため Git にコミットしないでください。

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告を FAIL として扱います:
     - python -m kabusys.validate_config --strict

6. DB 初期化
   - run_execution / run_monitoring 実行時に必要なテーブル（監視用テーブル等）は自動的に作成されます。
   - DuckDB / SQLite のデフォルトパス:
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - ペーパートレード SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading 時に使用）

使い方（起動例）
----------------
- ExecutionEngine（発注エンジン）を起動:
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite に記録（本番 DB と分離）
    - 起動時に data/stop_requested.flag が存在すると起動せず終了
    - 実行中に stop flag を検出するとエンジンに停止命令を送り終了します
    - PID ファイル: data/execution.pid（設定で変更可）

- Monitoring を起動:
  - python -m kabusys.run_monitoring
  - オプション:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - 注意:
    - Monitoring は Settings にかかわらず本番 sqlite_path を使用して監視ログを書き込みます
    - 停止フラグ: data/stop_requested.flag を検出すると監視ループを停止

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で別ファイルを指定可能、環境変数 PAPER_TRADING_SQLITE_PATH でも指定できます

AI 機能の利用（ニュース NLU / レジーム検知）
---------------------------------------
- OPENAI_API_KEY を環境変数に設定する必要があります（または各関数に api_key 引数を渡す）。
- news_nlp.score_news / regime_detector.score_regime は OpenAI API を呼び出します。API エラー時のフォールバック策やリトライが組み込まれていますが、API キーは必須です。

主要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
  - paper_trading: MockBrokerClient を使用し発注はペーパートレード DB に記録
  - live: 本番モード（実際に発注）
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード用 SQLite、デフォルト data/paper_trading.db）
- OPENAI_API_KEY（AI 機能利用時に必要）
- LOG_LEVEL（デフォルト INFO）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔（秒）上書き）
- KILL_FLAG_PATH（kill.flag のパス、デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリア: "1" で有効）

停止・Kill Switch
-----------------
- KillSwitch は risk_monitor 等の判定で data/kill.flag を書き込み、ExecutionEngine に停止指示を与えます。
- 明示的停止は data/stop_requested.flag を作成する方法で行われます（運用スクリプトや手動でファイルを作成）。
- Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動削除します（本番では 0 を推奨）。

ログ
----
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一されています。
- デフォルトログディレクトリ: logs/
- 各アプリ（execution, monitoring など）は logs/<app_name>.log に日次ローテーションで出力され、コンソール（stdout）にも出ます。

ディレクトリ構成（主なファイル）
------------------------------
src/
  kabusys/
    __init__.py
    config.py                 — 環境変数 / Settings
    config_setup.py           — .env 対話式ウィザード
    validate_config.py        — 設定検証 CLI
    run_execution.py          — ExecutionEngine 起動スクリプト
    run_monitoring.py         — SystemMonitor 起動スクリプト
    utils/
      logging_setup.py        — ログ設定ユーティリティ
      process_priority.py     — プロセス優先度 / CPU affinity 設定
    monitoring/
      monitoring_db.py        — 監視用 SQLite テーブル管理（init / CRUD）
      system_monitor.py       — システム状態 / データ鮮度監視
      risk_monitor.py         — ドローダウン・ポジション上限監視
      trade_monitor.py        — 注文滞留・約定異常チェック（ファイル内に実装あり）
      kill_switch.py          — kill.flag 管理
      monitoring_engine.py    — 各 Monitor を束ねるエンジン
      alert_manager.py        — （アラート送信ロジックを含む想定）
    execution/                 — 発注関連モジュール群（BrokerFactory 等）
    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
    research/
      factor_research.py
      feature_exploration.py
    ai/
      news_nlp.py              — ニュースセンチメント (OpenAI)
      regime_detector.py       — 市場レジーム判定 (OpenAI)
    tools/
      paper_verification_report.py
    data/                      — デフォルトの DB / flag / pid ファイル（実行時に作成される）
      (例) monitoring.db, paper_trading.db, kabusys.duckdb, kill.flag, stop_requested.flag, execution.pid

補足 / 運用上の注意
-------------------
- .env は機密情報を含むため絶対に VCS にコミットしないでください（config_setup にも注意書きあり）。
- KABUSYS_ENV によって発注先や DB が変わるため、環境値の切り替えには慎重に。
- run_monitoring は MONITOR_POLL_INTERVAL を環境変数で調整できます。0 以下や無効な値は無視され、デフォルト 60 秒にフォールバックします。
- AI 機能は外部 API を利用するため、API コスト・レート制限・レイテンシに注意してください。OpenAI 呼び出しはリトライ・バックオフロジックを持ちます。
- 本番（live）環境では KILL_FLAG_CLEAR_ON_START を 0 にし、LINE 通知（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を設定することを推奨します。

ライセンス
----------
このリポジトリには明示的なライセンスファイルが含まれていません。利用・配布の際は作成者に確認してください。

以上で README の概要です。必要であれば、起動時のより詳細な手順（systemd サービス定義例、コンテナ化手順、CI 設定）や各モジュールの API ドキュメントを追補できます。どの追加情報が必要か教えてください。