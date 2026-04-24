README.md

プロジェクト概要
- KabuSys は日本株自動売買向けのモジュール群（ポートフォリオ構築、発注エンジン、監視、リサーチ、AI ニュース解析 等）をまとめた Python パッケージです。
- 設計方針：
  - 本番（live） / ペーパートレード（paper_trading） / 開発（development）を環境変数で切替可能。
  - DB は DuckDB（分析）と SQLite（監視・発注履歴／ペーパートレード）を使用。
  - OpenAI など外部 API 呼び出しはオプション（AI モジュール）で、キーは環境変数で指定。
  - 多くの処理はフェイルセーフ設計（API 失敗時のフォールバック、部分書き込みによる保護など）。

主な機能一覧
- 起動スクリプト
  - run_execution: ExecutionEngine を起動（KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し paper_trading DB に記録）。
  - run_monitoring: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔を変更可能）。
- 設定管理 / ツール
  - config_setup: .env を対話式に作成・更新するウィザード。
  - validate_config: 設定検証 CLI（.env と config/*.yaml の存在/妥当性チェック）。--strict オプションあり。
  - tools.paper_verification_report: ペーパートレード DB から検証レポートを生成。
- ポートフォリオ構築（純粋関数）
  - portfolio.select_candidates / calc_equal_weights / calc_score_weights
  - portfolio.calc_position_sizes（リスクベース、等配分等）
  - portfolio.apply_sector_cap / calc_regime_multiplier（セクター制約・レジーム補正）
- リサーチ
  - research.calc_momentum / calc_volatility / calc_value：DuckDB の prices_daily / raw_financials を使ったファクター計算。
  - research.calc_forward_returns / calc_ic / factor_summary：特徴量探索・IC 計算等。
- AI（ニュース解析・レジーム判定）
  - ai.score_news: raw_news を集約して OpenAI（gpt-4o-mini 等）でセンチメントを算出し ai_scores に書き込む。
  - ai.regime_detector: ETF（1321）MA とマクロニュースの LLM センチメントを合成して market_regime を生成。
  - いずれも OPENAI_API_KEY が必要。API 失敗時のフォールバックあり。
- 監視（Monitoring）
  - monitoring.SystemMonitor / TradeMonitor / RiskMonitor を統合する MonitoringEngine。
  - monitoring.monitoring_db: 監視用 SQLite テーブル群の初期化・読み書き。
  - kill_switch: ドローダウン等の条件で data/kill.flag を書いて ExecutionEngine を停止させる仕組み。

セットアップ手順（開発用）
1. Python と仮想環境
   - 推奨: Python 3.9+（duckdb 等の互換性に注意）。
   - 仮想環境作成:
     python -m venv .venv
     source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（package ファイルは本リポジトリに無いため最小例を記載）
   pip install duckdb psutil openai
   - 任意／機能に応じて：
     pip install PyYAML    # config/*.yaml の内容検証を行う場合
   - sqlite3 は標準ライブラリに含まれます。

3. .env の準備
   - 対話式ウィザードで作成:
     python -m kabusys.config_setup
   - またはテンプレート（.env.example があれば参照）を編集して作成。
   - 必須環境変数（例）:
     JQUANTS_REFRESH_TOKEN=your_token_here
     KABU_API_PASSWORD=your_password_here
   - 便利なデフォルト（未設定時に利用される値）:
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     KABUSYS_ENV=development  # development / paper_trading / live
     LOG_LEVEL=INFO
   - 自動ロード無効化（テスト等）:
     KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 設定検証
   python -m kabusys.validate_config
   - --strict を付けると警告があると exit(1) で失敗扱いになります。

5. データディレクトリ・ログディレクトリの準備
   - 実行時に自動作成されますが、権限やパスを事前に確認してください。
   - デフォルト:
     data/                  # SQLite / pid / flag 等
     logs/                  # ログファイル（app_name による分割）

使い方（主要コマンド）
- ExecutionEngine を起動（本番は注意）
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは paper_trading 用 SQLite を使い実際の発注は行いません。
  - 停止は data/stop_requested.flag を作成するか、実行中に Ctrl+C。

- Monitoring を起動
  python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を変更:
    export MONITOR_POLL_INTERVAL=30  # 30 秒間隔
  - 監視プロセスは常に本番用の sqlite_path を使用して監視ログを保存します（KABUSYS_ENV に依らず）。
  - 監視ループの停止: data/stop_requested.flag ファイルを作成するか Ctrl+C。

- .env の作成/更新（ウィザード）
  python -m kabusys.config_setup

- 設定検証（CLI）
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db
  - オプション: --db PATH で別 DB を指定

- AI 機能の利用
  - ai.score_news / ai.regime_detector は OpenAI API を使用します。環境変数 OPENAI_API_KEY を設定してください。
  - 例（Python スクリプト内から呼び出す）:
      from kabusys.ai.news_nlp import score_news
      # duckdb_conn は duckdb.connect(...) で取得
      score_news(duckdb_conn, target_date, api_key=None)  # api_key=None の場合は環境変数を参照

重要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
- LOG_LEVEL — デフォルト: INFO
- OPENAI_API_KEY — AI モジュールを使う場合に必要
- PAPER_FILL_MODE — paper_trading の MockBroker の動作（instant|partial|never|reject）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 本番環境で kill.flag を自動クリアするか（0/1、0 推奨）

停止フラグ / Kill Switch
- run_execution / run_monitoring はプロジェクトルート下の data/stop_requested.flag を監視しており、存在すると安全にシャットダウンします。
- monitoring.kill_switch は条件を満たすと data/kill.flag を書き、ExecutionEngine に停止信号を送る仕組み（Execution 側で kill.flag を検出して停止する仕様）。
- 本番環境では KILL_FLAG_CLEAR_ON_START=0 を推奨（自動クリアは危険）。

ログ
- ログは console（stdout）と日次ローテートされたファイル（logs/<app_name>.log）に出力されます。
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一されています。

ディレクトリ構成（主要部分）
- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数／設定読み込み
    - config_setup.py          — .env 対話式ウィザード（CLI）
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor 起動スクリプト
    - data/                    — （パッケージ内で参照される想定の）データディレクトリ（DB / pid / flag 等）
    - utils/
      - logging_setup.py       — ログ初期化ユーティリティ
      - process_priority.py    — プロセス優先度／CPU affinity 設定
    - execution/               — 発注関連コンポーネント（Engine, OrderManager, BrokerFactory 等）
    - monitoring/
      - monitoring_db.py       — 監視用 SQLite テーブル定義 + MonitoringDB クラス
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
    - research/
      - factor_research.py
      - feature_exploration.py
    - ai/
      - news_nlp.py            — ニュース NLP スコアリング（OpenAI 使用）
      - regime_detector.py
    - tools/
      - paper_verification_report.py
    - monitoring/               — （監視関連のコード群。上に列挙済み）
- logs/                       — ログ出力先（デフォルト。自動作成）

注意事項・運用上のヒント
- KABUSYS_ENV=live の状態では実際に発注が行われます。設定ミスや API キーの漏洩に十分注意してください。
- monitor / execution をデーモンとして運用する場合、ログや PID ファイル（data/execution.pid 等）の管理、定期的なバックアップを推奨します。
- AI モジュールは外部 API（OpenAI）を使うためレイテンシやコストが発生します。API 失敗時はフォールバック挙動が組み込まれていますが、運用ポリシーを定めてください。
- DuckDB / SQLite のパスは .env で変更可能。分析用と監視用/発注用 DB は分離して使う設計（paper_trading では別 SQLite を使用）。

ライセンス / バージョン
- パッケージバージョンは kabusys.__version__ = "0.1.0"（ソース内参照）。

サポート / 開発
- 開発者向け: 自動テスト、CI、requirements.txt や packaging（pyproject.toml 等）を整備してください。
- 実運用前に python -m kabusys.validate_config で必須設定が揃っていることを確認することを強く推奨します。

以上

（必要であれば README にサンプル .env や systemd unit ファイル、より詳しいコマンド例・API 使用例を追記します。どの内容を追加しますか？）