README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ・監視を目的とした Python パッケージです。本リポジトリは以下の主要機能を持ちます。

- 実行エンジン（ExecutionEngine）による発注ロジック（ペーパートレード / 本番切替可能）
- 監視（Monitoring）: システム状態・注文状況・リスク指標の定期チェックとアラート／Kill Switch
- ポートフォリオ構築ユーティリティ（銘柄選定・配分・株数算出）
- リサーチ／ファクター計算（モメンタム、バリュー、ボラティリティ 等）
- AI モジュール（ニュースセンチメント、レジーム判定） — OpenAI を利用
- 付帯ツール（設定ウィザード、設定検証、ペーパートレード検証レポート など）

主な設計方針:
- DB は DuckDB（分析用）と SQLite（監視・発注履歴）を併用
- 本番とペーパートレードは DB を分離（設定で切替）
- ルックアヘッドバイアスを避ける設計（データ取得で target_date を尊重）
- フェイルセーフ（API 失敗時は安全側のフォールバック）を重視

機能一覧
--------
- run_execution: ExecutionEngine 起動スクリプト（KABUSYS_ENV による挙動切替）
  - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し data/paper_trading.db に記録
  - プロセス優先度の設定、PID ファイル管理、停止フラグ対応
- run_monitoring: SystemMonitor ポーリングループ起動スクリプト
  - ポーリング間隔は MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）
  - 監視 DB は環境にかかわらず本番 sqlite_path を使用
- monitoring パッケージ:
  - SystemMonitor: CPU/メモリ/Disk、プロセス生存、データ鮮度をチェック
  - TradeMonitor: 注文遅延・約定異常の検出（trade_logs 参照）
  - RiskMonitor: ドローダウン・ポジション上限の監視、ダッシュボード更新
  - KillSwitch: 条件を満たせば data/kill.flag を生成し ExecutionEngine を止めるシグナル
  - MonitoringDB: SQLite を使った監視ログ永続化
  - MonitoringEngine: 上記モジュールを束ねるポーリングエンジン
- portfolio パッケージ:
  - 銘柄選定、等分配・スコア加重配分、セクターキャップ適用、ポジションサイズ計算
- research パッケージ:
  - ファクター計算（momentum, value, volatility）、将来リターン、IC 計算、統計サマリー
- ai パッケージ:
  - news_nlp: raw_news を OpenAI に送り銘柄毎にセンチメントを算出、ai_scores へ保存
  - regime_detector: マクロニュース + ETF MA に基づく市場レジーム判定
- utils:
  - logging_setup: 統一ログ設定（stdout + 日次ローテートファイル）
  - process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ
- tools:
  - paper_verification_report: ペーパートレード DB から検証レポートを生成
- 設定周り:
  - config_setup: .env の対話式生成ウィザード
  - validate_config: .env と config/*.yaml の事前チェック CLI

前提条件
--------
- Python 3.9+（コード内型ヒントや一部の記法を想定）
- システムにより追加のネイティブ依存がある場合があります（psutil 等）
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- AI 機能を使う場合:
  - OPENAI_API_KEY（OpenAI API を利用）

セットアップ手順
---------------
1. リポジトリをクローンし、作業ディレクトリへ移動します。
   - 例: git clone ... && cd <repo>

2. 仮想環境を作成して有効化します（推奨）。
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストールします。
   - 推奨: pip install -r requirements.txt
   - requirements.txt が無い場合の主要パッケージ例:
     - pip install duckdb psutil openai PyYAML

4. .env を作成します（config_setup ウィザード推奨）。
   - python -m kabusys.config_setup
   - あるいは .env を手動で作成（例: DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）
   - 注意: .env は絶対に Git にコミットしないでください。

5. 設定の検証（任意）。
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

主要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: デフォルト data/monitoring.db（Monitoring は常に本番 sqlite_path を参照）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- OPENAI_API_KEY: OpenAI を使う場合
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START: 本番での自動クリアは危険（0 推奨）

使い方（起動例）
----------------

1. ExecutionEngine 起動（本番 / ペーパートレードの切替）
   - ペーパートレード:
     - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
     - この場合、MockBrokerClient を使用し data/paper_trading.db に記録されます。
   - 本番:
     - KABUSYS_ENV=live python -m kabusys.run_execution

2. Monitoring 起動
   - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で変更できます（例: MONITOR_POLL_INTERVAL=30）。

注意点:
- run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使って監視 DB を初期化・書込します。

3. 設定ウィザード / 検証
   - 設定ウィザード: python -m kabusys.config_setup
   - 設定検証: python -m kabusys.validate_config [--strict]

4. ペーパートレード検証レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - --db オプションで DB パスを指定可能（PAPER_TRADING_SQLITE_PATH 環境変数でも指定可）

5. AI / リサーチ関数の利用（プログラムから）
   - 例: from kabusys.ai import score_news
     - score_news(conn, target_date, api_key=...)
   - 例: from kabusys.research import calc_momentum
     - calc_momentum(duckdb_conn, date(2026, 4, 1))

停止方法
--------
- ExecutionEngine を安全に停止するには、monitoring の Kill Switch により data/kill.flag が書き込まれるか、data/stop_requested.flag を作成して監視スレッドやスクリプトに停止を通知できます。
- run_execution / run_monitoring の両方は stop_requested.flag を監視しているため、プロジェクトルート下の data/stop_requested.flag を作成するとループ処理を終了します。
- kill.flag は ExecutionEngine に対する停止シグナル（KILL_FLAG_CLEAR_ON_START 設定に注意）。

ログ / データ配置
-----------------
- デフォルトのログディレクトリ: logs/
  - ログは日次ローテーションで <app_name>.log に出力されます（TimedRotatingFileHandler、30日分保持）
- デフォルトのデータパス:
  - DuckDB: data/kabusys.duckdb
  - SQLite（監視）: data/monitoring.db
  - SQLite（ペーパー）: data/paper_trading.db
- PID / フラグ:
  - data/execution.pid（ExecutionEngine の PID）
  - data/stop_requested.flag（外部による停止要求）
  - data/kill.flag（Kill Switch）

ディレクトリ構成
----------------
（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / .env 自動ロードと Settings クラス
  - config_setup.py                — .env 対話式ウィザード
  - validate_config.py             — 起動前の設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — ペーパートレード検証レポート
  - utils/
    - logging_setup.py             — 共通ログセットアップ
    - process_priority.py          — プロセス優先度・CPU affinity
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (アラート送信処理)
  - execution/                      — 発注関連（Engine, order_manager, broker_factory 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py

開発・テストのヒント
--------------------
- .env の自動読み込みはデフォルトで有効です。テスト時に無効化するには
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- PyYAML がインストールされていない場合、validate_config は YAML 内容検証をスキップします（警告）。
- OpenAI 呼び出し部分はユニットテスト用に内部呼び出し関数を差し替えられるよう設計されています（patch 可能）。
- ローカルで安全に試すには KABUSYS_ENV=development または paper_trading を使用してください（live は注意）。

ライセンス / バージョン
-----------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（現状: 0.1.0）。

お問い合わせ
----------
不明点や修正提案はリポジトリの Issue に記載してください。README に載っていない実装詳細や運用上の注意点はコードコメント（各モジュールの docstring）に記載していますので参照してください。