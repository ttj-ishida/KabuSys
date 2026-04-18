# KabuSys

日本株向け自動売買システムのコードベース。ポートフォリオ構築・発注実行（実取引 / ペーパートレード）・監視・AI を使ったニュースセンチメント判定・研究ユーティリティ等を含むモジュール群から構成されています。

以下はこのリポジトリの README（日本語）です。

---

目次
- プロジェクト概要
- 機能一覧
- 前提条件
- セットアップ手順
- 環境設定 (.env)
- 設定検証
- 実行方法（起動スクリプト / ツール）
- 停止方法・フラグについて
- ログ・データファイル
- ディレクトリ構成（主要ファイル一覧）
- 備考 / 注意点

---

プロジェクト概要
- KabuSys は日本株の自動売買を支援するライブラリ兼実行フレームワークです。
- システムは主要な機能を分離（execution, monitoring, research, ai, portfolio など）しており、実行用スクリプトでプロセスを起動して運用します。
- Paper Trading（ペーパートレード）モードがあり、本番データベースと分離して安全に検証できます。
- DuckDB を分析用に、SQLite を監視／トレードログ用に使用します。
- OpenAI を用いたニュースセンチメントや市場レジーム判定の機能を備えています（APIキーが必要）。

機能一覧
- ExecutionEngine 起動（run_execution.py）
  - 本番 / ペーパートレード切り替え（KABUSYS_ENV）
  - ブローカークライアント抽象化（実ブローカー / MockBroker の切替）
  - リスク管理・注文管理・約定照合など
- Monitoring（run_monitoring.py / monitoring モジュール）
  - システム稼働状況監視（CPU / メモリ / ディスク / プロセス生存）
  - 注文ログ監視、ドローダウン監視、KillSwitch による停止判定
  - アラート発行（LINE等の設定を利用する想定）
- Portfolio 構築（portfolio モジュール）
  - 候補選定、重み計算、ポジションサイズ算出、セクター上限適用などの純粋関数
- Research（research モジュール）
  - ファクター計算、将来リターン計算、IC（情報係数）算出、統計概要
  - DuckDB を使った SQL / Python ベースの計算
- AI（ai モジュール）
  - ニュースの NLP スコアリング（news_nlp.py）
  - 市場レジーム判定（regime_detector.py）
  - OpenAI API（gpt-4o-mini など）を利用（APIキー要）
- ツール
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）
- 設定支援
  - 対話式 .env 作成ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
- ユーティリティ
  - ロギング設定（utils/logging_setup.py）
  - プロセス優先度設定（utils/process_priority.py）
  - 設定読み込み／Settings（config.py）
- 永続化（monitoring/monitoring_db.py）
  - system_status, trade_logs, positions, risk_logs, dashboard テーブルの管理

前提条件
- Python 3.10 以上（コード内の型ヒントや union 演算子 `|` を使用しているため）
- システムにより追加のネイティブライブラリが必要な場合あり（psutil 等）
- 必要な Python パッケージ（主なもの）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config の YAML 検証を行う場合、任意）
- SQLite は標準ライブラリで利用可能

セットアップ手順（ローカル開発向け）
1. リポジトリをクローンしてワークディレクトリに移動
2. 仮想環境を作成して有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）
4. データディレクトリの作成（必要なら）
   - mkdir -p data logs

環境設定 (.env)
- 設定は環境変数または .env ファイルから読み込みます（config.py が自動でルートの .env / .env.local をロードします）。自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- 対話式ウィザードで .env を作成できます:
  - python -m kabusys.config_setup
- 主な環境変数（必須）
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
  - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- 主な環境変数（任意 / 説明）
  - KABUSYS_ENV — 実行環境 (development | paper_trading | live). デフォルト: development
    - paper_trading: MockBroker を使用し data/paper_trading.db を使用
    - live: 本番挙動（実発注など）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector 等で使用）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知設定（任意）
  - MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒。run_monitoring で参照、デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（live では危険。0 推奨）
- .env ファイルは機密情報を含むため Git にコミットしないでください（config_setup で生成されるヘッダーに注意書きがあります）。

設定検証
- 設定の整合性チェック:
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱い（exit(1)）

実行方法（起動スクリプト / 主要コマンド）
- 実行エンジン（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録します。本番環境（live）では本物のブローカークライアントを使用する設定になります。
  - 実行中に data/stop_requested.flag が作成されると起動を中止または実行を停止します（run_execution で参照）。
  - PID ファイル: Settings.pid_file_path（デフォルト data/execution.pid）
- 監視プロセス（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き（秒。デフォルト 60）
  - Monitoring は常に本番 sqlite_path を使用（環境にかかわらず監視 DB を共通で使用する設計の箇所あり）
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH > デフォルト data/paper_trading.db の順で解決）
- AI / 研究関数はライブラリ API として使用
  - 例: kabusys.ai.score_news(conn, target_date, api_key=...)
  - OpenAI を使う機能は OPENAI_API_KEY が必要
- ログ設定は共通ユーティリティを使用
  - setup_logging(app_name="execution") 等で logs/<app_name>.log に日次ローテーションで出力されます

停止方法・フラグについて
- kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）
  - KillSwitch（監視ロジック）が条件に該当した際に書き込み、ExecutionEngine に対して停止要求（外部的な“安全停止”）を出す仕組みのフラグ
  - KillSwitch.write は冪等（既に存在する場合は上書きしない）
- stop_requested.flag（data/stop_requested.flag）
  - run_execution / run_monitoring がループ中に参照しており、存在すると起動を中止または実行を停止します（手動で停止させたい場合に使う）
  - 実運用時の外部停止用フラグ
- 実行中の停止のためにファイルを削除/作成する場合は data ディレクトリのパーミッションに注意してください。

ログ / データファイル
- ログ: デフォルト logs/ ディレクトリ（環境変数 LOG_DIR で上書き可能）
  - ファイル名はアプリ名プレフィックス（例: execution.log, monitoring.log）で日次ローテーション
- データ:
  - DuckDB: data/kabusys.duckdb（デフォルト）
  - SQLite（監視）: data/monitoring.db（デフォルト）
  - SQLite（Paper Trading）: data/paper_trading.db（paper_trading モード用）
  - PID / フラグ: data/execution.pid, data/kill.flag, data/stop_requested.flag など

ディレクトリ構成（主要ファイル）
（src/kabusys 以下を想定。抜粋）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込み（Settings）
  - config_setup.py          — 対話式 .env ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度・CPU affinity 設定
  - execution/               — 発注 / エンジン関連（省略ファイル群）
  - monitoring/
    - monitoring_db.py       — SQLite テーブル初期化・永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI）によるスコアリング
    - regime_detector.py      — マーケットレジーム判定（OpenAI + MA）
    - __init__.py
  - tools/
    - paper_verification_report.py

備考 / 注意点
- 本リポジトリは実際の注文 API（kabuステーション等）や実取引を扱うため、live モード時は設定・権限に十分な注意が必要です。特に KABUSYS_ENV=live の際は .env の内容や Kill Switch の設定を慎重に確認してください。
- .env ファイルは機密情報（APIキー、パスワード）を含むため、決して Git にコミットしないでください。
- OpenAI を利用する機能は API コストおよびレート制限に注意してください。news_nlp と regime_detector にはリトライ・バックオフロジックが組み込まれていますが、API 使用料は発生します。
- DuckDB / SQLite のパスやログディレクトリの親ディレクトリが存在しない場合は、validate_config で警告が出ますが、起動時に自動作成されることが多いです。権限設定等も確認してください。
- Python の依存パッケージのバージョン互換性に注意してください（openai SDK のメジャーバージョンアップ等で API 呼び出し方が変わることがあります）。

---

簡単な運用フロー例
1. 仮想環境構築 & 依存インストール
2. python -m kabusys.config_setup で .env を生成
3. python -m kabusys.validate_config で設定を検証
4. python -m kabusys.run_monitoring をデーモンで起動（監視）
5. python -m kabusys.run_execution を起動（ExecutionEngine）
6. 実行中に問題があれば monitoring が kill.flag を書き込み ExecutionEngine を停止させる、または管理者が data/stop_requested.flag を作成して停止させる

---

追加ヘルプ
- 各スクリプトは Python の -m モードでエントリポイントとして動作します。詳細は各ファイル内の docstring を参照してください。
- さらなる拡張（ブローカーの実装、戦略モデル、マスターデータ等）は execution/ や strategy 関連モジュールに追加してください。

必要があれば、README に含める「サンプル .env テンプレート」や「デプロイ / systemd / supervisor 用ユニットファイル例」も作成します。どちらが必要か教えてください。