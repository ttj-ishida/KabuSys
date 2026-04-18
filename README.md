KabuSys — 日本株自動売買システム（README — 日本語）

概要
- KabuSys は日本株の自動売買・リサーチ・監視機能を備えた小規模なシステムです。
- DuckDB を用いたファクター計算やニュースNLP（OpenAI）を使ったセンチメント評価、ExecutionEngine（発注ロジック）とそれを監視する Monitoring コンポーネントを持ちます。
- 環境に応じて paper_trading（モックブローカー）と live（実運用）を切替可能で、監視・Kill Switch による安全停止機構を備えています。

主な機能一覧
- ExecutionEngine 起動スクリプト（run_execution）  
  - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 用の SQLite に記録（本番 DB と分離）
  - PID ファイル管理、停止フラグ検知による安全停止
- Monitoring（run_monitoring / MonitoringEngine）  
  - システムリソース監視（CPU / メモリ / ディスク）、データ鮮度チェック、プロセス生存チェック
  - 監視ログを SQLite に保存（system_status, trade_logs, risk_logs, positions, dashboard）
  - KillSwitch による停止フラグ（data/kill.flag）書き込み、アラート通知連携（LINE 等の設定があれば）
- Portfolio モジュール（選定・配分・リスク調整・ポジションサイズ計算）  
  - 等重配分 / スコア加重 / リスクベースの単純関数群
- Research（factor_research / feature_exploration）  
  - Momentum, Volatility, Value 等のファクター計算（DuckDB を使用）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- AI（news_nlp / regime_detector）  
  - ニュース記事を OpenAI（gpt-4o-mini 想定）でセンチメント評価し ai_scores に書き込み
  - ETF とマクロ記事を組み合わせた市場レジーム判定（bull/neutral/bear）
- ユーティリティ  
  - .env 対話式作成ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report）

セットアップ手順（ローカル開発向け）
1. リポジトリをクローンする
   - git clone ... && cd repo

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - Unix/macOS: source .venv/bin/activate
   - Windows (PowerShell): .\.venv\Scripts\Activate.ps1

3. 必要なパッケージをインストール
   - 必須: duckdb, psutil, openai
   - 任意（YAML 検証）: PyYAML
   - 例:
     - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt があれば `pip install -r requirements.txt` を使用）

4. 環境変数（.env）を作成
   - 推奨: 対話式ウィザードを実行して .env を作成
     - python -m kabusys.config_setup
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要: .env を絶対に Git にコミットしないこと

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 厳密モード（警告を FAIL 扱い）: python -m kabusys.validate_config --strict

基本的な使い方
- ExecutionEngine の起動
  - 設定例（paper_trading）:
    - KABUSYS_ENV=paper_trading を .env に設定するか環境変数で export してください。
    - paper_trading では MockBrokerClient を使いデータは data/paper_trading.db（または PAPER_TRADING_SQLITE_PATH）に保存されます。
  - 起動:
    - python -m kabusys.run_execution
  - 停止:
    - run_execution は data/stop_requested.flag を監視しています。停止させるにはそのファイルを作成してください（外部管理のため注意）。
    - Kill Switch が発動すると data/kill.flag が書かれ、ExecutionEngine 側が停止を検出します。

- Monitoring の起動
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - Monitoring は常に本番 sqlite_path を使用（KABUSYS_ENV にかかわらず）
  - 起動:
    - python -m kabusys.run_monitoring
  - 停止:
    - run_monitoring は data/stop_requested.flag を検知してループを抜けます。停止ファイルを置くと次のポーリングで終了します。

- .env 作成ウィザード / 検証
  - ウィザード: python -m kabusys.config_setup
  - 検証: python -m kabusys.validate_config [--strict]

- Paper Trading 検証レポート
  - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）
  - 実行例:
    - python -m kabusys.tools.paper_verification_report
    - 期間指定: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - レポートは稼働率、注文成功率、送信率、レイテンシ（P95）等を計算して PASS/FAIL 判定を行います。

主要な環境変数（抜粋）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 動作モード:
  - KABUSYS_ENV = development | paper_trading | live
- DB / ログ:
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, default: data/paper_trading.db)
  - LOG_LEVEL (DEBUG/INFO/...)
  - LOG_DIR (デフォルト: logs/)
- その他:
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒数）
  - OPENAI_API_KEY（news_nlp / regime_detector で必要）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート通知用、任意）
  - KILL_FLAG_CLEAR_ON_START（本番での自動クリアは危険 → default 0 推奨）

安全に関する注意点
- .env は機密情報を含むため、絶対にリポジトリにコミットしないこと。
- KABUSYS_ENV=live の場合は設定を慎重に確認してください（validate_config に警告が出ます）。
- KILL_FLAG_CLEAR_ON_START=1 を本番で設定するのは危険です（自動的に kill.flag をクリアしてしまう）。
- Monitoring の停止/起動制御は data/stop_requested.flag と data/kill.flag によって行われます。手動でフラグを書き換える運用では注意して扱ってください。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数 / Settings 管理
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）による銘柄別センチメント評価
    - regime_detector.py — 市場レジーム判定（ETF + マクロSentiment）
  - monitoring/
    - monitoring_db.py — 監視用 SQLite 永続化層（スキーマ初期化含む）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — （取引ログ監視 — 期間内の滞留/異常検出）
    - risk_monitor.py — ドローダウン監視・ポジション上限監視
    - monitoring_engine.py — 複数モニタを束ねるエンジン
    - kill_switch.py — Kill Switch 実装（data/kill.flag 書き込み）
    - alert_manager.py — （アラート管理・通知）
  - execution/
    - execution_engine.py — ExecutionEngine の本体（発注セッション管理）
    - order_manager.py / order_repository.py / reconciler.py / risk_manager.py — 発注関連コンポーネント
    - broker_factory.py — BrokerClient の生成（実ブローカー or Mock）
  - portfolio/
    - portfolio_builder.py — 候補選定・得点ソート
    - position_sizing.py — 発注株数計算
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — モメンタム/バリュー/ボラティリティ等
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - data/ (ランタイム生成)
    - monitoring.db（デフォルト SQLITE_PATH）
    - paper_trading.db（paper_trading 用）
    - kabusys.duckdb（デフォルト DUCKDB_PATH）
    - execution.pid / stop_requested.flag / kill.flag
  - logs/（デフォルトログディレクトリ、setup_logging により生成）

補足
- DuckDB は分析用のローカル DB として利用します。prices_daily, raw_financials, raw_news 等のテーブルを前提としたファクタ計算モジュールが含まれます。
- OpenAI による NLP 機能は API キーが必要です。API エラー時はフォールバック動作（0.0 等）を取り、システム全体が停止しないよう設計されています。
- 各モジュールはテストしやすい純粋関数設計（副作用を最小化）を意識して実装されています。monitoring_db などの永続層はシンプルな読み書きインターフェースを提供します。

問い合わせ / 開発メモ
- 何をどう動かせばよいか分からない場合は、まず `python -m kabusys.config_setup` で .env を作成し、`python -m kabusys.validate_config` で状態を確認してください。
- 実際に発注を行う live 環境に切り替える際は、KABUSYS_ENV=live と各 API キー/パスワードの設定、LINE 等のアラート設定を必ず確認してください。

以上。必要であれば README を README.md 形式のマークダウンに整形したり、実行例や systemd / cron 用のサービスユニットサンプルを追加できます。どの情報を追加しますか？