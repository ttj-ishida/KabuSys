KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買＆リサーチ基盤の軽量実装です。  
主な機能はシグナル生成・ポートフォリオ構築・発注（ExecutionEngine）・監視（Monitoring）・研究（ファクター計算）・AI を用いたニュース解析などを含みます。  
このリポジトリはモジュール単位で整備されており、実運用（live）・ペーパートレード（paper_trading）・開発（development）モードを切り替えて利用できます。

主な特徴
--------
- ExecutionEngine：本番・ペーパートレード双方に対応。ペーパートレード時は MockBroker により本番 DB と分離（data/paper_trading.db）。
- Monitoring：システム稼働状況、データ鮮度、注文・リスクに関する監視・アラート管理。Kill Switch（data/kill.flag）で ExecutionEngine を停止可能。
- Portfolio モジュール：候補選定、重み計算、ポジションサイズ計算、セクターキャップ等の純粋関数群。
- Research：DuckDB を用いたファクター計算（Momentum, Volatility, Value 等）と特徴量解析ユーティリティ。
- AI：OpenAI を用いたニュースのセンチメント計算（news_nlp）、市場レジーム判定（regime_detector）。
- ユーティリティ：ログ設定、プロセス優先度設定、設定ウィザード・バリデーション CLI、検証レポート生成ツール等。
- ログ：コンソール出力 + 日次ローテーションのファイル出力（logs/<app_name>.log）。

前提・依存
-----------
- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config ファイル検証を行う場合）
- 標準で sqlite3 を利用（組み込み）、DuckDB を分析用 DB として使用

インストール（例）
-----------------
1. 仮想環境作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/Mac)
   - .venv\Scripts\activate     (Windows)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML

設定（.env）
-----------
本プロジェクトは .env / .env.local といったファイル、または環境変数で設定を読み込みます。自動ロードの仕様は kabusys.config モジュールを参照してください。

おすすめ手順（対話式ウィザード）
1. 環境ファイル作成（対話式）
   - python -m kabusys.config_setup
     - J-Quants トークン、kabu API パスワードなどを対話的に設定できます。
     - .env は絶対に Git にコミットしないでください。

2. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

主要環境変数（抜粋）
- KABUSYS_ENV: 実行環境 [development | paper_trading | live]（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: （必須）J-Quants API 用トークン
- KABU_API_PASSWORD: （必須）kabuステーション API パスワード
- OPENAI_API_KEY: OpenAI を使う機能で必要（news_nlp, regime_detector）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード DB（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（例: INFO）
- KILL_FLAG_CLEAR_ON_START: 本番で Kill Flag を自動クリアしないよう注意（0 推奨）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

使い方（実行コマンド）
--------------------

1) ExecutionEngine を起動する
- 通常起動
  - python -m kabusys.run_execution
- ペーパートレードで起動する場合
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - この場合、MockBroker を使い data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）へ記録され、本番 DB と分離されます。
- 起動時に data/stop_requested.flag が存在すると起動をスキップします。PID ファイルは data/execution.pid に記録されます。
- Kill Switch（data/kill.flag）が書かれると動作停止のシグナルになります。

2) Monitoring を起動する
- python -m kabusys.run_monitoring
- MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（例: MONITOR_POLL_INTERVAL=30）
- Monitoring は実行環境に関係なく本番 sqlite_path を使用して監視データを記録します。
- 設定された pid ファイルや stop_requested.flag を参照して動作制御します。

3) Paper Trading 検証レポート作成（ツール）
- python -m kabusys.tools.paper_verification_report
- 期間指定:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB 指定:
  - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

ログ
----
- ログはデフォルトで logs/<app_name>.log に日次ローテートで出力されます。コンソール出力は stdout に出ます。
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一されています。

安全機構（Kill Switch / Stop Flag）
--------------------------------
- Kill Switch:
  - リスク監視で閾値を超えた場合、data/kill.flag に理由を書き込み ExecutionEngine を停止させる仕組み（KillSwitch）。
  - 本番では KILL_FLAG_CLEAR_ON_START=0 を推奨（起動時に自動クリアされると危険）。
- Stop Flag:
  - data/stop_requested.flag が存在すると run_execution/run_monitoring のループは停止・起動スキップを行います。管理運用用に使用できます。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要モジュールと説明（抜粋）です。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数自動ロード・Settings クラス（設定取得ユーティリティ）
  - config_setup.py
    - .env 対話式ウィザード
  - validate_config.py
    - 設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリング起動スクリプト
  - execution/
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py ...
    - 発注・注文管理・リスク管理のコア実装（実装ファイルはコードベースに依存）
  - monitoring/
    - monitoring_db.py
      - SQLite を用いた監視ログ永続化層
    - system_monitor.py
      - CPU/メモリ/ディスク・データ鮮度・プロセス監視
    - trade_monitor.py
      - 注文滞留や約定異常監視（コード中に存在）
    - risk_monitor.py
      - ドローダウン・ポジション上限監視
    - monitoring_engine.py
      - 各モニタを束ねるエンジン
    - kill_switch.py
      - フラグファイル書き込みによる停止シグナル
    - alert_manager.py
      - アラート送信の抽象（LINE などを統合する想定）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - ポートフォリオ構築・ポジションサイズ計算・制約適用の純粋関数群
  - research/
    - factor_research.py
    - feature_exploration.py
    - DuckDB を使ったファクター計算・統計解析
  - ai/
    - news_nlp.py
      - OpenAI を用いたニュースセンチメント解析（ai_scores テーブルへの書き込み）
    - regime_detector.py
      - MA200 とマクロニュースで市場レジーム（bull/neutral/bear）を判定
  - tools/
    - paper_verification_report.py
      - ペーパートレード結果の検証レポート生成

注意事項 / 運用メモ
------------------
- .env ファイルは機密情報（API トークン等）を含むため、Git 管理下に置かないでください。
- OpenAI を使う処理は API キー（OPENAI_API_KEY）とコストに依存します。運用時は呼び出し回数や課金に注意してください。
- 本番運用時は KABUSYS_ENV=live の設定を慎重に行い、設定検証（python -m kabusys.validate_config）を必ず実行してください。
- ローカル環境での検証には paper_trading モードを利用し、PAPER_TRADING_SQLITE_PATH を確認してください。
- DuckDB は分析用でスキーマ定義（prices_daily, raw_financials 等）に依存します。初期データ投入は別途スクリプトが必要です（ここでは省略）。

開発・拡張のヒント
------------------
- research / portfolio モジュールの関数は純粋関数（DB 参照なし）で実装されているため、ユニットテストが書きやすい設計です。
- OpenAI 呼び出し部分は _call_openai_api の差し替えやモックでテスト可能に設計されています。
- monitoring_db.init_monitoring_db は冪等でテーブル作成・マイグレーションを行うため、運用開始時に一度実行されます。

ライセンス・バージョン
---------------------
- バージョンはパッケージ定義内で __version__ = "0.1.0" として管理されています。ライセンス情報はリポジトリのルートに従ってください（本 README では省略）。

問い合わせ
--------
実装や運用に関する質問があれば、リポジトリの issue や担当者へお問い合わせください。

以上が README に含める基本情報です。必要に応じて運用手順（デプロイ、systemd ユニット、監視ダッシュボード設定など）を追加してください。