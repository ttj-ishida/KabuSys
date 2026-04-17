# KabuSys — README

概要
- KabuSys は日本株向けの自動売買 / 研究 / 監視を想定した Python パッケージです。
- 主な機能には、ExecutionEngine による発注処理（実取引 / ペーパートレード）、監視（System / Trade / Risk）、ポートフォリオ構築・ポジションサイズ計算、ファクター計算・リサーチ、LLM（OpenAI）を使ったニュース NLP / レジーム判定、ならびに運用支援ツール類が含まれます。
- 設定は .env ファイルまたは環境変数で管理します。DB はデフォルトでローカルの DuckDB / SQLite ファイルを使用します。

主な機能
- Execution
  - 実口座またはペーパートレード（KABUSYS_ENV=paper_trading）に対応
  - BrokerClientFactory によるブローカークライアント生成
  - ExecutionEngine / OrderManager / RiskManager / Reconciler 等の実行基盤（run_execution.py から起動）
- Monitoring
  - SystemMonitor（CPU・メモリ・ディスク、プロセス生存、データ鮮度）
  - TradeMonitor（滞留注文・約定異常）
  - RiskMonitor（ドローダウン・ポジション数）
  - KillSwitch（閾値を超えた場合に kill.flag を書いて ExecutionEngine を停止）
  - AlertManager（LINE push による通知）
  - monitoring_engine によるポーリング制御（run_monitoring.py から起動）
- Portfolio
  - 銘柄候補選定、等加重・スコア加重、リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ決定（単元株丸め、aggregate cap）
- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計
- AI（OpenAI）
  - news_nlp: ニュース記事をまとめて LLM でセンチメントスコア化し ai_scores に格納
  - regime_detector: ETF（1321）MA とマクロニュースを LLM で判定して market_regime に書き込み
- ツール
  - 環境設定ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report.py）

前提・依存関係（想定）
- Python 3.10+
- 推奨パッケージ（requirements.txt が無い場合は手動で導入）:
  - duckdb
  - psutil
  - requests
  - openai
  - PyYAML（config 検証の内容チェックに任意で使用）
- ネットワーク接続（OpenAI / LINE API / kabuステーション を利用する場合）
- .env に各種シークレットを設定（下記参照）

セットアップ手順（開発 / ローカル実行向け）
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo>

2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate （Windows: .venv\Scripts\activate）

3. 必要パッケージのインストール
   - pip install duckdb psutil requests openai PyYAML

   ※ プロジェクトに requirements.txt がある場合は pip install -r requirements.txt を使ってください。

4. .env の作成
   - 対話式ウィザードを実行:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に .env を作成し、必須変数を設定する。

必須の環境変数（最低限）
- JQUANTS_REFRESH_TOKEN （必須）
- KABU_API_PASSWORD （必須）

主な任意 / デフォルト変数
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY: OpenAI を使う場合に必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager 用（任意）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START など（config.Settings 参照）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

使い方（主要なスクリプト）
- 環境セットアップ（.env の作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict  （警告も失敗扱い）

- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - 仕様:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、デフォルトで data/paper_trading.db に記録（本番 DB と分離）
    - 起動前に data/stop_requested.flag が存在する場合は起動を行わない
    - 実行中に data/stop_requested.flag が作成されると実行エンジンを停止する
    - PID ファイルは data/execution.pid（Settings.pid_file_path）に書き込まれる

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 仕様:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
    - 監視は本番 sqlite_path を使用（KABUSYS_ENV に依存しない）
    - stop フラグ: data/stop_requested.flag を検出すると監視ループを終了

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを指定可能。環境変数 PAPER_TRADING_SQLITE_PATH でも指定可。

- AI 関連（コード API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

停止・Kill Switch
- KillSwitch は監視ロジックの一部で、しきい値超過時に Settings.kill_flag_path（デフォルト data/kill.flag）へ理由を書き込みます。
- ExecutionEngine は kill.flag を検知すると安全停止または起動拒否を行う設計です。
- 手動で停止したい場合は run 実行中に data/stop_requested.flag を作成してください（両 run_* スクリプトが監視）。

デフォルトファイル・パス
- data/kabusys.duckdb （DuckDB）
- data/monitoring.db （監視用 SQLite）
- data/paper_trading.db （ペーパートレード専用 SQLite）
- data/execution.pid （ExecutionEngine の PID）
- data/kill.flag （Kill Switch）
- data/stop_requested.flag （run スクリプトの停止フラグ）

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動読み込み / Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - utils/
    - __init__.py
    - process_priority.py
  - （execution / data / others は実装による追加ファイルあり）

注意点・運用上のヒント
- validate_config を先に実行して必須環境変数や DB パス等の基本チェックを行ってください。PyYAML がない場合は YAML ファイル内容の検査はスキップされます。
- KABUSYS_ENV=paper_trading を使えば本番 DB やブローカーに影響を与えずに検証ができます（paper_trading 用 DB は PAPER_TRADING_SQLITE_PATH で上書き可能）。
- OpenAI を使う機能は API キー（OPENAI_API_KEY）が必要です。API 呼び出しはリトライ・フォールバック処理を実装しているものの、API 利用料に注意してください。
- monitoring は本番監視用として設計されているため、KABUSYS_ENV にかかわらず Settings.sqlite_path を使う点に注意してください（run_monitoring の挙動）。
- process priority / cpu affinity 設定は psutil を使って行います。権限不足時は警告が出ますが処理は継続します。

サンプル .env（最小例）
- JQUANTS_REFRESH_TOKEN=your_jquants_token_here
- KABU_API_PASSWORD=your_kabu_password_here
- KABUSYS_ENV=development
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- OPENAI_API_KEY=sk-XXXX
- LINE_CHANNEL_ACCESS_TOKEN=
- LINE_USER_ID=
- LOG_LEVEL=INFO

開発者向け
- 各モジュールは外部状態への依存を抑えた設計（DuckDB/SQLite 接続や client インジェクション）になっています。ユニットテスト時は DB 接続や OpenAI 呼び出し関数をモックしやすく設計されています。
- monitoring/monitoring_db.init_monitoring_db は冪等でテーブル追加・マイグレーションを行います。初回起動時に自動で DB のスキーマが作成されます。

ライセンス・貢献
- （リポジトリに LICENSE があればここに記載してください）
- バグ報告や機能追加は Issue / PR で受け付けてください。

問い合わせ
- 実運用や設定に関する質問はリポジトリの Issue に記載してください。

以上。必要であれば README に入れる具体的な例（実行コマンド例、.env の完全テンプレート、systemd ユニットサンプルなど）を追加します。どの情報を詳しく載せたいか教えてください。