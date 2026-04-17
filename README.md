KabuSys — 日本株自動売買システム
================================

このリポジトリは、日本株自動売買システム「KabuSys」のコアライブラリと実行／監視用のスクリプト群を含みます。戦略のポートフォリオ構築、ポジションサイズ計算、監視エンジン、実行エンジン（ブローカー接続を抽象化）、およびニュース NLP / レジーム判定などの補助機能が実装されています。

主要ポイント
- Python パッケージとして設計（パッケージルート: src/kabusys）。
- DuckDB（履歴データ解析）と SQLite（監視ログ・注文ログ）を併用。
- 本番 / Paper Trading を環境変数 KABUSYS_ENV で切替。Paper Trading は本番 DB と分離（data/paper_trading.db）。
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価・レジーム判定機能を実装。
- 監視（MonitoringEngine）によりシステム稼働状況、滞留注文、異常約定などを検出し、LINE通知や Kill Switch によりエンジン停止が可能。

主な機能一覧
- execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - Broker クライアント抽象化（本番 / Mock）
  - OrderManager, OrderRepository, Reconciler：注文状態管理・再同期機能
- monitoring
  - SystemMonitor：CPU/メモリ/Disk/データ鮮度/PID チェック
  - TradeMonitor：滞留注文・約定価格異常検出
  - RiskMonitor：ドローダウン・ポジション上限監視
  - MonitoringEngine：ポーリングループ、KillSwitch、AlertManager（LINE）
  - streamlit_dashboard：監視ダッシュボード
- portfolio（純粋関数）
  - 銘柄選定、重み計算、セクター制限、ポジションサイズ計算
- research
  - factor_research, feature_exploration：ファクター計算、将来リターン、IC、統計サマリー
- ai
  - news_nlp：ニュースの LLM によるセンチメントスコア生成
  - regime_detector：市場レジーム判定（ma200 + マクロセンチメント合成）
- tools
  - paper_verification_report：Paper Trading 検証レポート生成スクリプト
- utils
  - process_priority：プロセス優先度 / CPU affinity 設定

セットアップ手順
- 前提
  - Python 3.10 以上（| 型ヒントなどを使用）
  - システムに duckdb, psutil, requests, openai, streamlit 等がインストールされていること

- 仮想環境作成（推奨）
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

- 必要パッケージのインストール（例）
  - pip install duckdb psutil requests openai streamlit

- ディレクトリの準備
  - data ディレクトリを作成（DB・PID・フラグファイル等）
    - mkdir -p data

- 環境変数
  - .env / .env.local をプロジェクトルートに置くことで自動読み込みされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - 主な環境変数（Settings 参照）：
    - JQUANTS_REFRESH_TOKEN (必須)
    - KABU_API_PASSWORD (必須)
    - OPENAI_API_KEY (AI 機能を使う場合必須)
    - KABU_API_BASE_URL (既定: http://localhost:18080/kabusapi)
    - LINE_CHANNEL_ACCESS_TOKEN (任意: LINE 通知)
    - LINE_USER_ID (任意: LINE 通知先)
    - DUCKDB_PATH (既定: data/kabusys.duckdb)
    - SQLITE_PATH (既定: data/monitoring.db)
    - PAPER_TRADING_SQLITE_PATH (既定: data/paper_trading.db)
    - PAPER_FILL_MODE (instant / partial / never / reject; 既定: instant)
    - KABUSYS_ENV (development / paper_trading / live; 既定: development)
    - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
    - MONITOR_POLL_INTERVAL (run_monitoring スクリプトのポーリング間隔秒、既定 60)
    - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等

- DB 初期化
  - 監視用テーブルは run_monitoring/run_execution 実行時に init_monitoring_db() によって自動作成されます。手動で初期化したい場合は sqlite3 で接続して init_monitoring_db() を呼ぶか、スクリプトを起動してください。

使い方（主要スクリプト）
- 監視ループ起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は常に本番の sqlite_path を使用（環境に依らず monitoring DB は本番パスが想定されます）
  - 停止: data/stop_requested.flag を作成するとループは終了します

- 実行エンジン起動
  - python -m kabusys.run_execution
  - Paper Trading モード:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - この場合は MockBrokerClient が使用され、DB は PAPER_TRADING_SQLITE_PATH（既定 data/paper_trading.db）に記録されます
  - 実行中停止:
    - data/stop_requested.flag を作成すると Engine 停止を試行します
  - 実行時に data/execution.pid に PID を書きます（PID ファイルにより stale PID 検出を行います）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 出力: 稼働率、注文成功率、送信率、レイテンシ（P95）等を集計して PASS / FAIL 判定

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用で DB を開き、Overview / Positions / Orders / System を表示

- AI（ニューススコア・レジーム判定）
  - news_nlp.score_news(conn, target_date, api_key=...)
    - DuckDB 接続を渡してニュースを集計し OpenAI でスコアを取得、ai_scores テーブルに書き込みます
  - regime_detector.score_regime(conn, target_date, api_key=...)
    - ma200 とマクロセンチメントを合成して market_regime テーブルに書き込みます
  - 実行には OPENAI_API_KEY の設定が必要

注意点 / 運用上のポイント
- Paper Trading は本番 DB と完全分離するため、KABUSYS_ENV=paper_trading を使ってください。
- run_monitoring は Monitoring DB（SQLITE_PATH）を使います。監視は環境に依らず本番監視 DB を使う設計になっています（重要）。
- Kill Switch（data/kill.flag）: KillSwitch により条件を満たすと data/kill.flag が書き込まれ、ExecutionEngine に停止シグナルを送ることができます。flag のクリアは KillSwitch.clear() または手動削除で行ってください。
- プロセス優先度: 起動スクリプトは set_process_priority("high") を呼び、可能なら優先度を上げます。権限が足りない場合は警告を出してスキップします。
- .env の読み込み: プロジェクトルート（.git または pyproject.toml がある場所）を自動検出して .env / .env.local を読み込む。OS 環境変数は保護されます。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定管理
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper トレード検証レポート
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
    - streamlit_dashboard.py
    - __init__.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他ブローカー関連・order_repository 等 ※一部省略)
  - utils/
    - process_priority.py
    - __init__.py
  - data/ (運用ディレクトリ、実行時に使用)
    - monitoring.db (既定 SQLITE_PATH)
    - paper_trading.db (既定 PAPER_TRADING_SQLITE_PATH)
    - kabusys.duckdb (既定 DUCKDB_PATH)
    - execution.pid / stop_requested.flag / kill.flag

ハンズオン例（よく使うコマンド）
- 開発環境で監視を動かす（短い間隔で動作確認）
  - MONITOR_POLL_INTERVAL=10 python -m kabusys.run_monitoring
- Paper Trading で実行エンジン起動（Mock Broker）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Paper Trading レポート（過去期間）
  - python -m kabusys.tools.paper_verification_report --from 2026-03-01 --to 2026-03-31
- Streamlit ダッシュボード起動
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

FAQ / トラブルシューティング（簡易）
- DB が見つからない / 読み取り不可
  - monitoring スクリプト実行前に data ディレクトリと DB ファイルの存在/パーミッションを確認してください。
- OpenAI API 呼び出し失敗
  - OPENAI_API_KEY を正しく設定し、ネットワーク接続を確認してください。429 / 5xx は自動リトライがありますが、上限があります。
- PID ファイルが無効 / 古い PID 検出
  - PID ファイルを手動で削除してください（data/execution.pid）。SystemMonitor は stale PID を検出して削除し、リスクログに記録します。

ライセンス / 貢献
- 本リポジトリのライセンス／貢献ルールはリポジトリルートの LICENSE / CONTRIBUTING を参照してください（存在しない場合は管理者に確認してください）。

最後に
- この README はコードベースの主要機能と運用上の注意点をまとめたものです。実運用前には必ずローカルでのエンドツーエンド検証（Paper Trading）とバックアップ運用フローの確認を行ってください。質問や改善提案があれば ISSUE を立ててください。