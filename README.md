README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤の一部を抜粋した Python パッケージです。
このリポジトリには以下の主要機能が含まれます:

- ExecutionEngine（発注エンジン）起動スクリプトと発注関連ユーティリティ
- Monitoring（監視）サブシステム（システム状態・注文・リスクの監視、Kill Switch）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ計算、リスク調整）
- リサーチ（ファクター計算、特徴量探索）
- AI ベースのニュース NLP / レジーム判定（OpenAI を利用）
- 各種運用ツール（設定ウィザード、設定検証、Paper Trading 検証レポート 等）

ライセンス・バージョン（パッケージ内）
- バージョン: 0.1.0 (src/kabusys/__init__.py)

主な機能一覧
-------------
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動。KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper_trading 用 DB を利用。
  - run_monitoring.py: SystemMonitor をポーリングで実行（MONITOR_POLL_INTERVAL で間隔変更可）。
- 監視・ログ
  - monitoring_db: SQLite ベースの監視テーブル群（system_status, trade_logs, positions, risk_logs, dashboard）。
  - MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager（通知は設定に依存）。
- ポートフォリオ構築
  - 候補選定 (select_candidates)、等重・スコア重み (calc_equal_weights / calc_score_weights)
  - リスク調整 (apply_sector_cap, calc_regime_multiplier)
  - ポジションサイジング (calc_position_sizes)
- リサーチ
  - ファクター計算 (Momentum / Volatility / Value)
  - 将来リターン・IC 計算、統計サマリ
- AI 機能（OpenAI）
  - news_nlp.score_news: ニュースを LLM でスコアリングして ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF（1321）の MA200 とマクロ記事の LLM センチメントを合成して市場レジーム判定
- 運用ツール
  - config_setup: .env を対話的に作成/更新
  - validate_config: .env と config/*.yaml の基本検証
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成

セットアップ手順
----------------
（例: ローカル開発環境）
1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   最低限必要となる主要パッケージ:
   - duckdb
   - psutil
   - openai  (AI 機能を使う場合)
   - PyYAML（validate_config の YAML 検査を行いたい場合）

   例:
   - pip install duckdb psutil openai pyyaml

   （リポジトリに requirements.txt があればそれを使用してください。）

3. プロジェクトルートで .env を作成
   - 対話ウィザードを使う:
     python -m kabusys.config_setup
   - もしくは手動で .env を作成（.env.example を参考に）

4. 設定の事前検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります:
     python -m kabusys.validate_config --strict

5. データディレクトリ等（必要に応じて）
   - デフォルトで使用されるファイル:
     - DuckDB: data/kabusys.duckdb  (環境変数 DUCKDB_PATH)
     - SQLite (監視): data/monitoring.db  (SQLITE_PATH)
     - Paper Trading SQLite: data/paper_trading.db  (PAPER_TRADING_SQLITE_PATH)
     - ログディレクトリ: logs/（LOG_DIR で変更可）
     - PID / フラグ: data/execution.pid, data/stop_requested.flag, data/kill.flag

使い方
------
起動関連
- ExecutionEngine（発注エンジン）起動
  - 簡易:
    python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV に応じて paper_trading / live / development の挙動が変わります。
    - paper_trading の場合は専用 DB（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と分離されます。
    - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
    - 停止は stop_requested.flag を作成すると実行中スレッドが検知して停止します（data/stop_requested.flag）。

- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書きできます（デフォルト 60）。
  - run_monitoring は監視用 SQLite（Settings.sqlite_path）を使用します（環境にかかわらず本番 sqlite_path を参照する実装上の仕様）。
  - data/stop_requested.flag が置かれるとループを終了します。

停止・Kill Switch
- KillSwitch は監視ロジックの中で条件に応じて data/kill.flag を書き込み、ExecutionEngine に停止指示を与える仕組みです。
- 管理者が強制停止したい場合は stop フラグファイル (data/stop_requested.flag) を作成してください（両スクリプトはこのファイルを参照して終了します）。

Paper Trading 検証
- レポート生成:
  python -m kabusys.tools.paper_verification_report
  オプション:
    --from YYYY-MM-DD
    --to YYYY-MM-DD
    --db PATH  （PAPER_TRADING_SQLITE_PATH 環境変数より優先）

AI 機能（OpenAI）
- 環境変数 OPENAI_API_KEY を設定する必要があります。
- news_nlp.score_news / regime_detector.score_regime は OpenAI API（gpt-4o-mini）を利用します。
- 大量リクエスト時はレート制限や一時エラーに対してリトライが実装されていますが、API キーと使用料に注意してください。

ログ出力
- 共通ロギング設定関数: kabusys.utils.logging_setup.setup_logging(app_name=...)
  - デフォルトで stdout（コンソール）と日次ローテートログ（logs/<app_name>.log）を出力します。
  - ログレベル: 環境変数 LOG_LEVEL または引数で設定可能。
  - ログディレクトリ: LOG_DIR 環境変数または引数で変更可能。

主要環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- OPENAI_API_KEY — AI 機能で必須
- DUCKDB_PATH — デフォルト data/kabusys.duckdb
- SQLITE_PATH — デフォルト data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — デフォルト data/paper_trading.db
- LOG_LEVEL — デフォルト INFO
- LOG_DIR — ログ保存ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング秒数（デフォルト 60）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, PAPER_FILL_MODE（paper_trading の振る舞い制御）など

ディレクトリ構成（主要ファイル）
----------------------------
src/kabusys/
- __init__.py
- config.py
  - Settings クラス: 環境変数の集中管理、自動 .env ロード機能
- config_setup.py
  - .env の対話式ウィザード
- validate_config.py
  - 起動前の設定検証 CLI

- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading 分離、PID/stop フラグ管理）

- run_monitoring.py
  - SystemMonitor ポーリング起動スクリプト（MONITOR_POLL_INTERVAL 対応）

- ai/
  - news_nlp.py: ニュースを LLM でスコアリングして ai_scores に保存
  - regime_detector.py: 市場レジーム判定を行い market_regime に書き込む
  - __init__.py

- monitoring/
  - monitoring_db.py: SQLite テーブル作成・MonitoringDB クラス（永続層）
  - monitoring_engine.py: 各モニタを束ねるエンジン
  - system_monitor.py: システム状態・データ鮮度チェック
  - risk_monitor.py: ドローダウン・ポジション上限監視
  - trade_monitor.py: （コードベースに存在）取引監視ロジック
  - kill_switch.py: kill.flag 書き込みロジック
  - その他: alert_manager 等

- execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
  - （発注ロジックとブローカ抽象化）

- portfolio/
  - portfolio_builder.py: 候補選定・重み計算
  - position_sizing.py: 株数計算・丸め（単元株）
  - risk_adjustment.py: セクターキャップ・レジーム乗数
  - __init__.py

- research/
  - factor_research.py: Momentum / Volatility / Value 計算（DuckDB を利用）
  - feature_exploration.py: 将来リターン・IC・統計サマリ
  - __init__.py

- tools/
  - paper_verification_report.py: Paper Trading の検証レポート
  - __init__.py

- utils/
  - logging_setup.py: 共通ログ設定
  - process_priority.py: プロセス優先度・CPU affinity 設定
  - __init__.py

運用上の注意
-------------
- 本コードは本番運用を想定したガードやログ出力を含みますが、実際に資金を動かす前に十分なテストを行ってください。
- KABUSYS_ENV=live の場合は特に LINE 通知設定や Kill Switch 設定を慎重に確認してください（validate_config にて注意喚起を行います）。
- AI（OpenAI）経由のスコアはコストとレイテンシ、誤応答（パースエラーや不正な JSON）を考慮して扱ってください。スコアのクリッピングや失敗時のフォールバックロジックは実装済みですが、運用ルールを作成してください。
- Paper Trading モードは本番 DB と完全に分離するよう設計されています。PAPER_TRADING_SQLITE_PATH を確認してください。

問い合わせ・貢献
----------------
- この README はリポジトリの現状コードから自動的に作成されています。実装と README の差分があれば Issue を立ててください。
- 機能追加やバグ修正は Pull Request を送ってください。テスト・ドキュメントの追加を歓迎します。

以上。必要であれば実際のコマンド例や .env のテンプレート、各モジュールの詳細な API ドキュメント（関数シグネチャや戻り値の詳細）を追加で作成します。どの情報を優先して追加しますか？