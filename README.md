KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株の自動売買・リサーチ基盤を想定した Python パッケージです。  
主な目的は以下を含みます:

- 戦略（ファクター計算、特徴量分析）による銘柄選定・配分・株数決定
- ExecutionEngine による発注ロジック（本番 / ペーパートレード切替）
- 監視（System / Trade / Risk）と Kill Switch による安全停止
- Paper Trading の結果検証レポート生成
- ニュース NLP / レジーム検出のための OpenAI 統合（任意）

主な設計方針は「本番 DB とペーパートレード DB の分離」「ルックアヘッドバイアス回避」「フェイルセーフ（API失敗時の安全なフォールバック）」です。

機能一覧
--------
- 環境設定ウィザード (.env 生成) — kabusys.config_setup
- 設定検証 CLI (.env と config/*.yaml の検査) — kabusys.validate_config
- ExecutionEngine 起動スクリプト（本番 / paper_trading 切替） — run_execution.py
  - paper_trading の場合は MockBroker を使用し data/paper_trading.db に記録
- Monitoring ポーリング（SystemMonitor） — run_monitoring.py
  - MONITOR_POLL_INTERVAL 環境変数でインターバル上書き（デフォルト60s）
- MonitoringDB（SQLite）を使ったログ永続化（system_status, trade_logs, positions, risk_logs, dashboard）
- RiskMonitor（ドローダウン・ポジション上限監視）・KillSwitch（kill.flag の書き込み）
- MonitoringEngine：複数 Monitor を束ねてアラート判定・Kill Switch 発動
- Portfolio モジュール：候補選定、重み計算、ポジションサイズ計算、セクター制限、レジーム乗数
- Research：ファクター計算（momentum/value/volatility）、将来リターン、IC 計算、統計サマリ
- AI モジュール（任意）：
  - news_nlp: raw_news を LLM（OpenAI）でセンチメント評価して ai_scores に書込
  - regime_detector: ma200 + マクロニュースの LLM 評価で市場レジーム判定
- ツール：Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

動作要件（主な依存）
--------------------
- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（config/*.yaml の検証を行う場合、任意）

セットアップ手順
--------------
1. リポジトリをクローン / 配布パッケージを入手。

2. 仮想環境作成（推奨）:
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール（例）:
   - pip install duckdb psutil openai PyYAML
   - （本番では requirements.txt を用意している場合はそれを使用）

4. .env の作成:
   - 対話式ウィザード: python -m kabusys.config_setup
     - J-Quants / kabu API トークンなどの必須値を入力します。
   - もしくは .env を手動作成。サンプル（抜粋）:
     JQUANTS_REFRESH_TOKEN=your_token_here
     KABU_API_PASSWORD=your_password_here
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO

   - 自動ロード:
     - プロジェクトルートに .env/.env.local があれば kabusys.config が起動時に読み込みます。
     - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

5. 設定検証（必須項目があるか確認）:
   - python -m kabusys.validate_config
   - 警告も厳密に扱う場合: python -m kabusys.validate_config --strict

使い方（主要コマンド）
--------------------

- ExecutionEngine を起動（本番/ペーパートレードを .env の KABUSYS_ENV で切替）:
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading のとき、MockBrokerClient を使用し data/paper_trading.db に書き込みます（本番 DB と分離）。
    - 起動時に data/stop_requested.flag が存在すると起動をスキップ。
    - 実行中に data/stop_requested.flag が作成されるとエンジンを停止します。
    - PID ファイルを書き出します（デフォルト: data/execution.pid）。Settings.pid_file_path で変更可。

- Monitoring を起動（SystemMonitor ポーリング）:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定可能（デフォルト 60）。
  - python -m kabusys.run_monitoring
  - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使用して監視ログを記録します。

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）

- 設定ウィザード:
  - python -m kabusys.config_setup

主要な環境変数（抜粋）
---------------------
- KABUSYS_ENV: execution モード（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant|partial|never|reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログファイルディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL: monitoring のポーリング間隔（秒）
- OPENAI_API_KEY: OpenAI を使うモジュールの API キー（news_nlp / regime_detector）

停止・Kill Switch（安全停止）
----------------------------
- run_execution と run_monitoring はプロジェクトルートの data/stop_requested.flag を検出すると終了処理を行います（起動時のスキップや実行中の停止）。
- Monitoring 側の KillSwitch はリスク条件（ドローダウンやポジション過多）を満たすと data/kill.flag を書き込み ExecutionEngine に停止シグナルを送ります（ExecutionEngine 側で kill.flag を検出して停止する仕組みが想定されています）。
- kill.flag のパスは Settings.kill_flag_path で設定可能。
- Kill flag の手動クリアはファイルを削除するだけです（例: rm data/kill.flag）。

ログ
----
- ログはコンソール（stdout）と日次ローテートされたファイルに出力されます（logs/<app_name>.log）。
- ログ設定は kabusys.utils.logging_setup.setup_logging を通じて共通化されています。
- LOG_DIR, LOG_LEVEL 環境変数で制御可能。

DB ファイル（デフォルト）
------------------------
- DuckDB: data/kabusys.duckdb
- Monitoring SQLite: data/monitoring.db
- Paper trading SQLite: data/paper_trading.db（paper_trading モード用）

注意事項 / 運用メモ
-----------------
- paper_trading モードは本番の取引 API にアクセスせず、別の SQLite に結果を記録するため安全に検証できます。
- AI 機能（news_nlp, regime_detector）を利用する場合は OPENAI_API_KEY が必要です。API 呼び出しはリトライ・フェイルセーフを備えていますが、利用料・レート制限に注意してください。
- config/*.yaml の内容検証は PyYAML がインストールされている場合に行われます。インストールしていない場合は YAML チェックがスキップされます。
- .env は絶対に Git にコミットしないでください（config_setup でも注意書きあり）。
- Process 優先度や CPU affinity の設定は psutil を利用しており、権限や OS によっては失敗する場合があります（警告ログレベルでスキップ）。

主要ディレクトリ構成（抜粋）
---------------------------
src/kabusys/
- __init__.py
- config.py                 — 環境変数 / Settings 管理
- config_setup.py           — .env 対話ウィザード
- validate_config.py        — 設定検証 CLI
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
- utils/
  - logging_setup.py        — ログ初期化ユーティリティ
  - process_priority.py     — プロセス優先度設定ユーティリティ
- monitoring/
  - monitoring_db.py        — SQLite 永続化層
  - system_monitor.py       — システム状態・データ鮮度監視
  - risk_monitor.py         — ドローダウン・ポジション監視
  - kill_switch.py          — kill.flag 管理
  - monitoring_engine.py    — Monitor を束ねるエンジン
  - alert_manager.py        — （アラート送信の抽象化、実装は含まれる場合あり）
  - trade_monitor.py        — 発注ログ監視（存在）
- execution/                 — ExecutionEngine / BrokerFactory / OrderManager 等（実装あり）
- portfolio/                 — portfolio_builder, position_sizing, risk_adjustment
- research/                  — factor_research, feature_exploration
- ai/
  - news_nlp.py             — ニュースを LLM でスコア化
  - regime_detector.py      — 市場レジーム判定
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成

（上記は主要ファイルの抜粋です。詳細はソース配下を参照してください。）

開発 / デバッグ
----------------
- 単体機能のテストや run_once 相当の動作確認は、MonitoringEngine.run_once のような単発実行用 API を利用できます。
- ログレベルを DEBUG に設定すると詳細な内部ログが得られます（LOG_LEVEL=DEBUG）。
- DuckDB に保存される時系列データや raw_news 等を用意することで research/ai モジュールをローカルで検証できます。

ライセンス・バージョン
---------------------
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）
- ライセンス情報はリポジトリのトップレベル LICENSE を参照してください（ない場合はプロジェクト方針に従ってください）。

付録：よく使うコマンド（まとめ）
-----------------------------
- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- Execution 起動: python -m kabusys.run_execution
- Monitoring 起動: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

不明点や README に追加したい項目（例: 実際の ExecutionEngine の設定、Broker 実装、アラート先の詳細など）があれば教えてください。必要に応じてサンプル .env のテンプレートや運用チェックリストも作成します。