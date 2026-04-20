README
=====

概要
----
KabuSys は日本株向けの自動売買および研究ユーティリティ群を含む小規模なプロジェクトです。  
主な目的は以下のとおりです。

- 自動売買エンジン（ExecutionEngine）と監視サブシステム（Monitoring）
- ポートフォリオ構築・ポジションサイジングの純粋関数ライブラリ
- ファクター計算・特徴量探索（DuckDB を用いた研究用モジュール）
- ニュースの NLP スコアリングや市場レジーム判定（OpenAI API を利用）
- paper trading 用の検証・レポート出力ツール
- 環境設定ウィザード・設定検証ツール

特徴
----
- モジュール分割により、発注ロジックとデータ処理／研究ロジックを分離
- DuckDB と SQLite を併用：DuckDB は時系列・分析用、SQLite は監視／取引ログ用
- Paper Trading（ペーパートレード）を本番 DB と分離して安全に検証可能
- OpenAI を用いたニュースセンチメント・レジーム判定機能（API キー必須）
- kill.flag / stop_requested.flag によるシンプルな外部制御（強制停止等）
- ログ構成の統一（コンソール + 日次ローテーションファイル）

セットアップ
----------
前提
- Python 3.10 以上（| 型注釈や新しい型を使用しているため）
- 作業ルートはリポジトリルート（pyproject.toml/.git がある場所）を推奨

必須ライブラリ（例）
- duckdb
- psutil
- openai
- （任意）PyYAML（config の検証に利用）

pip でインストール例:
    pip install duckdb psutil openai PyYAML

環境変数 / .env
- .env または .env.local をプロジェクトルートに作成して環境変数を設定します。
- 自動読み込み：デフォルトで .env（→ .env.local）を自動読み込みします。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

重要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（news/regime 機能で必須）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL: (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- DUCKDB_PATH: DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: PaperTrading の約定モード（instant|partial|never|reject）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用、デフォルト 60）

.env を対話的に作成するには:
    python -m kabusys.config_setup

設定検証
- .env と config/*.yaml を起動前に検証できます:
    python -m kabusys.validate_config
- 警告をエラーと見なす strict モード:
    python -m kabusys.validate_config --strict

使い方
------

開発・実行の基本コマンド例
- 実行（ExecutionEngine）を起動:
    PYTHONPATH=src python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db にデータを書きます。
  - 起動時に data/stop_requested.flag が存在すると起動を拒否します（停止フラグ）。

- 監視ループを起動:
    PYTHONPATH=src python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定できます（例: MONITOR_POLL_INTERVAL=30）。
  - 監視は本番 sqlite_path（SQLITE_PATH）を常に使用します（環境に依らず）。

- Paper Trading 検証レポート:
    PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db か環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。

- ニュース NLP / レジーム判定（ライブラリ関数）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続を受け取り、DB 上のテーブルに書き込みを行います。OPENAI_API_KEY を設定してください。

停止制御・フラグ
- 停止（外部停止要求）:
  - data/stop_requested.flag: run_execution / run_monitoring がループ中に検知すると安全に停止します（手動で作成してもらう）。
- Kill Switch:
  - KillSwitch は data/kill.flag を作成して ExecutionEngine 停止のシグナルを送ります。設定やリスクイベントにより自動で書き込まれます。
- PID ファイル:
  - data/execution.pid 等に PID を書く設計になっています（Settings.pid_file_path）。

ログ
- デフォルトで logs/ ディレクトリにアプリ名別のログファイルが日次ローテーションで出力されます（30日保持）。
- ログレベルは LOG_LEVEL 環境変数で変更可能。

注意点 / 運用留意
- OpenAI を使用する機能は API キーが必要で、API の呼び出し制限や費用に注意してください。失敗時はフェイルセーフで処理を継続する実装になっていますが、想定外の動作を招く可能性があります。
- Production (KABUSYS_ENV=live) 設定時は kill フラグや自動クリア設定（KILL_FLAG_CLEAR_ON_START）に注意してください。
- Process priority 設定は psutil により行われます。設定実行には権限が必要な場合があります。
- Paper Trading は本番 DB と分離されるよう設計されていますが、設定ミスで上書きしないよう .env のパスに注意してください。

ディレクトリ構成
----------------
（プロジェクトルート直下に src/ があり、Python パッケージ kabusys を含む想定）

src/kabusys/
- __init__.py
  - パッケージ初期化、バージョン定義

- config.py
  - 環境変数 / .env ロード、Settings クラス（各種設定プロパティ）

- config_setup.py
  - .env を対話的に生成・更新するウィザード

- validate_config.py
  - 起動前の設定検証 CLI

- run_execution.py
  - ExecutionEngine の起動スクリプト（スレッドで Engine を実行、stop flag を監視）

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で制御）

- utils/
  - logging_setup.py: ログ設定ユーティリティ（コンソール + 日次ファイル）
  - process_priority.py: プロセス優先度・CPU affine 設定ユーティリティ
  - （その他ユーティリティを配置）

- monitoring/
  - monitoring_db.py: SQLite テーブル作成・永続化 API（system_status, trade_logs, positions, risk_logs, dashboard 等）
  - system_monitor.py: システム状態・データ鮮度チェック
  - trade_monitor.py: 発注／約定ログの監視（滞留注文、異常約定検出等）
  - risk_monitor.py: ドローダウン・ポジション上限チェック
  - kill_switch.py: kill.flag 書き込みロジック
  - monitoring_engine.py: 各 Monitor を束ねるエンジン
  - alert_manager.py: （アラート送信の管理。LINE 等の通知を想定）

- execution/
  - execution_engine.py: ExecutionEngine（取引セッション管理）
  - broker_factory.py: ブローカークライアント生成（Mock を含む）
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py 等

- portfolio/
  - portfolio_builder.py: 候補選定・重み計算（等配分・スコア加重）
  - position_sizing.py: 発注株数決定・リスク制限
  - risk_adjustment.py: セクター上限・レジーム乗数

- research/
  - factor_research.py: Momentum/Value/Volatility 等のファクター計算（DuckDB）
  - feature_exploration.py: 将来リターン・IC・統計サマリー等
  - __init__.py: 研究系 API エクスポート

- ai/
  - news_nlp.py: ニュースの LLM ベースセンチメントスコアリング（ai_scores へ書込）
  - regime_detector.py: 市場レジーム判定（ETF MA + マクロニュース + LLM の組合せ）
  - __init__.py

- tools/
  - paper_verification_report.py: Paper Trading の検証レポート生成
  - __init__.py

データ・ログ・一時ファイル
- data/ (デフォルト)
  - monitoring.db (SQLITE_PATH)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - kabusys.duckdb (DUCKDB_PATH)
  - stop_requested.flag, kill.flag, execution.pid などの制御ファイル
- logs/
  - <app_name>.log 日次ローテーションで保管

開発ヒント
----------
- ソースツリー直下で PYTHONPATH=src を使ってモジュールを実行するのが簡単です（例: PYTHONPATH=src python -m kabusys.run_monitoring）。
- DuckDB テーブル（prices_daily, raw_financials, raw_news 等）は研究・AI 機能で参照されます。データ投入・スキーマはプロジェクト内のドキュメント（例: README や別の設計資料）に従ってください。
- validate_config と config_setup を活用して環境変数のミスを防いでください。

ライセンス / 貢献
----------------
- 本リポジトリでのライセンス記載がない場合は、プロジェクトオーナーと相談してください。  
- バグ修正・改善提案は Pull Request を送るか Issue を作成してください。

以上です。必要ならば README の英語版、または具体的な運用手順（systemd / supervisor によるサービス化、Dockerfile、requirements.txt の追加など）も作成します。どの情報を追加しますか？