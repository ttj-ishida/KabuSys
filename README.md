# KabuSys

日本株向け自動売買システムのリポジトリ（ライブラリ / 起動スクリプト群）。  
この README はコードベース（src/kabusys 以下）をもとにプロジェクトの概要、機能、セットアップ、使い方、ディレクトリ構成を日本語でまとめたものです。

---

プロジェクト内での用語・挙動に関する重要ポイント
- デフォルトのデータファイル
  - DuckDB: data/kabusys.duckdb
  - 監視用 SQLite: data/monitoring.db
  - ペーパートレード SQLite: data/paper_trading.db
- 環境切替
  - KABUSYS_ENV により動作モードを切替（development / paper_trading / live）
  - paper_trading 時は MockBrokerClient を使用し、本番 DB と完全分離して data/paper_trading.db を使用します
- 停止制御
  - run_execution.py / run_monitoring.py はプロジェクト内の data/stop_requested.flag を検出すると安全に終了します
  - KillSwitch（運用上の緊急停止）は data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります
- ログ
  - ロギング初期化は共通関数 setup_logging を通じて行います。デフォルトで logs/<app_name>.log に日次ローテーションで出力します
- プロセス優先度
  - 起動スクリプトは開始時に set_process_priority("high") を呼び出します（psutil を使用）

---

主な機能一覧
- 実行エンジン関連
  - ExecutionEngine 起動スクリプト（run_execution.py）: 発注・注文管理・リスク管理・和解処理を含む実行パイプライン
  - Paper trading モード（KABUSYS_ENV=paper_trading）での分離実行（専用 SQLite）
- 監視関連
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせた MonitoringEngine（run_monitoring.py 経由で稼働）
  - 監視結果の永続化（SQLite / monitoring_db）
  - Kill Switch（リスク条件で自動停止フラグを書き込む）
- ポートフォリオ構築
  - 候補選定、重み付け（等分・スコア加重）、単元丸め、リスク調整（セクター上限・レジーム乗数）
- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を使用）
  - 将来リターン計算、IC 計算、統計サマリ
- AI（LLM）連携
  - ニュースのセンチメントスコア化（OpenAI API を利用、ai.news_nlp）
  - マーケットレジーム判定（ai.regime_detector）
- 運用ツール
  - .env 対話式ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report.py）

---

セットアップ手順（開発環境）
1. リポジトリをクローン
   - git clone ... && cd <repo>

2. Python 仮想環境の準備（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - 必須 / 推奨パッケージ（環境に応じてインストールしてください）:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（validate_config で YAML 検証を行う場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （このリポジトリには requirements.txt が含まれていないため、プロジェクトで必要なパッケージを明示的に追加してください。）

4. 初期設定ファイル（.env）の作成
   - 対話式ウィザードを推奨:
     - python -m kabusys.config_setup
   - ウィザードで生成された .env を編集して必要なトークン・パス等を設定してください。

5. 設定検証
   - python -m kabusys.validate_config
   - 警告を厳密に扱う場合: python -m kabusys.validate_config --strict

注意:
- 本番運用時は KABUSYS_ENV=live の下で設定を慎重に管理してください。
- .env は機密情報を含むため絶対に Git にコミットしないでください。

---

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN — J‑Quants API（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境 (development / paper_trading / live)
- OPENAI_API_KEY — OpenAI API キー（AI モジュール利用時）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring 用。デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（1 = 有効。live 環境では 0 推奨）

---

基本的な使い方 / コマンド
- .env を作成・編集
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いで exit(1)

- 実行エンジンを起動
  - python -m kabusys.run_execution
  - Paper trading モードにするには KABUSYS_ENV=paper_trading を設定してから起動（PAPER_TRADING_SQLITE_PATH を確認）

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring  （ポーリング間隔を上書き）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db path/to/paper_trading.db

- AI スコアリング / レジーム判定（プログラムから呼ぶ）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - いずれも OPENAI_API_KEY が必要（引数 api_key で上書き可能）

停止・緊急停止方法
- 通常停止（run_execution / run_monitoring）
  - プロジェクトルートの data/stop_requested.flag を作成すると、ループは次のポーリングで検知して安全に終了します
- Kill Switch（システム側から Execution を止めたい場合）
  - KillSwitch は data/kill.flag を書き込みます（Monitoring 側が評価して作成）
  - ExecutionEngine は kill.flag の有無を監視して起動中に停止動作を行います
- 起動時に kill.flag を自動クリアする設定は KILL_FLAG_CLEAR_ON_START=1（本番では 0 推奨）

ログ・ファイルパス
- ログ: logs/<app_name>.log（setup_logging により日次ローテーションで保存）
- DB: data/*.db（DuckDB・SQLite）
- PID ファイル: data/execution.pid（ExecutionEngine が PID を管理）

注意点 / オペレーションのヒント
- process priority 設定は OS と権限に依存します（psutil による実装）。権限不足の場合は警告が出てスキップされます。
- DuckDB 側の実行は SQL を使って大量データを処理する設計です。DuckDB のパフォーマンス特性に留意してください。
- AI モジュールは外部 API（OpenAI）を利用するため、レートリミット・失敗時のフェイルセーフ処理が組み込まれていますが、API キーとコスト管理は運用者の責任です。
- validate_config は PyYAML がある場合に config/*.yaml のパース検証を行います。インストールしておくと安心です。

---

ディレクトリ構成（抜粋）
- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / Settings 管理
    - config_setup.py          — .env 対話ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — Monitoring 起動スクリプト
    - tools/
      - paper_verification_report.py
    - ai/
      - news_nlp.py
      - regime_detector.py
      - __init__.py
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py (存在前提)
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py (存在前提)
    - execution/
      - execution_engine.py (存在前提)
      - order_manager.py (存在前提)
      - order_repository.py (存在前提)
      - broker_factory.py (存在前提)
      - reconciler.py (存在前提)
      - risk_manager.py (存在前提)
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - utils/
      - logging_setup.py
      - process_priority.py
      - __init__.py
    - data/                     — 実行時に利用するファイル群（デフォルト）
      - *.db
      - stop_requested.flag
      - kill.flag
      - execution.pid
- config/
  - *.yaml                    — 各種設定テンプレート（system_config.yaml等）

（補足）一部モジュール・ファイルは本 README 作成時点の抜粋に基づき記載しています。実際のリポジトリではさらに多くのファイルやサブパッケージが存在する場合があります。

---

開発者向けメモ
- 関数・クラスはできるだけ副作用を抑えて設計されています（例: portfolio の関数は純粋関数）
- DuckDB 接続を渡して計算する方式を多用しており、外部 I/O を分離してテストしやすい構成です
- AI 関連は API 呼び出しラッパーを内部で定義しているため、ユニットテストでは該当関数をモックしてください（例: unittest.mock.patch）

---

問題が発生したら
- まず python -m kabusys.validate_config で設定不備をチェック
- logs/<app>.log を確認して詳細を把握
- 環境変数・.env の設定ミスが多いので .env を見直してください

---

この README はコードベースのコメント・実装をもとに作成しています。追加で「使い方の詳しいチュートリアル」や「運用手順書（運用チェックリスト・障害対応）」が必要であれば、目的に合わせて別途作成します。