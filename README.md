# KabuSys

KabuSys は日本株の自動売買システムのコードベースです。本リポジトリには以下の主要機能群を含みます: 注文実行エンジン、監視（System / Trade / Risk）コンポーネント、ポートフォリオ構築ロジック、リサーチ（ファクター計算）モジュール、AI を使ったニュース NLP / レジーム判定、および運用ユーティリティ群。

以下はこのコードベースの概要、機能、セットアップ手順、使い方、ディレクトリ構成の説明です。

プロジェクト概要
- 目的: 日本株向けの自動売買基盤（ExecutionEngine）と、それを安全に運用するための監視・アラート・リスク管理機能を提供する。
- 設計方針:
  - DB は SQLite（監視ログや paper trading 用 DB）と DuckDB（価格・財務データ分析）を使用。
  - Paper Trading モードでは実際のブローカー API を使わず MockBrokerClient と専用 DB（data/paper_trading.db）で完全に分離。
  - AI モジュールは OpenAI（gpt-4o-mini）を利用し、ニュースセンチメントやマクロセンチメントを算出する（API キー必須）。
  - モジュールはテスト性・冪等性を考慮して実装されている（例: DB 初期化は冪等、部分失敗に配慮した書き込み等）。

機能一覧
- Execution
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
  - ブローカーファクトリ / OrderManager / Reconciler（起動時の自動リコンシリエーション）
  - RiskManager による発注前のリスクチェック（ポジション比率・利用率・ドローダウン等）
  - Paper Trading モード（KABUSYS_ENV=paper_trading）で MockBroker を用いる
- Monitoring
  - SystemMonitor: CPU・メモリ・ディスク・プロセス状態・データ鮮度監視
  - TradeMonitor: 滞留注文 / 約定価格異常検出
  - RiskMonitor: ドローダウンやポジション上限の監視とリスクイベント記録
  - MonitoringEngine: 上記モニタを束ねてポーリング -> アラート送信 / Kill Switch 評価
  - AlertManager: LINE Messaging API による通知（チャンネルアクセストークン / ユーザID 必要）
  - Streamlit ダッシュボード（src/kabusys/monitoring/streamlit_dashboard.py）で監視状況の可視化
  - monitoring 用の SQLite スキーマ定義 / 永続化（monitoring_db.py）
- Portfolio（銘柄選定・配分・サイズ計算）
  - 候補選び・等重・スコア重み（portfolio_builder.py）
  - セクター制限、レジーム乗数（risk_adjustment.py）
  - 株数算出、単元株丸め、集約上限スケーリング（position_sizing.py）
- Research（DuckDB を用いたファクター / 探索）
  - Momentum / Volatility / Value のファクター計算（factor_research.py）
  - 将来リターン計算、IC（情報係数）、統計サマリ（feature_exploration.py）
- AI
  - ニュース NLP による銘柄別センチメントスコアリング（kabusys.ai.news_nlp.score_news）
  - レジーム判定（kabusys.ai.regime_detector.score_regime）
  - OpenAI API 呼び出しはリトライ・エラーハンドリング・レスポンス検証を備える
- 運用ユーティリティ
  - 環境設定管理（src/kabusys/config.py）: .env 自動読み込み（.env.local が .env を上書き）
  - プロセス優先度 / CPU affinity の設定ユーティリティ（utils/process_priority.py）
  - 各種ツールスクリプト（例: Paper Trading 検証レポート生成ツール）

セットアップ手順（ローカル開発・運用向け）
1. Python バージョン
   - Python 3.9+ を推奨（コードは typing /新構文を利用）
2. リポジトリをクローンし、仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール
   - 必要なライブラリ（抜粋）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - 例:
     - pip install duckdb psutil requests openai streamlit
   - 実運用では requirements.txt / poetry / pip-tools を用意して管理してください（このコードベースには同梱されていないため環境に合わせて作成）。
4. データディレクトリの用意
   - デフォルトでは data/ 以下を使います:
     - data/monitoring.db （監視用 SQLite）
     - data/paper_trading.db （PaperTrading 用 SQLite）
     - data/kabusys.duckdb （DuckDB）
     - data/execution.pid （実行エンジンの PID 保存）
     - data/stop_requested.flag / data/kill.flag（停止・強制停止フラグ）
   - 必要に応じて先に空ファイルやディレクトリを作成しておくと安心です（コードは起動時に親ディレクトリ作成を行う箇所あり）。
5. 環境変数 / .env
   - 自動読み込み順: OS 環境変数 > .env.local > .env
   - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
   - 主な環境変数:
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須機能で使用）
     - KABU_API_PASSWORD: kabuステーション API 用（必須）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
     - SQLITE_PATH: 監視 DB path（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: PaperTrading DB path（デフォルト: data/paper_trading.db）
     - DUCKDB_PATH: DuckDB path（デフォルト: data/kabusys.duckdb）
     - PAPER_FILL_MODE: instant | partial | never | reject（paper trading のフィルモード）
     - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔秒（デフォルト: 60）。1以上の整数で指定。無効な値はデフォルトにフォールバック。

使い方（主要な実行例）
- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 機能:
    - プロセス優先度を high に設定（可能な場合）
    - monitoring 用 SQLite（Settings.sqlite_path）と DuckDB に接続
    - SystemMonitor.check_once() を周期的に実行（MONITOR_POLL_INTERVAL 秒、デフォルト 60）
    - data/stop_requested.flag が存在するとループを終了
    - 監視は monitoring DB を常に本番 sqlite_path で使用（run_monitoring は KABUSYS_ENV に関わらず sqlite_path を使用）
- ExecutionEngine を起動（発注エンジン）
  - python -m kabusys.run_execution
  - 機能:
    - KABUSYS_ENV=paper_trading のときは paper_sqlite_path（data/paper_trading.db）を使用し、MockBrokerClient を用いる
    - 通常は settings.sqlite_path（本番監視 DB と同じファイル）を使用
    - 起動時に stop flag（data/stop_requested.flag）があれば起動を中止
    - data/execution.pid に PID を書く
    - スレッドで ExecutionEngine.run_session を実行し、stop flag を検知すると停止要求を送る
- Streamlit ダッシュボード（監視）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視用 DB を read-only モードで開き、Overview / Positions / Orders / System 情報を表示
- Paper Trading 検証レポート生成ツール
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - 簡易的な Pass/Fail 基準で稼働率・注文成功率・送信率・P95 レイテンシ等を出力
- AI 機能（プログラム経由）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - どちらも OPENAI_API_KEY を引数または環境変数で指定する必要あり

運用上の注意
- 停止制御:
  - 実行中プロセスを安全に停止させるために data/stop_requested.flag（run_monitoring/run_execution で参照）を用いる
  - KillSwitch（監視側）は data/kill.flag を書き込み、ExecutionEngine に対して停止シグナルを送る設計
  - kill.flag は Settings.kill_flag_clear_on_start 等の設定で起動時クリア制御が可能
- DB マイグレーション:
  - monitoring_db.init_monitoring_db() は冪等にテーブルを作成し、既存 DB に対する簡単なカラム追加マイグレーションも行う
- Paper Trading:
  - paper_trading 環境では本番ブローカーとは完全に分離された DB を使用することが推奨される
- OpenAI API 呼び出しに関する注意:
  - API レート制限・エラーに対してリトライロジックを組んであるが、コストとレート制限に注意してください

主要ディレクトリ構成（src/kabusys 以下）
- __init__.py
  - パッケージ定義・バージョン
- config.py
  - 環境変数の自動読み込みロジック、Settings クラス（各種パス・閾値・フラグ）
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔指定）
- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading の場合は専用 DB と MockBroker を使用）
- monitoring/
  - monitoring_db.py: monitoring 用 SQLite スキーマ・DB 操作ラッパー（MonitoringDB）
  - system_monitor.py: CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - trade_monitor.py: 注文滞留 / 約定価格異常検出
  - risk_monitor.py: ドローダウン / ポジション上限チェック
  - kill_switch.py: kill.flag 書き込み・評価ロジック
  - alert_manager.py: LINE Push API による通知（クールダウン管理付き）
  - monitoring_engine.py: 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py: 監視ダッシュボード（Streamlit）
- execution/
  - order_manager.py: Order 管理・状態遷移の外向け API
  - reconciler.py: 起動時のブローカー照合・ポジション差分検出
  - （他に broker_factory, execution_engine, order_repository 等が想定）
- portfolio/
  - portfolio_builder.py: 候補選定・スコアソート
  - position_sizing.py: 株数決定・ロット丸め・集約スケール
  - risk_adjustment.py: セクター上限・レジーム乗数
- research/
  - factor_research.py: Momentum/Volatility/Value ファクター計算（DuckDB）
  - feature_exploration.py: 将来リターン・IC・統計サマリ等
- ai/
  - news_nlp.py: ニュースを LLM に投げて銘柄別スコアを生成・ai_scores テーブルに書込
  - regime_detector.py: ETF MA200 とマクロセンチメントを合成してレジーム判定、market_regime に書込
- tools/
  - paper_verification_report.py: Paper Trading 用の検証レポート出力ツール
- utils/
  - process_priority.py: プロセス優先度 / CPU affinity ユーティリティ

補足（よく使うパス・フラグ）
- デフォルト DB / ファイル
  - DuckDB: data/kabusys.duckdb
  - Monitoring SQLite: data/monitoring.db
  - PaperTrading SQLite: data/paper_trading.db
  - Execution PID: data/execution.pid
  - 停止要求（ランナーによる停止）: data/stop_requested.flag
  - Kill Switch: data/kill.flag
- 環境変数一例（.env に記述）
  - KABUSYS_ENV=development
  - JQUANTS_REFRESH_TOKEN=...
  - KABU_API_PASSWORD=...
  - OPENAI_API_KEY=...
  - LINE_CHANNEL_ACCESS_TOKEN=...
  - LINE_USER_ID=...
  - SQLITE_PATH=data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
  - DUCKDB_PATH=data/kabusys.duckdb
  - MONITOR_POLL_INTERVAL=60

最後に
- この README はコードベースの主要な使い方・構成をまとめたものです。実運用やデプロイ時は追加の設定（ログ回転、プロセスマネージャー systemd / supervisor、バックアップ、セキュリティ対策）や詳細なテストを実施してください。
- 何か特定のコンポーネント（例: ExecutionEngine の設定、AI モジュールのテスト方法、DB スキーマの拡張など）について詳しいドキュメントが必要であれば教えてください。必要に応じて追記します。