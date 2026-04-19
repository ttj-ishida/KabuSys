KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買基盤（研究・ポートフォリオ構築・発注・監視・AI 補助機能を含む）です。  
コード構成はモジュール化されており、以下の主要機能を備えます。

機能一覧
--------
- 実行エンジン（ExecutionEngine）
  - live / paper_trading / development の実行モード
  - paper_trading 時は MockBroker を使用し、paper_trading 用 DB に記録して本番 DB と分離
- 監視（Monitoring）
  - システム状態（CPU/メモリ/ディスク）、プロセス生存確認、データ鮮度チェック
  - 発注ログ・リスクログ・ダッシュボードの永続化（SQLite）
  - Kill Switch（条件により停止フラグを書き込む）
  - アラート発行（AlertManager 経由）
- ポートフォリオ構築
  - 候補選定、等重/スコア重み、ポジションサイズ計算（リスクベース含む）
  - セクター上限やレジーム乗数の適用
- 研究（Research）
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン・IC 計算・統計サマリ
- AI 補助
  - ニュース NLP による銘柄センチメント（OpenAI を使用）
  - マクロニュース + ETF MA に基づく市場レジーム判定（LLM と組合せ）
- ツール
  - Paper Trading 検証レポート生成スクリプト等
- ユーティリティ
  - ロギング設定、プロセス優先度 / CPU affinity 設定、.env 対話ウィザード、設定検証 CLI

セットアップ手順
----------------

1. リポジトリをクローン
   - git clone ... してプロジェクトルートへ移動

2. Python 環境
   - Python 3.9+ を推奨
   - 仮想環境を作成して有効化するのが望ましい（venv, pyenv 等）

3. 依存関係のインストール
   - 必須（少なくとも）:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（config 検証で YAML の内容チェックを行う際に必要、任意）
   - 例:
     - pip install duckdb psutil openai pyyaml
   - 注意: sqlite3 は標準ライブラリに含まれます。

4. .env を作成（対話ウィザード推奨）
   - python -m kabusys.config_setup
   - 対話式で必要な環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を生成できます。
   - 生成後は python -m kabusys.validate_config で設定検証を行ってください。

5. データディレクトリの準備
   - デフォルトでは data/ 下に DB やフラグファイルが置かれます。自動作成されますが、権限等を確認してください。

主要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN （必須）
- KABU_API_PASSWORD      （必須）
- KABUSYS_ENV            （development | paper_trading | live、デフォルト: development）
- DUCKDB_PATH            （デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            （デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL              （DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
- OPENAI_API_KEY         （AI 機能を使う場合に必要）
- PAPER_FILL_MODE        （paper_trading の約定モード: instant/partial/never/reject、デフォルト instant）
- LOG_DIR                （ログファイルを格納するディレクトリ、デフォルト logs/）

使い方
------

起動スクリプト（モジュール形式）
- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます。
  - 起動時に data/stop_requested.flag が存在すると起動を中止します。
  - 実行中は data/execution.pid に PID を書き込みます（設定により変更可能）。

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能。デフォルト 60 秒。
  - 監視は常に（KABUSYS_ENV に関わらず）本番 sqlite_path を使用します。
  - 停止フラグ（data/stop_requested.flag）を検知するとループを終了します。

ユーティリティ / CLI
- .env 作成ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いになります。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定可能

AI 関連
- OpenAI API を利用する機能（ニュース NLP / レジーム判定）は OPENAI_API_KEY を設定する必要があります。
- API 呼び出しにはリトライ/バックオフ処理が組み込まれていますが、API キーと通信環境を確認してください。

停止 / Kill Switch
- KillSwitch は条件により data/kill.flag を書き込み、ExecutionEngine に停止を促します。
- 手動で停止したい場合は data/stop_requested.flag を作成することで実行中の run_execution/run_monitoring を優雅に停止できます。

ログ
----
- ログはデフォルトで stdout（コンソール）と日次ローテーションされるファイル（logs/<app_name>.log）に出力されます。
- ログレベルは環境変数 LOG_LEVEL または setup_logging の引数で制御可能。

ディレクトリ構成
----------------
（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py             — ニュースセンチメント（OpenAI）
    - regime_detector.py      — 市場レジーム判定（MA + LLM）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (※実装ファイルがある場合)
  - execution/
    - execution_engine.py     — 実行エンジン本体（EngineConfig 等）
    - order_manager.py
    - order_repository.py
    - broker_factory.py       — Broker クライアント生成（Mock / 実ブローカー）
    - reconciler.py
    - risk_manager.py
  - data/ (実行時に生成されることがある)
    - monitoring.db (デフォルト SQLITE_PATH)
    - paper_trading.db (paper_trading 用 DB)
    - stop_requested.flag
    - kill.flag
    - execution.pid
  - utils/
    - logging_setup.py
    - process_priority.py

補足 / 運用上の注意
------------------
- 本番モード（KABUSYS_ENV=live）は重大なリスクを伴います。validate_config で設定を十分に検証してください。
- paper_trading モードは本番 DB と完全分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- AI 機能を利用する場合は OPENAI_API_KEY が必須です。API 利用料やレート制限に注意してください。
- MONITOR_POLL_INTERVAL の値は整数秒で、1 秒以上を指定してください（不正値は 60 秒にフォールバックされます）。
- process_priority.set_process_priority() により起動時にプロセス優先度を上げようとしますが、プラットフォーム・権限により失敗することがあります（警告ログ）。

貢献・拡張
------------
- モジュールは概ね純粋関数・依存注入で設計されています。ユニットテストや差し替え用スタブ（MockBroker 等）を用意するとテストしやすくなります。
- 将来的な拡張例:
  - 銘柄別 lot_size 対応（現在は固定単元）
  - 外部データソースの追加、バックテストモジュールの統合
  - AlertManager の追加チャネル（メール/Slack 等）

ライセンス
----------
- プロジェクトルートに LICENSE がある場合はそちらを参照してください。

この README はコードの主要なエントリポイントと運用ポイントをまとめたものです。細かい API や実装の仕様は各モジュールのドキュメント（関数 docstring / コメント）を参照してください。