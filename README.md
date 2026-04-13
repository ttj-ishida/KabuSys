KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤の一部として実装された Python パッケージ群です。  
主な目的は以下の通りです。

- 注文発行・状態管理（ExecutionEngine / OrderManager / Reconciler）
- 監視・アラート（MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ算出）
- リサーチ（ファクター計算・特徴量解析）
- AI を使ったニュースセンチメント（OpenAI を利用した news_nlp / regime_detector）
- Paper Trading 用の検証レポート生成ツール

特徴
----
- 設定は環境変数または .env/.env.local で管理（kabusys.config.Settings）
- 本番と Paper Trading を環境変数 KABUSYS_ENV で切り替え可能（development / paper_trading / live）
- 監視データは SQLite（monitoring.db）に永続化。DuckDB を分析用データ格納に利用
- OpenAI（gpt-4o-mini 等）を用いたニューススコアリングとレジーム判定を実装
- Streamlit を使った簡易ダッシュボードを同梱
- フェイルセーフ設計（リトライ、部分失敗時の安全な DB 操作、kill flag など）

セットアップ手順
----------------

1. Python 環境
   - Python 3.9+ を推奨（コードは typing の新構文を利用）
   - 仮想環境を作成して有効化してください。

2. 依存パッケージのインストール（代表的なパッケージ）
   - duckdb, psutil, openai, requests, streamlit
   - 例:
     pip install duckdb psutil openai requests streamlit

   （プロジェクトに requirements.txt がある場合はそちらを使ってください）

3. 環境変数 / .env の準備
   - プロジェクトルートに .env（または .env.local）を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須（用途により異なるが最低限）:
     - JQUANTS_REFRESH_TOKEN — J-Quants API（必要なら）
     - KABU_API_PASSWORD — kabuステーション API 用パスワード（発注に必須）
   - OpenAI 機能を使う場合:
     - OPENAI_API_KEY — OpenAI API キー
   - 主なオプション（既定値を含む）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
     - SQLITE_PATH — 監視 DB（data/monitoring.db）
     - DUCKDB_PATH — DuckDB path（data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（data/paper_trading.db）
     - PAPER_FILL_MODE — paper_trading の約定モード ("instant"|"partial"|"never"|"reject")、デフォルト "instant"
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用
     - PID_FILE_PATH / KILL_FLAG_PATH 他の監視関連設定
     - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒。デフォルト 60）

   - 例 (.env):
     KABUSYS_ENV=paper_trading
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=your_password
     PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

4. データディレクトリ
   - data/ 配下に SQLite / DuckDB ファイルを置きます。必要なテーブルは実行時に初期化されるものがあります（例: init_monitoring_db）。

使い方
------

- 実行エンジン（ExecutionEngine）
  - 本番または paper_trading の ExecutionEngine を起動します。
  - コマンド例:
    - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH に記録して本番 DB と分離します。
    - 実行開始時にプロセス優先度を "high" に設定します（set_process_priority）。

- 監視ポーリング（SystemMonitor 単独起動スクリプト）
  - コマンド例:
    - python -m kabusys.run_monitoring
  - オプション:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 挙動:
    - system_status / trade_logs / risk_logs / positions / dashboard を用いて監視ログを永続化・アラートや kill.flag 書き込みの判断を行います。
    - 監視では常に production の sqlite_path を使用します（設定で本番 DB を参照している点に注意）。

- Paper Trading 検証レポート
  - コマンド例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - --db オプションで SQLite パスを指定できます（PAPER_TRADING_SQLITE_PATH 環境変数と併用可能）。
  - 出力:
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の集計と PASS/FAIL 判定を標準出力に表示します。

- Streamlit ダッシュボード（監視用）
  - 起動例:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 機能:
    - ダッシュボード（Overview）、Positions、Orders、System の表示。監視 DB を read-only モードで開きます。

- AI 機能（ニュース NLP / レジーム判定）
  - OpenAI API キー（OPENAI_API_KEY）が必要です。無い場合は例外になります。
  - news_nlp.score_news(conn, target_date, api_key=None) や regime_detector.score_regime(conn, target_date, api_key=None) を呼べます。
  - 実行時は DuckDB 接続を渡し、ai_scores / market_regime 等のテーブルへ冪等的に書き込みます。

注意点 / 運用メモ
-----------------
- monitoring は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path（Settings.sqlite_path）を参照する設計になっています。Paper Trading と監視 DB を完全に分離したい場合は設定を調整してください。
- run_execution は KABUSYS_ENV=paper_trading のとき PAPER_TRADING_SQLITE_PATH を使い、本番 DB と分離します。
- kill.flag により ExecutionEngine に停止シグナルを送ります。kill.flag は Settings.kill_flag_path（デフォルト data/kill.flag）に書き込まれます。
- OpenAI 呼び出しはレート制限や 5xx を考慮してリトライロジックを実装していますが、API 使用は有料かつレート制限が存在するため運用時に注意してください。
- DB 初期化（監視テーブル等）は init_monitoring_db() が呼ばれるため手動で作成する必要はありませんが、DuckDB の prices_daily / raw_financials 等のリサーチ用テーブルは外部データ投入が必要です。

ディレクトリ構成（抜粋）
----------------------
src/kabusys/
- __init__.py
  - パッケージ定義（バージョン等）
- config.py
  - 環境変数・設定読み込みロジック（.env 自動ロード、Settings クラス）
- run_execution.py
  - ExecutionEngine 起動スクリプト（本番 / paper_trading 切替対応）
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト

サブパッケージ:
- execution/
  - order_manager.py, reconciler.py, order_repository.py など
  - 注文管理・ブローカ連携・再同期ロジック
- monitoring/
  - monitoring_db.py — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py — CPU/メモリ/ディスク/プロセス/データ鮮度監視
  - trade_monitor.py — 注文滞留・約定価格異常検出
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag 管理
  - alert_manager.py — LINE 通知（push）
  - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
  - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
- portfolio/
  - portfolio_builder.py — 候補選定・重み付け
  - position_sizing.py — 発注株数計算（リスクベース / 等分配 等）
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — Momentum / Volatility / Value 等の計算（DuckDB ベース）
  - feature_exploration.py — 将来リターン・IC 計算等
- ai/
  - news_nlp.py — ニュースセンチメントを OpenAI に送って ai_scores に書き込む
  - regime_detector.py — ETF MA とマクロセンチメントを合成して市場レジーム判定
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成スクリプト
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

その他
-----
- DB スキーマやマイグレーションは monitoring/monitoring_db.py に実装されています（init_monitoring_db）。
- ロギングは各モジュールで logging を使用しています。LOG_LEVEL 環境変数で制御できます。
- テスト・CI、詳細なデプロイ手順や BrokerClient 実装（kabu ステーション連携）はプロジェクト外の実装に依存します。

貢献 / 連絡
----------
- この README はコードベースの抜粋に基づいて作成しています。実際の運用、依存関係、追加設定（Broker クライアントの設定等）はリポジトリ内の他ファイル / ドキュメントを参照してください。必要であれば README を拡張して具体的な .env.example や systemd サービス定義、docker-compose 例なども追加できます。