KabuSys — 日本株自動売買システム（簡易 README）
======================================

概要
----
KabuSys は日本株の自動売買／リサーチ／監視を目的とした小規模なパイプラインです。
主な機能群は以下を含みます。
- ExecutionEngine（発注エンジン）: 本番 / ペーパートレード対応（Mock Broker）
- Monitoring（監視）: システム状態・データ鮮度・注文状況・リスク監視、Kill Switch
- Research / AI: ファクター計算、特徴量解析、ニュース NLP によるセンチメント評価、レジーム判定
- Portfolio construction: 候補選定・重み決定・ポジションサイジング・セクター制約
- ユーティリティ: 設定ウィザード、設定検証、ログ設定、プロセス優先度設定など
- ツール: Paper Trading 検証レポート生成スクリプト

主な特徴
-------
- 環境変数ベースの設定（.env/.env.local 自動読み込み、ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）
- KABUSYS_ENV に応じたモード切替（development / paper_trading / live）
- ペーパートレードは本番 DB と分離（PAPER_TRADING_SQLITE_PATH）
- DuckDB を分析用データベースとして使用
- OpenAI（gpt-4o-mini）を用いたニュース NLP / レジーム判定（API キー任意）
- ログは console と logs/<app>.log に日次ローテーションで出力
- 監視コンポーネントが kill.flag を書き込むことで ExecutionEngine に停止シグナルを送れる（Kill Switch）

前提・依存
----------
推奨: Python 3.10+
主な外部依存パッケージ（最低限）:
- duckdb
- psutil
- openai
- （任意）PyYAML：config/*.yaml の内容検証に使用

仮想環境を作成してインストールしてください（プロジェクトに requirements.txt がある場合はそちらを使用してください）。
例:
- python -m venv .venv
- source .venv/bin/activate
- pip install duckdb psutil openai pyyaml

セットアップ手順
----------------
1. リポジトリをクローンし、作業ディレクトリをプロジェクトルートにする。
2. 仮想環境を作成・有効化し、必要パッケージをインストール。
3. 環境変数設定（.env）
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - あるいは .env を手動作成してください（.env.example を参照）。
   - 自動ロード: プロジェクトルートの .env と .env.local が自動読み込みされます（OS 環境変数が優先）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - （OpenAI 機能利用時）OPENAI_API_KEY
   - 重要な設定（デフォルト値を示す）:
     - KABUSYS_ENV: development | paper_trading | live  （default: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - PAPER_FILL_MODE: instant | partial | never | reject (default: instant)
     - LOG_LEVEL: INFO（デフォルト）
     - KILL_FLAG_CLEAR_ON_START: 0（本番では 0 を推奨）
4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）。

ログ・ディレクトリ
------------------
- デフォルトのログディレクトリ: logs/
- 各アプリは logs/<app_name>.log（TimedRotatingFileHandler、日次、30世代保存）
- setup_logging() が全起動スクリプトで共通に使用されます。

使い方（起動コマンド）
--------------------
- ExecutionEngine（起動例）
  - 本番/開発/ペーパーの切替は KABUSYS_ENV で制御
  - ペーパートレードでは MockBroker を使い、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録され、本番 SQLite と分離されます。
  - 起動:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - KABUSYS_ENV=live python -m kabusys.run_execution
- Monitoring（ポーリング監視）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、デフォルト 60）
  - 停止方法: プロジェクトルート/data/stop_requested.flag を作成するとループが検知して終了します
- 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db /path/to/paper_trading.db （環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）
- AI / レジーム判定（プログラム API）
  - kabusys.ai.score_news や kabusys.ai.regime_detector.score_regime を呼び出して利用します（OpenAI APIキーが必要）。

重要ファイル・フラグ
-------------------
- data/stop_requested.flag: run_monitoring / run_execution の起動ループを終了させるためのフラグ（存在検出で終了）
- data/execution.pid: ExecutionEngine が書き込む PID ファイル（run_execution が使用）
- data/kill.flag: KillSwitch が書き込む停止フラグ（存在すると ExecutionEngine を止めるトリガー）
  - KillSwitch は RiskMonitor の判定（ドローダウン超過など）で書き込まれます
  - Settings.kill_flag_clear_on_start が 1 の場合は起動時に kill.flag を自動クリアします（本番では 0 推奨）

設定（Settings）について
-----------------------
- 設定は kabusys.config.Settings クラスで管理され、環境変数から参照されます。
- 自動 .env 読み込み:
  - プロジェクトルート（.git または pyproject.toml がある場所）から .env を読み込みます
  - 読み込み順: OS env > .env.local > .env
  - 無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- 代表的プロパティ:
  - settings.env (development/paper_trading/live)
  - settings.sqlite_path / settings.duckdb_path
  - settings.paper_sqlite_path
  - settings.paper_fill_mode
  - settings.pid_file_path, settings.kill_flag_path
  - settings.log_level, settings.is_live / is_paper / is_dev

監視・リスクまわりのポイント
----------------------------
- MonitoringDB（SQLite）: system_status, trade_logs, positions, risk_logs, dashboard テーブルを持つ。
- SystemMonitor:
  - CPU / メモリ / ディスク使用率、Execution プロセスの有無、株価データ鮮度をチェックして system_status に記録。
- TradeMonitor: 注文の滞留・約定異常などを検出（trade_logs を参照）。
- RiskMonitor:
  - ダッシュボードのハイウォーターマークを管理し、ドローダウン閾値超過・ポジション数上限などを検知して risk_logs に記録。
  - 必要に応じて KillSwitch をトリガーする。
- KillSwitch:
  - 指定された条件で data/kill.flag を書き込み、ExecutionEngine に停止を促す。

分析 / リサーチ
----------------
- research.factor_research: Momentum / Volatility / Value 等のファクター計算（DuckDB 接続を受け取る）
- research.feature_exploration: 将来リターン計算、IC（Spearman）や基本統計量
- ai.news_nlp: raw_news を OpenAI に投げて銘柄ごとのセンチメント（-1.0〜1.0）を ai_scores に書き込む
- ai.regime_detector: ETF（1321）200日 MA とマクロニュース（LLM）を合成して market_regime に書き込む

ポートフォリオ構成ロジック
-------------------------
- portfolio.portfolio_builder: 候補選定、等重／スコア加重の重み算出
- portfolio.position_sizing: リスクベース・等分配・スコア配分による株数計算、単元株（lot_size）で丸め、合計額がキャッシュを超える場合のスケールダウンロジック
- portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）、レジーム乗数計算

ユーティリティ
-------------
- utils.logging_setup.setup_logging: 全スクリプトで一貫したログ設定（stdout + 日次ローテーションファイル）
- utils.process_priority.set_process_priority: psutil を使って Windows / POSIX を吸収した優先度設定
- config_setup.py: .env を対話式に作成/更新
- validate_config.py: .env と config/*.yaml の存在や基本的妥当性チェック（PyYAML があれば YAML のパース検証も行う）

ディレクトリ構成（抜粋）
------------------------
src/kabusys/
- __init__.py
- config.py                      — 環境変数 / Settings
- config_setup.py                — .env 対話ウィザード
- validate_config.py             — 設定検証 CLI
- run_execution.py               — ExecutionEngine 起動スクリプト
- run_monitoring.py              — SystemMonitor 起動スクリプト
- execution/                      — Execution 運用モジュール群（broker, engine, order_manager 等）
- monitoring/
  - monitoring_db.py             — SQLite 永続化層（監視）
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py
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
  - logging_setup.py
  - process_priority.py
- data/ (実行時に作成されることが多い)
  - monitoring.db (SQLITE_PATH)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - kabusys.duckdb (DUCKDB_PATH)
  - kill.flag / stop_requested.flag / execution.pid

運用上の注意
------------
- 本番（KABUSYS_ENV=live）では kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は危険です。0 を推奨。
- .env は決して Git にコミットしないでください（config_setup の注記も参照）。
- OpenAI を利用する場合 API コストが発生します。バッチ数やトークン数に注意してください。
- DuckDB / SQLite のパスは環境変数で適切に分離してください（特にペーパートレード用 DB）。

トラブルシューティング
-----------------------
- ログディレクトリ作成失敗時はコンソールのみ出力されます（setup_logging は失敗をログに出力）。
- psutil の権限でプロセス優先度や CPU affinity が設定できない場合は警告が出てスキップされます。
- OpenAI 呼び出しはレート制限や一時障害を考慮してリトライロジックがあります。キー未設定時は例外になります。

開発・拡張のヒント
------------------
- DuckDB 接続を渡す形でファクター計算や AI スコアリング関数は設計されているため、テスト用の小さな DuckDB を作って単体テストを行いやすくなっています。
- AI 呼び出し関数は内部で抽象化されており、テストでは _call_openai_api をモックして挙動を検証できます。
- .env の自動ロードはプロジェクトルート検出に依存するため、パッケージ配布時も相対経路で環境を再現できます。

ライセンス・貢献
----------------
- このリポジトリのライセンス・貢献方針は本 README に含まれていません。必要に応じて LICENSE ファイルや CONTRIBUTING を追加してください。

補足
----
README に書かれた動作・設定はソースコード内 docstring / コメントに基づいています。詳細は各モジュール（kabusys/*.py）を参照してください。質問や追加情報があれば教えてください。