KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株向けの自動売買/リサーチ基盤の一部実装です。本リポジトリは以下の責務を持つモジュール群を含みます。

- 実行エンジン（ExecutionEngine）と発注ロジック（execution/*）
- 監視・アラート・Kill Switch（monitoring/*）
- ポートフォリオ構築・ポジションサイジング（portfolio/*）
- ファクター／リサーチ（research/*）
- AI を使ったニュースセンチメント・レジーム判定（ai/*）
- ユーティリティ（utils/*）、設定管理・ウィザード（config_*）など
- 開発用ツール（tools/*）

特徴・主な機能
----------------
- マルチモード実行環境: development / paper_trading / live（KABUSYS_ENV）
  - paper_trading モードでは MockBrokerClient を使い、データを data/paper_trading.db に保存して本番 DB と分離。
- 監視コンポーネント:
  - SystemMonitor: CPU/MEM/DISK、プロセス生存、株価データ鮮度を監視
  - TradeMonitor / RiskMonitor: 注文滞留・約定異常・ドローダウン・ポジション上限を監視
  - KillSwitch: しきい値超過時に data/kill.flag を書き、ExecutionEngine を停止可能
- ログ管理: 統一的なログ設定（console + 日次ローテーション、logs/<app>.log）
- ポートフォリオ構築: 候補選定・等分/スコア重み配分・リスク調整・ポジション数算出（単元丸め対応）
- リサーチ: Momentum/Value/Volatility 等のファクター計算（DuckDB を利用）
- AI 機能:
  - news_nlp: OpenAI (gpt-4o-mini 等) によるニュース記事のセンチメント集約 → ai_scores へ保存
  - regime_detector: ETF（1321等）の MA とマクロセンチメントを合成して市場レジーム判定
- 開発支援ツール:
  - .env 設定ウィザード（config_setup）
  - 起動前設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）

前提・依存
----------
主な Python ライブラリ（環境に応じてインストールしてください）:
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config/*.yaml の構文チェックを行う場合のみ必要）
（sqlite3 は標準ライブラリで利用）

セットアップ手順
----------------
1. リポジトリをクローンして仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （AI 機能や YAML 検証を使わない場合は openai / PyYAML は任意）

3. .env の作成
   - 対話式ウィザードで作成: python -m kabusys.config_setup
   - 手動で作成する場合は .env.example を参考に .env をルートに配置してください。
   - 自動ロード:
     - 起動時に .env / .env.local を自動で読み込みます（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

主な環境変数（重要）
-------------------
（詳細は config.py を参照）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要な任意/設定:
- KABUSYS_ENV: development | paper_trading | live  (デフォルト: development)
- DUCKDB_PATH: data/kabusys.duckdb（分析用）
- SQLITE_PATH: data/monitoring.db（監視/履歴用）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用 DB）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR
- OPENAI_API_KEY: AI モジュール利用時に必要
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動でクリアする（本番では 0 推奨）

使い方（起動・ユーティリティ）
------------------------------

1. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱い（exit code 1）

2. 設定ウィザード（.env 作成）
   - python -m kabusys.config_setup

3. ExecutionEngine（発注エンジン）の起動
   - 簡単にローカル実行: python -m kabusys.run_execution
   - paper_trading モードで実行する場合:
     - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
     - この場合 MockBrokerClient が利用され、デフォルトで data/paper_trading.db に記録されます。
   - 実行時の挙動:
     - 起動時にプロセス優先度を high に設定し、settings.pid_file_path に PID を出力します。
     - data/stop_requested.flag が存在すると起動せず即終了します。
     - 停止は kill.flag（KillSwitch）や stop_requested.flag を用いる運用を想定。

4. Monitoring（監視ループ）の起動
   - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）
   - Monitoring は設定にかかわらず本番 sqlite_path（SQLITE_PATH）を使用して監視テーブルを管理します。
   - run_monitoring は data/stop_requested.flag を監視して停止します。

5. 停止・Kill Switch
   - KillSwitch は条件に合致すると data/kill.flag を書き込み、ExecutionEngine 側がこれを検出して停止します。
   - また管理用に data/stop_requested.flag を作成すると run_* スクリプトのループを止めるための簡易停止が可能です。

6. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report
   - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
   - DB 指定: --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数優先）

ログ・PID・フラグファイル
-------------------------
- logs/: ログファイルが出力されます（app 名でファイル名が決まる、日次ローテーション）
- data/execution.pid (デフォルト): ExecutionEngine の PID 保存先
- data/kill.flag: KillSwitch が書き込む停止フラグ（存在すれば ExecutionEngine により停止される）
- data/stop_requested.flag: 起動スクリプト（run_monitoring / run_execution）が監視している停止フラグ

開発時の注意点
--------------
- .env は機密情報を含むため決してリポジトリにコミットしないでください。
- DuckDB は分析用の読み取り／書き込み先です。AI モジュールやリサーチは DuckDB のテーブル（prices_daily, raw_financials, raw_news 等）を参照します。
- AI 機能を有効にする場合は OPENAI_API_KEY を設定してください。
- validate_config は起動前の基本チェックを提供します。production (KABUSYS_ENV=live) の場合は特に注意して実行してください。

ディレクトリ構成（主要ファイル）
-------------------------------
以下は src/kabusys 配下の主要モジュールの一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数/設定管理
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 起動前設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py           — ログ設定ユーティリティ
    - process_priority.py        — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py           — SQLite 永続化（system_status / trade_logs / positions / risk_logs / dashboard）
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
  - execution/                   — 発注関連（broker_factory, execution_engine, order_manager, risk_manager 等）
  - portfolio/                   — portfolio_builder, position_sizing, risk_adjustment
  - research/                    — factor_research, feature_exploration
  - ai/
    - news_nlp.py                — ニュース NLP（OpenAI 呼び出し）
    - regime_detector.py         — レジーム判定
  - data/ (想定 runtime ディレクトリ)
    - monitoring.db (SQLITE_PATH デフォルト)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH デフォルト)
    - kabusys.duckdb (DUCKDB_PATH デフォルト)
    - kill.flag / stop_requested.flag / execution.pid

よくある運用例
--------------
- ローカルで設定ウィザード → 設定検証 → paper_trading で実行
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- 監視プロセスをデーモンとして実行（簡易例）
  - nohup python -m kabusys.run_monitoring &

- Paper Trading レポートを生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10

補足
----
- 設定の読み込み順: OS 環境変数 > .env.local > .env（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）
- run_monitoring は MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
- AI 機能（news_nlp, regime_detector）は OpenAI API の呼び出しを伴い、API 失敗時はフェイルセーフで処理を続行する（既定のフォールバック値を使用）

ライセンス・貢献
----------------
（ここにライセンス情報や貢献方法を追記してください）

以上。README に不明点や追加で書いてほしい実運用手順（systemd ユニット例、Docker 化手順など）があればお知らせください。