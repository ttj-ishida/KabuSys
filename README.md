# KabuSys

日本株向け自動売買システムの参照実装（ライブラリ＋起動スクリプト群）。

このリポジトリは取引エンジン、監視、ポートフォリオ構築、リサーチ、AI を組み合わせたモジュール群で構成されています。実運用向けのガード（Kill Switch、リスク監視、ログ管理など）を備え、Paper Trading（模擬発注）モードでの完全分離もサポートします。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要 CLI / スクリプト）
- 環境変数（主なもの）
- ディレクトリ構成（主要ファイルの説明）
- 補足・運用ノート

---

プロジェクト概要
- 株式自動売買システムの参考実装。発注ロジックは ExecutionEngine、監視は Monitoring 系コンポーネント、銘柄選定やポジションサイズは portfolio モジュール、因子計算や特徴量解析は research モジュールで提供されます。
- DuckDB を分析用DB、SQLite を監視/履歴用 DB として利用します。
- 本番（live）/ペーパー（paper_trading）/開発（development）を環境切替でサポート。ペーパートレードは本番 DB と分離された専用 SQLite を使用します。

機能一覧
- ExecutionEngine: 注文管理、リスク管理、リコンサイル（実発注またはモック発注）
- Monitoring:
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / プロセス生存の監視
  - TradeMonitor / RiskMonitor: 滞留注文やドローダウン・ポジション上限の監視
  - KillSwitch: 条件に応じた停止フラグ（data/kill.flag）書き込み
  - MonitoringEngine: 各モニタを束ねた定期ポーリング
- Portfolio: 候補選定、重み付け、ポジションサイズ計算、セクター制限、レジーム調整
- Research: ファクター（Momentum/Value/Volatility 等）計算、IC 計算、将来リターン計算
- AI:
  - news_nlp: OpenAI を用いたニュースセンチメント -> ai_scores 書込み
  - regime_detector: ETF の MA とマクロニュースの LLM スコアを合成して市場レジーム判定
- ツール:
  - config_setup: 対話式 .env 生成ウィザード
  - validate_config: 環境変数 / config/*.yaml の事前検証 CLI
  - paper_verification_report: ペーパートレード結果の検証レポート生成
- ユーティリティ:
  - logging_setup: 統一的なログ設定（console + 日次ローテーションファイル）
  - process_priority: OS を吸収したプロセス優先度 / CPU affinity 設定
  - 環境変数自動読み込み（プロジェクトルートの .env, .env.local）

セットアップ手順（開発用）
1. Python 環境を用意
   - 推奨: Python 3.10+
   - 仮想環境を作成して有効化:
     - python -m venv .venv
     - source .venv/bin/activate  (Linux / macOS)
     - .venv\Scripts\activate     (Windows)

2. 依存パッケージをインストール
   - 必要なパッケージの例:
     - duckdb
     - psutil
     - openai
     - PyYAML（config YAML 検証に任意）
   - 例:
     - pip install duckdb psutil openai PyYAML

3. 環境変数の設定
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - あるいは .env(.local) を直接作成
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - その他主要変数は次節参照

4. 設定検証（起動前推奨）
   - python -m kabusys.validate_config
   - 警告もエラーとして扱う厳格モード:
     - python -m kabusys.validate_config --strict

5. データディレクトリの準備
   - デフォルトでは以下ファイルパスを参照／作成します:
     - data/kabusys.duckdb  (DuckDB)
     - data/monitoring.db   (SQLite: 監視)
     - data/paper_trading.db (Paper Trading 用 SQLite)
   - ログ: logs/<app_name>.log（日次ローテーション）

使い方（主要 CLI / スクリプト）
- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告でも exit(1)

- 起動: 監視プロセス（常駐ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）をオーバーライド（デフォルト 60）
  - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使用

- 起動: 実行エンジン（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）へ記録
  - 起動時に data/stop_requested.flag が存在すると起動を中止
  - 実行中は data/execution.pid ファイルを使用

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db

- ライブラリ関数（プログラムから利用）
  - AI:
    - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key=...)
  - Research:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
  - Portfolio:
    - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier

主要な環境変数（抜粋）
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境
  - KABUSYS_ENV: development | paper_trading | live
    - paper_trading: MockBroker を使用しデータを data/paper_trading.db に分離
- DB / ファイル
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用 SQLite)
  - PID_FILE_PATH (default: data/execution.pid)
  - KILL_FLAG_PATH (default: data/kill.flag)
- ログ
  - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
  - LOG_DIR (default: logs/)
- 監視
  - MONITOR_POLL_INTERVAL (run_monitoring のポーリング秒。デフォルト 60)
  - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
- Paper Trading 挙動
  - PAPER_FILL_MODE: instant | partial | never | reject (デフォルト: instant)
- OpenAI
  - OPENAI_API_KEY（AI モジュールの呼び出しで必要）

設定自動読み込み
- プロジェクトルート（.git または pyproject.toml を基準）から .env、.env.local を自動で読み込みます（OS 環境変数が優先）。
- 自動読み込みを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

監視・停止フローの簡単な説明
- KillSwitch がトリガー（例: ドローダウン超過）すると data/kill.flag を書き込み、ExecutionEngine は起動時／実行中にこのフラグを検知して停止します。
- run_monitoring / run_execution では stop フラグファイル（data/stop_requested.flag）や kill.flag の存在をチェックして動作制御します。

ディレクトリ構成（主なファイル・モジュール）
- src/kabusys/
  - __init__.py
  - config.py
    - Settings クラス: 環境変数を集約・検証。自動 .env 読み込みロジック含む。
  - config_setup.py
    - .env 対話ウィザード
  - validate_config.py
    - 起動前設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト（KABUSYS_ENV により本番/ペーパー切替）
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔制御）
  - utils/
    - logging_setup.py: 一貫したログ設定（stdout + 日次ローテーション）
    - process_priority.py: プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py: SQLite ベースの永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py: システム状態・データ鮮度監視
    - trade_monitor.py: （滞留注文・約定異常検出等 — 実装参照）
    - risk_monitor.py: ドローダウン・ポジション上限監視
    - kill_switch.py: Kill Switch のフラグ操作
    - monitoring_engine.py: 各 Monitor を束ねるエンジン
    - alert_manager.py: （LINE などへの通知を担う想定）
  - execution/
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
      - 注文発行・管理・リスク制御の主要ロジック（ファイル群）
  - portfolio/
    - portfolio_builder.py: 候補選定・スコアソート
    - position_sizing.py: 株数算出ロジック（単元丸め・集約キャップ）
    - risk_adjustment.py: セクターキャップ・レジーム乗数
  - research/
    - factor_research.py: Momentum/Value/Volatility 等ファクター計算（DuckDB 使用）
    - feature_exploration.py: 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py: ニュースを OpenAI でスコアリングして ai_scores へ保存
    - regime_detector.py: マクロ + MA200 を LLM と合成して market_regime を算出
  - tools/
    - paper_verification_report.py: ペーパートレード検証レポート生成ツール

補足・運用ノート
- DuckDB / SQLite はファイルベースの DB です。複数プロセスで書き込みを行う場合は排他制御や DB 分離（例: paper_trading）に注意してください。
- ログは logs/<app_name>.log に日次ローテーションで保存されます。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。
- OpenAI 等の外部 API を使用する機能は API キーが必要です。API の利用制限や課金に注意してください（テストやローカル開発ではモック化を推奨）。
- 実運用（KABUSYS_ENV=live）では Kill Switch 設定や LINE 通知設定を必ず確認してください。validate_config は live 環境向けの警告チェックを行います。

免責
- 本リポジトリは教育/参考実装です。実際の資金を運用する際は十分なテストとレビューを行い、法令・取引所ルールを遵守してください。

--- 
以上。README に含めてほしい追加項目（例: サンプル .env, requirements.txt の内容、CI / デプロイ手順）があれば教えてください。