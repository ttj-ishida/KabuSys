README
======

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした Python パッケージ群です。本リポジトリは取引実行（ExecutionEngine）、監視（MonitoringEngine）、ポートフォリオ構築、ファクター計算、AI によるニュースセンチメント評価などのコンポーネントを含みます。

主な設計方針
- DuckDB / SQLite を用いたオンプレミスデータ処理・永続化
- 本番／ペーパー（模擬）環境の明確な分離（KABUSYS_ENV）
- 外部 API（kabuステーション、J-Quants、OpenAI 等）は設定により利用（失敗時は安全にフォールバック）
- 監視は独立して本番の monitoring DB を使用（環境に依存しない運用）

主な機能一覧
- Execution
  - ExecutionEngine による注文発行・リスク管理・再突合（Reconciler）
  - ブローカー抽象化（live / paper_trading）
  - OrderManager / OrderRepository による注文状態管理
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク・プロセス監視・データ鮮度チェック
  - TradeMonitor: 滞留注文・約定価格異常の検出
  - RiskMonitor: ドローダウン・ポジション上限の検出とアラート記録
  - KillSwitch: フラグファイルにより ExecutionEngine を停止させる仕組み
  - AlertManager: LINE Push による通知（クールダウンあり）
  - streamlit ベースの監視ダッシュボード（read-only）
- Portfolio
  - 候補選定、等比重・スコア比重配分、ポジションサイズ計算、セクター制約、レジーム乗数
- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB 上で SQL による高速処理）
  - 将来リターン計算、IC（Information Coefficient）等の統計分析ユーティリティ
- AI
  - ニュース NLP（OpenAI）による銘柄別センチメントスコア化（ai_scores への書き込み）
  - 市場レジーム判定（ma200 + マクロセンチメントの融合）
- ツール
  - paper_verification_report: Paper Trading データからの検証レポート生成

セットアップ手順
----------------
※プロジェクトは src 配下にパッケージとして配置されています。開発環境では PYTHONPATH を通す、またはパッケージをインストールしてください。

1. Python 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール（代表例）
   - pip install duckdb psutil openai requests streamlit
   - ※requirements.txt がある場合は pip install -r requirements.txt を推奨

3. 環境変数 / .env の用意
   - ルートに .env（または .env.local）を作成することで自動ロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須（実行機能により変動）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - AI 系を使う場合:
     - OPENAI_API_KEY
   - その他の設定（例とデフォルト）
     - KABUSYS_ENV=development | paper_trading | live  （default: development）
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PAPER_FILL_MODE=instant|partial|never|reject  （デフォルト: instant）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（通知）
     - LOG_LEVEL=INFO
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
   - .env の書式は shell 互換（export KEY=val など）で、コメント・クォートにも対応します。

4. データディレクトリ
   - data/ 以下に DB やフラグファイルを置く運用を想定しています。必要に応じてディレクトリを作成してください。
   - 例: mkdir -p data

使い方（主要コマンド）
--------------------

開発中はソースルートを PYTHONPATH に含めて実行するのが簡単です:
例: PYTHONPATH=src python -m kabusys.run_monitoring

1. 監視ループを起動（Monitoring）
   - python -m kabusys.run_monitoring
   - 説明:
     - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で指定（デフォルト: 60）
     - 監視は KABUSYS_ENV に関わらず settings.sqlite_path（デフォルト data/monitoring.db）を使用
     - 停止方法: プロジェクトルートの data/stop_requested.flag を作成するとループが終了

2. 実行エンジンを起動（Execution）
   - python -m kabusys.run_execution
   - 説明:
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient が使用され、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ記録されます（本番 DB と分離）
     - stop フラグ: data/stop_requested.flag を作成すると停止処理が開始されます
     - 起動時に pid ファイル（data/execution.pid, デフォルト）を書きます

3. Streamlit ダッシュボード（監視）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 説明: read-only 接続で監視 DB を閲覧できます

4. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - オプション:
     - --db PATH: SQLite ファイルパス（デフォルト: data/paper_trading.db）
   - 出力: 稼働率、注文成功率、P95 レイテンシなどの判定（PASS/FAIL）

5. AI/レジーム関連
   - ニューススコア付け（コード例）
     - from kabusys.ai.news_nlp import score_news
     - score_news(conn, target_date, api_key="...")  ※OpenAI API キーが必要
   - レジーム判定
     - from kabusys.ai.regime_detector import score_regime
     - score_regime(conn, target_date, api_key="...")

停止 / フラグ類
- data/stop_requested.flag: run_monitoring / run_execution が参照する停止フラグ（存在するとループ停止）
- data/kill.flag: KillSwitch が書き込むフラグ。ExecutionEngine に停止シグナルを送る目的で作成される
- data/execution.pid: ExecutionEngine の PID 管理用ファイル

設定詳細（Settings）
- 設定ロジックは kabusys.config.Settings に集約されています。主なプロパティ:
  - env, is_live, is_paper, is_dev
  - duckdb_path, sqlite_path, paper_sqlite_path
  - paper_fill_mode (instant|partial|never|reject)
  - pid_file_path, kill_flag_path, kill_flag_clear_on_start
  - CPU/MEM/DISK 閾値（監視用）
- .env の自動ロードはプロジェクトルートの .env / .env.local を優先的に読み込みます（OS 環境変数は protected）。

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py                    — パッケージ定義
- config.py                      — 環境変数・設定管理（.env 自動ロード含む）
- run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
- run_execution.py               — ExecutionEngine 起動スクリプト
- tools/
  - __init__.py
  - paper_verification_report.py  — Paper Trading 検証レポート生成スクリプト
- ai/
  - __init__.py
  - news_nlp.py                   — ニュース NLP / OpenAI 呼び出し
  - regime_detector.py            — 市場レジーム判定（MA200 + マクロセンチメント）
- monitoring/
  - __init__.py
  - monitoring_db.py              — SQLite テーブル定義・永続化 API
  - monitoring_engine.py          — 各 Monitor の束ね（ポーリングロジック）
  - system_monitor.py             — CPU/メモリ/ディスク・プロセス・データ鮮度
  - trade_monitor.py              — 注文滞留 / 約定異常検出
  - risk_monitor.py               — ドローダウン / ポジション上限監視
  - kill_switch.py                — フラグ書き込みによる停止発動
  - alert_manager.py              — LINE push 通知
  - streamlit_dashboard.py        — streamlit ダッシュボード
- execution/
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - (その他: broker_factory, execution_engine, order_record など)
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py
- research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py
- utils/
  - process_priority.py           — プロセス優先度 / CPU affinity ユーティリティ
  - __init__.py

注意事項 / 運用メモ
- 監視ループ（run_monitoring）は MONITOR_POLL_INTERVAL（秒）で間隔を変更できます（デフォルト 60 秒）。
- Monitoring は環境に関わらず常に settings.sqlite_path を使用して監視 DB に記録します（意図的な設計）。
- paper_trading モードでは本番 DB と完全に分離された PAPER_TRADING_SQLITE_PATH に記録されます。
- OpenAI API を利用する機能は API キーの設定が必須です。API 呼び出しはリトライやフェイルセーフが組み込まれていますが、料金やレート制限に注意してください。
- streamlit ダッシュボードは monitoring DB を読み取るだけなので本番 DB を読み取り専用で開く運用が可能です（URI の ?mode=ro を内部で使用）。

トラブルシューティング
- PID ファイルが stale（プロセスが存在しない）場合、SystemMonitor が検出して削除し、risk_logs に STALE_PID を記録します。
- KillSwitch が kill.flag を書き込んだ場合は、当該ファイルを手動で削除してから再起動してください（または KillSwitch.clear() を実行するユーティリティを作成）。
- .env の自動読み込みが働かない場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されていないか、プロジェクトルートが正しく検出されているかを確認してください。

ライセンス / 貢献
- この README はリポジトリ内のコードに基づいて作成されています。変更や拡張を行う場合は各モジュールの docstring を参照してください。
- 貢献ガイドラインやライセンスファイルが別途存在する場合はそちらに従ってください。

以上。追加で README に追記したいコマンド例や環境変数のテンプレート（.env.example）などがあれば教えてください。