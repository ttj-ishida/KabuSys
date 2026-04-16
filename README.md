KabuSys — 日本株自動売買システム（リポジトリ README）
概要、機能、セットアップ、使い方、ディレクトリ構成を日本語でまとめます。

プロジェクト概要
- KabuSys は日本株の自動売買 / リサーチ / 監視を行うための内部ライブラリ群とランナー（ExecutionEngine / Monitoring）を含むシステムです。
- DuckDB を用いたリサーチ（ファクター計算・特徴量探索）、SQLite による監視ログ保存、外部ブローカー API（本番 or Mock）経由の発注や再同期、LLM（OpenAI）を用いたニュース NLP / レジーム検知などの機能を持ちます。
- 設計方針として「本番と paper_trading の分離」「ルックアヘッドバイアスの排除」「フェイルセーフ（API失敗時のフォールバック）」等が反映されています。

主な機能一覧
- ExecutionEngine（発注エンジン）
  - Broker クライアント（実ブローカー or Mock）を用いた発注、注文管理、リコンシリエーション機能
  - リスク管理（RiskManager）やOrderManager, Reconciler などのコンポーネントを統合
  - KABUSYS_ENV=paper_trading 時は MockBroker を使用し、paper 用 SQLite に記録（実 DBと分離）
- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、Execution プロセスの存在チェック
  - TradeMonitor: 滞留注文（stale order）や約定異常価格の検出
  - RiskMonitor: ドローダウン & ポジション上限の監視、ダッシュボード更新
  - KillSwitch / AlertManager: しきい値到達時の kill.flag 書込みや LINE への通知（push）
  - MonitoringEngine: 上記 Monitor を定期実行するポーリングエンジン
  - Streamlit ダッシュボード（監視情報の可視化）
- Research / Portfolio
  - ファクター計算（momentum / volatility / value など）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
  - 銘柄選定、重み計算、ポジションサイズ算出、セクター制限やレジーム乗数
- AI（OpenAI）
  - ニュース記事を LLM でスコアリングして ai_scores に保存（news_nlp）
  - マクロニュース + 板情報を使った市場レジーム判定（regime_detector）
- ツール
  - paper_trading の検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

セットアップ手順（開発・実行に必要な最低限）
1. 前提
   - Python 3.10+（typing の | 記法、match などが不要だが union の記法を使用）
   - SQLite（Python 標準ライブラリ sqlite3 で十分）
2. リポジトリクローン
   - git clone <repo>
   - 作業ディレクトリのルートに移動（pyproject.toml や .git がある階層がプロジェクトルートとなる）
3. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
4. 依存パッケージのインストール
   - pip install duckdb psutil requests openai streamlit
     （必要に応じてバージョンを固定してください）
   - 標準ライブラリで済むもの（sqlite3, threading, logging 等）は追加不要
5. 環境変数 / .env
   - プロジェクトルートに .env, .env.local を置くと自動で読み込まれます（環境変数が優先）。
   - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
   - 主要な環境変数（代表例）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN（必須: J-Quants 関連）
     - KABU_API_PASSWORD（必須: kabuステーション API 用）
     - OPENAI_API_KEY（AI 機能を使う場合必須）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（AlertManager が LINE に送る場合）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用 DB デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE（paper_trading の約定挙動: instant|partial|never|reject。デフォルト instant）
     - MONITOR_POLL_INTERVAL（監視ポーリング間隔秒。デフォルト 60）
     - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START 等
6. データディレクトリ
   - data/ 以下に DB, pid, flag ファイルが作成されます（例: data/monitoring.db, data/execution.pid, data/kill.flag）。
   - 必要に応じてディレクトリを手動で作成しておくと良いです。

基本的な使い方（起動・操作）
- Execution エンジン起動（実運用 or paper_trading）
  - 環境変数で環境を指定:
    - 本番/実トレード: export KABUSYS_ENV=live
    - 試験的 paper_trading: export KABUSYS_ENV=paper_trading
  - 起動コマンド:
    - python -m kabusys.run_execution
    - 実行時、paper_trading 環境なら MockBroker を使い paper_trading 用 SQLite に記録します。
  - 停止方法:
    - run_execution は data/stop_requested.flag の存在を監視します。停止したい場合はこのファイルを作成してください（例: touch data/stop_requested.flag）。また、KillSwitch による停止は data/kill.flag の作成で実行エンジンに停止シグナルが送られます（KillSwitch は条件を満たすと自動で書き込みます）。
- Monitoring 起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60）。
  - 監視は本スクリプトが起動した環境に関わらず sqlite_path のデフォルト（本番パス）を使用します（監視は本番 DB を参照する設計）。
- Streamlit ダッシュボード
  - 起動例:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視用 SQLite を read-only で開いて可視化します。
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 簡易な稼働率・注文成功率・レイテンシ等のサマリを標準出力に出力します。
- AI 機能（ニュース NLP / レジーム判定）
  - OPENAI_API_KEY を設定してから、kabusys.ai.score_news / regime_detector.score_regime をアプリケーションから呼び出してください。
  - OpenAI API の呼び出しはバッチ分割、リトライ、レスポンス検証、スコアクリッピングなどのフェイルセーフ実装があります。

注意事項 / 運用メモ
- DB 分離
  - paper_trading モードでは paper 用 SQLite（デフォルト data/paper_trading.db）を使用し、本番データベースと完全に分離します。
- フラグファイル
  - data/stop_requested.flag: run_execution / run_monitoring が起動中ループで停止を検出するファイル
  - data/kill.flag: KillSwitch が書き込むことで ExecutionEngine に停止を促す（KillSwitch は条件判定後に書き込む）。Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すれば起動時にクリアできます。
- プロセス優先度 / CPU affinity
  - 起動時に set_process_priority("high") を呼びます（psutil を使用）。権限不足で設定できない可能性があるため警告ログのみ出ます。
- Logging / ログレベル
  - Settings.log_level によるチェックあり。環境変数 LOG_LEVEL で変更可能。
- DuckDB / prices_daily テーブルなど
  - リサーチ系は DuckDB にロードされた prices_daily / raw_financials 等のテーブルを利用します。まずはデータを DuckDB に用意してください。
- テスト / 開発
  - モジュールは関数単位に分割されており、個別にユニットテストを書きやすい設計です。OpenAI 呼び出しは内部関数を patch してテスト可能です。

主なディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / .env 自動読み込み / Settings
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py      — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他 Broker 関連・ExecutionEngine 実装ファイル)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - process_priority.py
  - data/ (実行時に生成される想定)
    - monitoring.db (デフォルト)
    - kabusys.duckdb (デフォルト)
    - paper_trading.db (paper_trading 用)
    - execution.pid, stop_requested.flag, kill.flag

開発者向けヒント
- .env のパースは config._parse_env_line に実装済みで、export プレフィックスやクォート、インラインコメントをかなり正確に扱います。
- 自動 .env 読み込みはプロジェクトルートの検出（.git または pyproject.toml）を行ってから実行されます。CI 等で自動読み込みを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- OpenAI 呼び出しはレスポンスの JSON 構造を厳密に検証します。テストでは _call_openai_api をモックすることを推奨します。

よく使うコマンド例
- 実行エンジン起動（paper_trading）
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution
- 監視起動
  - python -m kabusys.run_monitoring
- ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper 検証レポート（例）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

問い合わせ / 貢献
- バグ修正や機能改善は Pull Request を送ってください。設計方針（ルックアヘッド回避、フェイルセーフ等）を維持するようお願いします。

以上がリポジトリの概要と導入・運用に必要な情報のサマリです。README に追記してほしい具体的な点（例: 依存バージョン固定、起動スクリプトの supervisor/systemd サンプル、詳細な DB スキーマ説明など）があれば教えてください。