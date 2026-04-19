KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株向けの自動売買・研究・監視用ライブラリ兼実行環境です。  
このリポジトリは次の主要機能を備えます。

- 戦略・ポートフォリオ構築ロジック（銘柄選定、重み付け、ポジション決定）
- 研究用ファクター計算・特徴量解析（DuckDB を用いたオフライン分析）
- 実行エンジン（ExecutionEngine）および監視（MonitoringEngine）
- Paper Trading 検証レポート生成ツール
- ニュース NLP / 市場レジーム判定（OpenAI API を利用）
- 監視ログ永続化（SQLite）・モニタリング用ユーティリティ

主な特徴
-------
- モジュール設計により、研究（research）→ ポートフォリオ構築（portfolio）→ 発注・管理（execution）→ 監視（monitoring）を分離
- DuckDB を使った高速な時系列 / 財務データ集計
- .env ベースの設定管理と対話式ウィザード（config_setup）
- 起動前チェック（validate_config）による設定検証
- Kill Switch（監視で危険を検出したら ExecutionEngine を停止する仕組み）
- Paper Trading と Live Trading を分離する設計（DB などを切り替え可能）
- ログはコンソール(stdout) と日次ローテートファイルに出力（logs/<app>.log）

必須外部ライブラリ（代表）
-------------------------
実行に必要な主要パッケージ（抜粋）:
- duckdb
- psutil
- openai
- PyYAML（config ファイル検証は任意）
標準ライブラリ: sqlite3, logging, threading, datetime など

セットアップ手順
----------------

1. Python 環境を作成
   - Python 3.9+ を推奨。仮想環境（venv/conda 等）を使って下さい。

2. 依存パッケージをインストール
   - 例:
     pip install duckdb psutil openai pyyaml

   （プロジェクトに requirements.txt がある場合はそれを利用してください）

3. .env の作成
   - 対話式ウィザードで .env を生成できます:
     python -m kabusys.config_setup
   - あるいは手動で .env を用意。自動読み込み: プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）。

4. 設定検証（推奨）
   - 起動前に設定を検証:
     python -m kabusys.validate_config
   - 警告も FAIL にしたい場合:
     python -m kabusys.validate_config --strict

5. データベース等ディレクトリの準備
   - デフォルトで data/ 以下に SQLite / DuckDB、logs/ にログが作成されます。権限を確認してください。

主要な環境変数（要確認）
-----------------------
（抜粋。詳しくは config.py を参照）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意・重要:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: デフォルト data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB（デフォルト data/paper_trading.db）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
- OPENAI_API_KEY: ニュース NLP / レジーム判定で使用する場合必須
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）

使い方（起動・ツール）
---------------------

- 環境設定ウィザード（.env 生成）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  （--strict を付けると警告も失敗扱い）

- 実行エンジン（ExecutionEngine）起動
  python -m kabusys.run_execution
  説明:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ記録して本番 DB と分離します。
    - 起動時に data/stop_requested.flag が既に存在する場合は起動せず終了します。
    - プロセス優先度を high に設定します（psutil を利用）。

- 監視プロセス起動
  python -m kabusys.run_monitoring
  説明:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可（デフォルト 60 秒）。
    - 監視は Settings.sqlite_path（デフォルトの本番 monitoring DB）を利用します（KABUSYS_ENV に依存しない点に注意）。
    - data/stop_requested.flag を検知するとループを抜けます。

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report
  オプション:
    --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  説明:
    - PAPER_TRADING_SQLITE_PATH または --db で指定した DB を参照してレポートを生成します。

- AI（ニュース NLP / レジーム判定）
  - ai モジュールは OpenAI API（例: gpt-4o-mini）を呼び出します。API キーは環境変数 OPENAI_API_KEY で指定してください。
  - 実行関数:
    - kabusys.ai.score_news
    - kabusys.ai.regime_detector.score_regime
  - API 呼び出しはリトライやバックオフの実装が組み込まれていますが、APIキー/料金には注意してください。

ログと運用
----------
- ログ出力は kabusys.utils.logging_setup により統一管理されます。
- デフォルト出力先:
  - stdout（StreamHandler）
  - ファイル: logs/<app_name>.log（TimedRotatingFileHandler、日次ローテーション、30日保持）
- LOG_DIR 環境変数でログディレクトリを指定可。

Kill Switch / 停止運用
---------------------
- KillSwitch によってリスク（ドローダウンやポジション過多）が判定されると data/kill.flag が書き込まれ、ExecutionEngine 停止のトリガーとして利用できます。
- 実行停止要求は data/stop_requested.flag を作成することで run_monitoring や run_execution が検知して安全に終了します。
- ExecutionEngine の pid は data/execution.pid に書き出されます。

ディレクトリ構成（主要ファイル）
-------------------------------

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/設定読み込み
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py       — SQLite 監視 DB レイヤ
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — （注文関連監視）
    - risk_monitor.py        — ドローダウン／ポジション上限監視
    - kill_switch.py         — Kill Switch 実装
    - monitoring_engine.py   — 各 Monitor を束ねる実行ループ
    - alert_manager.py       — （アラート送信管理: LINE など）
  - execution/                — ExecutionEngine・Order 管理等（発注ロジック）
  - portfolio/
    - portfolio_builder.py   — 候補選定・等重/スコア重み計算
    - position_sizing.py     — 株数計算・合計キャップ処理
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — 各種ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン・IC・統計
  - ai/
    - news_nlp.py            — ニュースを LLM でスコアリング
    - regime_detector.py     — 市場レジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - data/ (実行時に生成)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading モード)
    - stop_requested.flag
    - kill.flag
    - execution.pid

注意点 / 運用上のヒント
-----------------------
- KABUSYS_ENV は development / paper_trading / live をサポート。live を指定する場合は十分な確認と通知設定（LINE 等）を行ってください。
- .env を絶対にリポジトリにコミットしないこと（config_setup でも警告が出ます）。
- 監視プロセスは monitoring DB に接続してログを保存します。monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使う点に注意。
- OpenAI を使う機能は API 呼び出しに料金が発生します。大量実行時や自動化前にテストを行ってください。
- duckdb/SQLite のバージョンや仕様によって executemany の挙動が異なる場合があります（コード内に互換性考慮の実装あり）。

開発者向け
----------
- コードはモジュール化されているため、個別関数（例: research.calc_momentum や portfolio.calc_position_sizes）をユニットテストしやすく設計されています。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テスト時に自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ロギング設定は setup_logging() を共通で呼び出すことで統一されます。ユニットテストではログ出力を抑制するかキャプチャしてください。

ライセンス・貢献
----------------
- 本リポジトリのライセンス情報・コントリビュート方法はプロジェクトルートの LICENSE / CONTRIBUTING を参照してください（存在しない場合はリポジトリ管理者に確認）。

問い合わせ
----------
不明点やバグ報告はリポジトリの Issue を立てるか、プロジェクト管理者へ連絡してください。

以上が README の概要です。追加で「インストール用 requirements.txt の例」や「運用用 systemd ユニット/cron のサンプル」「よくあるトラブルシュート」を追記したい場合は教えてください。