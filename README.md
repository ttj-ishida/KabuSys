# KabuSys

KabuSys は日本株向けの自動売買／研究プラットフォームの一部実装です。本リポジトリには、発注実行エンジン、監視（Monitoring）機能、ポートフォリオ構築ユーティリティ、リサーチ用モジュール、ニュース NLP / レジーム判定などの補助ツールが含まれます。

以下はこのコードベースの README（日本語）です。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（起動／停止／ツール）
- 環境変数（主要なもの）
- ディレクトリ構成（概要）
- 運用上の注意点

---

プロジェクト概要
- 日本株自動売買システム（KabuSys）のコンポーネント群のサンプル／実装。
- 発注ロジックそのもの（ExecutionEngine）と、それを監視・保護する監視スタック（SystemMonitor, TradeMonitor, RiskMonitor）を備える。
- Paper Trading モードをサポートし、本番 DB と分離して検証可能。
- DuckDB を使ったデータ分析・ファクター計算モジュール、OpenAI を利用するニュース NLP / レジーム判定の統合機能、Streamlit ダッシュボードなどを提供。

主な機能一覧
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使い、paper_trading 用の専用 SQLite DB に記録して本番 DB と分離。
  - プロセス優先度を高に設定して実行。
  - 停止フラグ（data/stop_requested.flag）で安全に停止可能。
- Monitoring（run_monitoring.py）
  - SystemMonitor / TradeMonitor / RiskMonitor を周期的に実行し、監視データを SQLite に保存。
  - MONITOR_POLL_INTERVAL でポーリング間隔を調整（デフォルト 60 秒）。
  - Monitoring は実行環境（KABUSYS_ENV）に関わらず本番 sqlite_path を使用（設定に注意）。
- KillSwitch / AlertManager
  - リスク閾値（ドローダウン・ポジション上限など）を超えると data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送る。
  - LINE Messaging API 経由の通知機能（AlertManager）。
- Portfolio（portfolio.*）
  - 候補選定、等配分／スコア配分、リスク調整（セクターキャップ、レジーム乗数）、ポジションサイズ計算（単元丸め・利用可能資金のスケーリング）を提供する純粋関数群。
- Research（research.*）
  - DuckDB 上でファクター計算（モメンタム／ボラティリティ／バリュー）や将来リターン、IC（Information Coefficient）などの分析を実行。
- AI（ai.*）
  - raw_news を用いたニュースセンチメント評価（OpenAI）と銘柄ごとの ai_scores 書込み。
  - マクロニュース + ETF（1321）の MA200 値から市場レジーム判定を行い market_regime テーブルへ書き込み。
  - API 呼び出しは冗長性を考慮したリトライ・フェイルセーフ実装。
- Tools
  - Paper Trading の検証レポート生成ツール（kabusys.tools.paper_verification_report）。
- Streamlit ダッシュボード
  - 監視データ（dashboard / positions / trade_logs / system_status / risk_logs）を可視化する簡易 UI。

セットアップ手順（ローカル開発向け）
1. Python バージョン
   - Python 3.10 以上を推奨（typing の | 記法等を使用）。

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール（代表例）
   - pip install duckdb psutil requests openai streamlit
   - sqlite3 は標準ライブラリに含まれます。
   - 実際のプロジェクトでは requirements.txt を作成して管理してください。

4. プロジェクトルートに data ディレクトリを作る
   - mkdir -p data

5. 環境変数 / .env の用意
   - プロジェクトは自動的にプロジェクトルートの .env / .env.local を読み込みます（OS 環境変数優先）。
   - テストや明示的に読み込みを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定できます。
   - 必須（主要）環境変数：JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - AI 機能を使う場合：OPENAI_API_KEY
   - 例（プロジェクトルート/.env）:
     JQUANTS_REFRESH_TOKEN=your_jquants_token
     KABU_API_PASSWORD=your_kabu_password
     OPENAI_API_KEY=sk-...
     KABUSYS_ENV=development
     PAPER_FILL_MODE=instant
     SQLITE_PATH=data/monitoring.db
     DUCKDB_PATH=data/kabusys.duckdb
     PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

注意: .env のパースはシェル風の export KEY=val / quoted values / inline comment をある程度サポートします（config.py 内の実装参照）。

使い方（コマンドと運用）
- ExecutionEngine（発注エンジン）起動
  - 本番風: KABUSYS_ENV=live python -m kabusys.run_execution
  - Paper Trading（モックブローカー・専用 DB）: KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 動作: process priority を "high" に設定し、Thread でエンジンを起動します。起動時に data/stop_requested.flag が存在する場合は起動を中止します。
  - 停止: data/stop_requested.flag を作成すると走査ループで検知してエンジン停止を促します（run_execution と run_monitoring 両方で使用）。
- Monitoring 起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き（例: MONITOR_POLL_INTERVAL=30）。
  - 注意: Monitoring は KABUSYS_ENV に関係なく Settings.sqlite_path（デフォルト data/monitoring.db）を使用します。
- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - もしくは python -m streamlit run ... と同様に実行。
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Kill / Stop 制御
  - stop_requested.flag（data/stop_requested.flag）:
    - run_monitoring.py と run_execution.py はプロジェクトルートの data/stop_requested.flag を参照してループを終了します。運用上の「安全停止」用フラグ。
  - kill.flag（data/kill.flag）:
    - KillSwitch（監視側）が条件を満たすと data/kill.flag を書き込み、ExecutionEngine に「停止せよ」と指示します（ExecutionEngine 側がこのファイルをチェックしている場合）。
    - 手動で解除する場合: rm data/kill.flag または KillSwitch.clear() を利用する（Python API）。
- Paper Trading DB の分離
  - KABUSYS_ENV=paper_trading のとき、run_execution は Settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使います。これにより本番監視 DB と注文ログが分離されます。

主要な環境変数（抜粋）
- 必須 / 主要
  - JQUANTS_REFRESH_TOKEN — J-Quants API トークン（Settings.jquants_refresh_token）
  - KABU_API_PASSWORD — kabuステーション API パスワード
- AI / optional
  - OPENAI_API_KEY — OpenAI API キー（ai.news_nlp, ai.regime_detector で使用）
- 動作制御 / パス
  - KABUSYS_ENV — "development" | "paper_trading" | "live"（デフォルト development）
  - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring にのみ使用）
  - SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
  - DUCKDB_PATH — DuckDB ファイル（デフォルト data/kabusys.duckdb）
  - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
  - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, PAPER_FILL_MODE など（Settings を参照）

ディレクトリ構成（主要ファイルの説明）
- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数 / Settings 管理（.env 自動読み込みロジック含む）
  - run_execution.py — ExecutionEngine 起動スクリプト（実行用エントリポイント）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - execution/
    - order_manager.py — 発注管理（OrderManager）
    - reconciler.py — リコンシリエーション（起動時復旧）
    - order_repository.py, order_record.py, execution_engine.py, broker_factory.py, ...（発注周りの実装）
  - monitoring/
    - monitoring_db.py — 監視用 SQLite 永続化層（テーブル定義・CRUD）
    - system_monitor.py — システム・データ鮮度チェック
    - trade_monitor.py — 注文滞留・約定異常チェック
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書き込みロジック
    - alert_manager.py — LINE push 通知
    - monitoring_engine.py — 各 Monitor を束ねる実行エンジン
    - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py — ポートフォリオ関連の純粋関数群
  - research/
    - factor_research.py, feature_exploration.py — ファクター計算・特徴量解析
  - ai/
    - news_nlp.py — ニュースの NLP スコアリング（OpenAI）
    - regime_detector.py — レジーム判定（MA200 + マクロセンチメント）
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

運用上の注意点 / 実装に関する補足
- Monitoring と Execution の DB 分離:
  - run_monitoring は常に Settings.sqlite_path を使用（コメントでも明記）。Production 監視 DB を想定しているため KABUSYS_ENV に依存しません。
  - run_execution は KABUSYS_ENV に応じて paper_sqlite_path または sqlite_path を選択します。
- プロセス優先度:
  - 実行開始時に set_process_priority("high") を試みます（権限によって失敗する場合はワーニング）。
- OpenAI 呼び出し:
  - ニュース NLP / レジーム判定は OpenAI（gpt-4o-mini 想定）を利用します。API キーが未設定の場合はそれぞれ例外やフェイルセーフ（多くはスコア 0.0）になります。大量呼び出し時はレート制限に注意。
- マイグレーション:
  - monitoring_db.init_monitoring_db は idempotent（既存 DB に対するマイグレーション処理を含む）。初回実行時にテーブル・カラムを作成します。
- ロギング:
  - 各スクリプトは基本的に logging.basicConfig(level=logging.INFO) を使用。必要に応じて LOG_LEVEL 環境変数（Settings.log_level）を設定して強化できます。
- フラグ・ファイル方式:
  - 停止や kill のためのファイルベースのシグナル（data/stop_requested.flag, data/kill.flag）を用いており、コンテナや単純な運用環境で分かりやすく実装されています。運用時は権限・共有場所に注意してください。

---

以上です。必要であれば以下を追加できます:
- requirements.txt の推奨内容
- より詳細な起動手順（systemd / Docker / docker-compose 用のサンプル）
- unit tests の実行方法や CI 設定例
- 各モジュールの API ドキュメント（関数別のパラメータ説明）