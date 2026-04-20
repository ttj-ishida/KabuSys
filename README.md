KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買システム（リサーチ / ポートフォリオ構築 / 実行 / 監視 / ツール群）を含む Python パッケージです。設計は本番安全性（本番・ペーパートレードの分離、Kill Switch、ログ/監視など）を重視しています。

主な特徴
--------
- リサーチ: DuckDB 上の prices_daily/raw_financials を用いたファクター計算（モメンタム、バリュー、ボラティリティ等）。
- ポートフォリオ構築: 候補選定、重みづけ、ポジションサイズ算出（等分配・スコア加重・リスクベース）やセクター集中制限。
- 実行エンジン: 実際のブローカー／モックブローカー（KABUSYS_ENV=paper_trading）を切替えて注文管理・リスク管理を行う（ExecutionEngine 起動スクリプトあり）。
- 監視: システム稼働・データ鮮度・注文滞留・ドローダウン等を監視し、必要に応じて Kill Switch（data/kill.flag）を作成して ExecutionEngine 停止を要求。
- AI 支援: OpenAI（gpt-4o-mini）を用いたニュースのセンチメントスコアリングと市場レジーム判定（AI 呼び出しは OPENAI_API_KEY 必須）。
- 運用ツール: .env 対話ウィザード、設定検証、Paper Trading の検証レポートなど。

セットアップ手順
----------------

前提
- Python 3.9+（プロジェクトは typing 等を多用しています）
- Git ワークツリー（プロジェクトルート検出に .git または pyproject.toml を使用）

1. リポジトリをチェックアウト
   - git clone ... などで取得します。

2. 仮想環境を作成・有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS) または .venv\Scripts\activate (Windows)

3. 依存パッケージをインストール
   本リポジトリに requirements.txt は含まれていませんが、主に以下が必要です:
   - duckdb
   - psutil
   - openai
   - PyYAML（config/*.yaml の構文チェックを使う場合、任意）
   インストール例:
   - pip install duckdb psutil openai pyyaml

4. 環境変数設定 (.env)
   - 対話式ウィザードで .env を生成できます:
     - python -m kabusys.config_setup
   - 必須環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要な環境変数（抜粋）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 時）
     - OPENAI_API_KEY: OpenAI を使用する場合に必要
     - LOG_LEVEL: ログレベル（DEBUG/INFO/...）
   - 設定検証:
     - python -m kabusys.validate_config
       --strict を付けると警告も FAIL 扱いになります。

5. データディレクトリ等の作成（必要に応じて）
   - ログディレクトリはデフォルト logs/、SQLite/DuckDB は data/ 下に置くことが多いです。
   - logging_setup.py は起動時にログディレクトリを自動作成しますが、権限に注意してください。

使い方（主要な CLI / スクリプト）
-------------------------------

- 環境設定ウィザード
  - python -m kabusys.config_setup
  - .env を対話式で作成・更新します。

- 設定検証
  - python -m kabusys.validate_config
  - 起動前チェック（必須環境変数・DB パス・YAML 構文など）。

- ExecutionEngine 起動（実取引/ペーパートレード）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録（本番 DB と分離）。
  - 実行時、data/execution.pid に PID を書きます。停止要求: data/stop_requested.flag を作成すると起動中のループが終了します。
  - 起動時に data/kill.flag の自動クリアを行う設定（KILL_FLAG_CLEAR_ON_START）がありますが、本番では無効（0）推奨。

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - 監視ループ（デフォルト 60 秒間隔）を開始します（MONITOR_POLL_INTERVAL 環境変数で秒数を上書き可）。
  - 監視は本番 sqlite_path（data/monitoring.db など）を使用し、SystemMonitor / TradeMonitor / RiskMonitor 等を実行してログ/アラート/kill flag を管理します。
  - 停止フラグ: data/stop_requested.flag を置くとループが終了します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - PAPER_TRADING_SQLITE_PATH 環境変数または --db で DB を指定できます。
  - 稼働率、注文成功率、送信率、P95 レイテンシ等を算出し PASS/FAIL を判定します。

ライブラリ API（概要）
--------------------
主要モジュールと役割（抜粋）:

- kabusys.config
  - Settings クラス: アプリケーション設定（環境変数の読み取り・検証）
  - 自動で .env/.env.local を読み込む仕組み（無効化可能: KABUSYS_DISABLE_AUTO_ENV_LOAD）

- kabusys.utils
  - logging_setup.setup_logging(app_name=..., log_dir=..., level=...): 統一ログ設定
  - process_priority.set_process_priority(level): psutil を使ったプロセス優先度設定

- kabusys.monitoring
  - monitoring_db.init_monitoring_db / MonitoringDB: 監視用 SQLite テーブルの作成・読み書き
  - system_monitor.SystemMonitor: CPU/メモリ/ディスク、データ鮮度、実行プロセス監視
  - risk_monitor.RiskMonitor: ドローダウン、ポジション上限監視
  - kill_switch.KillSwitch: data/kill.flag を書いて ExecutionEngine に停止指示
  - monitoring_engine.MonitoringEngine: 各 Monitor をまとめてポーリング

- kabusys.execution (エンジン本体は実装ファイル群に含まれます)
  - BrokerClientFactory、ExecutionEngine、OrderManager、RiskManager、Reconciler 等で構成
  - paper_trading モードでは MockBrokerClient を用いる設計

- kabusys.portfolio
  - portfolio_builder.select_candidates / calc_equal_weights / calc_score_weights
  - position_sizing.calc_position_sizes（単元丸め、aggregate cap、lot 単位調整を実装）
  - risk_adjustment.apply_sector_cap / calc_regime_multiplier

- kabusys.research
  - factor_research.calc_momentum / calc_volatility / calc_value（DuckDB を直接参照）
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank

- kabusys.ai
  - news_nlp.score_news: raw_news を OpenAI でセンチメント評価し ai_scores に書き込む
  - regime_detector.score_regime: MA200 とマクロセンチメントを合成して市場レジームを判定

運用上の重要点
--------------
- 環境分離:
  - KABUSYS_ENV=paper_trading のときは paper_sqlite_path を使い、本番データベースと完全に分離されます。
- Kill Switch:
  - kill.flag（Settings.kill_flag_path, デフォルト data/kill.flag）が作成されると ExecutionEngine は停止を検討できます（監視側で評価・作成）。
  - Stop フラグ: data/stop_requested.flag を作成すると run_* スクリプトのループが終了します（運用停止用）。
- ログ:
  - logs/<app_name>.log に日次ローテーションで出力。LOG_DIR 環境変数で変更可。
- OpenAI:
  - ai モジュールを使う場合は OPENAI_API_KEY を設定してください。API 呼び出しはリトライ・フェイルセーフ設計になっていますが、API のコストとレート制限に注意してください。

ディレクトリ構成（主要ファイル）
-------------------------------

src/kabusys/
- __init__.py
- config.py                       — 環境変数 / 設定管理
- config_setup.py                 — .env 対話式ウィザード
- validate_config.py              — 起動前設定検証 CLI
- run_execution.py                — ExecutionEngine 起動スクリプト
- run_monitoring.py               — Monitoring 起動スクリプト

src/kabusys/utils/
- logging_setup.py                — ログ設定ユーティリティ
- process_priority.py             — プロセス優先度 / CPU affinity

src/kabusys/monitoring/
- monitoring_db.py                — monitoring DB（SQLite）レイヤー
- system_monitor.py               — システム状態・データ鮮度監視
- trade_monitor.py                — 注文関連監視（滞留など） ※（実装ファイル群の一部）
- risk_monitor.py                 — ドローダウン・ポジション監視
- kill_switch.py                  — Kill Switch 実装
- monitoring_engine.py            — 各モニタを束ねるエンジン
- alert_manager.py                — アラート送信管理（LINE など）※（実装ファイル群の一部）

src/kabusys/execution/
- execution_engine.py             — ExecutionEngine 本体（設計上の中心）
- broker_factory.py               — Broker クライアントの生成（実/モック切替）
- order_manager.py/
- order_repository.py/
- reconciler.py/
- risk_manager.py/

src/kabusys/portfolio/
- portfolio_builder.py
- position_sizing.py
- risk_adjustment.py
- __init__.py

src/kabusys/research/
- factor_research.py
- feature_exploration.py
- __init__.py

src/kabusys/ai/
- news_nlp.py                     — ニュース NLP スコアリング（OpenAI）
- regime_detector.py              — 市場レジーム判定（MA + LLM）

src/kabusys/tools/
- paper_verification_report.py    — Paper Trading 検証レポート生成ツール
- __init__.py

データ・ログ関連（運用）
- data/                           — デフォルトの DB / flag / pid を置く想定ディレクトリ
  - monitoring.db (SQLITE_PATH)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - kabusys.duckdb (DUCKDB_PATH)
  - execution.pid
  - stop_requested.flag
  - kill.flag
- logs/                           — ログ出力先（LOG_DIR）

サンプル .env（抜粋）
--------------------
以下は .env の一部サンプル（config_setup で対話的に作成できます）:

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

補足
----
- config/ 以下の YAML（system_config.yaml など）は運用設定やストラテジ設定用です。validate_config は PyYAML がインストールされていれば YAML のパース検証も行います（未インストールなら警告）。
- モジュールのドキュメントや各関数の docstring を参照することで、詳細な引数や挙動を確認できます。

問題・貢献
--------
バグ報告や改善提案は Issue を立ててください。設計方針や API 仕様の変更は事前に議論をお願いします。

---
この README はコードベース（src/kabusys/*.py）を基に作成しました。さらに詳しい操作方法や実運用チェックリストが必要であれば追加します。