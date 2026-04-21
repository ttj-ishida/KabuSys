KabuSys — 日本株自動売買システム（README）
====================================

概要
----
KabuSys は日本株の自動売買・研究・監視を行うための小規模フレームワークです。  
主な責務は以下の通りです。

- 売買ロジック（ポートフォリオ構築、ポジションサイズ算出）
- 注文実行（ExecutionEngine）とリスク管理
- システム・注文状況の監視（Monitoring）
- 研究用ファクター計算・特徴量解析（DuckDB を利用）
- Paper Trading 用の分離された DB と検証レポート生成
- ニュース NLP（OpenAI）を使ったセンチメント評価と市場レジーム判定

このリポジトリは、実運用向けの運用ユーティリティ（ログ設定、プロセス優先度設定、kill/stop フラグなど）を含み、ローカル開発・ペーパートレード・本番環境を想定した設計になっています。

主な機能一覧
------------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し、paper_trading 用 DB に記録（本番 DB と分離）
  - プロセス優先度を設定し、PID ファイルでプロセス管理
- Monitoring（run_monitoring.py）
  - SystemMonitor / TradeMonitor / RiskMonitor を定期ポーリング
  - KillSwitch（data/kill.flag）判定と ExecutionEngine 停止のトリガー
  - ポーリング間隔: 環境変数 MONITOR_POLL_INTERVAL（デフォルト 60 秒）
  - 監視ログは SQLite（デフォルト data/monitoring.db）に永続化
- 設定ウィザード（config_setup.py）と設定検証 CLI（validate_config.py）
  - .env の対話的作成・更新、起動前の設定検証（--strict オプションあり）
- Paper Trading 検証レポート（tools/paper_verification_report.py）
  - ペーパートレード DB を読み、稼働率・注文成功率・レイテンシ等を集計して PASS/FAIL 判定
- 研究モジュール（research）
  - モメンタム／ボラティリティ／バリューなどのファクター計算（DuckDB）
  - 将来リターン計算、IC（Information Coefficient）など
- AI モジュール（ai）
  - OpenAI を使ったニュースセンチメント（news_nlp）と市場レジーム判定（regime_detector）
  - OpenAI API キーを必要とする機能あり
- ポートフォリオ構築（portfolio）
  - 候補選定、重み計算、セクター上限適用、ポジションサイズ計算（単元丸め・aggregate cap）

セットアップ手順
----------------
1. リポジトリをクローンし、Python 仮想環境を作成
   - 推奨: Python 3.9+
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 主に以下が必要になります（プロジェクト依存により増減する可能性あり）:
     - duckdb, psutil, openai, PyYAML（config 検証で使用）
   - 例:
     - pip install duckdb psutil openai PyYAML

3. .env ファイル作成（対話ウィザード推奨）
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に .env を作成してください。
   - 自動ロード: 起動時に .env（および .env.local）を自動読み込みします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）。

4. 設定検証（必須環境変数やパスの確認）
   - python -m kabusys.validate_config
   - 警告を厳密エラーとして扱う場合:
     - python -m kabusys.validate_config --strict

5. データディレクトリ作成（必要に応じて）
   - デフォルト DB / PID / フラグファイル等は data/ 下に配置されます。自動で作成されることもありますが事前に権限や所有権を確認してください。

主要環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading: MockBrokerClient を使用、PAPER_TRADING_SQLITE_PATH に書き込み
  - live: 本番モード（注意深く設定を）
- OPENAI_API_KEY: OpenAI を利用する機能で必要
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード DB（デフォルト data/paper_trading.db）
- LOG_LEVEL (デフォルト INFO)、LOG_DIR（デフォルト logs/）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading 時の約定モード（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1。production は 0 推奨）
- PID_FILE_PATH / KILL_FLAG_PATH: PID・kill flag のパスを上書き可能

使い方（主要スクリプト）
------------------------
- 監視ループ起動（常駐）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数で秒間隔を変更可能（例: MONITOR_POLL_INTERVAL=30）

  補足:
  - monitoring は KABUSYS_ENV に関係なくデフォルトで production sqlite_path（SQLITE_PATH）を使います（監視データの一元管理のため）。
  - data/stop_requested.flag が存在するとループは終了します。

- ExecutionEngine 起動（注文処理）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を指定すると Paper Trading モードになり、data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）に記録され本番 DB と分離されます。
  - 起動時に data/stop_requested.flag が既に存在すると起動せず終了します。
  - 実行中に stop flag を立てると安全に停止を試みます。
  - PID ファイル: data/execution.pid（設定で変更可能）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict オプションで警告もエラー扱いに

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH でも DB パスを指定可

- AI / 研究系（ライブラリ関数として使用）
  - ニュース NLP（OpenAI 必須）
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - OPENAI_API_KEY が必要。API 呼び出しはリトライや検証を含む安全設計。
  - レジーム判定
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 研究モジュール（DuckDB 接続を渡して利用）
    - kabusys.research.calc_momentum(conn, dateobj)
    - kabusys.research.calc_volatility(...)
    - 等

運用上の注意
-------------
- kill.flag / stop_requested.flag
  - KillSwitch は data/kill.flag を書くことで ExecutionEngine に停止要求を伝えます（監視側が書き込む設計）。
  - stop_requested.flag（data/stop_requested.flag）は run_monitoring/run_execution の即時停止フラグとして利用されます。
- ログ
  - デフォルトで stdout と logs/<app_name>.log（日次ローテーション）に出力されます。ログディレクトリ/ファイルの作成に失敗した場合はコンソールのみで継続します。
- プロセス優先度
  - 起動スクリプトは最初にプロセス優先度を "high" に設定します。psutil が必要で、OS の権限により設定に失敗する場合があります（警告ログのみ）。
- Paper Trading と本番 DB の分離
  - paper_trading モードでは PAPER_TRADING_SQLITE_PATH に書き込み、本番 SQLITE_PATH とは別に運用されます。必ず設定を確認してください（特に本番環境では KABUSYS_ENV=live に注意）。

主要ディレクトリ構成
--------------------
（リポジトリルート: src/kabusys 以下を想定）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定読み込みロジック（.env 自動ロード含む）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前チェック CLI
  - run_monitoring.py         — Monitoring 起動スクリプト
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート CLI
  - ai/
    - news_nlp.py              — ニュースセンチメント（OpenAI）処理
    - regime_detector.py       — 市場レジーム判定（AI + MA）
  - monitoring/
    - monitoring_db.py        — 監視用 SQLite テーブル初期化 / ラッパー
    - system_monitor.py       — システム・データ鮮度監視
    - trade_monitor.py        — 注文滞留・異常検知（存在）
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - kill_switch.py          — KillSwitch（flag 書き込み）
    - alert_manager.py        — Alert 管理（存在）
  - execution/
    - execution_engine.py     — ExecutionEngine（存在）
    - order_manager.py        — 注文管理
    - order_repository.py     — 注文永続化
    - reconciler.py           — 注文整合処理
    - risk_manager.py         — リスク制御
    - broker_factory.py       — ブローカークライアント生成（Mock 対応）
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 株数算出・集約制限
    - risk_adjustment.py      — セクター上限・レジーム乗数
  - research/
    - factor_research.py      — ファクター計算（momentum/value/volatility）
    - feature_exploration.py  — 将来リターン・IC・統計サマリー
  - utils/
    - logging_setup.py        — 統一ログ設定
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
  - data/                     — (実行時) data ファイル群（DB、PID、flags 等）

補足（開発者向け）
-----------------
- .env は絶対に VCS にコミットしないでください（config_setup 生成ファイルにも注意書きあり）。
- DuckDB を研究用データのクエリに使う設計のため、prices_daily や raw_financials、raw_news 等のテーブルが前提です。データ投入やスキーマ準備は別途スクリプトで行ってください（本リポジトリ外の想定）。
- OpenAI 周りは API レスポンスの検証・リトライロジックを含んでいますが、API 使用はコストが発生します。API キーの管理に注意してください。
- 本 README はコードベースの主要機能に基づく概要です。詳細な挙動は各モジュールの docstring を参照してください。

ライセンス・貢献
----------------
- （ここにライセンス情報を記載してください。例: MIT ライセンス等）
- バグ修正・機能追加はプルリクエストで受け付けます。運用上の重要な変更は README・config.example 等の更新も合わせて行ってください。

以上。README に関して補足や特定のコマンドや設定例（.env テンプレートなど）を追記したい場合は教えてください。