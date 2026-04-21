KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株の自動売買・モニタリング・リサーチ機能を含むモジュール群です。  
README は簡潔にプロジェクトの概要、機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

プロジェクト概要
----------------
KabuSys は自動売買アルゴリズム（ExecutionEngine）、システムモニタリング（Monitoring）、ポートフォリオ構築、ファクター計算／リサーチ、AI を使ったニュースセンチメント評価などを含む統合システムです。  
主な設計方針は次の通りです。

- 監視と発注を分離（Monitoring と Execution を別プロセスで運用）
- Paper Trading 環境を本番 DB から分離（ペーパートレード専用 SQLite）
- DuckDB を分析用に利用、SQLite を監視・発注ログ用に利用
- OpenAI（gpt-4o-mini）等を使った NLP 機能を備える（API キー必須）
- .env による柔軟な設定管理、対話式の設定ウィザード・検証ツールあり

主な機能一覧
--------------
- Execution
  - ExecutionEngine（発注フロー、リスク管理、リコンシリエーション）
  - BrokerClientFactory による本番 / モックブローカー切替（KABUSYS_ENV=paper_trading）
  - OrderRepository / OrderManager / RiskManager 等
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス・データ鮮度監視
  - TradeMonitor / RiskMonitor: 注文・ドローダウン等の監視およびログ記録
  - KillSwitch: 監視から Execution 停止フラグを書き出す仕組み
  - MonitoringEngine: 各 Monitor をまとめたポーリング実行
  - monitoring_db: 監視用 SQLite のスキーマ定義と永続層
- Portfolio（ポートフォリオ構築）
  - 候補選定、等金額/スコア加重、セクター上限の適用、ポジションサイズ計算（単元丸め含む）
- Research（リサーチ）
  - ファクター計算（Momentum / Volatility / Value）
  - 特徴量探索（forward returns, IC, 統計サマリ等）
  - DuckDB を利用した SQL + Python ベースの処理
- AI（ニュース NLP / レジーム判定）
  - ニュース記事を LLM（OpenAI）でセンチメント解析し ai_scores に保存
  - マクロニュースと ETF の MA 乖離を組み合わせて市場レジーム判定
- ツール
  - config_setup: .env を対話式に作成・更新するウィザード
  - validate_config: .env と config/*.yaml の事前検証 CLI
  - paper_verification_report: Paper Trading の検証レポート生成

セットアップ手順（概要）
---------------------
※ 実行環境は Python 3.10+ を推奨します（型注釈の union 演算子 | を使用）。具体的な requirements.txt がある場合はそれに従ってください。

1. リポジトリをクローン／展開
   - git clone ... またはソースを配置

2. 仮想環境の作成（任意推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 一般的に必要となるパッケージ（本コードで参照されている例）
     - duckdb
     - psutil
     - openai
     - PyYAML （config 検証で任意）
   - 例:
     - pip install duckdb psutil openai PyYAML

4. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 生成後、設定を検証:
     - python -m kabusys.validate_config
   - 主要な環境変数（例）
     - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
     - 推奨: KABUSYS_ENV (development | paper_trading | live), DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL
     - OpenAI を利用する場合: OPENAI_API_KEY
     - Paper Trading 用 DB: PAPER_TRADING_SQLITE_PATH（省略時 data/paper_trading.db）
   - 注意: .env は決してリポジトリにコミットしないこと。

5. データディレクトリの準備
   - デフォルトで data/、logs/ 等を使用。logging_setup が自動作成を試みますが、権限等で失敗する場合は手動で作成してください。

使い方（起動例）
----------------

モジュールはスクリプトモードで実行可能です（python -m <module>）。主な起動方法:

- ExecutionEngine を起動（本番 / paper_trading は KABUSYS_ENV に依存）
  - 簡易起動:
    - python -m kabusys.run_execution
  - Paper Trading で起動する例:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
  - Execution 起動時の挙動:
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し paper_sqlite_path（デフォルト data/paper_trading.db）を使用
    - 起動時に data/stop_requested.flag が存在すれば起動をスキップ
    - 実行中は data/execution.pid に PID を書き込み（設定により違う場所を使用可能）

- Monitoring を起動（監視ループ）
  - python -m kabusys.run_monitoring
  - オプション (環境変数):
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）。無効値はデフォルトにフォールバック。
  - 監視は環境変数 KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する点に注意（監視は運用 DB を監視する想定）

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code 1）

- .env ウィザード
  - python -m kabusys.config_setup

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数が優先される）

停止・Kill Switch に関する運用
-----------------------------
- 実行プロセスの停止リクエスト
  - run_execution / run_monitoring はそれぞれ data/stop_requested.flag の存在を監視しています。管理者が停止したい場合はそのファイルを作成してください（内容は任意）。プロセスは次のループで検知して終了します。
- Kill Switch（自動停止）
  - 監視側（KillSwitch）が条件を満たすと data/kill.flag に理由を記述して ExecutionEngine に停止要求を出します。ExecutionEngine 側はこの flag の存在をチェックして停止します。
  - KILL_FLAG_CLEAR_ON_START 環境変数が "1" に設定されていると起動時に kill.flag を自動でクリアします（本番環境では 0 推奨）。

ログ
----
- ロギングは kabusys.utils.logging_setup.setup_logging で統一管理され、デフォルトで stdout と logs/<app_name>.log（日次ローテーション）へ出力します。
- LOG_DIR, LOG_LEVEL 環境変数で挙動を上書きできます。

主要な設定項目（抜粋）
--------------------
- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）
- OPENAI_API_KEY（AI 機能を使う場合必須）
- LOG_LEVEL（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔、秒）
- KILL_FLAG_CLEAR_ON_START（0/1）

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主な構成です（抜粋）:

- kabusys/
  - __init__.py
  - config.py                : 環境変数/.env の読み込みと Settings
  - config_setup.py          : .env 対話式ウィザード
  - validate_config.py       : 設定検証 CLI
  - run_execution.py         : ExecutionEngine 起動スクリプト
  - run_monitoring.py        : SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py : Paper Trading のレポート生成
  - execution/               : Execution 系コンポーネント群（Engine, OrderManager 等）
  - monitoring/
    - monitoring_db.py       : SQLite スキーマと DB 操作ラッパ
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py            : ニュース NLP（OpenAI を使用）
    - regime_detector.py     : 市場レジーム判定（ETF MA + LLM）
  - utils/
    - logging_setup.py
    - process_priority.py    : プロセス優先度設定（psutil）
  - data/ (ランタイムで使用されることが多い)
    - *.db, *.flag, pid ファイル等

監視 DB スキーマ（monitoring_db.py 概要）
---------------------------------------
- system_status: CPU/メモリ/ディスク/プロセス稼働などのポーリングログ
- trade_logs: 発注イベントログ（event_type: Created/Sent/Filled 等）
- positions: 保有ポジション
- risk_logs: リスク関連イベントログ（ドローダウン、ポジション上限等）
- dashboard: 集計（portfolio_value, cash, drawdown_pct 等）

注意事項 / 運用上のポイント
-------------------------
- 本番運用時は KABUSYS_ENV=live の設定を慎重に行ってください（validate_config が警告を出します）。
- OpenAI API 利用はコストが発生します。API キーは安全に管理してください。
- process_priority 設定は psutil を使います。権限不足で設定できない場合は警告を出して続行します。
- .env 自動読み込みはデフォルトで有効ですが、テスト等で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

トラブルシューティング（短記）
------------------------------
- .env を生成/更新したら: python -m kabusys.validate_config で検証
- ログが出力されない／ファイルが作れない: LOG_DIR のディレクトリ権限や logging_setup の出力先を確認
- Paper Trading 用 DB と本番監視 DB を混同しないこと（paper_trading は paper_sqlite_path を使用）

貢献 / 変更履歴
----------------
- この README はコードベースの主要機能から自動的に要点を抽出してまとめています。実装を変更した場合は README の該当箇所を適宜更新してください。

以上がリポジトリの概要と実行に必要な基本情報です。必要であれば、さらに詳細なデプロイ手順（systemd ユニット例、Dockerfile、CI 設定など）や運用手順（バックアップ、ログローテーション確認、監視アラート設定例）を追記します。どの情報が必要か教えてください。