KabuSys — 日本株自動売買システム (README)
====================================

概要
----
KabuSys は日本株向けの自動売買システムのコアライブラリ群です。  
主な目的は「戦略の計算・銘柄選定」「ポジションサイズ計算」「発注管理（ExecutionEngine）」「システム監視（Monitoring）」「Research / ファクター計算」「AI を使ったニュース解析（OpenAI）」などの機能を提供することです。  
設計方針として、DB（DuckDB / SQLite）経由でデータを扱い、実行スクリプトは環境変数で挙動を切り替えられるようになっています。

主な機能一覧
--------------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番 / ペーパートレードを環境変数で切替可能（KABUSYS_ENV）
  - Paper trading は専用 SQLite（data/paper_trading.db）へ記録し、本番 DB と分離
- Monitoring（監視）
  - SystemMonitor / TradeMonitor / RiskMonitor の統合（MonitoringEngine）
  - kill.flag による ExecutionEngine 停止（KillSwitch）
  - 監視ログ永続化（SQLite, monitoring_db）
- ポートフォリオ構築モジュール（kabusys.portfolio）
  - 候補選定・重み計算・セクター制限・ポジションサイズ計算（等金額・スコア重み・リスクベース）
- Research（kabusys.research）
  - ファクター計算（Momentum, Volatility, Value）
  - 将来リターン・IC 計算・統計サマリー等
- AI モジュール（kabusys.ai）
  - ニュース NLP による銘柄別センチメントスコアリング（OpenAI）
  - 市場レジーム判定（regime_detector） — MA + マクロニュースセンチメントの合成
- ツール
  - 設定ウィザード（config_setup.py）: 対話的に .env を生成
  - 設定チェック CLI（validate_config.py）
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）
- ユーティリティ
  - ログ設定ユーティリティ（utils.logging_setup）
  - プロセス優先度 / CPU affinity 設定（utils.process_priority）
  - 設定読み込み（config.py）: .env / .env.local の自動ロードと Settings API

セットアップ手順
----------------

1. リポジトリをクローン
   - git clone ... （適宜）

2. Python 環境
   - 推奨: Python 3.10+（コードベースは型ヒントに modern syntax を使用）
   - 仮想環境の作成・有効化:
     - python -m venv .venv
     - source .venv/bin/activate (Linux/macOS) または .venv\Scripts\activate (Windows)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - オプション: PyYAML を入れると validate_config が YAML ファイルのパース検証を行えます
     - pip install pyyaml

   （プロジェクトに requirements.txt があればそれを使ってください）

4. 環境変数 (.env) の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
     - ウィザードが .env を生成します（既存 .env があれば読み込んで更新できます）
   - もしくは .env.example を参照して手動作成してください
   - 重要な環境変数（抜粋）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - OPENAI_API_KEY (AI 機能を使う場合)
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）
   - 注意: .env は Git にコミットしないでください。

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

6. データディレクトリ等
   - デフォルトの DB / PID / フラグファイル は project_root/data 下に配置されます（存在しない場合自動作成されることが多いです）
   - ログはデフォルト logs/ に出力されます

使い方（起動例）
----------------

- ExecutionEngine（発注エンジン）を起動:
  - 本番/ペーパートレードは KABUSYS_ENV で切り替え
  - python -m kabusys.run_execution
  - Paper trading の場合は Settings.is_paper=True になり、専用の SQLite（PAPER_TRADING_SQLITE_PATH）・ MockBrokerClient を使用

- Monitoring を起動（デフォルトは監視間隔 60 秒）:
  - MONITOR_POLL_INTERVAL 環境変数で間隔（秒）を上書き可能
    - 例: export MONITOR_POLL_INTERVAL=30
  - python -m kabusys.run_monitoring
  - 監視は常に本番用 sqlite_path を参照（環境にかかわらず）

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db でデータベースパスを直接指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- 設定ウィザード:
  - python -m kabusys.config_setup

- 設定検証 CLI:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

ライブラリ API の例
-------------------
（簡単な import / 呼び出し例）

- ポートフォリオモジュール:
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes

- Research ファクター計算（DuckDB 接続を渡す）:
  - import duckdb
  - from kabusys.research import calc_momentum, calc_volatility, calc_value
  - conn = duckdb.connect("data/kabusys.duckdb")
  - res = calc_momentum(conn, date(2026, 4, 1))

- AI ニューススコア（OpenAI API キーが必要）:
  - from kabusys.ai import score_news
  - conn = duckdb.connect("data/kabusys.duckdb")
  - n_written = score_news(conn, date(2026, 4, 1), api_key="sk-...")

- Monitoring DB 操作用クラス:
  - from kabusys.monitoring.monitoring_db import MonitoringDB
  - m = MonitoringDB(sqlite_conn)
  - m.log_system_status(...)

重要な挙動メモ
----------------
- ペーパートレードは本番 DB と完全分離する設計（paper_trading 用 sqlite path を使用）
- run_monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用して監視します
- 停止・強制停止制御:
  - 停止フラグ: project_root/data/stop_requested.flag を置くと run_monitoring / run_execution のループが終了します
  - Kill Switch: kill.flag を生成すると ExecutionEngine に停止シグナルを送ります（ファイルベースの簡易キルスイッチ）
  - PID ファイル: data/execution.pid 等を使用してプロセス管理
- MONITOR_POLL_INTERVAL（秒）で監視間隔を調整可能。無効値はデフォルト 60 秒にフォールバックする仕様
- OpenAI を使う機能は API のエラー・レート制限に対してリトライやフェイルセーフ実装あり（ただし API キーは必須）

ディレクトリ構成
-----------------
（主要ファイル・サブパッケージの概要）

- src/kabusys/
  - __init__.py — パッケージ定義、__version__
  - config.py — Settings クラス（環境変数/.env の読み込みとアクセス）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前に設定検証を行う CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

  - ai/
    - news_nlp.py — ニュースを OpenAI でスコアリングするロジック
    - regime_detector.py — 市場レジーム判定（MA + LLM）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 発注株数決定ロジック
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — Momentum/Volatility/Value 等のファクター計算
    - feature_exploration.py — 将来リターン/IC/統計サマリ
  - monitoring/
    - monitoring_db.py — SQLite 監視 DB スキーマ / 永続化 API
    - system_monitor.py — システム状態 / データ鮮度監視
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag の管理
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - execution/ (発注関連コンポーネント: broker_factory, execution_engine, order_manager 等)
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定

ログ・DB・データファイル位置（デフォルト）
-----------------------------------------
- logs/ — ログファイル（app_name ごとに日次ローテート）
- data/kabusys.duckdb — DuckDB（デフォルト）
- data/monitoring.db — 監視用 SQLite（デフォルト）
- data/paper_trading.db — ペーパートレード用 SQLite（デフォルト）
- data/execution.pid — ExecutionEngine の PID（設定により上書き可能）
- data/kill.flag — Kill Switch フラグ（手動/自動で作成される）
- data/stop_requested.flag — run_* スクリプトの停止トリガーファイル

運用上の注意
-------------
- KABUSYS_ENV=live の場合は本番運用となり、誤操作で実際の発注が行われます。JQUANTS / kabu API キーや LINE 通知設定を慎重に管理してください。
- .env は決して Git 等にコミットしないでください。
- 本リポジトリは基礎ライブラリ/実行スクリプト群を提供します。実際に運用するには broker クライアントや strategy 実装、監視ルールのカスタマイズ等が別途必要です。
- OpenAI を使用する機能は API 料金・利用制限の対象です。使用前に必ずコストと API 利用制限を確認してください。

ライセンス / 貢献
------------------
（ここにプロジェクトのライセンス情報やコントリビュート方法を追記してください）

以上。README は必要に応じてプロジェクト固有の運用手順や追加のコマンド例を追記してください。