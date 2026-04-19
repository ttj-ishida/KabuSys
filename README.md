README — KabuSys（日本語）
========================

概要
----
KabuSys は日本株の自動売買／リサーチ用ライブラリ群です。  
ポートフォリオ構築、ポジションサイジング、リスク制御、監視（Monitoring）、実行エンジン（Execution）、AI（ニュースセンチメント／レジーム判定）、リサーチ（ファクター計算）などのコンポーネントを含みます。  
テスト用のペーパートレード（完全に本番 DB と分離）や、モジュール単位での検証ツールが用意されています。

主な機能
--------
- 実行エンジン起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録（本番 DB と分離）。
  - プロセス優先度設定、PID ファイル管理、スレッドでの実行／停止処理をサポート。
- 監視プロセス起動スクリプト（run_monitoring.py）
  - SystemMonitor 等をポーリングし、監視ログ（SQLite）へ永続化。MONITOR_POLL_INTERVAL でポーリング間隔を調整可能（デフォルト 60 秒）。
  - 監視は本番 sqlite_path を使用（環境にかかわらず本番監視 DB を参照する設計）。
- 監視DB ラッパー（monitoring/monitoring_db.py）
  - system_status / trade_logs / positions / risk_logs / dashboard 等のテーブル作成・読み書き機能を提供（冪等）。
- リスク監視（RiskMonitor）、KillSwitch、MonitoringEngine、各種アラート連携（AlertManager：別モジュール）による自動停止判断
  - 例：ドローダウン閾値超過やポジション数オーバー時に kill.flag を作成して ExecutionEngine を停止
- ポートフォリオ構築（portfolio/*）
  - 候補選定、等金額／スコア加重、セクター制限、レジーム乗数、株数決定・丸め（単元株）等の純粋関数群
- リサーチ（research/*）
  - DuckDB を使ったファクター（モメンタム、バリュー、ボラティリティ）計算、将来リターン計算、IC 計測、統計サマリ等
- AI（ai/*）
  - OpenAI を使ったニュースセンチメント（news_nlp）、市場レジーム判定（regime_detector）機能
  - API エラー時のリトライやフェイルセーフ機構あり
- ユーティリティ
  - .env 対話式ウィザード（config_setup.py）
  - 起動前設定検証 CLI（validate_config.py）
  - ロギング設定（utils/logging_setup.py）
  - プロセス優先度 / CPU affinity ユーティリティ（utils/process_priority.py）
- ツール
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）

セットアップ手順
---------------
1. リポジトリをチェックアウト／クローン
   - ルートに pyproject.toml または .git がある想定（設定自動ロードに使用）

2. Python 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate あるいは .venv\Scripts\activate

3. 依存パッケージをインストール
   - 主要依存例（requirements.txt があればそれを使用）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証で任意）
   - 例:
     - pip install duckdb psutil openai PyYAML

4. 環境変数（.env）を準備
   - 推奨: 対話式ウィザードを使用して .env を作成
     - python -m kabusys.config_setup
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要なオプション / デフォルト
     - KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_LEVEL: INFO
     - LOG_DIR: logs/
     - OPENAI_API_KEY: OpenAI を使う機能で必須

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告も FAIL 扱いにする場合:
     - python -m kabusys.validate_config --strict

使い方
------
- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB を使用（PAPER_TRADING_SQLITE_PATH）
    - 起動時に data/stop_requested.flag が存在すると起動せず終了
    - PID ファイル（デフォルト data/execution.pid）を管理

- 監視プロセスを起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で変更できる（デフォルト 60）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 停止: リポジトリの data/stop_requested.flag を作成するとループを抜けて終了（run_execution からも同一フラグを参照）
  - 監視は常に本番 sqlite_path を使う設計（KABUSYS_ENV に依存しない点に注意）

- .env の対話式作成/更新
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict で警告もエラー扱い

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - --db /path/to/paper_trading.db
    - または環境変数 PAPER_TRADING_SQLITE_PATH を設定

- AI 機能（ニュース NLP / レジーム判定）
  - OPENAI_API_KEY を環境変数に設定して使用
  - モジュール関数を呼び出して DuckDB 接続と target_date を渡して実行（API キーは引数でも渡せます）
  - OpenAI 呼び出しはリトライ・フェイルセーフ実装あり（失敗時は安全側のフォールバック）

ログ・ファイル・フラグ
--------------------
- ログ
  - デフォルト: logs/<app_name>.log（TimedRotatingFileHandler による日次ローテーション、バックアップ 30 日分）
  - LOG_DIR 環境変数で変更可
  - LOG_LEVEL 環境変数（DEBUG/INFO/WARNING/ERROR/CRITICAL）または setup_logging の引数で調整

- DB
  - DuckDB: デフォルト data/kabusys.duckdb（duckdb_path）
  - SQLite (monitoring): data/monitoring.db（sqlite_path）
  - Paper Trading SQLite: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）

- PID / フラグ
  - PID ファイル: data/execution.pid（ExecutionEngine 用）
  - 停止要求フラグ: data/stop_requested.flag（run_monitoring / run_execution が参照）
  - Kill Switch フラグ: data/kill.flag（KillSwitch が作成。ExecutionEngine 起動時の KILL_FLAG_CLEAR_ON_START=1 に注意）

ディレクトリ構成（主要ファイル）
------------------------------
（パスはパッケージルート src/kabusys を基準に記載）

- kabusys/
  - __init__.py
  - config.py                 — 環境変数・.env 自動ロード、Settings クラス
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py             — ニュースセンチメント（OpenAI）
    - regime_detector.py      — レジーム判定（OpenAI + ETF MA）
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層
    - system_monitor.py       — システム・データ鮮度監視
    - risk_monitor.py         — ドローダウン・ポジション監視
    - trade_monitor.py        — (発注ログ監視: 別ファイル)
    - kill_switch.py          — kill.flag 書き込みユーティリティ
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - alert_manager.py        — (通知管理: 別ファイル)
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 株数決定・スケーリング
    - risk_adjustment.py      — セクター制限・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py      — モメンタム／ボラティリティ／バリュー計算
    - feature_exploration.py  — IC / フォワードリターン / 統計
    - __init__.py
  - utils/
    - logging_setup.py        — ロギング初期化ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity
    - __init__.py
  - execution/                — Execution 関連の実装群（BrokerFactory 等）
  - data/                     — （デフォルトの DB / フラグ / PID を配置するディレクトリ）
  - その他: research, portfolio, monitoring などの補助モジュール群

運用上の注意
------------
- KABUSYS_ENV の設定
  - development / paper_trading / live のいずれかを設定してください。live は本番であるため注意が必要（validate_config にて警告）。
- Paper Trading
  - ペーパートレード環境は本番 DB と完全分離されるよう実装されています（PAPER_TRADING_SQLITE_PATH を使用）。
- モニタリングは本番 DB を使用する点に注意
  - run_monitoring は Settings により本番 sqlite_path を参照します（KABUSYS_ENV にかかわらず）。
- Kill Switch / stop flag
  - kill.flag（KillSwitch）と stop_requested.flag（run_* スクリプトが監視する停止トリガー）は運用上重要です。特に本番では誤って自動クリアしないよう KILL_FLAG_CLEAR_ON_START の設定に注意してください。

開発／拡張のヒント
------------------
- DuckDB 接続を渡して research / ai モジュールを単体テストできます（DB のテスト用データを用意）。
- OpenAI API を使う関数は api_key を引数でも渡せるため、テスト時にモックを注入しやすく設計されています。
- logging_setup.setup_logging を各起動スクリプトで呼ぶことでログ挙動を統一しています。

ライセンス / バージョン
-----------------------
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）

問い合わせ・貢献
----------------
- バグ報告や機能追加はリポジトリの Issue を利用してください。README の補足や CI・テストスイートの追加も歓迎します。

以上。README に含めたい追加情報（例: requirements.txt の内容、実際の起動コマンドの systemd ユニット例など）があれば教えてください。必要に応じて追記します。