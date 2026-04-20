KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株向けの自動売買／リサーチ／監視フレームワークです。本リポジトリは以下の主要機能を含みます。

- 発注エンジン（ExecutionEngine）と発注周辺のリスク管理
- 監視サブシステム（System / Trade / Risk のモニタリング、Kill Switch）
- ポートフォリオ構築（銘柄選定、重み算出、ポジションサイズ決定）
- リサーチ（ファクター計算、特徴量解析）
- AI 支援モジュール（ニュース NLP によるセンチメント評価、レジーム判定）
- 運用補助ツール（.env ウィザード、設定検証、ペーパートレード検証レポート等）

注: パッケージは Python モジュールとして設計されています。実行スクリプトはモジュールとして起動可能（python -m kabusys.…）。

主な機能一覧
-------------
- 実行モード切り替え: KABUSYS_ENV により development / paper_trading / live をサポート。paper_trading は本番 DB と分離してモックブローカーを使用。
- ExecutionEngine 起動スクリプト: src/kabusys/run_execution.py
  - ブローカーファクトリ、OrderManager、RiskManager、Reconciler を組み立ててエンジンを起動
  - 停止フラグ（data/stop_requested.flag）で安全停止
  - PID ファイル（data/execution.pid）を使用
- Monitoring（監視）:
  - run_monitoring.py によるポーリングループ起動（MONITOR_POLL_INTERVAL 環境変数で間隔上書き可）
  - System / Trade / Risk モニタ、KillSwitch、AlertManager 統合（monitoring_engine）
  - 監視ログ永続化（SQLite）: monitoring_db モジュールがテーブル作成／読み書きを担う
- ポートフォリオ構築:
  - 銘柄候補選定、等加重・スコア加重、リスクベースの株数算出、セクターキャップ、レジーム乗数
- リサーチ:
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）等の統計解析
- AI:
  - ニュースを LLM（OpenAI）でスコアリングして ai_scores に書き込み（kabusys.ai.news_nlp.score_news）
  - マクロニュースと ETF の MA 乖離を組み合わせた市場レジーム判定（kabusys.ai.regime_detector.score_regime）
- ユーティリティ:
  - .env 対話式ウィザード: kabusys.config_setup
  - 設定検証 CLI: kabusys.validate_config
  - ペーパートレード検証レポート: kabusys.tools.paper_verification_report

セットアップ手順
----------------
以下は一般的なセットアップ手順です。環境や運用方針に合わせて適宜調整してください。

1. リポジトリをクローン
   - git clone ... && cd <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 本リポジトリに requirements.txt がある場合:
       pip install -r requirements.txt
   - 主な必須パッケージ（機能に応じて）:
       pip install duckdb psutil openai PyYAML
   - 注意: 実運用ではローカル環境に合わせてバージョン固定してください。

4. 初期環境変数（.env）を作成
   - 対話式ウィザード:
       python -m kabusys.config_setup
   - 生成後、設定を検証:
       python -m kabusys.validate_config
     --strict オプションで警告をエラー扱いにできます。

5. ディレクトリ作成（必要に応じて）
   - data/ ログ・DB・フラグ等を保存するディレクトリを準備:
       mkdir -p data logs

主要な環境変数（代表）
---------------------
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境（development | paper_trading | live）
- DUCKDB_PATH: DuckDB ファイルパス（分析用 DB）
- SQLITE_PATH: 監視用 SQLite（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 時に使用）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
- LOG_LEVEL / LOG_DIR: ログ出力に関する設定
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、default: 60）
- PAPER_FILL_MODE: ペーパートレード時の執行挙動（instant | partial | never | reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアする（0/1）

使い方（よく使うコマンド）
------------------------

- .env を作成（ウィザード）
  - python -m kabusys.config_setup

- 設定を検証
  - python -m kabusys.validate_config
  - 本番前には --strict を推奨

- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは MockBroker を使用し、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に保存されます。
  - 起動前に data/kill.flag を自動消去したい場合は KILL_FLAG_CLEAR_ON_START=1（本番では推奨しません）

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数で間隔上書き可（例: MONITOR_POLL_INTERVAL=120）

- 停止方法
  - 監視ループやエンジンは data/stop_requested.flag の存在を検出すると優雅に終了します（停止用フラグ）。
  - ExecutionEngine に対しては Kill Switch（data/kill.flag）を書き込むと停止トリガになります。KillSwitch は監視コンポーネントが評価して作成します。

- Paper Trading 検証レポートを生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI スコアリング（プログラム呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡して呼ぶと ai_scores テーブルに書き込みます（OPENAI_API_KEY が必要）
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

重要ファイル・フラグ
-------------------
- data/stop_requested.flag — 監視・実行ループを停止する外部フラグ（存在するとループが終了）
- data/kill.flag — Kill Switch が書き込む停止フラグ（ExecutionEngine に停止を促す）
- data/execution.pid — ExecutionEngine の PID 保存先（run_execution が使用）
- logs/ — ログファイル（setup_logging が出力）

監視 DB（SQLite）
----------------
監視用 DB（monitoring.db）は monitoring_db モジュールが以下テーブルを作成／管理します（冪等）:

- system_status: CPU/MEM/DISK/プロセス状態の時系列ログ
- trade_logs: 発注イベントログ（latency_ms カラムを含む）
- positions: 保有ポジションテーブル
- risk_logs: リスク関連イベント（ドローダウン・ポジション上限等）
- dashboard: ダッシュボード集計（常に id=1 の単一行）

監視 DB は init_monitoring_db(conn) により自動マイグレーション（カラム追加等）を行います。

ディレクトリ構成（概要）
----------------------
（src/kabusys 以下の主要モジュールと役割）

- kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数読み込み・Settings 抽象化（.env の自動読み込み含む）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）でのセンチメント評価と ai_scores 書き込み
    - regime_detector.py — マーケットレジーム判定と書き込み
  - portfolio/
    - portfolio_builder.py — 候補選定・重み算出
    - position_sizing.py — 株数計算（allocation policies）
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン・IC・統計サマリー等
  - monitoring/
    - monitoring_db.py — 監視 DB 層（テーブル作成・CRUD）
    - system_monitor.py — システムデータフレッシュネス・プロセス監視
    - trade_monitor.py — 発注履歴・滞留注文・約定異常検出（実装参照）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — Kill Switch（フラグ生成）
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py — 通知管理（LINE 等、実装に依存）
  - utils/
    - logging_setup.py — 一貫したログ設定（Stream + 日次ローテートファイル）
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

補足・注意事項
--------------
- KABUSYS_ENV の設定は重要です。live モードでは特に注意して環境変数と Kill Switch の扱いを確認してください。
- 本リポジトリの AI 機能は OpenAI API（API キー）に依存します。呼び出し回数やコストに注意してください。
- .env は絶対にリポジトリにコミットしないでください（config_setup でもその旨の注記があります）。
- ログディレクトリ作成に失敗した場合はコンソール出力のみ動作します（setup_logging の仕様）。
- ペーパートレード運用時は PAPER_FILL_MODE 等の設定を確認してください（instant / partial / never / reject）。

ライセンス・貢献
----------------
- 本 README ではライセンス情報を含めていません。実際のリポジトリに LICENSE ファイルが存在する場合はそちらを参照してください。
- バグ報告・機能追加は issue/PR を通じて行ってください。

以上。プロジェクト全体のエントリポイントや具体的な API の使い方は各モジュールのドキュメント（ソース内 docstring）を参照してください。必要であれば各コンポーネントごとの詳細なドキュメント（例: ExecutionEngine の起動フロー、OrderManager API、AlertManager の設定方法等）を別途作成します。