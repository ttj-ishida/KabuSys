README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤のミニマル実装です。  
このリポジトリには、注文実行エンジン（ExecutionEngine）、監視モジュール、ポートフォリオ構築ロジック、ファクター計算、ニュースNLP / レジーム判定（OpenAI 統合）などの主要コンポーネントが含まれます。

主要な設計方針
- 実運用を想定した安全側設計（Kill Switch、リスク監視、ログローテーション、フェイルセーフ）
- DuckDB（分析）と SQLite（監視 / 発注ログ）の併用
- OpenAI を使った NLP（ニュースセンチメント）とそれを利用したレジーム判定
- .env による環境変数管理と対話式ウィザード / 検証ツールを同梱

機能一覧
--------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV により paper_trading（MockBroker）/ live（実ブローカ）を切り替え
  - paper_trading 時は data/paper_trading.db に完全分離して記録
  - PID ファイル・停止フラグに対応
- Monitoring（run_monitoring.py）
  - SystemMonitor / TradeMonitor / RiskMonitor をポーリングして監視ログを保存
  - KillSwitch による自動停止トリガー（kill.flag）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
- 監視用永続層（monitoring_db.py）
  - system_status, trade_logs, positions, risk_logs, dashboard 等のテーブル作成・操作
- RiskMonitor / KillSwitch
  - ドローダウン・ポジション上限の監視、閾値超過時に kill.flag を生成
- ログ設定ユーティリティ（utils/logging_setup.py）
  - stdout ストリーム + 日次ローテートファイルログを統一的に設定
- process_priority（utils/process_priority.py）
  - Windows / POSIX に対応したプロセス優先度設定ユーティリティ
- ポートフォリオ構築（portfolio/*.py）
  - 候補選定、重み付け、位置サイズ計算、セクター制限、レジーム乗数など
- 研究用モジュール（research/*.py）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）、IC 計算、統計サマリ
- AI 関連（ai/news_nlp.py, ai/regime_detector.py）
  - OpenAI を使ったニュースセンチメント算出と market_regime 書き込み
- ユーティリティツール
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
  - Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report

必須 / 推奨環境
---------------
- Python 3.10 以上（型ヒントの | 演算子等を使用）
- pip
- 推奨パッケージ（最低限）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config/*.yaml の内容検証を行う場合に必要）
- SQLite は標準で付属
- （任意）ログ出力先用に書き込み可能な logs/ ディレクトリ

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <リポジトリURL>
   - cd <repo>

2. 仮想環境を作成（推奨）
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - macOS/Linux: source .venv/bin/activate

3. 必要パッケージをインストール
   - 例:
     - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt がある場合はそれを使用してください。）

4. .env を作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - または手動でプロジェクトルートに .env を作成（例を .env.example から参考に）

   主な環境変数（必須）
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD

   主なオプション
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - paper_trading: data/paper_trading.db を使用して発注をシミュレート
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（paper_trading 時に使用）
   - LOG_LEVEL / LOG_DIR
   - OPENAI_API_KEY（ai 機能を使う場合、必須）

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになる

使い方
------
起動スクリプト
- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録します
  - 起動時に data/stop_requested.flag が存在すると起動をキャンセルします
  - 実行中に stop を指示するにはプロジェクトルートに data/stop_requested.flag を作成

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - デフォルトで 60 秒ごとにポーリング（MONITOR_POLL_INTERVAL 環境変数で上書き可）
  - 監視は常に本番の sqlite_path（Settings.sqlite_path）を使用して監視テーブルへログを残します
  - 監視中に data/stop_requested.flag を作成すると監視ループは終了します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH を上書き）

- .env 関連ツール
  - 対話式作成: python -m kabusys.config_setup
  - 検証: python -m kabusys.validate_config [--strict]

運用上のフラグ / ファイル
- Kill Switch (自動)
  - モジュールが条件を満たすと data/kill.flag を作成します（ExecutionEngine に停止シグナル用途）
  - Settings.kill_flag_path でカスタマイズ可能
- 手動停止フラグ
  - data/stop_requested.flag を作成すると run_execution / run_monitoring は終了処理を開始
- PID ファイル
  - data/execution.pid（デフォルト）に PID を書く仕組みあり

注意点 / 運用メモ
- KABUSYS_ENV が live の場合は特に注意し、設定 (.env, config/*.yaml, LINE 通知設定等) を確認してください。
- OpenAI を利用する機能は API キーと課金が必要です。API 呼び出しはリトライとフェイルセーフを備えていますが、コストとレイテンシに注意してください。
- DuckDB / SQLite のファイルパスは .env で調整できます。プロダクションでは適切な永続化とバックアップを行ってください。
- ログは logs/<app_name>.log（デフォルト logs/）に日次ローテートで出力されます。LOG_DIR 環境変数で変更可能。

ディレクトリ構成
--------------
(主要ファイルのみ抜粋)

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings 管理
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 起動前設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor ポーリング起動スクリプト

  - ai/
    - news_nlp.py                — ニュース NLP（OpenAI 統合）
    - regime_detector.py         — 市場レジーム判定（MA + マクロNLP）

  - portfolio/
    - portfolio_builder.py       — 候補選定・重み計算
    - position_sizing.py         — 株数計算・スケーリング
    - risk_adjustment.py         — セクター上限・レジーム乗数

  - research/
    - factor_research.py         — モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py     — 将来リターン / IC / 統計サマリ

  - monitoring/
    - monitoring_db.py           — SQLite スキーマ & DB 操作
    - monitoring_engine.py       — Monitor 統合ループ
    - system_monitor.py          — システム状態・データ鮮度監視
    - risk_monitor.py            — ドローダウン・ポジション上限監視
    - kill_switch.py             — kill.flag 操作
    - (trade_monitor.py, alert_manager.py 等が存在する想定)

  - execution/                   — 発注ロジック関連（BrokerFactory, Engine, OrderManager 等）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
  - utils/
    - logging_setup.py           — ログ設定ユーティリティ
    - process_priority.py        — プロセス優先度 / CPU affinity ユーティリティ

- config/
  - system_config.yaml, data_config.yaml, ...（テンプレ / 実運用設定ファイル）

- data/
  - monitoring.db (デフォルト)
  - kabusys.duckdb (デフォルト)
  - paper_trading.db (paper_trading 用)
  - kill.flag / stop_requested.flag / execution.pid などの運用ファイル

トラブルシューティング
---------------------
- .env が読み込まれない / 自動ロードを無効化したい:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みが無効になります。
- config/*.yaml の検証で PyYAML が無いとスキップされます。内容検証を行いたい場合は PyYAML をインストールしてください。
- ログディレクトリの作成に失敗した場合、ファイルログが無効化されコンソールのみになります（stderr に警告が出ます）。
- OpenAI 呼び出し失敗時はフェイルセーフでスコアを 0 にするか、そのチャンクをスキップします。API キーとレート制限を確認してください。

開発者向けメモ
---------------
- 各モジュールはユニットテスト可能な純粋関数を多く含み、外部依存（DB 接続や OpenAI クライアント）は引数で注入する設計になっています。
- DuckDB 接続オブジェクトを引数に受け取り SQL と Python を組み合わせた処理を行う実装が多いです。
- Logging は各スクリプト起動時に setup_logging(app_name=...) を呼んで統一してください。

ライセンス / バージョン
-----------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（現在 0.1.0）。

その他
----
- 本 README はコードベースから抽出可能な情報を元に作成しました。運用に際しては .env.example や config/*.yaml、各モジュールのドキュメント（コメント）を併せてご参照ください。