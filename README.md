KabuSys — 日本株自動売買システム
================================

この README はリポジトリ内の主要スクリプト・モジュールから作成した概要ドキュメントです。
実装の詳しい挙動は各モジュールの docstring / ソースを参照してください。

1) プロジェクト概要
-----------------
KabuSys は日本株向けの自動売買プラットフォームのコアモジュール群です。主な機能は以下です。
- 注文実行エンジン（ExecutionEngine）とそれを支えるブローカークライアント・リスク管理
- 監視コンポーネント（System / Trade / Risk）と Kill Switch（停止フラグ）機能
- ポートフォリオ構築（候補選定・重み付け・株数算出）モジュール（純粋関数）
- 研究用モジュール（ファクター計算・特徴量探索）
- ニュース NLP（OpenAI）を用いたセンチメント評価と市場レジーム判定
- ペーパートレード用ロジック、検証レポート生成ツール
- 設定ウィザードおよび設定検証 CLI
- ロギング・プロセス優先度ユーティリティ等の共通ユーティリティ

設計上のポイント:
- 実行環境 (KABUSYS_ENV) により paper_trading / live / development を切替可能
- ペーパートレード時は本番 DB と分離（data/paper_trading.db がデフォルト）
- DuckDB を分析用 DB、SQLite を監視・発注ログ領域として使用
- OpenAI 呼び出しは外部 API に依存（api_key は環境変数または引数で指定）

2) 主な機能一覧
----------------
- 起動スクリプト
  - run_execution.py — ExecutionEngine の起動（KABUSYS_ENV により MockBroker を選択）
  - run_monitoring.py — SystemMonitor 単体のポーリングループ起動（停止フラグ監視）
- 設定関連
  - config_setup.py — 対話式 .env 生成ウィザード
  - validate_config.py — .env および config/*.yaml の事前検証 CLI
- 監視（monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine
  - monitoring_db.py — SQLite スキーマ初期化および読み書きラッパー
  - KillSwitch — 条件に応じて data/kill.flag を書き込み Execution を停止させる
  - alert_manager（通知処理、実装ファイル参照）
- 注文関連（execution）
  - BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager（実装参照）
  - Paper trading 用の分離 DB サポート
- ポートフォリオ（portfolio）
  - 銘柄選定、重み計算、リスク調整、ポジションサイジング（純粋関数）
- 研究（research）
  - factor_research: momentum / volatility / value 等のファクター計算（DuckDB 経由）
  - feature_exploration: 将来リターン計算、IC、統計サマリ
- AI（ai）
  - news_nlp: OpenAI を用いたニュース記事の銘柄別センチメント付与 / ai_scores への書込み
  - regime_detector: MA + LLM を組み合わせた市場レジーム判定（market_regime テーブル）
- ツール
  - tools.paper_verification_report — ペーパートレード履歴の検証レポート生成

3) セットアップ手順
-------------------
前提: Python 3.9+（プロジェクトの pyproject.toml を参照してください）

1. 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install -r requirements.txt
   ※ requirements.txt がない場合は少なくとも以下を入れてください:
     - duckdb
     - psutil
     - openai
     - PyYAML（設定ファイル検証を行う場合）
   （テスト用に unittest.mock など標準ライブラリで十分な箇所あり）

3. 環境ファイル (.env) を作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - 最低限必要な環境変数:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development / paper_trading / live) — デフォルトは development
     - OPENAI_API_KEY （AI 機能を使う場合）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB; デフォルト: data/monitoring.db）
   - 例 (.env の抜粋)
     JQUANTS_REFRESH_TOKEN=your_token_here
     KABU_API_PASSWORD=your_kabu_password_here
     KABUSYS_ENV=development
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db

4. 設定検証
   - python -m kabusys.validate_config
   - 問題がある場合は出力に従って .env / config/*.yaml を修正

5. ディレクトリの作成（ログ・データ）
   - デフォルトで使用されるディレクトリ:
     - data/ （SQLite / PID / フラグファイル等）
     - logs/ （ログファイル）
   - setup_logging が自動でディレクトリ作成を試みますが、パーミッション等の問題を事前に確認してください。

4) 使い方（起動例）
-------------------

- ExecutionEngine を起動
  - 本番・ペーパー共通起動:
    python -m kabusys.run_execution
  - KABUSYS_ENV 環境変数の値により、paper_trading の場合は MockBrokerClient を使用し、ペーパートレード専用 DB (PAPER_TRADING_SQLITE_PATH) に書き込みます。
  - 起動時、data/execution.pid に PID が作成される想定（Settings.pid_file_path）

- Monitoring を起動（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト: 60）
  - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視 DB は環境によらず production path）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict をつけると警告も失敗扱いで exit(1)

- Paper Trading 検証レポート（履歴から PASS/FAIL を判定）
  - python -m kabusys.tools.paper_verification_report
  - 期間フィルタ:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI / レジーム判定 / ニューススコアリング（研究・バッチ的に呼ぶ想定）
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を使って DuckDB 接続と target_date を渡して実行します。
  - OpenAI API キーは OPENAI_API_KEY または関数引数で与えます。

停止 / Kill Switch
- ExecutionEngine の強制停止はデータディレクトリ内のフラグファイルを利用:
  - data/kill.flag に理由文字列が書かれると ExecutionEngine 側で検知して停止する動作が組まれています（KillSwitch）。
- run_monitoring.py / run_execution.py は data/stop_requested.flag の存在をチェックしてプロセスを安全に終了します。

ログ
- ログは logs/<app_name>.log に日次ローテーションで保存されます（デフォルト 30 日保持）。
- 標準出力にもログを出します（StreamHandler は stdout）。

環境変数の主な一覧
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 任意／重要:
  - KABUSYS_ENV: development | paper_trading | live
  - OPENAI_API_KEY: AI 機能利用時
  - DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 時）
  - PAPER_FILL_MODE: ペーパートレードの約定モード（instant|partial|never|reject）
  - LOG_LEVEL, LOG_DIR
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"1" で有効。production では注意）

5) ディレクトリ構成（主要ファイル）
----------------------------------
以下は src/kabusys 以下の主なモジュールと簡単な説明です（完全な一覧はリポジトリ参照）。

- kabusys/
  - __init__.py — パッケージ定義（__version__ 等）
  - config.py — 環境変数 / Settings クラス。自動 .env ロード機能あり
  - config_setup.py — 対話式 .env 作成ウィザード
  - validate_config.py — 起動前の設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 起動スクリプト

- kabusys/utils/
  - logging_setup.py — 統一的なログ設定ユーティリティ
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

- kabusys/monitoring/
  - monitoring_db.py — SQLite スキーマ初期化と永続化ヘルパー（MonitoringDB クラス）
  - system_monitor.py — システム稼働監視・データ鮮度チェック
  - trade_monitor.py — 発注ログ・滞留注文・約定異常監視（詳細実装あり）
  - risk_monitor.py — ドローダウン・ポジション数等の監視
  - kill_switch.py — kill.flag 管理
  - monitoring_engine.py — 各 Monitor を束ねるポーリング機構
  - alert_manager.py — アラート送信・通知管理（実装参照）

- kabusys/execution/
  - BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, RiskManager, Reconciler 等（注文処理関連）

- kabusys/portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py — ポートフォリオ構築用純粋関数群

- kabusys/research/
  - factor_research.py — momentum/volatility/value 等のファクター計算（DuckDB）
  - feature_exploration.py — forward returns, IC, factor summary

- kabusys/ai/
  - news_nlp.py — OpenAI を用いたニュースの銘柄別スコア付け
  - regime_detector.py — MA + LLM を組み合わせた市場レジーム判定

- kabusys/tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト

- data/
  - データファイルやフラグファイル（data/monitoring.db、data/paper_trading.db、data/kill.flag、data/stop_requested.flag、data/execution.pid など）

6) トラブルシューティング / 運用メモ
-------------------------------------
- 設定検証: 起動前に python -m kabusys.validate_config を実行してエラー／警告を確認すること。
- ログ出力先に書込権限があるか確認してください（logs/）。
- ペーパートレード時は PAPER_TRADING_SQLITE_PATH、PAPER_FILL_MODE を確認してください。
- OpenAI 関連: レート制限やネットワークエラーが起こりうるため、news_nlp/regime_detector はリトライ処理やフェイルセーフ（0.0 やスキップ）を備えています。API キーの管理には十分注意してください。
- kill.flag / stop_requested.flag:
  - 開発時に誤って本番停止フラグを立てないよう注意してください（KILL_FLAG_CLEAR_ON_START を誤設定すると危険）。
  - run_monitoring / run_execution は stop_requested.flag の存在を見て安全に終了します。

7) 参考（実行例）
-----------------
- .env 作成:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Execution 起動:
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Monitoring 起動:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10

最後に
-----
本 README はソースコードの docstring に基づき作成しています。実際の運用やデプロイの際は config/*.yaml（存在する場合）やデプロイ手順、CI/CD の設定なども合わせて整備してください。詳細実装や追加の運用ルールは各モジュールのコメントを参照してください。質問や追加のドキュメント化が必要であれば教えてください。