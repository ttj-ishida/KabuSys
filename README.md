README.md

概要
---
KabuSys は日本株向けの自動売買・リサーチ基盤です。本リポジトリは以下の主要機能を持つモジュール群を含みます。
- 発注・実行エンジン（ExecutionEngine、ペーパートレード対応）
- 監視コンポーネント（System / Trade / Risk の監視、Kill Switch）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制約）
- リサーチ（ファクター計算、特徴量探索、IC計算）
- AI モジュール（ニュースセンチメントによる ai_score、レジーム判定）
- 運用補助ツール（.env ウィザード、設定検証、ペーパートレード検証レポート）

主な設計方針
- データ永続化に DuckDB（分析用）と SQLite（監視／発注履歴）を併用
- 本番とペーパートレードの DB を分離可能
- .env ベースの設定読み込み（.env.local を上書き）＋対話式ウィザード
- LLM 呼び出しはフェイルセーフ（失敗時にスコアを 0 にする等）

機能一覧
---
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により MockBroker を切替）
  - run_monitoring.py: SystemMonitor をポーリングして監視ログを収集
- 設定管理
  - config.py: Settings クラス（環境変数から各種設定を取得）
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: 起動前の設定検証 CLI（--strict オプション）
- 監視関連
  - monitoring/monitoring_db.py: SQLite のスキーマ初期化・読み書き API
  - monitoring/system_monitor.py / trade_monitor.py / risk_monitor.py / monitoring_engine.py / kill_switch.py / alert_manager.py（監視、Kill Switch、アラート）
  - run_monitoring がポーリングループを実行（MONITOR_POLL_INTERVAL で変更可）
- 発注・実行関連
  - execution パッケージ（BrokerFactory / ExecutionEngine / OrderManager 等）
  - run_execution は KABUSYS_ENV=paper_trading の場合に paper_trading DB を使用
- ポートフォリオ構築（pure function）
  - portfolio.portfolio_builder: 候補選定、等重み／スコア重み計算
  - portfolio.position_sizing: 株数計算（単元丸め、aggregate cap 等）
  - portfolio.risk_adjustment: セクター上限・レジーム乗数
- リサーチ
  - research.factor_research: Momentum / Volatility / Value 等のファクター計算（DuckDB 経由）
  - research.feature_exploration: 将来リターン計算、IC、統計サマリ
- AI 関連
  - ai.news_nlp: ニュースを LLM でセンチメント化し ai_scores に永続化
  - ai.regime_detector: ma200 とマクロセンチメントを合成して市場レジーム判定
- ツール
  - tools.paper_verification_report: ペーパートレード DB から検証レポート生成

セットアップ手順
---
前提
- Python 3.10+ を推奨（型注釈で PEP 604 の union 型等を使用）
- SQLite は標準ライブラリに含まれます
- 推奨依存ライブラリ:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証でオプション）
  - （必要に応じて他モジュール）

例: 仮想環境作成・依存パッケージ（requirements.txt が無い場合の例）
1. 仮想環境作成
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（例）
   - pip install duckdb psutil openai PyYAML

3. プロジェクトルートに移動（.env/.env.local を配置）
   - git clone <repo>
   - cd <repo>
   - cp .env.example .env  （存在する場合）
   - python -m kabusys.config_setup で対話式に .env を作成可能

推奨 .env（最低限必要なキー）
- JQUANTS_REFRESH_TOKEN=your_token_here
- KABU_API_PASSWORD=your_password_here
- KABUSYS_ENV=development | paper_trading | live
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db (ペーパートレード用)
- OPENAI_API_KEY=... （AI 機能を使う場合）
- LOG_LEVEL=INFO

設定検証
- python -m kabusys.validate_config
  - --strict をつけると警告があると exit(1) になります
- config_setup により .env を対話式で生成できます:
  - python -m kabusys.config_setup

使い方（主要スクリプト）
---
1) 監視ループを起動
- デフォルトで MONITOR_POLL_INTERVAL=60 秒
- 環境変数で上書き:
  - export MONITOR_POLL_INTERVAL=30
- 起動:
  - python -m kabusys.run_monitoring
- 挙動:
  - monitoring は Settings.sqlite_path を使用して監視ログを永続化（環境にかかわらず本番 sqlite_path を使用）
  - data/stop_requested.flag を作成するとループは終了します（stop フラグ）
  - ログは logs/monitoring.log に日次ローテートで出力（setup_logging）

2) 実行エンジンを起動（ExecutionEngine）
- ペーパートレードで起動する例:
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution
- 挙動:
  - paper_trading の場合は settings.paper_sqlite_path（デフォルト data/paper_trading.db）に記録され、本番 DB と分離
  - プロセス優先度を high に設定
  - data/stop_requested.flag を配置するとエンジンを停止する
  - PID ファイルを data/execution.pid に書き込み（設定で変更可）

3) AI / レジーム判定 / ニューススコア
- OpenAI API を使うため OPENAI_API_KEY を設定
- ニューススコアのバッチ処理はコード API を呼び出す形式:
  - 例: from kabusys.ai.news_nlp import score_news
  - score_news(conn, target_date, api_key=...)
- レジーム判定:
  - from kabusys.ai.regime_detector import score_regime

4) ペーパートレード検証レポート
- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

ファイル・停止フラグ・Kill Switch
- stop フラグ: data/stop_requested.flag（run_monitoring.py / run_execution.py が参照）
- Kill Switch: Settings.kill_flag_path（デフォルト data/kill.flag）。KillSwitch はリスク基準を満たすとこのファイルを書き込み、ExecutionEngine はこのフラグを検知して停止する設計
- kill_flag_clear_on_start: 起動時に kill.flag を自動でクリアするかの設定（デフォルト 0。本番では 0 を推奨）

ディレクトリ構成（主要ファイル）
---
src/
  kabusys/
    __init__.py
    config.py                    # Settings の実装・.env 自動読み込み
    config_setup.py              # 対話式 .env ウィザード
    validate_config.py           # 設定検証 CLI
    run_execution.py             # ExecutionEngine 起動スクリプト
    run_monitoring.py            # SystemMonitor ポーリング起動スクリプト

    utils/
      __init__.py
      logging_setup.py           # ロギング設定ユーティリティ
      process_priority.py        # プロセス優先度設定ユーティリティ

    monitoring/
      monitoring_db.py           # SQLite スキーマ / 永続化 API
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      kill_switch.py
      monitoring_engine.py
      alert_manager.py

    execution/                    # 発注・実行関連（主要なクラスやファクトリ）
      (BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager, ...)

    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
      __init__.py

    research/
      factor_research.py
      feature_exploration.py
      __init__.py

    ai/
      news_nlp.py
      regime_detector.py
      __init__.py

    data/                         # デフォルトの DB 等（リポジトリルートに data/ を想定）
      (kabusys.duckdb, monitoring.db, paper_trading.db のデフォルトパス)

    tools/
      __init__.py
      paper_verification_report.py

ログ
- デフォルト保存先: logs/
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一管理（コンソール出力は stdout、ファイルは日次ローテート）

注意事項 / 運用上のヒント
- .env は絶対にリポジトリにコミットしないこと（config_setup のヘッダも注意喚起あり）
- KABUSYS_ENV は "development" | "paper_trading" | "live" のいずれかを設定
- 本番での起動前に validate_config.py で設定チェックを行うことを強く推奨
- AI 機能を使う際は API キー（OPENAI_API_KEY）を準備し、トークン使用量に注意すること
- run_monitoring は常に Settings.sqlite_path（監視 DB）を使用する点に注意（監視 DB は環境に依らず本番パスを使う意図）

FAQ（よくある質問）
- Q: ペーパートレードと本番の DB はどう分離されますか？
  - A: run_execution は settings.is_paper を見て paper_sqlite_path を使います。monitoring は本番 sqlite_path を使用する設計です（監視は一元化）。

- Q: 停止させるにはどうする？
  - A: data/stop_requested.flag を作成すると run_monitoring/run_execution は検知して終了します。Kill Switch は条件達成で data/kill.flag を書き込み、Execution 側で検知して停止します。

- Q: ロギングの出力先を変更したい
  - A: kabusys.utils.logging_setup.setup_logging の引数 log_dir を渡すか、環境変数 LOG_DIR を設定してください。

追加情報・拡張
---
- config/*.yaml のテンプレートや scripts/generate_config.py（存在する場合）で詳細設定を生成できます。validate_config は PyYAML がない場合は YAML 検証をスキップします（警告）。
- AI モデル・バックオフ・JSON バリデーション等は堅牢化を意識して実装されています。OpenAI SDK のバージョン差分に注意して運用してください。

問題報告 / コントリビューション
---
不具合や提案は Issue を立ててください。小さな修正は PR を歓迎します。README に記載の環境設定や起動フローで不明点があれば問い合わせください。