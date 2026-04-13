プロジェクト: KabuSys
===============

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした Python パッケージ群です。
主な目的は以下です。

- 取引実行エンジン（ExecutionEngine）による発注・リスク管理
- モニタリング（System / Trade / Risk）とアラート（LINE）機能
- ポートフォリオ構築（候補選定・重み付け・株数算出）
- リサーチ用ファクター計算（momentum / volatility / value など）
- AI 補助機能（ニュースセンチメント、レジーム判定）
- 開発・検証向けツール（Paper Trading 用 DB、検証レポート、Streamlit ダッシュボード）

主な特徴
--------
- 環境ごとに挙動を切り替え（KABUSYS_ENV=development|paper_trading|live）
  - paper_trading モードでは Mock ブローカーと独立した SQLite（data/paper_trading.db）を使用
- 監視（Monitoring）コンポーネントは常に本番用 sqlite_path を使用して稼働ログを残す
- OpenAI を用いたニュースセンチメントとレジーム判定（API キー必須）
- DuckDB を用いた価格・財務データの高速集計（research / ai モジュールで使用）
- Streamlit による監視ダッシュボード表示機能
- フェイルセーフ設計（DB マイグレーション、API リトライ、部分失敗の保護）

セットアップ手順
----------------
1. Python 環境を作成（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 代表的な依存（requirements.txt がない場合の参考）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - 例:
     - pip install duckdb psutil requests openai streamlit

3. プロジェクトルートに .env を配置（任意）
   - config モジュールはプロジェクトルート（.git または pyproject.toml を基準）から .env/.env.local を自動ロードします。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 必須環境変数の設定（.env または OS 環境変数）
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - OPENAI_API_KEY (AI 機能を使う場合必須)
   - 任意:
     - KABUSYS_ENV (development|paper_trading|live, デフォルト: development)
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - SQLITE_PATH（monitoring DB、デフォルト: data/monitoring.db）
     - DUCKDB_PATH（DuckDB ファイル、デフォルト: data/kabusys.duckdb）
     - PAPER_FILL_MODE（paper_trading の約定挙動: instant|partial|never|reject、デフォルト: instant）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート通知用）
     - PID_FILE_PATH / KILL_FLAG_PATH（プロセス管理用）
     - MONITOR_POLL_INTERVAL（監視ポーリング間隔 秒、デフォルト 60）

   - 参考の .env 項目（例）
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - KABUSYS_ENV=paper_trading
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...

使い方（主要スクリプト／モジュール）
-------------------------------

- 監視ループを起動（SystemMonitor ポーリング）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、1以上。デフォルト 60）
  - 監視は Settings.sqlite_path を常に使用（環境にかかわらず本番 DB を見る設計）

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 DB に書き込みを行います（本番 DB と完全分離）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH より優先）
  - 出力: 稼働率・注文成功率・送信率・レイテンシ等の指標と PASS/FAIL 判定

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ローカルの monitoring SQLite を read-only で参照して UI を表示

- AI 機能（プログラム的利用）
  - ニュースのスコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key=None)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=None)
  - いずれも OpenAI API キーが必要（引数または OPENAI_API_KEY 環境変数）

動作上の注意点・設計方針（抜粋）
--------------------------------
- Settings:
  - 自動的にプロジェクトルートの .env/.env.local を読み込みます（OS 環境変数が優先）。詳細は src/kabusys/config.py を参照。
- モニタリング:
  - monitoring_db.init_monitoring_db() が DB スキーマを作成・マイグレーション（冪等）します。
  - KillSwitch は data/kill.flag を書き込むことで ExecutionEngine 停止を指示できます（RiskMonitor の判定に基づく）。
- Execution:
  - paper_trading モードは本番 DB と分離されるため検証に安全です。
  - 起動時にプロセス優先度を set_process_priority("high") で設定しようとします（psutil を使用、権限不足等で失敗してもフェイルオーバー）。
- AI モジュール:
  - OpenAI への呼び出しはリトライ（指数バックオフ）を行い、失敗時はフェイルセーフ（ゼロフォールバックまたはスキップ）で続行します。
  - 出力は厳密な JSON を期待しますが、パース失敗時のリカバリ処理も実装されています。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
  - パッケージ初期化（バージョン等）
- config.py
  - 環境変数・設定読み込みロジック（.env 自動ロード、Settings クラス）
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading 時は MockBroker を使用）

サブパッケージ（主なもの）
- kabusys/monitoring/
  - monitoring_db.py — SQLite スキーマ定義・永続化ラッパー (MonitoringDB)
  - system_monitor.py — CPU/メモリ/ディスク／データ鮮度／PID チェック
  - trade_monitor.py — 注文滞留・約定価格異常監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — フラグファイルによる停止シグナル
  - alert_manager.py — LINE Push 通知（クールダウン付き）
  - monitoring_engine.py — 複数 Monitor を束ねるポーリングエンジン
  - streamlit_dashboard.py — Streamlit ダッシュボード

- kabusys/execution/
  - order_manager.py, order_repository.py, reconciler.py, execution_engine.py, broker_factory など
  - 発注ロジック、ブローカーインターフェース、再同期（reconciliation）機能を含む

- kabusys/portfolio/
  - portfolio_builder.py — 候補選定・重み付け
  - position_sizing.py — 株数算出・丸め・集計キャップ処理
  - risk_adjustment.py — セクター制限・レジーム乗数

- kabusys/research/
  - factor_research.py — momentum / volatility / value 等のファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン計算、IC 等の統計解析

- kabusys/ai/
  - news_nlp.py — ニュースを OpenAI でスコアリングして ai_scores に書き込む
  - regime_detector.py — ETF MA200 とマクロニュースを合成してレジーム判定

- kabusys/utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

- kabusys/tools/
  - paper_verification_report.py — Paper Trading DB から検証レポートを生成

運用上のヒント
--------------
- 開発環境では KABUSYS_ENV=development を使い、paper_trading で検証したい場合は KABUSYS_ENV=paper_trading に切り替えます。
- monitoring は常に本番用 sqlite_path を参照する設計のため、監視ログの分離が必要な場合は sqlite_path を適切に設定してください。
- 実行中は data/execution.pid に PID が書かれ、stale PID の検出や kill.flag による停止要求処理が行われます。
- Streamlit ダッシュボードは監視 DB を read-only で開いて表示します。監視が起動していない場合はエラーが出ます。

補足・参照
-----------
- 詳細な実装やアルゴリズムの設計注記は各モジュールの docstring 内に記載しています（src 以下の .py ファイルを参照してください）。
- 環境変数の自動ロード挙動・パース仕様は src/kabusys/config.py のコメントを参照してください。
- OpenAI 呼び出しはレスポンス検証・リトライロジックを実装していますが、API キーの管理・レート制御には注意してください。

問題・質問
-----------
この README に抜けや誤りがあれば、どの部分かを教えてください。README の補足・翻訳・例の追加などは対応します。