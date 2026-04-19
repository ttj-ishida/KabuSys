KabuSys
======

日本株向けの自動売買システム（ライブラリ＋起動スクリプト群）。  
このリポジトリは取引エンジン、監視 (monitoring)、ポートフォリオ構築、リサーチ（ファクター計算）、AI を使ったニュース評価などのコンポーネントを含みます。

主な目的
- 本番／ペーパートレードの実行エンジン
- システム・取引・リスクの常時監視と Kill Switch
- ファクター計算・特徴量解析（DuckDB ベース）
- ニュースを LLM（OpenAI）でスコアリングして銘柄ごとの AI スコアを生成
- ペーパートレード結果の検証レポート出力

機能一覧
- 起動スクリプト
  - run_execution: ExecutionEngine を起動（KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し data/paper_trading.db に記録）
  - run_monitoring: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔指定可）
- 設定管理・検証
  - config_setup: 対話式ウィザードで .env を生成／更新
  - validate_config: .env / config/*.yaml の静的チェック
- モニタリング
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine（アラート送信や Kill Switch 連動）
  - SQLite ベースの監視 DB（monitoring_db）スキーマ自動作成・マイグレーション
- 実行系
  - ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager（発注／約定管理）
  - Paper trading と本番 DB の分離（paper_trading 用 DB 別ファイル）
- ポートフォリオ構築
  - 候補選定、重み計算（等分／スコア加重）、ポジションサイズ計算（単元丸め、リスク制限）
  - セクター上限の適用、レジーム乗数
- リサーチ
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン、IC（スピアマン）計算、統計サマリー
- AI（OpenAI）
  - news_nlp: ニュースを銘柄ごとに集約して LLM でセンチメント評価 → ai_scores へ保存
  - regime_detector: ETF（1321）MA200 + マクロニュースで市場レジーム判定
- ツール
  - tools.paper_verification_report: ペーパートレード DB を解析して PASS/FAIL レポートを出力
- ユーティリティ
  - logging_setup: コンソール + 日次ローテーションファイルロギング設定
  - process_priority: Windows / POSIX を吸収したプロセス優先度設定

セットアップ手順（ローカル）
1. Python 環境を用意
   - 推奨: Python 3.9+（実装で typing | が使われているため 3.10 以上を推奨）
   - 仮想環境を作成・有効化
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 無い場合は最低限以下をインストール:
     - pip install duckdb psutil openai
   - (オプション) YAML 検証や追加ツール:
     - pip install PyYAML

3. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - または手動でプロジェクトルートに .env を作成（必須項目は後述）

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）

5. データディレクトリ / ログディレクトリ
   - デフォルト SQLite / DuckDB / PID / ログの場所は .env か環境変数で上書き可能（下記「重要な環境変数」参照）
   - logs/ ディレクトリは自動で作成されますが、パーミッションに注意してください

重要な環境変数（主要）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (default: development). 有効値: development, paper_trading, live
  - paper_trading: MockBrokerClient を利用し data/paper_trading.db に記録
  - live: 本番（発注が行われます）
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- LOG_LEVEL (default: INFO)
- OPENAI_API_KEY (AI モジュール使用時に必要)
- PAPER_FILL_MODE (paper_trading の約定動作: instant|partial|never|reject)
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング間隔秒, default: 60)
- KILL_FLAG_CLEAR_ON_START (0/1)
- LOG_DIR (logging_setup で使用、デフォルト logs/)

使い方（主なコマンド）
- 環境ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（production/paper を .env で切替）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - KABUSYS_ENV=live python -m kabusys.run_execution
  - 実行はバックグラウンドで PID ファイル (data/execution.pid) を作成します
  - 停止は data/stop_requested.flag の作成 or kill シグナルで

- 監視サービス起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は system/trade/risk をポーリングし、必要に応じて data/kill.flag を書き込む等のアクションを行います
  - 監視プロセスも stop_requested.flag を参照して終了します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite ファイルパスを指定可能。デフォルトは data/paper_trading.db（PAPER_TRADING_SQLITE_PATH 環境変数も参照）

- ライブラリ API（スクリプトから利用）
  - AI スコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key=...)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=...)

ログ
- デフォルト: stdout と logs/<app_name>.log（日次ローテーション、30日分保持）
- setup_logging() を各起動スクリプトで呼び出します
- LOG_DIR 環境変数／引数でログ保存先を上書き可

Kill Switch / 停止フラグの動作
- KillSwitch（監視側）が条件を満たすと data/kill.flag を作成します（既存であれば上書きしない）
- ExecutionEngine は起動時に kill flag が存在すれば起動せず終了します
- Execution 停止は data/stop_requested.flag を作成することで外部からの停止要求を出せます（run_execution/run_monitoring がこのファイルを監視）

データベース
- DuckDB: 分析・リサーチ用（デフォルト data/kabusys.duckdb）
- SQLite: 監視ログ（monitoring.db, デフォルト data/monitoring.db）
- Paper Trading: paper_trading 用に別 SQLite（data/paper_trading.db）を使い本番 DB と分離
- 初回起動時に必要なテーブルは init_monitoring_db() で自動作成されます

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
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
    - trade_monitor.py         (実装ファイルあり)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py         (アラート送信の抽象化)
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - monitoring/                (監視用コード群)
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/
    - (デフォルト DB / PID / フラグファイルが置かれる想定ディレクトリ)
- logs/
  - (ログファイル群)

注意事項 / 運用上のヒント
- .env は絶対にリポジトリにコミットしないでください（機密情報が含まれます）。
- KABUSYS_ENV=live の場合、LINE アラート等の設定が必須ではありませんが、未設定だと本番アラートが届きません（validate_config は警告を出します）。
- KILL_FLAG_CLEAR_ON_START は本番で 1 にしないことを推奨（誤って Kill Switch を自動クリアしてしまうおそれがあります）。
- OpenAI 関連のフローは API 制限や費用が発生するため、キー管理と実行頻度に注意してください。
- psutil による優先度設定・CPU affinity 設定は権限が必要になる場合があります。権限不足時は警告が出てスキップされます。
- DuckDB のバージョンや SQLite の挙動により executemany の空リストがエラーになる点に注意（コード側でも対策済み）。

トラブルシューティング
- .env の自動ロードを無効にする:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みをスキップします（テスト用途）
- ログファイルが作成されない:
  - 権限や LOG_DIR のパスを確認し、setup_logging の出力エラーを stderr で確認してください
- DB への書き込みエラー:
  - パスの親ディレクトリが存在するか確認してください（validate_config でも警告します）

貢献・拡張ポイント（候補）
- order execution のブローカーインタフェース実装追加（リアルブローカー連携）
- strategy / signal generation モジュールの追加
- モニタリングの外部通知（Slack 等）プラグイン化
- 単体テスト・CI の追加（validate_config による静的チェックは既にあり）

ライセンス / バージョン
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（現状 0.1.0）。

以上がこのコードベースの概要と基本的な使い方です。  
特定のモジュールの詳細な使い方（例: AI スコアリングのテスト方法、ExecutionEngine の設定項目や RiskConfig のチューニング値）については、該当ソースファイルの docstring / コメントを参照してください。必要であれば README に追記します。