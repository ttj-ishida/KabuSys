README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤の骨格を提供するパッケージです。
本リポジトリには以下の主要機能を含みます:

- 実行エンジン（ExecutionEngine）の起動スクリプト（発注処理）
- 監視モジュール（System / Trade / Risk をポーリングし Kill Switch を管理）
- ポートフォリオ構築ユーティリティ（候補選定・重み計算・ポジションサイズ算出）
- ファクター計算・特徴量探索（DuckDB を用いたファクター算出）
- AI ベースのニュース NLP / レジーム判定（OpenAI API を利用）
- 各種ユーティリティ（ログ設定、環境設定ウィザード、設定検証など）
- ペーパートレード検証レポート出力スクリプト

主な設計方針:
- DB は DuckDB（分析）と SQLite（監視／発注ログ）を併用
- 本番とペーパートレードの DB 分離をサポート
- LLM 呼び出しは冗長性・バックオフ・バリデーションを組み込む
- 自動化に伴う安全策（Kill Switch、リスク監視、プロセス優先度設定）を実装

機能一覧
--------
- 実行 / 監視
  - run_execution.py: ExecutionEngine を起動。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用して data/paper_trading.db に記録。
  - run_monitoring.py: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔変更可）。
- 設定管理
  - config_setup.py: .env を対話的に作成・更新するウィザード。
  - validate_config.py: .env と config/*.yaml の事前検証 CLI（--strict オプションあり）。
- 監視系
  - monitoring/*: MonitoringDB（永続化）、SystemMonitor / TradeMonitor / RiskMonitor、KillSwitch、MonitoringEngine、アラート管理。
- ポートフォリオ構築
  - portfolio/*: 候補選定、等重／スコア加重、セクター制限、ポジションサイズ計算（単元丸め含む）。
- リサーチ
  - research/*: ファクター計算（モメンタム／バリュー／ボラティリティ）、将来リターン、IC 計算、統計サマリー。
- AI
  - ai/news_nlp.py: raw_news をまとめて OpenAI に送信し ai_scores を書き込む。
  - ai/regime_detector.py: ETF の MA とマクロニュースを組み合わせて市場レジームを判定。
- ツール
  - tools/paper_verification_report.py: ペーパートレード DB から検証レポートを生成。

セットアップ手順
----------------
以下は一般的なセットアップ手順の例です。プロジェクト固有の追加依存は適宜追記してください。

1. レポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存ライブラリのインストール（主要依存）
   - pip install duckdb psutil openai
   - PyYAML は config/*.yaml の構文チェックに使われます（任意）:
     - pip install PyYAML

   （requirements.txt がある場合は pip install -r requirements.txt を使用）

4. 環境変数設定（.env）
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - 主要な環境変数（.env の主な項目）
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB, デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード時の専用 SQLite、default: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を利用する場合）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート通知用、任意）
     - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR）
     - KILL_FLAG_CLEAR_ON_START（1 にすると起動時に kill.flag を自動クリア。production では 0 推奨）
   - 自動ロード:
     - 実行時、プロジェクトルートに .env / .env.local があれば自動的にロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告をエラー扱いにする場合は --strict を付ける

使い方
------
基本的な実行コマンド（パッケージモードでの実行）:

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使い、PAPER_TRADING_SQLITE_PATH に発注ログを記録します。
    - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
    - 実行中の停止は data/stop_requested.flag を作成することで実行スレッドに停止を伝えます。

- Monitoring（ポーリング監視）起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV にかかわらず sqlite_path（本番の監視 DB）を使用します。
  - 停止はプロジェクトルート/data/stop_requested.flag を作成して行います。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを指定可能（省略時は PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db）

- AI 機能（モジュール API）
  - ai.score_news(conn, target_date, api_key=None) — OpenAI API キーを環境変数 OPENAI_API_KEY に設定して使用
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは直接モジュール関数として呼び出すことができます（DuckDB 接続を渡す）。

ログ
----
- ログはデフォルトで logs/<app_name>.log に日次ローテーション（30 日保持）で出力されます。
- app_name は setup_logging に渡す値（run_execution/set to "execution"、run_monitoring/set to "monitoring" 等）に対応。
- LOG_DIR 環境変数でログディレクトリを変更できます。

停止と Kill Switch
-----------------
- ExecutionEngine の強制停止用フラグ:
  - KillSwitch は data/kill.flag を書くことで ExecutionEngine に停止を促す仕組みを提供します（kill.flag を書くと停止を試みる）。
  - KillSwitch を書く基準は Monitoring の RiskMonitor などが判断します。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していると kill.flag を自動的にクリアします（本番では 0 推奨）。
- run_execution / run_monitoring の即時終了:
  - data/stop_requested.flag を作成すると起動中ループが検知して終了します（管理者の手動停止用）。

ディレクトリ構成（抜粋）
-----------------------
- src/
  - kabusys/
    - __init__.py
    - config.py               — 環境変数/設定管理
    - config_setup.py         — .env 対話ウィザード
    - validate_config.py      — 設定検証 CLI
    - run_execution.py        — ExecutionEngine 起動スクリプト
    - run_monitoring.py       — Monitoring 起動スクリプト
    - utils/
      - logging_setup.py      — ログ設定ユーティリティ
      - process_priority.py   — プロセス優先度 / CPU affinity
    - monitoring/
      - monitoring_db.py      — SQLite 永続化層（初期化・API）
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py      (アラート管理／LINE 等）
    - execution/              — ExecutionEngine / OrderManager / BrokerFactory 等
    - portfolio/              — portfolio_builder, position_sizing, risk_adjustment
    - research/               — factor_research, feature_exploration
    - ai/
      - news_nlp.py
      - regime_detector.py
    - tools/
      - paper_verification_report.py
    - data/                   — 実行時に使用するファイル（例: *.db, *.pid, stop_requested.flag, kill.flag）
- config/
  - system_config.yaml, data_config.yaml, strategy_config.yaml, risk_config.yaml, execution_config.yaml, monitoring_config.yaml
  （config/*.yaml の存在は validate_config.py で確認できます。PyYAML が無い場合は YAML 検証はスキップされます）

注意点 / トラブルシューティング
--------------------------------
- OpenAI API を使用する機能を利用する場合、OPENAI_API_KEY を設定してください。API エラー時は多くの処理がフォールバック（スコア 0 や処理スキップ）するよう設計されていますが、API キーが無いと機能は使えません。
- psutil を利用してプロセス優先度や CPU affinity を設定します。権限不足で警告が出る場合がありますが、スキップして継続します。
- DuckDB および SQLite のファイルはデフォルトで data/ 配下に作成されます。必要に応じて .env でパスを上書きしてください。
- ログディレクトリの作成に失敗すると、ファイル出力は無効化されコンソールのみの出力になります。
- run_monitoring は監視 DB（SQLITE_PATH）を使用します。監視は常に sqlite_path を参照する点に注意してください（環境に依らず本番監視 DB を想定）。

ライセンス / バージョン
-----------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（例: 0.1.0）。

お問い合わせ / 貢献
------------------
バグ報告や機能改善の提案は issue を立ててください。Pull Request は歓迎します。README に未記載の実行フローや設定がある場合はドキュメントの追加をお願いします。

以上。README に不足している具体的な導入手順（requirements.txt、DB 初期データ生成スクリプトなど）があれば、リポジトリに合わせて追記してください。