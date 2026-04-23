# KabuSys

日本株自動売買システム（ライブラリ & 実行スクリプト群）

このリポジトリは、アルゴリズムトレードの実行エンジン、監視機能、ポートフォリオ構築、リサーチ、AI（ニュース NLP）連携などをまとめたモジュール群です。SQLite / DuckDB をデータ永続化に用い、kabuステーション等のブローカー API と連携して発注を行います。

----

## 概要

- 実行コンポーネント（ExecutionEngine）と監視コンポーネント（Monitoring）を分離して実装。
- Paper Trading（ペーパートレード）用モードをサポートし、本番 DB と分離して動作可能。
- DuckDB を用いたリサーチ・ファクター計算、OpenAI を用いたニュースセンチメント解析などの補助機能を提供。
- ローカルでの対話的な .env 生成ウィザード、設定検証ツールを備え、運用準備を支援。

----

## 主な機能一覧

- 実行（Execution）
  - ExecutionEngine（発注・注文管理・リスク管理・再調整）
  - BrokerClientFactory を通じ本番／モックブローカーを切替（KABUSYS_ENV）
  - ペーパートレード用の専用 SQLite DB（data/paper_trading.db）

- 監視（Monitoring）
  - SystemMonitor：CPU / メモリ / ディスク / プロセス稼働・データ鮮度監視
  - TradeMonitor：注文滞留・約定異常などの監視（ソースに存在）
  - RiskMonitor：ドローダウン・ポジション上限監視、リスクアラートの永続化
  - KillSwitch：閾値超過時に data/kill.flag を書き込んで Execution 停止を指示
  - MonitoringEngine：各モニタのポーリング・アラート連携

- ポートフォリオ構築（純関数）
  - 候補選定 / 等配分・スコア重み配分 / リスク調整（セクターキャップ・レジーム乗数）
  - ポジションサイズ計算（単元株丸め・集約キャップ処理）

- リサーチ
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）などの統計分析ユーティリティ

- AI（ニュース NLP / レジーム検知）
  - OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント算出と ai_scores への格納
  - マクロニュースを用いた市場レジーム判定（market_regime テーブル書き込み）

- ユーティリティ
  - .env 対話式セットアップウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report）
  - ロギング設定ユーティリティ（logs/ 日次ローテート）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

----

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone ...

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なパッケージをインストール
   - 必須依存（例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config YAML 検証にオプション）
   - 例:
     - pip install duckdb psutil openai PyYAML

   ※ 本リポジトリに requirements ファイルがある場合はそちらを使用してください。

4. .env を作成
   - 対話ウィザードを使う（推奨）
     - python -m kabusys.config_setup
   - 直接編集する場合は `.env.example`（もしくは README の環境変数説明）を参考に作成

5. 設定を検証
   - python -m kabusys.validate_config
   - 本番用設定を厳密にチェックしたい場合:
     - python -m kabusys.validate_config --strict

6. データディレクトリ等の確認
   - デフォルト DB / ログパス（必要に応じて .env で上書き）
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
     - LOG_DIR (default: logs/)
   - ログディレクトリは自動作成されますが、権限等を確認してください。

----

## 環境変数（主要）

- KABUSYS_ENV
  - 値: development | paper_trading | live
  - paper_trading の場合、MockBrokerClient を使用し paper_trading 用 DB を使います。

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY（AI 機能を使用する場合）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）
- LOG_DIR（ログ出力先、デフォルト logs/）
- KILL_FLAG_CLEAR_ON_START（0/1、デフォルト 0。本番での自動クリア保護）
- PAPER_FILL_MODE（paper_trading の MockBroker の挙動: instant|partial|never|reject）
- MONITOR_POLL_INTERVAL（監視ループの秒間隔、デフォルト 60）
- その他: LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート通知用）

----

## 使い方（主要スクリプト）

- 環境セットアップ
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 実行中に data/stop_requested.flag が作られるとエンジンは安全に停止します。
  - paper_trading モード:
    - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient が使用され、PAPER_TRADING_SQLITE_PATH に記録されます。

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で調整可能（デフォルト 60）
  - 監視は Settings に基づき本番 sqlite_path を使用（環境に依らず監視 DB は本番設定を使う仕様）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または DB を明示して:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI 機能（ニュース NLP / レジーム判定）
  - OPENAI_API_KEY を設定し、関数を呼び出す:
    - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key=None)  # api_key None → 環境変数参照
  - API キー未設定時は ValueError が送出されます。

- Kill Switch（運用時）
  - KillSwitch は RiskMonitor 等の結果に応じて data/kill.flag を生成します。
  - Execution 起動時に kill flag を検出すると起動を行わない等の保護があります。
  - Kill flag は Settings.kill_flag_path（デフォルト data/kill.flag）で指定します。

- 停止制御
  - run_monitoring / run_execution ともにプロジェクトルート下の data/stop_requested.flag を検出するとループを抜けて停止します。
  - run_execution は data/execution.pid をプロセス管理用に使用します。

----

## ログ/監視

- ログ設定は kabusys.utils.logging_setup.setup_logging で統一管理されます。
  - デフォルトでコンソール（stdout）と日次ローテートのファイルログ（logs/<app_name>.log）を出力します。
  - LOG_DIR 環境変数や引数でログディレクトリを変更可能。
  - 保持: 30 日分（TimedRotatingFileHandler）

- プロセス優先度は起動時に `psutil` を用いて "high" に設定されます（set_process_priority）。

----

## ディレクトリ構成（主なファイルと説明）

- src/kabusys/
  - __init__.py
  - config.py
    - Settings クラス: 環境変数を読み取りアプリの設定を提供
  - config_setup.py
    - .env を対話的に生成・更新するウィザード
  - validate_config.py
    - 起動前設定検証 CLI（--strict 対応）
  - run_execution.py
    - ExecutionEngine 起動スクリプト（スレッド実行、停止フラグ検出）
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL）
  - utils/
    - logging_setup.py：ロギング設定ユーティリティ
    - process_priority.py：プロセス優先度 / CPU affinity 設定
  - execution/
    - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py
      - 実行エンジン本体（発注・注文管理・リスク管理等） — 詳細実装は該当ファイル参照
  - monitoring/
    - monitoring_db.py：監視用 SQLite の初期化・読み書きラッパ
    - system_monitor.py：CPU/メモリ/ディスク・データ鮮度・プロセス監視
    - trade_monitor.py：注文関連の監視（存在）
    - risk_monitor.py：ドローダウン・ポジション上限監視
    - kill_switch.py：kill.flag の作成・確認
    - monitoring_engine.py：各 Monitor を束ねるエンジン
    - alert_manager.py：アラート発行（LINE 等を経由する想定の管理）
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py
      - 候補選定 / 重み計算 / ポジションサイズ算出 / セクター制限等
  - research/
    - factor_research.py：ファクター計算（momentum/volatility/value）
    - feature_exploration.py：将来リターン / IC / 統計要約
  - ai/
    - news_nlp.py：ニュースを OpenAI でスコアリングし ai_scores へ書込
    - regime_detector.py：マクロ + MA200 によるレジーム検出
  - tools/
    - paper_verification_report.py：ペーパートレード検証レポート生成
  - data/ (実行時に使用するディレクトリ、デフォルト)
    - monitoring.db（SQLite、Settings.sqlite_path）
    - paper_trading.db（Paper Trading 用 SQLite、PAPER_TRADING_SQLITE_PATH）
    - kabusys.duckdb（DuckDB、Settings.duckdb_path）
    - kill.flag / stop_requested.flag / execution.pid（制御フラグ / PID）

----

## 運用上の注意

- 本番（KABUSYS_ENV=live）では設定ミスが重大な影響を及ぼすため、必ず validate_config を実行し、KILL_FLAG_CLEAR_ON_START=0 を推奨します。
- Paper Trading は本番 DB と分離しているため、誤って紙取引データを本番に書き込むリスクは低い設計ですが、.env の設定やパスの確認は慎重に行ってください。
- OpenAI を使う機能は API 利用料金が発生します。API キーと使用範囲を管理してください。
- run_monitoring/run_execution は stop_requested.flag を検出して終了するため、手動で停止フラグをつけることで安全に停止できます。KillSwitch は運用上の強制停止トリガーとして動作します。

----

## トラブルシューティング / デバッグ

- ログが出力されない / ファイル作成に失敗する場合は LOG_DIR の書き込み権限を確認してください。
- psutil による優先度変更で AccessDenied が出る場合、適切な権限で起動するか優先度変更を無効化してください。
- OpenAI API 呼び出しで失敗する場合は API キー、ネットワーク、レート制限、モデル名（_MODEL）を確認してください。ニュース NLP / レジーム検出は失敗時フォールバックの処理を実装していますが、ログ確認が必要です。
- DuckDB / SQLite のファイルパスは .env で上書き可能です。ファイルの存在・権限を確認してください。

----

必要であれば、README に含めるサンプル .env の雛形や運用フロー（デプロイ例、systemd ユニット例、cron エントリ等）も追加できます。どの情報を優先して追加しますか？