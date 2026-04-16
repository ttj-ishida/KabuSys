# KabuSys

日本株自動売買システムのコアライブラリ群と運用用ユーティリティ群です。本リポジトリには実運用向けのモジュール（ExecutionEngine、Monitoring、AI 補助モジュール、ポートフォリオ構築・ポジション算出ロジック、研究用ファクター計算など）が含まれます。

この README ではプロジェクト概要、主要機能、セットアップ手順、使い方（起動方法・運用ワークフロー）、およびディレクトリ構成を日本語でまとめます。

注意: 実際にブローカーや API キーを接続する箇所は本コードでも抽象化されています。実稼働環境での使用前に十分な検証を行ってください。

## プロジェクト概要
- 目的：日本株自動売買のエンジンと運用支援ツール群を提供する。
- 構成要素（主なモジュール）：
  - execution: 発注エンジン、OrderManager、Reconciler（再同期）等
  - monitoring: システム稼働監視、注文監視、リスク監視、アラート（LINE）等
  - ai: ニュース NLP（OpenAI）によるセンチメント評価、レジーム検出
  - portfolio: 候補選定・ウェイト計算・ポジションサイズ計算・セクター上限・レジーム乗数
  - research: ファクター計算・特徴量探索・IC 計算等（DuckDB ベース）
  - tools: Paper Trading 検証レポート生成スクリプト、監視ダッシュボード（Streamlit）等
  - utils: プロセス優先度・CPU affinity 設定などのユーティリティ
  - config: 環境変数読み込み / 設定ラッパー（Settings）

## 主な機能一覧
- Execution
  - 実注文発行 / 注文状態管理（OrderManager, OrderRepository）
  - 起動時の自動リコンシリエーション（Reconciler）
  - リスク管理（RiskManager）や注文再送等の仕組みを統合可能
  - Paper trading モード（MockBroker）をサポートし、本番 DB と分離した専用 SQLite を使用
- Monitoring
  - SystemMonitor：CPU / メモリ / ディスク / プロセス状態 / データ鮮度監視
  - TradeMonitor：滞留注文・約定異常価格検出
  - RiskMonitor：ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch：条件に応じて data/kill.flag を作成し ExecutionEngine に停止シグナルを送出
  - AlertManager：LINE Messaging API による通知（クールダウン管理）
  - Streamlit ダッシュボード（read-only）で監視状況の可視化
- AI / データ処理
  - ニュースを OpenAI API（gpt-4o-mini 想定）で評価し ai_scores テーブルに保存
  - マクロニュース + ETF ma200 による市場レジーム判定と保存
  - DuckDB を用いたファクター計算（Momentum / Volatility / Value）
- Portfolio construction（純粋関数）
  - 候補選定、等重・スコア重み付け
  - セクター制限適用、レジームに応じた資金乗数
  - ポジションサイズ計算（lot 単位丸め、aggregate cap、リスクベース等）
- Tools
  - paper_verification_report: Paper Trading DB を解析して稼働率・注文成功率・レイテンシなどの検証レポートを出力

## セットアップ手順（開発 / 実行環境）
前提：Python 3.10+（型ヒントで | を使用しているため）を推奨します。

1. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 代表的な依存パッケージ（プロジェクトに requirements.txt は含まれていない想定）:
     - duckdb
     - psutil
     - openai
     - requests
     - streamlit
   - 例:
     - pip install duckdb psutil openai requests streamlit

3. 環境変数 / .env
   - プロジェクトルートに .env/.env.local を置くと自動で読み込まれます（既存 OS 環境変数は上書きされません。`.env.local` は上書き可）。
   - 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 必須環境変数（運用する機能に応じて）：
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - OPENAI_API_KEY (AI 機能を使う場合)
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (LINE 通知を使う場合)
   - 監視・DB 関連のデフォルトは下記：
     - SQLITE_PATH (default: data/monitoring.db)
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
     - KABUSYS_ENV: development | paper_trading | live  (default: development)
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) (default: INFO)
     - MONITOR_POLL_INTERVAL (監視ループの間隔、秒。default: 60)

4. データディレクトリ
   - デフォルトで data/ 以下に DB・旗ファイル・pid ファイルなどを作成します。
   - 必要に応じて事前にディレクトリを作成してください。

## 使い方（実行方法）
以下は典型的な運用時コマンド例です。src 配下のスクリプトはパッケージとして実行できます（プロジェクトルートで実行想定）。

1. 監視ループの起動（Monitoring）
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（秒。1 未満は無効扱いでデフォルトにフォールバック）。
   - 実行:
     - python -m kabusys.run_monitoring
   - 動作:
     - Settings から sqlite_path（monitoring DB）を読み込み、init_monitoring_db でテーブルを作成
     - SystemMonitor.check_once() をループで呼ぶ（MONITOR_POLL_INTERVAL 秒ごと）
     - 停止手段: プログラム中断（Ctrl+C）またはプロジェクトルート/data/stop_requested.flag を作成して検知させる

2. Execution エンジン起動
   - 実行:
     - python -m kabusys.run_execution
   - 動作:
     - KABUSYS_ENV により paper_trading の場合は MockBrokerClient を使用（paper_trading 専用 DB を使用して本番 DB と分離）
     - ExecutionEngine を別スレッドで run_session 実行し、stop flag を監視して安全に停止
   - 重要:
     - Execution は paper_trading モード時に PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を用いるため、本番データと完全に分離されます。

3. Paper Trading 検証レポート
   - 実行:
     - python -m kabusys.tools.paper_verification_report
     - 期間を指定する場合:
       - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - DB 指定:
       - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
   - 出力: 稼働率・注文成功率・送信率・レイテンシ（P95 など）の検証レポートを標準出力へ表示

4. Streamlit 監視ダッシュボード（ローカル / read-only）
   - 実行:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 説明:
     - monitoring.db を read-only モードで開いてダッシュボードを表示します（MonitoringEngine が DB にデータを書き込んでいる前提）

5. AI 関連
   - ニュースセンチメントスコア生成:
     - モジュール関数: kabusys.ai.score_news(conn, target_date, api_key=None)
     - OPENAI_API_KEY が必要（引数でも指定可能）
     - raw_news / news_symbols テーブルを用いて ai_scores にスコアを書き込みます
   - レジーム判定:
     - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
     - prices_daily と raw_news を参照。OpenAI 呼び出しに失敗した場合はフォールバック挙動あり（安全重視）

## 重要な環境設定とファイル
- KABUSYS_ENV: development | paper_trading | live
  - paper_trading の場合は Execution が MockBroker を使用し、paper_trading 用 SQLite に記録
  - monitoring は環境に関係なく Settings.sqlite_path（本番 monitoring DB）を使用する設計になっている箇所があるため注意
- MONITOR_POLL_INTERVAL: 監視ループ間隔（秒）
- PAPER_FILL_MODE: Paper Trading の約定モード（instant | partial | never | reject）
- PID / flag ファイル:
  - data/execution.pid（ExecutionEngine の PID ファイル）
  - data/kill.flag（KillSwitch による Execution 停止トリガ）
  - data/stop_requested.flag（run_monitoring/run_execution が監視する停止フラグ）
- DB ファイル（デフォルト）
  - data/monitoring.db (SQLite)
  - data/paper_trading.db (Paper Trading 用 SQLite)
  - data/kabusys.duckdb (DuckDB)

## ロギング / レベル
- Settings.log_level で LOG_LEVEL を指定可能（環境変数 LOG_LEVEL）。
- 多くのスクリプトは logging.basicConfig(level=logging.INFO) を使うため、環境変数 LOG_LEVEL を設定するとより詳細にできます。

## ディレクトリ構成
（src/kabusys 配下の主要ファイルを抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数読み込み / Settings
    - run_monitoring.py        — SystemMonitor のポーリングループ起動スクリプト
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py  — Paper Trading 検証レポート生成
    - monitoring/
      - __init__.py
      - monitoring_db.py       — SQLite 永続層（テーブル作成含む）
      - system_monitor.py      — システム / データ鮮度監視
      - trade_monitor.py       — 注文滞留 / 約定異常監視
      - risk_monitor.py        — ドローダウン / ポジション上限監視
      - kill_switch.py         — kill.flag 書き込みユーティリティ
      - alert_manager.py       — LINE 通知（push）
      - monitoring_engine.py   — 各 Monitor を束ねるループ
      - streamlit_dashboard.py — Streamlit ダッシュボード
    - execution/
      - order_manager.py
      - reconciler.py
      - ...（broker_factory, execution_engine, order_repository 等）
    - portfolio/
      - portfolio_builder.py
      - risk_adjustment.py
      - position_sizing.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - ai/
      - news_nlp.py
      - regime_detector.py
    - utils/
      - process_priority.py
    - data/ (運用で作成されるファイル置き場。例: monitoring.db, paper_trading.db, stop_requested.flag, kill.flag, execution.pid）
- pyproject.toml / .git / 等（プロジェクトルート判定に使用）

## 運用上の注意 / ベストプラクティス
- Paper trading と実運用 DB は分離して運用してください（KABUSYS_ENV=paper_trading）。
- OpenAI API を利用する機能は API キー管理とコスト管理に注意してください。API 呼び出しに対してはリトライやフェイルセーフ（失敗時に 0 とみなす等）が実装されていますが、運用ルールを設けてください。
- kill.flag や stop_requested.flag を用いた外部停止機構があります。これらはフラグファイルの存在を確認してプロセスを停止・終了します。
- Monitoring は稼働性の主要指標を記録します。run_monitoring を長時間動かして dashboard や監視ログを参照してください。
- データ鮮度チェックは DuckDB 上の prices_daily を参照します。データ取り込みパイプライン（kabusys.data.pipeline など）を別途用意しておく必要があります。

## よく使うコマンドまとめ
- 監視を起動:
  - python -m kabusys.run_monitoring
- Execution を起動:
  - python -m kabusys.run_execution
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

この README はコードベース内のドキュメント文字列・設計コメントを要約して作成しています。実環境へデプロイする前に各設定（APIキー、DBパス、KABUSYS_ENV など）を確認し、テスト環境での十分な検証を実行してください。必要であれば .env.example を作成して運用者向けに必須変数を明示することを推奨します。