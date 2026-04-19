KabuSys — 日本株自動売買システム（README 日本語版）

概要
- KabuSys は日本株向けの自動売買・リサーチ・監視ツール群です。戦略（ファクター計算・特徴量探索）、ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）、Execution（発注エンジン / paper_trading モード対応）、監視（System/Trade/Risk Monitor）、AI モジュール（ニュース NLP、レジーム判定）、および運用ユーティリティを含みます。
- 設計の特徴：DuckDB を分析データ向けに使用、SQLite を監視／ペーパートレード向けに使用、環境変数ベースの設定、.env 対話ウィザード・検証ツールを提供。LLM（OpenAI）連携は任意機能。

主な機能一覧
- 設定管理
  - Settings クラスで環境変数・.env を読み込み（自動ロード: .env → .env.local、OS 環境変数優先）
  - 対話式 .env ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
- 実行エンジン（Execution）
  - 本番 / ペーパートレード切替（KABUSYS_ENV=paper_trading で MockBroker 使用、DB は data/paper_trading.db）
  - リスク管理、オーダー管理、Reconciler、ExecutionEngine（run_execution 起動スクリプト）
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - ポーリング監視（MONITOR_POLL_INTERVAL で間隔上書き可能）
  - Kill Switch（条件一致で data/kill.flag を作成し Execution を停止）
  - 監視ログ永続化（SQLite, monitoring_db モジュール）
- リサーチ / ポートフォリオ
  - ファクター計算（momentum, volatility, value 等）
  - 特徴量解析（forward returns, IC, summary）
  - 候補選定・重み付け・ポジションサイズ計算（等金額・スコア重み・リスクベース）
  - セクター制約・レジーム乗数の適用
- AI（任意）
  - ニュースを LLM（OpenAI）でセンチメント化して ai_scores に書き込み（kabusys.ai.news_nlp）
  - マクロニュース＋ETF MA200 で市場レジーム判定（kabusys.ai.regime_detector）
- ユーティリティ
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）
  - ロギングセットアップユーティリティ（logs 日次ローテート）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

セットアップ手順（開発 / 簡易）
1. Python 環境作成（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 必須（最小）: duckdb, psutil
   - AI 機能を使う場合: openai
   - 設定検証（YAML のパース）を有効にする場合: PyYAML
   例:
     pip install duckdb psutil
     pip install openai    # AI 機能使用時
     pip install pyyaml    # validate_config で YAML 内容検証を行いたい場合

   （requirements.txt はリポジトリに含まれていないため、環境に応じて必要パッケージを用意してください）

3. ディレクトリ作成（初回）
   - data/ と logs/ を作成:
     mkdir -p data logs

4. .env の初期作成（推奨）
   - 対話式ウィザードを使う:
     python -m kabusys.config_setup
   - ウィザードが生成する .env には機密トークン（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等）を設定してください。

5. 設定検証
   - python -m kabusys.validate_config
   - 必須環境変数（例）: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - --strict を付けると警告も失敗扱いになります。

主要環境変数（要点）
- KABUSYS_ENV: 実行環境。'development' | 'paper_trading' | 'live'（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- LOG_DIR: ログ出力ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使用する場合必須）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring にてデフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START: 本番で自動クリアすると危険（0 推奨）。live では注意喚起あり。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: プロジェクトルート自動 .env ロードを無効化（テスト用）

運用ファイル・フラグ
- data/stop_requested.flag: 実行中プロセス（monitoring / execution）がループを中断するための停止フラグとして参照
- data/kill.flag: KillSwitch が書き込むファイル。ExecutionEngine の停止シグナル
- data/execution.pid: ExecutionEngine の PID を保存（run_execution が使用）
- logs/<app>.log: 日次ローテートのログ（app_name は execution / monitoring 等）

使い方（代表的コマンド）
- 環境設定ウィザード:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Execution（発注エンジン）起動:
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し data/paper_trading.db に記録
  - 起動時に data/stop_requested.flag が存在すると起動せず終了
  - 実行中に data/stop_requested.flag を作成すると安全に停止（スレッドに通知して停止）

- Monitoring 起動:
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数で秒単位のポーリング間隔を上書き可能（デフォルト 60 秒）
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視ログを記録
  - 停止フラグ: data/stop_requested.flag を検知するとループを終了

- Paper Trading 検証レポート:
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI スコアリング（ライブラリ呼び出し例）
  - k abusys.ai.score_news(conn, target_date, api_key=None) をコードから呼ぶ（api_key を渡すか環境変数 OPENAI_API_KEY を設定）

ログとデバッグ
- ログは stdout にも出力され、logs/<app>.log に日次ローテーションで保存されます。
- ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で制御可。
- ログファイル作成に失敗した場合はコンソール出力のみで継続します。

トラブルシューティング（よくある問題）
- 必須環境変数未設定: validate_config で検出します。実行時に Settings が未設定変数で ValueError を投げます。
- OpenAI の呼び出し失敗: API キー未設定、ネットワーク、レート制限。AI モジュールは失敗時に保守的なフォールバック（スコア 0.0 等）を行う設計ですが、キーは必須です。
- ログディレクトリ作成失敗: 権限等の原因でファイルハンドラが作れない場合、コンソールのみで動作します。
- プロセス優先度変更に失敗: 一部 OS / 権限で設定できないことがあり、その場合は警告を出してスキップします。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/.env ロードと Settings 定義
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（監視ログ）
    - system_monitor.py
    - trade_monitor.py (参照あり)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (参照あり)
  - execution/               — Execution エンジン関連（OrderManager, BrokerFactory, Reconciler, RiskManager 等）
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
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py

補足（設計上の注意）
- 時刻取り扱い: 多くの箇所で UTC ISO8601 を利用。AI/リサーチ処理はルックアヘッドバイアスを防ぐ実装になっています（date.today() などに依存しない）。
- DB: DuckDB は分析向け、SQLite は監視／ペーパートレード用途で使い分けられます。monitoring の初期化処理は冪等です。
- Kill / Stop フラグ: ファイルベースのシンプルな仕組みでプロセス間制御（data/kill.flag, data/stop_requested.flag）を行います。運用時はこれらの存在と KILL_FLAG_CLEAR_ON_START 設定に注意してください。

ライセンス・バージョン
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）

以上。運用やデプロイ、CI に関する追加ドキュメントが必要であれば、目的（本番デプロイ / systemd / Docker / コンテナ化 など）を教えてください。さらに細かいコマンド例や .env.example の自動生成例も作成できます。