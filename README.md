# KabuSys — README (日本語)

バージョン: 0.1.0

概要
---
KabuSys は日本株自動売買システムのモジュール群です。本リポジトリは以下の主要機能を含みます。
- 発注/Execution エンジン（ExecutionEngine、OrderManager、Reconciler 等）
- 監視/モニタリング（SystemMonitor、TradeMonitor、RiskMonitor、MonitoringEngine）
- ポートフォリオ構築（銘柄選定・重み付け・ポジションサイズ算出）
- リサーチ用ファクター計算（Momentum / Value / Volatility 等）
- AI 支援処理（ニュースの NLP スコアリング、レジーム判定）
- 運用支援ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

主な特徴
---
- モジュール化された設計でテスト容易性と実運用の両立を目指す
- 本番/ペーパー切替（KABUSYS_ENV）で DB やブローカーを分離
- 監視ログは SQLite、時系列・集計処理は DuckDB を利用
- OpenAI を用いたニュースセンチメント / マクロセンチメント評価を実装（リトライ・バリデーション対応）
- Streamlit ダッシュボードで監視情報の可視化
- kill.flag による安全な停止シグナル、PID ファイル管理、プロセス優先度設定等の運用機能

セットアップ手順
---
1. リポジトリをクローン
   - git clone ... && cd <repo>

2. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 主要依存（最低限）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit（ダッシュボード利用時）
   - 例:
     - pip install duckdb psutil requests openai streamlit

   （プロジェクトに要求する厳密なバージョンは要件ファイルがある場合はそちらを使用してください。）

4. 環境変数 / .env
   - ルートに .env / .env.local を置くと自動で読み込まれます（OS 環境変数が優先）。
   - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 必須例:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を利用する場合:
     - OPENAI_API_KEY を設定してください。

主要な環境変数（主なもの）
---
- KABUSYS_ENV: 起動環境。development / paper_trading / live（デフォルト: development）
  - paper_trading: MockBroker を使用し data/paper_trading.db を使用（本番 DB と分離）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 外部 API 認証
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 通知用（AlertManager）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading のフィルモード（instant / partial / never / reject）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START 等

使い方（主要なスクリプト・コマンド）
---
- 監視ループ（Monitoring）
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能（秒、デフォルト 60）
    - 監視は常に settings.sqlite_path（本番 DB）を使用します
    - 停止はプロジェクトルート/data/stop_requested.flag を作成することで行えます

- Execution エンジン
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使い data/paper_trading.db に記録
    - 起動時に /data/stop_requested.flag が存在すると起動をスキップ
    - 実行中は data/execution.pid に PID を書きます。停止は stop flag により行います

- Streamlit ダッシュボード（監視可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    - 監視 DB を read-only で開きます。MonitoringEngine を先に起動してください

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
    - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）

- AI 関連（ライブラリ呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - これらは DuckDB 接続と target_date を受け取り、OpenAI API を使用して結果を DB に書き込みます

運用上のファイル・フラグ
---
- data/stop_requested.flag
  - run_monitoring / run_execution がポーリング中にこのファイルを検知すると終了します
- data/execution.pid（デフォルト）
  - ExecutionEngine が起動時に書き込む PID ファイル。SystemMonitor が存在確認を行います
- data/kill.flag（KillSwitch）
  - KillSwitch が危険事象検出時に書き込み、ExecutionEngine 側で停止シグナルとして扱います

ディレクトリ構成（主要ファイル）
---
- src/kabusys/
  - __init__.py                — パッケージ定義（バージョン等）
  - config.py                  — 環境変数・設定管理（.env 自動読み込み含む）
  - run_monitoring.py          — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
  - monitoring/
    - monitoring_db.py         — monitoring 用 SQLite 永続層（テーブル作成・CRUD ヘルパ）
    - system_monitor.py        — システム状態・データ鮮度監視
    - trade_monitor.py         — 注文滞留・約定異常監視
    - risk_monitor.py          — ドローダウン・ポジション上限監視
    - kill_switch.py           — kill.flag 書き込みロジック
    - alert_manager.py         — LINE Push 通知ラッパ
    - monitoring_engine.py     — 各 monitor を束ねたポーリングエンジン
    - streamlit_dashboard.py   — Streamlit ダッシュボード
  - execution/
    - order_manager.py         — 発注の高レベル API
    - order_repository.py      — Orders DB 操作（存在）
    - reconciler.py           — 起動時リコンシリエーション
    - ...（ブローカー関連インターフェース等）
  - portfolio/
    - portfolio_builder.py     — 候補選定・重み計算
    - position_sizing.py       — 発注株数算出（単元丸め等）
    - risk_adjustment.py       — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py      — ファクター計算（momentum/value/volatility）
    - feature_exploration.py  — 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI でセンチメント）
    - regime_detector.py      — レジーム判定（MA + マクロセンチメント合成）
  - data/                     — デフォルトの DB/フラグを置く想定ディレクトリ（自動生成される場合あり）
  - utils/
    - process_priority.py     — プロセス優先度 / CPU affinity 設定ユーティリティ

注意点 / トラブルシューティング
---
- DB 初期化:
  - run_monitoring / run_execution 内で監視 DB テーブルの初期化（冪等）を行います。初回起動で自動作成されます。
- 権限:
  - プロセス優先度設定（psutil による nice / priority）は権限不足で警告が出ることがありますが、処理自体は継続されます。
- OpenAI 呼び出し:
  - API キーが未設定だと例外になります。運用スクリプトでは例外を捕捉してフェイルセーフにする実装箇所がありますが、AI 機能を使う場合は OPENAI_API_KEY を設定してください。
- Paper Trading:
  - paper_trading 環境では本番 DB と完全分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- .env パース:
  - config._parse_env_line はシェル風の簡単なパーサを実装しています。複雑な構文は意図通りに解釈されない可能性があります。

開発・拡張のヒント
---
- 新しい監視ルールは monitoring/*.py に Monitor を追加し、MonitoringEngine に組み込む形で拡張できます。
- AI モジュールのテストは _call_openai_api を patch（モック）して行う設計です。
- DuckDB を利用したリサーチ機能は SQL ベースで実装されているため、テーブル定義に合わせてクエリを調整してください。

ライセンス・貢献
---
（本リポジトリにライセンスファイルがある場合はそちらを参照してください。貢献の流れや PR ポリシーをここに追記してください）

以上。必要であれば、README に含める実行例（env ファイルの最小例、systemd / supervisor 用のサンプル unit/サービス定義、requirements.txt の提案など）を追加で作成します。