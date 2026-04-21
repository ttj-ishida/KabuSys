# KabuSys — 日本株自動売買システム (README)

本ドキュメントは、提供されたコードベースに対する README です。プロジェクトの概要、主な機能、セットアップ手順、起動方法、ディレクトリ構成を日本語でまとめています。

注意: 実行には外部 API キーや環境変数が必要です。まずは「セットアップ手順」を参照してください。

---

目次
- プロジェクト概要
- 機能一覧
- 必要条件（依存ライブラリ）
- セットアップ手順
- 環境設定（.env）作成手順
- 起動／使い方
  - Execution エンジン起動
  - Monitoring 起動
  - 設定検証
  - Paper Trading 検証レポート生成
  - AI / レジーム・ニュース処理
- 重要な環境変数
- 停止・Kill スイッチの仕組み
- ディレクトリ構成（主要ファイルの説明）

---

プロジェクト概要
- KabuSys は日本株自動売買のためのシステム骨格です。
- 戦略のファクター計算、ポートフォリオ構築、ポジションサイズ計算、注文管理、監視（Monitoring）、Paper Trading 用の分離された DB、OpenAI によるニュース NLP を含む各種ユーティリティを備えます。
- 各コマンドライン用スクリプト（実行エンジン / 監視ループ / 設定ウィザード / 設定検証 / レポート生成）が提供されています。

機能一覧
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番（live）／ペーパートレード（paper_trading）を環境変数で切替可能
  - paper_trading 時は MockBrokerClient を使用し、Paper 用 SQLite DB に記録
  - プロセス優先度を起動時に High に設定
- Monitoring（run_monitoring.py）
  - SystemMonitor（CPU/メモリ/ディスク/プロセス監視・データ鮮度チェック）
  - TradeMonitor / RiskMonitor 等（監視コンポーネントは monitoring パッケージ内）
  - KillSwitch を使った ExecutionEngine 停止の自動評価
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）
  - 監視ログは SQLite（monitoring.db）に永続化
- AI モジュール
  - news_nlp: raw_news を OpenAI に投げて銘柄ごとのセンチメントスコアを ai_scores テーブルへ書き込み
  - regime_detector: ETF の MA200 乖離とマクロニュースの LLM 評価を合成して market_regime を判定・書き込み
- Research（ファクター計算・特徴量探索）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を利用）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリ
- Portfolio（銘柄選定・配分・サイズ計算）
  - 候補選定、等金額・スコア重み、リスクベースのポジションサイズ計算
  - セクター上限やレジーム乗数の適用
- ユーティリティ
  - 環境設定ウィザード（config_setup.py）で .env を対話的に生成
  - 設定検証 CLI（validate_config.py）
  - ログ設定ユーティリティ（utils.logging_setup）
  - プロセス優先度 / CPU affinity ユーティリティ（utils.process_priority）
  - Paper Trading 検証レポート生成（tools.paper_verification_report）

必要条件（依存ライブラリ）
- Python 標準ライブラリ: sqlite3, logging, threading, datetime, argparse, pathlib 等
- 外部パッケージ（少なくとも以下が必要）
  - duckdb
  - psutil
  - openai
  - PyYAML（config/*.yaml の内容検証用。インストールされていなくても動作はするが警告が出ます）
- 例: pip install duckdb psutil openai PyYAML

セットアップ手順
1. リポジトリをクローン／展開する
2. Python 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （requirements.txt を用意している場合は pip install -r requirements.txt）
4. data/ と logs/ ディレクトリを作成（logging_setup は自動作成を試みますが、明示的に作っておくと良い）
   - mkdir -p data logs
5. .env を準備する（次項参照）

環境設定（.env）作成手順
- 対話式ウィザード（推奨）
  - python -m kabusys.config_setup
  - 指示に従って値を入力し .env を生成します。
- 手動で作成する場合は以下の主要な環境変数を設定してください（例）:
  - JQUANTS_REFRESH_TOKEN=...
  - KABU_API_PASSWORD=...
  - KABUSYS_ENV=development|paper_trading|live
  - OPENAI_API_KEY=...（AI 機能を使う場合）
  - DUCKDB_PATH=data/kabusys.duckdb
  - SQLITE_PATH=data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
  - LOG_LEVEL=INFO
  - KILL_FLAG_CLEAR_ON_START=0
- 設定検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱い（終了コード 1）

起動／使い方

1) ExecutionEngine（注文エンジン）を起動
- コマンド:
  - python -m kabusys.run_execution
- 挙動:
  - 起動時にプロセス優先度を high に設定
  - KABUSYS_ENV=paper_trading のときは paper_sqlite_path に接続（本番 DB と分離）
  - エンジンはバックグラウンドスレッドで run_session を実行し、data/stop_requested.flag を検知すると停止する
  - 実行中、PID が data/execution.pid に書かれます（設定は Settings.pid_file_path から制御）

2) Monitoring（監視ループ）を起動
- コマンド:
  - python -m kabusys.run_monitoring
- オプション／環境変数:
  - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）
- 挙動:
  - 監視は本番 sqlite_path（Settings.sqlite_path）を使用（KABUSYS_ENV にかかわらず本番監視 DB を参照）
  - SystemMonitor / TradeMonitor / RiskMonitor 等を実行し、必要に応じて KillSwitch を発動して data/kill.flag を生成
  - data/stop_requested.flag を置くと監視ループが終了

3) 設定検証
- python -m kabusys.validate_config
- --strict を付けると警告も失敗（exit 1）

4) Paper Trading 検証レポート生成
- コマンド:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）
- 出力:
  - 稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）等の指標と PASS/FAIL 判定

5) AI 機能（ニュース NLP / レジーム判定）
- 環境変数 OPENAI_API_KEY が必要
- 関数を呼び出すことで DuckDB のテーブル（raw_news 等）を参照してスコアリング・判定を行います
  - kabusys.ai.news_nlp.score_news(...)
  - kabusys.ai.regime_detector.score_regime(...)
- API 呼び出しはレート制限やサーバーエラーに対してリトライ実装あり。失敗時はフェイルセーフ（ゼロフォールバックなど）します。

重要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）. default: development
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時必須）
- DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（paper_trading 環境で使用）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、default 60）
- PAPER_FILL_MODE: Paper Trading の fill モード（instant/partial/never/reject）
- PID_FILE_PATH: Execution PID ファイルパス（default: data/execution.pid）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

停止・Kill スイッチの仕組み
- Graceful stop:
  - data/stop_requested.flag を作成すると run_monitoring と run_execution はそれを検知して終了します（監視ループ側は flag を検知すると終了、実行エンジン側は thread を停止させる仕組み）。
- Kill Switch:
  - RiskMonitor / SystemMonitor / TradeMonitor の評価で致命的な条件が満たされると KillSwitch が data/kill.flag を書き込みます。ExecutionEngine は起動時の設定により kill.flag の自動クリア設定(KILL_FLAG_CLEAR_ON_START) を行うことができます（本番では 0 推奨）。
  - KillSwitch は冪等に振る舞い、既に flag が存在する場合は上書きしません。

ログとデータ
- ログ:
  - デフォルトは logs/<app_name>.log（TimedRotatingFileHandler により日次ローテーション、30日保持）
  - コンソール出力は stdout（stderr ではない）
- データ:
  - DuckDB: data/kabusys.duckdb（分析用）
  - SQLite（監視）: data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db

ディレクトリ構成（主要ファイルと説明）
- src/kabusys/
  - __init__.py — パッケージ定義（__version__ 等）
  - config.py — 環境変数 / Settings 管理。自動 .env ロード機能あり。
  - config_setup.py — 対話式 .env ウィザード（python -m kabusys.config_setup）
  - validate_config.py — 起動前の設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成
  - ai/
    - news_nlp.py — ニュースを OpenAI でスコアリングして ai_scores に書き込む
    - regime_detector.py — 市場レジーム判定（MA200 + マクロニュース LLM）
  - monitoring/
    - monitoring_db.py — SQLite テーブル初期化 / CRUD（system_status/trade_logs/positions/risk_logs/dashboard）
    - monitoring_engine.py — 各 Monitor を束ねて実行
    - system_monitor.py — システム状態・データ鮮度監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — data/kill.flag の作成・管理
    - （その他 TradeMonitor / AlertManager 等が含まれる想定）
  - execution/
    - execution_engine.py — ExecutionEngine（起動スクリプトがこれを組み立てる）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py 等（エンジンの構成要素）
    - broker_factory.py — ブローカークライアントの生成（本番/モック判定）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数計算・aggregate cap
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — Momentum/Volatility/Value 等のファクター計算（DuckDB)
    - feature_exploration.py — 将来リターン、IC、統計サマリ
  - utils/
    - logging_setup.py — 統一ロギング設定（Stream + TimedRotatingFile）
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - data/ （実行時に使用されるファイル群、コードベース外で生成される）
    - execution.pid, stop_requested.flag, kill.flag, *.db, etc.
  - config/ （YAML 設定ファイル群が想定される: system_config.yaml, data_config.yaml, ...）

補足 / 開発上の注意
- Monitoring は run_monitoring.py の docstring にある通り、KABUSYS_ENV にかかわらず監視用の本番 sqlite_path を使用します（運用上の注意）。
- run_execution は KABUSYS_ENV=paper_trading の場合に Paper Trading 用の DB を使用して本番 DB と完全分離します。
- OpenAI 利用部分は API コールの失敗に対して堅牢に設計されていますが、API キーや費用に注意して運用してください。
- .env は機密情報を含むため Git 管理下に置かないでください（config_setup も .env を Git にコミットしないよう注記しています）。
- DuckDB/SQLite のスキーマ変更は monitoring_db.init_monitoring_db が軽微なマイグレーション（カラム追加）を行いますが、重大な変更は慎重に扱ってください。

以上が概要です。運用にあたって不明点があれば、どのコンポーネントの使い方（例: ExecutionEngine の更なる起動オプション、AI スコアリングのバッチ単位調整など）が必要か教えてください。必要に応じて README を補足・拡張します。