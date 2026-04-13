# KabuSys

日本株向け自動売買システムの一部モジュール群の README（日本語）

このリポジトリは、注文実行エンジン、監視（Monitoring）、ファクター計算・リサーチ、AI を使ったニュースセンチメント評価、ポートフォリオ構築ユーティリティ等を含むモジュール群です。以下はプロジェクトの概要、機能、セットアップと使い方、ディレクトリ構成の説明です。

注意: README は提供されたコードベースを元に作成しています。実運用前に設定や依存ライブラリ、セキュリティ要件を十分に確認してください。

プロジェクト概要
- KabuSys は日本株の自動売買に関連するモジュール群です（注文管理、実行、監視、リサーチ、AI ニューススコアリング、ポートフォリオ構築など）。
- 各モジュールは明確に責務が分かれており、DB 永続化は主に SQLite（監視用）と DuckDB（時系列データ・リサーチ用）を使います。
- 実行環境は KABUSYS_ENV で切り替え可能（development / paper_trading / live）。paper_trading モードではブローカーはモックとなり、データは paper_trading.db に分離されます。

主な機能一覧
- Execution（run_execution.py）
  - ブローカークライアントの生成（実アダプタ or Mock）
  - OrderManager / RiskManager / Reconciler を組み合わせた ExecutionEngine の起動
  - paper_trading 環境では本番 DB と分離して data/paper_trading.db を使用
- Monitoring（run_monitoring.py と監視モジュール群）
  - SystemMonitor: CPU / メモリ / ディスク / プロセス生存チェック、データ鮮度チェック
  - TradeMonitor: 注文の滞留チェック、約定価格の異常検知
  - RiskMonitor: ドローダウン・ポジション上限の監視、ダッシュボード更新
  - KillSwitch: 異常時に flag ファイルを書き実行エンジン停止シグナルを送る
  - AlertManager: LINE Messaging API 経由でアラートをプッシュ
  - Streamlit ベースの監視ダッシュボード（streamlit_dashboard.py）
- AI（kabusys.ai）
  - news_nlp: OpenAI（gpt-4o-mini）を使ったニュースのセンチメントスコア化と ai_scores への書き込み
  - regime_detector: ETF（1321）MA200 とマクロニュースの LLM スコアを合成して market_regime 判定
- Research（kabusys.research）
  - ファクター計算（Momentum / Volatility / Value）、将来リターン計算、IC（Spearman）などの統計関数
  - DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算
- Portfolio（kabusys.portfolio）
  - 候補選定、等ウェイト / スコアウェイト計算、セクターキャップ適用、ポジションサイジング（lot 単位、リスク制限、aggregate cap）
- Utils
  - process_priority: プロセス優先度設定、CPU affinity（Windows / POSIX を吸収）
  - 環境変数読み込み・Settings（kabusys.config）: .env と .env.local の読み込み、自動ロード機能

セットアップ手順（開発用）
1. リポジトリをクローンする
   - git clone <repo-url>
2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate （Windows: .venv\Scripts\activate）
3. 必要ライブラリをインストール
   - 以下は主な依存項目です（requirements.txt がない場合の例）
     - duckdb
     - psutil
     - openai
     - requests
     - streamlit
   - 例:
     - pip install duckdb psutil openai requests streamlit
   - 実際のプロジェクトでは requirements.txt / poetry / pipenv を用意して管理してください。
4. データディレクトリを作成
   - mkdir -p data
   - （初回起動時に SQLite / DuckDB ファイルは自動作成 / マイグレーションされます）
5. 環境変数（.env）を用意
   - プロジェクトルートに .env / .env.local を置いてください（kabusys.config が自動で読み込みます）
   - 主要な環境変数（必須／推奨）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - OPENAI_API_KEY (AI 機能を使う場合に必須)
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB; デフォルト: data/paper_trading.db）
     - SQLITE_PATH（monitoring 用 DB; デフォルト: data/monitoring.db）
     - DUCKDB_PATH（DuckDB ファイル; デフォルト: data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート送信時）
     - PAPER_FILL_MODE（paper_trading の約定モード: instant|partial|never|reject、デフォルト: instant）
     - その他: PID_FILE_PATH, KILL_FLAG_PATH, CPU/MEM/DISK 閾値等（Settings を参照）
   - 自動ロード無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
6. DB 初期化
   - 監視 DB 初期化は run_monitoring/run_execution 内で init_monitoring_db が呼ばれます。手動で初期化する必要は通常ありません。

使い方（よく使うコマンド例）
- Monitoring を起動
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - python -m kabusys.run_monitoring
  - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 備考: run_monitoring は常に settings.sqlite_path（本番 monitoring DB）を使います（KABUSYS_ENV に依存しない）。
- ExecutionEngine を起動
  - KABUSYS_ENV によって動作が切り替わります。paper_trading の場合は MockBrokerClient を使用し paper_sqlite_path に記録します。
  - 例（本番想定）: KABUSYS_ENV=live python -m kabusys.run_execution
  - 例（ペーパー）: KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 実行開始時にプロセス優先度が "high" に設定されます（set_process_priority）。
- Streamlit 監視ダッシュボード起動
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは監視 DB を読み取り専用で開きます（起動中の MonitoringEngine が書き込みます）。
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで SQLite ファイルを指定可能（デフォルトは PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db）
- AI 機能呼び出し（コードから）
  - kabusys.ai.score_news(conn, target_date, api_key=None)  — OpenAI API キーを引数か環境変数で渡す
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

環境変数・設定の主な説明
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- JQUANTS_REFRESH_TOKEN: J-Quants API のトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- SQLITE_PATH: 監視用 SQLite DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE: paper_trading の約定動作（instant|partial|never|reject）

ディレクトリ構成（主要ファイルと説明）
- src/kabusys/
  - __init__.py — パッケージ定義（__version__ 等）
  - config.py — 環境変数の自動ロードと Settings クラス
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite ベースの永続化・CRUD ヘルパ（init も含む）
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py — 注文滞留・約定異常の監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — flag ファイルによる停止シグナルの管理
    - alert_manager.py — LINE へプッシュ通知送信
    - monitoring_engine.py — 各モニタを束ねるエンジン
    - streamlit_dashboard.py — Streamlit 監視 UI（起動方法あり）
  - execution/
    - order_manager.py — 注文状態遷移と外向き API
    - reconciler.py — 起動時リコンシリエーション（ブローカーと同期）
    - (その他: broker_factory, execution_engine, order_repository などが存在する前提)
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 株数決定・リスク制限・単元丸め
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 等のファクター計算
    - feature_exploration.py — 将来リターン計算・IC・統計サマリ
  - ai/
    - news_nlp.py — ニュースを LLM でスコアリングして ai_scores へ書込む
    - regime_detector.py — MA200 とマクロニュースで市場レジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成
  - data/（実行時に利用するデフォルト配置）
    - kabusys.duckdb (DUCKDB_PATH)
    - monitoring.db (SQLITE_PATH)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
    - kill.flag / execution.pid（PID・kill flag 用）

運用上の注意
- 実際の売買システムの運用は法的・金融上のリスクを伴います。本コードを本番で動かす場合はブローカー API の正確な仕様、レート制限、注文失敗のハンドリング、テスト、監査、および資金管理ルールを十分に整備してください。
- OpenAI 呼び出しは API コストとレイテンシが発生します。API キーの管理に注意してください。
- process priority / CPU affinity の設定は権限による失敗が起こり得ます（ログでスキップされます）。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を起点）から実行されることを前提としています。CI/コンテナ環境では OS 環境変数での管理を推奨します。

開発者向け補足
- monitoring DB のスキーマ変更時は monitoring_db.init_monitoring_db のマイグレーションコードを拡張してください（既存 DB に対して冪等に適用されます）。
- AI 部分の API 呼び出しはテスト時に _call_openai_api をモックする設計になっています（ユニットテストでの差し替えが容易）。
- DuckDB を用いた解析関数は接続を受け取る純粋関数的インタフェースになっており、テストがしやすい設計です。

ライセンス / 貢献
- この README に記載のコード片は提示コードに基づきます。実際のリポジトリの LICENSE を参照してください。
- バグ報告・プルリクエストはリポジトリの Issue / PR をご利用ください。

以上。必要であれば README にサンプル .env.example や systemd / Docker Compose の起動例、requirements.txt の候補等を追加で作成します。どの情報を追加しますか？