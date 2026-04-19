README
======

概要
----
KabuSys は日本株向けの自動売買 / リサーチ基盤のミニマルな実装群です。  
このリポジトリには、以下の機能群が含まれます。

- 実行エンジン起動スクリプト（ExecutionEngine を起動）
- 監視デーモン（System / Trade / Risk のポーリングとアラート / Kill Switch）
- ポートフォリオ構築・ポジションサイジングの純粋関数群
- リサーチ（ファクター計算・特徴量評価）
- AI を使ったニュースセンチメント / レジーム判定モジュール（OpenAI 利用）
- Paper Trading の検証用レポート作成ツール
- .env ウィザード / 設定検証ツール

本 README は開発者向けのセットアップ・実行手順、主要コンポーネントの説明、ディレクトリ構成をまとめたものです。

主な機能一覧
--------------
- 実行（Execution）
  - ExecutionEngine を起動してブローカークライアント経由で発注管理（本番 / ペーパートレード切替）
  - OrderRepository / OrderManager / RiskManager / Reconciler 等の組立て
- 監視（Monitoring）
  - SystemMonitor：CPU / メモリ / ディスク / データ鮮度 / プロセス死活監視
  - TradeMonitor：発注ログ監視（滞留注文・約定異常など）
  - RiskMonitor：ドローダウン・ポジション上限監視とリスクログ記録
  - KillSwitch：一定条件で data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringEngine：上記を束ねて定期ポーリング
- ポートフォリオ構築（Portfolio）
  - 銘柄選定（スコア順ソート）
  - 重み算出（等金額/スコア加重）
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ計算（ロット丸め、aggregate cap）
- リサーチ（Research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB 利用）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
- AI（OpenAI を利用）
  - news_nlp: ニュース記事を LLM でセンチメント化して ai_scores テーブルへ書き込み
  - regime_detector: ETF の MA200 とマクロニュースを合成して市場レジーム判定
- ツール
  - config_setup: .env を対話式に生成・更新
  - validate_config: 環境変数・config/*.yaml の起動前検証
  - paper_verification_report: Paper Trading の検証レポート生成

セットアップ手順
----------------

1. リポジトリをクローン、移動
   - 例: git clone ... && cd <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - 必要最低限のパッケージ例:
     - duckdb
     - psutil
     - openai
     - （任意）PyYAML（validate_config が config/*.yaml を検証する場合に必要）
   - 例:
     - pip install duckdb psutil openai
     - pip install pyyaml  # YAML 検証が必要な場合

   ※ requirements.txt があればそちらを使ってください（本コードでは同梱されていません）。

4. .env の作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - または .env.example を参考に手動で作成してプロジェクトルートに配置
   - 主な環境変数（抜粋）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (ペーパートレード用 DB, デフォルト: data/paper_trading.db)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - LOG_LEVEL (DEBUG/INFO/...)
     - OPENAI_API_KEY (AI 機能を使う場合必須)
     - PAPER_FILL_MODE (instant | partial | never | reject) — デフォルト "instant"
     - KILL_FLAG_CLEAR_ON_START (0/1) — 本番では 0 推奨

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付与すると警告も失敗扱いになります:
     - python -m kabusys.validate_config --strict

6. データ / ログ ディレクトリ
   - デフォルトで以下のパスを使用します。必要なら事前に作成してください（setup_logging/monitoring が自動作成を試みます）。
     - data/ (SQLite DB, pid, flag など)
     - logs/ (ログファイル: logs/execution.log, logs/monitoring.log など)

使い方（起動 / 実行）
-------------------

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading を設定した場合、MockBrokerClient（ペーパートレード）を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録されます（本番 DB と分離）。
    - 実行中に停止させたい場合は data/stop_requested.flag を作成します（run_execution はこれを検知して停止します）。
    - PID ファイル: data/execution.pid（Settings.pid_file_path で上書き可）
    - 起動時に KILL_FLAG_CLEAR_ON_START=1 が設定されていると kill.flag を自動クリアします（本番では 0 推奨）。

- 監視プロセスを起動
  - python -m kabusys.run_monitoring
  - 説明:
    - 監視ループはデフォルトで 60 秒間隔で実行されます。環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒数）。
      - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    - 監視は Settings.sqlite_path（デフォルト data/monitoring.db）に接続します。Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します。
    - 監視を停止するにはプロセスに SIGINT（Ctrl+C）を送るか、またはプロジェクトルート/data/stop_requested.flag を作成します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB パスは args または環境変数 PAPER_TRADING_SQLITE_PATH、未設定時は data/paper_trading.db。

- .env ウィザード
  - python -m kabusys.config_setup
  - 対話的に .env を生成 / 更新します。生成後は python -m kabusys.validate_config で検証してください。

主な環境変数の補足
-------------------
- KABUSYS_ENV: "development" | "paper_trading" | "live"
  - paper_trading の場合、発注は Mock（分離 DB に記録）されます
- OPENAI_API_KEY: AI 機能（news_nlp, regime_detector）を使う場合に必要
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレード時の約定挙動
  - 有効値: "instant", "partial", "never", "reject"
- KILL_FLAG_CLEAR_ON_START: 起動時に data/kill.flag をクリアするか（"1" でクリア）

停止 / Kill Switch
------------------
- 実行エンジンを強制停止・保守目的で「停止」するには次のいずれか：
  - data/stop_requested.flag を作成 → run_execution/run_monitoring が検知して優雅に終了
    - 例: mkdir -p data && touch data/stop_requested.flag
  - Kill Switch（自動判定）: RiskMonitor 等が条件を満たすと data/kill.flag を書き込み ExecutionEngine に停止指示を出します（KillSwitch クラス）。
  - kill.flag は Execution 起動時に自動クリアしたい場合、KILL_FLAG_CLEAR_ON_START=1 を .env に設定します（本番は 0 推奨）。

ロギング
-------
- ログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="execution" | "monitoring")
- デフォルトで logs/<app_name>.log に日次ローテート（30 日保持）
- コンソールには stdout にログを出力します（stderr ではない点に注意）

ディレクトリ構成（主要ファイル）
-------------------------------
以下は src/kabusys 以下の主な構成（要約）です。

- kabusys/
  - __init__.py
  - config.py                 — 環境変数/設定管理（.env 自動読み込み含む）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - monitoring/
    - monitoring_db.py        — SQLite の永続化（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py       — システム監視（CPU/メモリ/データ鮮度/プロセス）
    - trade_monitor.py        — （発注ログ監視: 実装参照）
    - risk_monitor.py         — ドローダウン / ポジション上限のチェック
    - kill_switch.py          — Kill Switch ロジック（kill.flag 書き込み）
    - monitoring_engine.py    — 各 Monitor を束ねる
    - alert_manager.py        — （通知管理: 実装参照）
  - execution/
    - execution_engine.py     — ExecutionEngine（起動 / セッション管理）
    - broker_factory.py       — ブローカークライアント生成（本番 / Mock 切替）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 発注株数計算 / aggregate cap
    - risk_adjustment.py      — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py      — モメンタム/ボラ/バリュー計算（DuckDB）
    - feature_exploration.py  — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py             — ニュースの LLM センチメント化（OpenAI）
    - regime_detector.py      — マクロ + MA200 によるレジーム判定（OpenAI optional）
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成ツール
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定ユーティリティ

補足（実装上の注意点）
---------------------
- Monitoring の DB（monitoring.db）は環境にかかわらず Settings.sqlite_path を使用します（監視は常に本番 DB を見る仕様）。
- ExecutionEngine は KABUSYS_ENV=paper_trading の場合、Paper 用の SQLite（PAPER_TRADING_SQLITE_PATH）を使って完全に分離されたログを取ります。
- DuckDB はリサーチ用の高速な分析用 DB として利用されます（デフォルト data/kabusys.duckdb）。
- OpenAI を利用する機能は API キー（OPENAI_API_KEY）が必要です。API 呼び出しはリトライ／バックオフを実装しており、失敗時はフェイルセーフ（スコア 0 等）で継続する設計です。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を検出して行います。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

トラブルシューティング
----------------------
- DB / ログ ディレクトリのパーミッションが原因でファイルが作れないと、ファイルハンドラの設定に失敗しコンソール出力だけになります。ログディレクトリを作成して権限を確認してください（logs/, data/）。
- validate_config で YAML 検証を行うには PyYAML が必要です。インストールされていない場合は警告が出て YAML 内容の検証をスキップします。
- OpenAI 関連でエラーが頻発する場合は API キーやネットワーク、レート制限の状態を確認してください。実装は 429 等をリトライする仕組みがあります。

ライセンス / バージョン
-----------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"

最後に
------
本リポジトリは実稼働システムのミニマルな設計・実装例を含みます。実運用前には設定・ログ出力・Kill Switch 挙動などを十分にテストし、安全に運用できることを確認してください。必要に応じて config/*.yaml や .env の各値を調整し、本番環境では LINE 等の通知設定を有効にしておくことを推奨します。