README
======

概要
----
KabuSys は日本株向けの自動売買・研究プラットフォームの一部を切り出した Python パッケージです。本リポジトリには以下の主要機能が含まれます。

- 実行エンジン（ExecutionEngine）の起動スクリプト / 実行制御
- 監視（Monitoring）コンポーネント（システム状態、注文監視、リスク監視、Kill Switch）
- ポートフォリオ構築ユーティリティ（候補選定・重み付け・ポジションサイズ計算 等）
- 研究用ファクター計算・特徴量解析（DuckDB を利用）
- AI を使ったニュース NLP / 市場レジーム判定（OpenAI API 経由）
- ペーパートレード検証レポート生成ツール 等のコマンドライン実行スクリプト

主な設計方針は「本番 DB とペーパートレード DB の分離」「ルックアヘッドバイアスを避ける」「堅牢なフェイルセーフ（API失敗時に安全にフォールバック）」です。

機能一覧
--------
- 起動 / 実行管理
  - run_execution.py: ExecutionEngine を起動。KABUSYS_ENV=paper_trading の場合は MockBroker を使い data/paper_trading.db に記録。
  - run_monitoring.py: SystemMonitor を定期ポーリングして監視ログを記録。MONITOR_POLL_INTERVAL で間隔を上書き可。

- 設定関連
  - config_setup.py: 対話的に .env を作成・更新するウィザード。
  - validate_config.py: .env と config/*.yaml の事前検証 CLI（--strict オプションで警告も FAIL 扱い）。

- 監視（monitoring）
  - system_monitor.py: CPU/メモリ/Disk/プロセス/データ鮮度をチェック。
  - trade_monitor.py / monitoring_db.py: 発注ログ・監視テーブル操作（SQLite）。
  - risk_monitor.py: ドローダウン・ポジション上限の監視、リスクイベント記録。
  - kill_switch.py: 条件を満たすと data/kill.flag を書いて ExecutionEngine を停止させる。
  - monitoring_engine.py: 複数の Monitor を束ねてポーリング・アラート発行。

- ポートフォリオ構築（純関数）
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py: 候補選定、重み付け、単元丸め、セクター上限、レジーム乗数。

- 研究（research）
  - factor_research.py: Momentum / Volatility / Value 等のファクターを DuckDB から算出。
  - feature_exploration.py: 将来リターン計算、IC（情報係数）、統計サマリー。

- AI（OpenAI）
  - ai/news_nlp.py: ニュース記事を集約して OpenAI（gpt-4o-mini 等）でセンチメントを算出、ai_scores テーブルへ書き込み。
  - ai/regime_detector.py: ETF の MA とマクロニュースセンチメントを合成して market_regime を算出・保存。

- ツール
  - tools/paper_verification_report.py: ペーパートレード DB を解析し PASS/FAIL 形式の検証レポートを出力。

セットアップ手順
--------------
前提
- Python（3.9+ を想定）
- SQLite は標準ライブラリで利用可能
- 必要パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config ファイル検証で任意）
インストール例:
  pip install duckdb psutil openai PyYAML

リポジトリ初期化
1. 必要なディレクトリを作成（任意: スクリプトは自動作成も試みますが手動で用意しておくと確実です）
   mkdir -p data logs

2. .env 作成（推奨: 対話ウィザードを利用）
   python -m kabusys.config_setup
   -> ウィザードに従って各種環境変数を入力し .env を生成します。

主な環境変数（重要）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
  - paper_trading: MockBroker を使い data/paper_trading.db を使用
  - live: 本番モード（実発注）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- LOG_LEVEL: ログレベル（DEBUG/INFO/…、デフォルト INFO）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレード時の約定モード（instant / partial / never / reject）

設定検証
- 自動検証:
  python -m kabusys.validate_config
- 警告を fail 扱いにする:
  python -m kabusys.validate_config --strict

使い方
------
起動スクリプト（CLI）
- 実行エンジンを起動（デフォルト動作）
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使って PAPER_TRADING_SQLITE_PATH に発注ログを残します。
  - 実行中は data/execution.pid が使用され、停止は data/stop_requested.flag を作ることで行えます。

- 監視ループを起動
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で指定可能（例: MONITOR_POLL_INTERVAL=30）。
  - 監視は本番 sqlite_path を常に参照します（環境に依らず monitoring.db を使用）。

停止方法（安全な停止信号）
- ExecutionEngine を extern から停止したいとき:
  - data/stop_requested.flag または data/kill.flag を書き込む（手動で内容を書いても良い）。run_execution / run_monitoring はこれらを検出して終了または停止を行います。
  - KillSwitch (monitoring 側) が条件を満たすと data/kill.flag を自動生成します。

ペーパートレード検証レポート
- データベースを指定してレポートを生成:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
  - --from / --to は YYYY-MM-DD 形式。--db オプションで DB パスを上書き可能。

AI 機能（OpenAI）
- news_nlp.score_news / regime_detector.score_regime は OPENAI_API_KEY が必要です。
- API キーを環境変数で渡すか、関数引数で明示的に渡してください。
- LLM 呼び出しはリトライやフェイルセーフを備えていますが、API 制限やコストに注意してください。

ライブラリ的利用
- ポートフォリオ関係:
  from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes
- 研究用:
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

ロギング
- 共通のログ初期化ユーティリティ:
  from kabusys.utils.logging_setup import setup_logging
  setup_logging(app_name="execution")
- デフォルトログディレクトリ: logs/、日次ローテートで 30 日分保持。

注意点 / 運用上のポイント
- 本番環境では KABUSYS_ENV=live を指定し、LINE 通知等の設定を確認してください。
- Kill Switch の自動クリア（KILL_FLAG_CLEAR_ON_START）は本番で 1 にしないことを推奨します（デフォルト 0）。
- ペーパートレードは本番 DB と分離されています（PAPER_TRADING_SQLITE_PATH）。誤って本番 DB を書き換えないよう環境変数を確認してください。
- OpenAI API 呼び出しは外部ネットワークに依存します。障害時は機能が限定的に動作する設計です（多くの箇所でゼロフォールバックを採用）。

ディレクトリ構成
----------------
以下は src/kabusys 以下の主要ファイル／ディレクトリの要約（抜粋）です。

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env の自動読み込み、Settings クラス
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングスクリプト

  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP（OpenAI 呼び出し、ai_scores 書き込み）
    - regime_detector.py     — 市場レジーム判定（MA + マクロニュース）

  - monitoring/
    - monitoring_db.py       — SQLite テーブル作成 / 永続化 API
    - system_monitor.py      — システム・データ鮮度監視
    - trade_monitor.py       — 注文監視（存在）
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — kill.flag 書き込みユーティリティ
    - monitoring_engine.py   — 各 Monitor をまとめて定期実行
    - alert_manager.py       — （アラート送信の実装が入る想定）

  - execution/
    - execution_engine.py    — ExecutionEngine（エンジン本体、セッション制御）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py      — Broker クライアントの切替（Mock / 実運用）

  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py

  - research/
    - factor_research.py
    - feature_exploration.py

  - tools/
    - paper_verification_report.py

  - utils/
    - logging_setup.py
    - process_priority.py

補足（開発者向け）
- monitoring_db.init_monitoring_db は冪等にテーブルを作成し、既存 DB の簡易マイグレーション（カラム追加）も行います。
- 多くのモジュールは外部接続（DuckDB / SQLite / OpenAI）を受け取る設計になっており、単体テストが容易です（接続や API 呼び出しはモック可能）。
- config._find_project_root は .git または pyproject.toml を基準にプロジェクトルートを探索するため、パッケージ配布後も .env の自動読み込みは安全に動作します。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化できます。

ライセンス / 貢献
----------------
本 README ではライセンス情報は含めていません。プロジェクトルートに LICENSE がある場合はそちらを参照してください。バグ報告や改善提案は Issue を立ててください。

以上。必要であれば「インストール用 requirements.txt の例」「systemd / Supervisor 用の起動ユニット例」「運用時チェックリスト」なども追記します。どの情報を優先して追加しますか？