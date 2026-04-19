# KabuSys

日本株自動売買システムのライブラリ/ツール群。戦略の研究・ファクター計算、ポートフォリオ構築、リスク制御、発注実行（実環境とペーパーの分離）、監視・アラート、LLM を使ったニュース評価・レジーム判定などを含むモジュール群です。

この README はリポジトリ内の主要スクリプト・モジュールをもとに作成しています。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（コマンド・主要スクリプト）
- 環境変数（重要な設定）
- ディレクトリ構成（主要ファイル一覧）
- 運用上の注意

---

プロジェクト概要
- KabuSys は日本株自動売買を目的としたモジュール群です。
- データ集計・ファクター計算（DuckDB を使用）、ポートフォリオ構築、ポジションサイズ算出、発注実行エンジン（本番 / ペーパートレード分離）、監視（System / Trade / Risk）、LLM を用いたニュースセンチメント評価・市場レジーム判定などを提供します。
- DB は主に DuckDB（分析用）と SQLite（監視・トレース・ペーパートレード用）を利用します。
- OpenAI API を用いるモジュール（ニュース NLP、レジーム判定）を含みますが、API キーが無い場合はそれらを呼ばない/失敗時はフェイルセーフで継続する設計です。

主な機能一覧
- データ / 研究
  - ファクター計算（momentum / volatility / value 等）: kabusys.research.factor_research
  - 将来リターン計算、IC 計算、統計サマリ: kabusys.research.feature_exploration
- ポートフォリオ構築
  - 候補選定、等重・スコア重み、リスク調整（セクター上限・レジーム乗数）: kabusys.portfolio
  - ポジションサイズ計算（リスクに基づく算出、単元丸め、アグリゲートキャップ等）
- 発注実行
  - ExecutionEngine 起動スクリプト（本番 / paper_trading の分岐）: run_execution.py
  - Broker クライアント抽象化（Mock 対応）
  - 注文管理、オーダーリポジトリ、リコンシリエーション、リスク管理
- 監視 / オペレーション
  - System / Trade / Risk モニタ、監視ループ起動スクリプト: run_monitoring.py
  - Kill Switch（条件を満たすと data/kill.flag を書き込み ExecutionEngine を停止）
  - 監視用 SQLite テーブル管理（monitoring_db）
  - MonitoringEngine: 各モニタをまとめてポーリングしてアラート・kill 判定を行う
- AI（LLM）関連
  - ニュース記事を OpenAI で評価し ai_scores に格納: kabusys.ai.news_nlp
  - マクロニュース + ETF MA から市場レジームを判定して market_regime に格納: kabusys.ai.regime_detector
  - OpenAI 呼び出しはリトライ・バリデーション・クリッピング等のフェイルセーフを実装
- ツール
  - .env 対話式ウィザード: kabusys.config_setup
  - 設定検証 CLI: kabusys.validate_config
  - Paper Trading 検証レポート生成スクリプト: kabusys.tools.paper_verification_report
- ユーティリティ
  - ログ設定ユーティリティ（stdout + 日次ローテート）: kabusys.utils.logging_setup
  - プロセス優先度 / CPU affinity ユーティリティ: kabusys.utils.process_priority
  - 環境変数ローディング / Settings 管理: kabusys.config

セットアップ手順（開発環境向け）
1. Python バージョン
   - Python 3.10 以上を推奨（typing の | や新しい文法を使用しています）。

2. リポジトリをクローン / ワークディレクトリを準備
   - プロジェクトルート（pyproject.toml や .git があるディレクトリ）を想定しています。

3. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

4. 依存パッケージをインストール
   - requirements.txt がない場合は最低限以下を入れてください:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証で使用。インストールしない場合は YAML チェックをスキップ）
   - 例:
     - pip install duckdb psutil openai PyYAML

5. データディレクトリの作成（必要に応じて）
   - デフォルトでは data/ 以下に DB やフラグファイルを作成します。手動で作成しておくと権限問題を回避できます:
     - mkdir -p data logs

6. .env の作成
   - 対話式ツールを使う:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成。必須となる環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
     - OPENAI_API_KEY（LLM 機能を使う場合）
   - その他: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START 等

7. 設定検証
   - python -m kabusys.validate_config
   - --strict をつけると警告も失敗扱いになります。

使い方（主要スクリプト）
- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 説明:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
    - 監視モジュールは実行環境にかかわらず本番用 sqlite_path（Settings.sqlite_path）を使用します。
    - 停止はプロジェクトルート/data/stop_requested.flag を作成すると監視ループが検知して終了します。

- ExecutionEngine（発注エンジン）を起動
  - python -m kabusys.run_execution
  - 説明:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、ペーパートレード専用 DB（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）へ記録します。本番 DB と完全に分離されます。
    - ExecutionEngine は data/execution.pid 等の PID ファイルを利用します。
    - 停止は data/stop_requested.flag の作成で検知して安全停止します。
    - 設定で KILL フラグ（data/kill.flag）を利用することで外部から停止シグナルを送れます（KillSwitch）。

- .env を対話的に作成 / 更新
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告でも exit(1) になります。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

環境変数（主要）
- 必須（最低限）
  - JQUANTS_REFRESH_TOKEN : J-Quants API 操作用トークン
  - KABU_API_PASSWORD : kabuステーション API のパスワード
- 実行環境
  - KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
    - paper_trading モードでは発注はモック＆専用 DB に記録されます。
- DB パス
  - DUCKDB_PATH : 分析用 DuckDB（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH : 監視 DB（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH : ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- ロギング
  - LOG_LEVEL : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
  - LOG_DIR : ログファイル保存先（デフォルト logs/）
- Execution / Monitoring
  - PID_FILE_PATH : 実行エンジンの PID ファイルパス（デフォルト data/execution.pid）
  - KILL_FLAG_PATH : Kill フラグファイルパス（デフォルト data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START : 起動時に kill.flag を自動でクリアするか（"1" で有効。production では注意）
  - MONITOR_POLL_INTERVAL : run_monitoring のポーリング間隔（秒）
- Paper / Mock
  - PAPER_FILL_MODE : instant / partial / never / reject（ペーパートレード時の約定挙動）
- OpenAI
  - OPENAI_API_KEY : LLM を使用する機能で必要（news_nlp, regime_detector）

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数の読み込み / Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前の設定検証 CLI
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定（stdout + 日次ローテート）
    - process_priority.py    — プロセス優先度・CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — SQLite 監視テーブル作成・監視ログ API
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — (注: 実装ファイルあり) 注文関連監視
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — Kill Switch 実装（flag 書込み）
    - monitoring_engine.py   — 各 Monitor を束ねる実行エンジン
    - alert_manager.py       — (実装ファイルあり) アラート送信ロジック
  - execution/
    - execution_engine.py    — ExecutionEngine 本体（起動・セッション管理）
    - order_manager.py       — オーダー管理
    - order_repository.py    — 注文ログ DB レイヤ
    - risk_manager.py        — 発注時のリスク制御
    - reconciler.py          — ブローカーと DB の突合
    - broker_factory.py      — BrokerClient の生成（Mock 対応）
  - portfolio/
    - portfolio_builder.py   — 候補選定 / 重み計算
    - position_sizing.py     — 株数計算 / ロット丸め / aggregate cap
    - risk_adjustment.py     — セクター上限 / レジーム乗数
  - research/
    - factor_research.py     — Momentum / Volatility / Value 等の計算（DuckDB 経由）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py            — raw_news を LLM で評価し ai_scores に書き込む
    - regime_detector.py     — ETF + マクロニュースで市場レジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレード集計レポート生成
  - data/                    — 実行時に使う（または生成される）ディレクトリ
    - monitoring.db (デフォルト)
    - kabusys.duckdb (デフォルト)
    - paper_trading.db (ペーパートレード)
    - kill.flag / stop_requested.flag / execution.pid

運用上の注意
- 本番（KABUSYS_ENV=live）での実行には十分注意してください。validate_config は live 環境時に警告が出る箇所をチェックします。
- Kill Switch（data/kill.flag）を使うと ExecutionEngine を停止できます。運用上、KILL_FLAG_CLEAR_ON_START=1 の設定は本番では危険です（自動クリアされるため）。
- ログは logs/<app_name>.log に日次ローテーションで保存されます。ログディレクトリの作成権限に注意してください。
- LLM 呼び出しは API の料金・レート制限に影響します。OPENAI_API_KEY は適切に管理してください。API 呼び出しはリトライ・バックオフがありますが、無制限に実行しないよう運用ポリシーを定めてください。
- データベースファイル（特に本番の monitoring.db）を誤ってペーパートレードと共有しないように設定を確認してください。paper_trading モードでは paper_trading.db を使用します。

補足・トラブルシューティング
- PyYAML 未インストール時、validate_config の YAML パースチェックはスキップされます（その旨のワーニングが出ます）。
- run_monitoring / run_execution の停止: プロジェクトルート/data/stop_requested.flag を作ればループ内で検知して安全に終了します（sys.exit ではなくクリーンなクローズ処理が行われます）。
- MONITOR_POLL_INTERVAL に不正な値（0 や負値、文字列）を渡した場合はデフォルト 60 秒にフォールバックします。

ライセンス・貢献
- （この README では省略しています。実プロジェクトでは LICENSE ファイルを必ず用意してください）

---

以上。必要であれば README にサンプル .env のテンプレートやデプロイ手順（systemd / cron / Docker コンテナ化）、より詳しい各モジュールの使い方（API 仕様、関数一覧・引数説明）を追加できます。どのトピックを優先して詳述しますか？