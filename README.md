KabuSys — 日本株自動売買システム（簡易 README）
================================================

概要
----
KabuSys は日本株向けの自動売買・研究・監視ツール群です。本リポジトリは以下の主要機能を含みます。

- 実運用／ペーパートレード両対応の ExecutionEngine（発注ロジック、注文管理、リスク管理、Reconciler 等）
- 監視サブシステム（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / MonitoringEngine）
- ポートフォリオ構築（候補選定、重み算出、ポジションサイジング、セクター制限）
- 研究用モジュール（ファクター計算、将来リターン／IC 計算、統計サマリ）
- ニュース NLP / レジーム判定（OpenAI を利用したニュースセンチメント評価）
- CLI ユーティリティ：.env ウィザード、設定検証、Paper Trading 検証レポート出力 など

主な設計方針
- 本番 DB とペーパートレード DB を分離（KABUSYS_ENV=paper_trading 時は paper DB に書き込み）
- ルックアヘッドバイアス回避のため、日付参照は呼び出し元から与える（date.today() の直接使用を避ける）
- フェイルセーフ設計：外部 API 失敗時は安全側にフォールバックして継続する

主な機能一覧
----------------
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV=paper_trading の場合は MockBroker を使用）
  - run_monitoring.py: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔指定可能）
- 環境管理 / 検証
  - config_setup.py: .env を対話式に生成・更新
  - validate_config.py: 環境変数および config/*.yaml の基本チェック
- 監視
  - monitoring/monitoring_db.py: 監視ログ用 SQLite テーブル作成・読み書き
  - monitoring/monitoring_engine.py: 各 Monitor を束ねるエンジン
  - monitoring/system_monitor.py, trade_monitor.py, risk_monitor.py, kill_switch.py 等
- 研究 / データ
  - research/factor_research.py, feature_exploration.py: DuckDB を使ったファクター計算・解析
- AI（OpenAI）
  - ai/news_nlp.py: ニュースを LLM で評価して ai_scores テーブルへ書き込み
  - ai/regime_detector.py: マクロセンチメント + ETF MA200 で市場レジーム判定
- ポートフォリオ
  - portfolio/portfolio_builder.py, position_sizing.py, risk_adjustment.py
- ツール
  - tools/paper_verification_report.py: ペーパートレード DB を対象に検証レポートを生成

セットアップ手順
----------------
1. Python と依存ライブラリのインストール（例）
   - 推奨: Python 3.9+
   - 依存例（プロジェクトに requirements.txt がある場合はそれを利用）
     - duckdb
     - psutil
     - openai
     - pyyaml（validate_config の YAML 検証用）
   例:
   - pip install duckdb psutil openai pyyaml

2. プロジェクトルートで初期ディレクトリを作成
   - data/ と logs/ を作る（多くのスクリプトがこれらを使用）
     - mkdir -p data logs

3. 環境変数の準備（.env 推奨）
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - もしくは .env を手動で作成（.env.example を参考に）

主に必要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- OPENAI_API_KEY — OpenAI を使う機能で必要（news_nlp, regime_detector）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 SQLite DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（KABUSYS_ENV=paper_trading の場合に使用）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/...）
- LOG_DIR — ログ出力先（デフォルト logs/）
- その他: PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, PAPER_FILL_MODE, MONITOR_POLL_INTERVAL など

使い方（主要コマンド）
--------------------
- .env の作成（対話式）
  - python -m kabusys.config_setup

- 設定の検証
  - python -m kabusys.validate_config
  - 警告もエラー扱いにする（CI 等）: python -m kabusys.validate_config --strict

- ExecutionEngine を起動
  - 本番/開発/ペーパートレードは KABUSYS_ENV で切り替え
  - 例（ペーパートレード）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 例（開発）:
    - python -m kabusys.run_execution
  - 注意:
    - 起動時に data/stop_requested.flag が存在すると起動を中止します
    - 実行中に stop flag が作られるとエンジンに停止シグナルを送り安全に終了します
    - 起動時にプロセス優先度を "high" に設定します（set_process_priority）

- SystemMonitor（監視）を起動
  - MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定可能（デフォルト: 60）
  - 例:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 注意:
    - 監視は監視用 SQLite（settings.sqlite_path）へ書き込みます（環境にかかわらず production sqlite_path を使用）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH を使用

- OpenAI を使う処理
  - news_nlp.score_news(conn, target_date, api_key=None) — OpenAI API キーを環境変数 OPENAI_API_KEY または引数で渡す
  - ai/regime_detector.score_regime(conn, target_date, api_key=None)

ログ / 出力
-----------
- デフォルトログディレクトリ: logs/
- ログファイル: <app_name>.log（app_name は起動時の設定。例: execution.log, monitoring.log）
- setup_logging() により stdout と日次ローテーションファイルハンドラが設定されます

監視・停止関連（Kill / Stop）
----------------------------
- 実行制御フラグ
  - data/stop_requested.flag — run_monitoring.py / run_execution.py の起動時・実行中に参照される停止フラグ
  - data/kill.flag — KillSwitch により書き込まれ、ExecutionEngine に停止指示を送る用途に使われる（kill_switch.py）
- KillSwitch の評価対象:
  - RiskMonitor（ドローダウン超過、ポジション上限超過）などにより kill.flag を書き込む
  - kill.flag は冪等に書き込まれ、既存の場合は上書きされません
  - ExecutionEngine は起動時や実行中に kill.flag を検出すれば停止します

アーキテクチャ・設計メモ
-----------------------
- DB
  - DuckDB: 履歴 / 研究用（prices_daily, raw_financials, raw_news, ai_scores, market_regime 等）
  - SQLite: 監視用（monitoring.db）・注文履歴
  - KABUSYS_ENV=paper_trading の場合、発注関連は専用の SQLite（data/paper_trading.db）に記録され、本番 DB と分離される
- 安全策
  - 外部 API（OpenAI 等）の失敗はリトライやフォールバック（例: macro_sentiment=0）を行い、例外で全体が止まらないよう設計
  - 設定検証・ウィザードにより起動前に設定不備を検出できる

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py (バージョン定義)
- config.py (Settings クラス、.env 自動読み込み・パース)
- config_setup.py (対話式 .env ウィザード)
- validate_config.py (起動前チェック)
- run_execution.py (ExecutionEngine 起動スクリプト)
- run_monitoring.py (SystemMonitor 起動スクリプト)

サブパッケージ（抜粋）
- ai/
  - news_nlp.py
  - regime_detector.py
- monitoring/
  - monitoring_db.py
  - monitoring_engine.py
  - system_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py (参照実装あり)
  - trade_monitor.py (参照実装あり)
- execution/
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - broker_factory.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py
  - process_priority.py

（注）上はリポジトリの主要モジュールを抜粋したものです。実際のファイル群は src/kabusys 配下にさらに存在します。

よくある運用ヒント
------------------
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にしておくことを推奨します（自動クリアは危険）。
- .env は絶対にバージョン管理にコミットしないでください（README ヘッダや config_setup にも注意喚起あり）。
- OpenAI を利用する機能は API コストが発生するため頻度やバッチサイズを運用ポリシーに合わせて調整してください。
- logs/ と data/ のバックアップやディスク容量監視を忘れないでください（monitoring でもディスク使用率を監視します）。

開発者向け
----------
- validate_config.py を CI に組み込むと環境変数や設定ファイルの欠落を事前検出できます。
- モジュールは可能な限り副作用を避け、外部接続は明示的な引数（conn, api_key, target_date）で渡す設計になっています。ユニットテストが書きやすいです。

ライセンス / バージョン
-----------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（現状 0.1.0）。

サポート / 追加情報
-------------------
- 詳細な仕様（PortfolioConstruction.md, StrategyModel.md 等）がプロジェクトに含まれている想定です。それらのドキュメントを参照して実装方針を理解してください。
- 実運用前に config_setup → validate_config → run_monitoring/run_execution の順でテスト環境で十分に検証してください。

以上。README に追加・改善したい箇所（例: 実際の requirements.txt を読み込んだ手順や CI 用の設定例）を教えていただければ、追記・修正します。