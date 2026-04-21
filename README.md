KabuSys — 日本株自動売買システム
================================

この README はこのリポジトリ内の主要モジュールと起動・運用手順をまとめたドキュメントです。
コードは src/kabusys 以下にあり、ローカル開発・ペーパートレード・本番（live）のいずれの実行モードにも対応しています。

README に含まれる内容
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（起動コマンド・主要 CLI）
- ディレクトリ構成（主要ファイル説明）

プロジェクト概要
----------------
KabuSys は日本株向けの自動売買システムおよびそれを支える補助ツール群です。主な設計方針は以下です。
- 戦略ロジック（ファクター計算、ポートフォリオ構築、ポジションサイズ計算）は純粋関数として実装（副作用を避ける）。
- 発注・決済ロジックは ExecutionEngine に委譲。ペーパートレードと本番を分離できる。
- モニタリングコンポーネントでシステム健全性・リスクを継続監視し、必要に応じて Kill Switch（flag ファイル）で Execution を停止。
- DuckDB（分析用）と SQLite（監視/発注履歴/ペーパートレード DB）を併用。
- OpenAI を使ったニュース NLP / レジーム判定機能を提供（オプション）。

主な機能一覧
-------------
- ExecutionEngine 起動（src/kabusys/run_execution.py）
  - KABUSYS_ENV に応じて本番 or ペーパートレード用の DB / ブローカークライアントを選択
  - 発注管理・リスク管理・注文照合（reconciler）を含む実行フロー
- Monitoring（src/kabusys/run_monitoring.py / monitoring/*）
  - SystemMonitor / TradeMonitor / RiskMonitor をポーリングして監視
  - 監視結果を SQLite に永続化（monitoring_db 関連）
  - KillSwitch による ExecutionEngine 停止制御
- 環境設定ウィザード（src/kabusys/config_setup.py）
  - 対話式に .env を生成・更新
- 設定検証 CLI（src/kabusys/validate_config.py）
  - .env や config/*.yaml の存在・妥当性をチェック
- Paper Trading 検証レポート（src/kabusys/tools/paper_verification_report.py）
  - ペーパートレード DB から稼働率、注文成功率、レイテンシ等を集計してレポート出力
- ポートフォリオ構築ユーティリティ（src/kabusys/portfolio/*）
  - 候補選定、重み付け、セクター上限適用、ポジションサイズ計算
- 研究用モジュール（src/kabusys/research/*）
  - ファクター計算（モメンタム・ボラティリティ・バリュー等）、特徴量探索、IC 計算
- AI 関連（src/kabusys/ai/*）
  - ニュース NLP による銘柄別センチメントスコア化（OpenAI）
  - 市場レジーム判定（MA＋LLM 合成）
- ユーティリティ（src/kabusys/utils/*）
  - ログ設定、プロセス優先度・CPU affinity 設定 など

前提・依存ライブラリ
-------------------
（最低限必要なもの）
- Python 3.10+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config/*.yaml 内容検証を行う場合に任意で使用）

インストール（例）
- 仮想環境作成・有効化
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- 必要パッケージをインストール
  - pip install duckdb psutil openai pyyaml

（注意）requirements.txt は本リポジトリに含まれていない想定のため、必要に応じて上記パッケージをインストールしてください。

設定（.env）
-----------
- 環境変数で設定を制御します。重要なキー（例）:
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
  - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
  - KABUSYS_ENV: execution モード（development / paper_trading / live） デフォルト: development
  - DUCKDB_PATH: 分析用 DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
  - OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
  - LOG_LEVEL, LOG_DIR 等

- .env を作成するには対話式ウィザードを利用できます:
  - python -m kabusys.config_setup
  -> ウィザードが .env を生成します（.env は Git 管理しないでください）。

設定検証
-------
- 起動前に設定を検証する:
  - python -m kabusys.validate_config
  - 厳密モード（警告を FAIL 扱い）:
    - python -m kabusys.validate_config --strict

使い方（起動・運用）
-------------------

- ExecutionEngine の起動
  - デフォルト（現在の .env を参照）:
    - python -m kabusys.run_execution
  - 振る舞い:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db（または PAPER_TRADING_SQLITE_PATH）へ記録。本番 DB と分離されます。
    - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
    - 実行中に data/stop_requested.flag が作られると Engine.stop() が呼ばれ安全に停止します。
    - pid ファイルは data/execution.pid（Settings.pid_file_path で指定可能）に出力されます。

- Monitoring の起動
  - python -m kabusys.run_monitoring
  - 特記事項:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒数で上書き可能（例: export MONITOR_POLL_INTERVAL=30）。
    - 監視は Settings.env に関わらず本番 sqlite_path（デフォルト: data/monitoring.db）を使用します。
    - 停止はリポジトリルート/data/stop_requested.flag を作成すると次ループで検知して終了します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する場合:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  - 簡易的に稼働率・注文成功率・レイテンシなどを評価します。

- AI（ニュース NLP / レジーム判定）
  - ニュース NLP（ai.score_news）や regime_detector.score_regime を直接呼ぶことができます。OpenAI API キーは環境変数 OPENAI_API_KEY または関数引数で渡します。
  - 例（スクリプト化して実行）:
    - python -c "from kabusys.ai.news_nlp import score_news; import duckdb, datetime; conn=duckdb.connect('data/kabusys.duckdb'); score_news(conn, datetime.date(2026,4,1))"
  - 注意: OpenAI を叩く処理は外部 API 呼び出しが発生するため API 利用料やレート制限に注意してください。失敗時はフェイルセーフとして一部処理をスキップする実装になっています。

停止・Kill Switch
-----------------
- ExecutionEngine を遠隔で停止させたい場合は data/kill.flag を書き込む（KillSwitch を使って書かれることを想定）。
- monitoring は KillSwitch の評価により条件を満たすと kill.flag を作成します。ExecutionEngine は起動時/実行中に kill.flag の存在を確認して停止します。
- 手動停止フラグ:
  - 停止リクエスト（監視/実行の早期終了）を行うには repository ルートの data/stop_requested.flag を作成してください（run_execution/run_monitoring はこれを検知して終了します）。
- kill.flag 自動クリア設定:
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番環境では 0 推奨）。

ログ出力
-------
- ログは標準出力（StreamHandler）と日次ローテートファイル（logs/<app_name>.log）に出力されます。
- LOG_DIR 環境変数でログ保存先を変更できます。
- LOG_LEVEL 環境変数でログレベルを制御します（デフォルト INFO）。

主要モジュール説明（抜粋）
-------------------------
- src/kabusys/config.py
  - Settings クラスで環境変数をラップしています。自動でプロジェクトルートの .env を読み込みます（無効化可）。
- src/kabusys/run_execution.py
  - ExecutionEngine の起点。paper_trading モードでは paper DB を使用。
- src/kabusys/run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト。
- src/kabusys/monitoring/*
  - monitoring_db: SQLite テーブル初期化・CRUD ヘルパー
  - system_monitor / trade_monitor / risk_monitor / monitoring_engine / kill_switch / alert_manager 等
- src/kabusys/portfolio/*
  - ポートフォリオ構築に関する純粋関数群（候補選定、重み、ポジションサイズ、セクター制限など）
- src/kabusys/research/*
  - DuckDB 接続を受けてファクター計算や将来リターン、IC・統計サマリー等を提供
- src/kabusys/ai/*
  - news_nlp.py: ニュースを LLM でスコアリングして ai_scores に書き込む
  - regime_detector.py: MA と LLM による市場レジーム判定

ディレクトリ構成（主要ファイル）
------------------------------
以下はリポジトリ内の主要ファイルと役割の抜粋（src/kabusys 配下）:

- __init__.py
  - パッケージ定義、バージョン
- config.py
  - 環境変数/設定の読み取り（Settings）
- config_setup.py
  - .env 対話式ウィザード
- validate_config.py
  - 起動前の設定検証 CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト
- run_monitoring.py
  - Monitoring ポーリングスクリプト
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
- research/
  - factor_research.py, feature_exploration.py
- ai/
  - news_nlp.py, regime_detector.py
- monitoring/
  - monitoring_db.py, system_monitor.py, trade_monitor.py, risk_monitor.py, kill_switch.py, monitoring_engine.py, alert_manager.py
- utils/
  - logging_setup.py, process_priority.py
- data/ (実行時に使用)
  - monitoring.db (SQLite), paper_trading.db, kabusys.duckdb, kill.flag, stop_requested.flag, execution.pid など（自動生成）

運用上の注意点
---------------
- .env は機密情報を含むため Git にコミットしないこと。config_setup.py によりテンプレートを生成できます。
- 本番（KABUSYS_ENV=live）で起動する場合は特に以下を確認:
  - LINE の通知設定がされているか（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）
  - KILL_FLAG_CLEAR_ON_START が 0（自動クリア無効）であること
  - 設定検証（python -m kabusys.validate_config）を実行して警告・エラーがないこと
- OpenAI を本番で利用する場合は API キー管理と使用量の監視を必ず行ってください。
- ログディレクトリ作成に失敗した場合はコンソール出力のみで運用されます（setup_logging がフォールバックします）。

トラブルシューティング（簡易）
------------------------------
- モニタリングが期待どおり動作しない:
  - MONITOR_POLL_INTERVAL の値が整数か確認（0 や負値は警告扱いでデフォルトにフォールバックします）。
  - data/stop_requested.flag の有無を確認（存在するとループは終了します）。
- Execution が起動できない:
  - .env の JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD の未設定を確認。
  - paper_trading モードで起動する場合は PAPER_TRADING_SQLITE_PATH のパーミッションを確認。
- AI 関連が失敗する:
  - OPENAI_API_KEY が設定されているか
  - ネットワークや RateLimit エラーが発生していないか（各処理はリトライ実装あり）

参考コマンドまとめ
-----------------
- .env 作成（対話式）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- Execution 起動
  - python -m kabusys.run_execution
- Monitoring 起動
  - python -m kabusys.run_monitoring
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

最後に
------
この README はコードベースに含まれるドキュメント（関数・モジュールの docstring）を元に作成しています。実運用前に必ずローカルで .env を準備し、validate_config で確認した上で小さなスコープ（ペーパートレード / 開発環境）で動作検証してください。必要に応じて各モジュールの docstring を参照してください。