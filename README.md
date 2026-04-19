KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤（ライブラリ兼実行スクリプト）です。  
主な責務は以下のとおりです。

- 発注エンジン（ExecutionEngine）による自動/ペーパートレード実行
- システム稼働監視とアラート / Kill Switch
- ポートフォリオ構築（銘柄選定・重み付け・株数決定）
- 研究用ファクター計算・特徴量解析（DuckDB を利用したオフライン処理）
- ニュースの NLP によるセンチメント評価（OpenAI API 経由）
- 運用・検証のためのユーティリティ（.env ウィザード、設定検証、検証レポート）

機能一覧
--------
- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動（KABUSYS_ENV=paper_trading のときは MockBrokerClient、paper_trading DB に記録）
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔変更可）
- 環境設定
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: 起動前の設定チェック（env / config/*.yaml / DB パス等）
- モニタリング
  - monitoring_engine.py / system_monitor.py / trade_monitor.py / risk_monitor.py
  - monitoring_db.py: SQLite に監視ログを永続化
  - kill_switch.py: 条件により data/kill.flag を書き込むことで ExecutionEngine 停止
- ポートフォリオ構築
  - portfolio_builder.py / position_sizing.py / risk_adjustment.py（等金額・スコア重み・リスクベース等）
- 研究用
  - research/factor_research.py: Momentum/Volatility/Value 等のファクター計算（DuckDB）
  - research/feature_exploration.py: 将来リターン計算、IC、統計サマリ等
- AI（OpenAI）
  - ai/news_nlp.py: ニュース記事をまとめて LLM でスコアリングし ai_scores に書き込む
  - ai/regime_detector.py: ETF の MA とマクロニュースで市場レジーム判定
- ツール
  - tools/paper_verification_report.py: ペーパートレード結果の期間レポート生成
- 共通ユーティリティ
  - utils/logging_setup.py: 一貫したログ設定（stdout + 日次ローテーションファイル）
  - utils/process_priority.py: プロセス優先度・CPU affinity 設定

前提 / 依存関係
--------------
最低限の依存ライブラリ（実行に必要な主要パッケージ）:
- Python 3.8+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config/*.yaml のパースを validate_config で行う場合に任意で利用）

インストール例（仮）:
- pip install duckdb psutil openai PyYAML

セットアップ手順
--------------
1. リポジトリをクローン／配置
   - プロジェクトルートには .env / data/ / logs/ 等が想定されます。

2. 依存パッケージをインストール
   - 上の pip コマンドを参考にインストールしてください。

3. .env を作成（対話式ウィザード推奨）
   - 実行: python -m kabusys.config_setup
   - ウィザードに沿って J-Quants や kabuAPI のトークン、DB パスなどを入力します。
   - 生成される .env は絶対に Git にコミットしないでください。

4. 設定検証（必須）
   - 実行: python -m kabusys.validate_config
   - --strict を付けると警告も失敗とみなして exit(1) になります:
     python -m kabusys.validate_config --strict

5. データベースディレクトリ作成
   - .env の DUCKDB_PATH / SQLITE_PATH 等の親ディレクトリ（通常 data/）を作成するか、起動時に自動で作成されますが、権限を確認してください。

使い方
------
基本的な起動・ユーティリティ実行例：

- ExecutionEngine 起動（実取引／ペーパートレード）
  - python -m kabusys.run_execution
  - 備考:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます。
    - 実行中に data/stop_requested.flag を作成すると安全に停止処理が走ります。
    - PID ファイルは data/execution.pid（Settings.pid_file_path）に書かれます。

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更できます（デフォルト 60 秒）。
  - Monitoring は監視用 sqlite（Settings.sqlite_path / data/monitoring.db の既定）に書き込みます。
  - data/stop_requested.flag を作成するとループを終了します。

- .env 対話式ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict で警告も失敗扱いにできます。

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（ニュース NLP / レジーム判定）
  - ライブラリ API を直接呼ぶ:
    from kabusys.ai.news_nlp import score_news
    from kabusys.ai.regime_detector import score_regime
  - OpenAI API キー: OPENAI_API_KEY 環境変数または関数引数で指定

重要な環境変数（抜粋）
------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: execution モード
  - 値: development | paper_trading | live（デフォルト development）
- DUCKDB_PATH: 分析 DB（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード DB（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定モード（instant|partial|never|reject、デフォルト instant）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時に必要）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、本番では 0 推奨）
- KILL_FLAG_PATH: kill.flag の保存先（デフォルト data/kill.flag）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト data/execution.pid）

停止・Kill Switch の仕組み
-----------------------
- 停止フラグ（stop_requested.flag）
  - run_monitoring.py / run_execution.py は data/stop_requested.flag の存在を監視し、あれば安全に終了します（手動停止用）。
- Kill Switch（自動停止）
  - RiskMonitor 等が条件を満たすと kill.flag に理由を書き込みます（デフォルト path は Settings.kill_flag_path）。
  - ExecutionEngine は起動時/実行中に kill.flag を検出すると停止します。
  - Settings.KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動クリアしますが、本番では危険なため 0 を推奨します。

ログ
----
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一管理されます。
- デフォルトで stdout と logs/<app_name>.log（日次ローテーション、30日保持）に出力します。
- ログディレクトリは LOG_DIR 環境変数またはデフォルト logs/ を使用します。

ライブラリとしての利用
--------------------
KabuSys は実行スクリプトだけでなく、研究・運用用関数の集合でもあります。主な呼び出し例:

- ポートフォリオ:
  from kabusys.portfolio import select_candidates, calc_score_weights, calc_position_sizes

- 研究:
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

- AI:
  from kabusys.ai import score_news

これらは DuckDB 接続オブジェクトや必要な引数（target_date など）を渡して利用します。各モジュールの docstring を参照してください。

ディレクトリ構成（抜粋）
--------------------
src/kabusys/
- __init__.py
- config.py                  — 環境変数 / Settings 管理
- config_setup.py            — .env 対話式ウィザード
- validate_config.py         — 起動前設定検証 CLI
- run_execution.py           — ExecutionEngine 起動スクリプト
- run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト
- utils/
  - logging_setup.py
  - process_priority.py
- monitoring/
  - monitoring_db.py
  - system_monitor.py
  - monitoring_engine.py
  - risk_monitor.py
  - kill_switch.py
  - (trade_monitor, alert_manager 等)
- execution/                  — ExecutionEngine, order_manager 等（実行ロジック）
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

開発・デバッグのヒント
--------------------
- 設定を反映するには .env を更新後にプロセスを再起動してください。
- validate_config を常に実行して設定漏れや明らかなミスを先に検出してください。
- Monitoring 起動時は MONITOR_POLL_INTERVAL を短めにして（テスト環境では 5〜10 秒）動作確認を行うとよいです。
- OpenAI を使う部分は API 呼び出しのリトライやフォールバックが実装されていますが、API キーやレート制限に注意してください。
- ログ出力先（logs/）のパーミッションを確認してください。ログディレクトリ作成に失敗するとコンソール出力のみになります。

ライセンス / 貢献
-----------------
- 本リポジトリにライセンスファイルがあればそちらに従ってください。  
- バグ報告・機能提案は issue を通じてお願いします。

補足
----
この README はリポジトリ内のスクリプト・モジュールの docstring とコードの挙動に基づいて作成しています。実環境での運用前には必ず設定検証（python -m kabusys.validate_config）・テスト（ペーパートレード）を行ってください。