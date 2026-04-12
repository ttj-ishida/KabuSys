KabuSys — 日本株自動売買システム
================================

このドキュメントはリポジトリ内のコードベース (src/kabusys/...) を基にした README です。
実行/開発のための概要、機能、セットアップ、使い方、ディレクトリ構成を日本語でまとめています。

プロジェクト概要
----------------
KabuSys は日本株の自動売買に関するモジュール群（アルファ生成・ポートフォリオ構築・発注実行・監視・リサーチ・AI 補助）を提供する Python パッケージです。  
設計方針として以下を重視します：

- DuckDB / SQLite を使ったローカルデータ処理（外部 API に依存しない解析機能）
- 発注ロジックとブローカークライアントを分離（paper_trading 環境では Mock を使用）
- 監視（MonitoringEngine）による稼働監視とアラート発信（LINE）
- LLM（OpenAI）を使ったニュース NLP / マクロ判定（フェイルセーフ設計）
- テスト容易性とクラッシュ耐性（リコンシリエーション、冪等 DB 初期化）

主な機能一覧
-------------
- 研究・ファクター計算（kabusys.research）
  - Momentum / Volatility / Value ファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定、等重・スコア重み、リスク調整（セクターキャップ・レジーム乗数）
  - 銘柄ごとの発注株数算出（単元丸め・aggregate cap）
- 発注実行（kabusys.execution）
  - OrderManager / ExecutionEngine / Reconciler — 注文状態管理・再同期・リスク管理
  - BrokerClientFactory により実運用ブローカー or Paper Trading 用 Mock を選択
- 監視（kabusys.monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine
  - 監視ログ永続化（SQLite, init_monitoring_db）
  - KillSwitch（データ駆動で ExecutionEngine を停止するフラグファイル）
  - LINE 通知を行う AlertManager
  - Streamlit ダッシュボード（簡易 GUI）
- AI 補助（kabusys.ai）
  - news_nlp: OpenAI を用いたニュースセンチメント（ai_scores への書込）
  - regime_detector: マクロ + ETF MA200 を組み合わせた日次レジーム判定（market_regime へ書込）
- ツール
  - paper_verification_report: paper_trading の検証レポート生成（注文成功率・稼働率・レイテンシ等）

セットアップ手順
----------------
1. Python 環境（推奨: 3.9+）を用意
   - 仮想環境を作成して有効化する例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - requirements.txt がない場合は主要依存を手動インストール:
     pip install duckdb psutil requests streamlit openai
   - プロジェクトに requirements.txt がある場合:
     pip install -r requirements.txt

3. 環境変数 / .env ファイル
   - ルートに .env / .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 最低限設定が必要な環境変数:
     - JQUANTS_REFRESH_TOKEN（J-Quants API 用）
     - KABU_API_PASSWORD（kabuステーション API 用パスワード）
     - OPENAI_API_KEY（AI 機能を使う場合）
   - そのほかは下記「重要な環境変数」を参照。

4. データディレクトリ準備
   - デフォルトの DB パス:
     - SQLite (monitoring): data/monitoring.db
     - DuckDB: data/kabusys.duckdb
     - Paper trading SQLite: data/paper_trading.db
   - 必要に応じて data ディレクトリを作成:
     mkdir -p data

使い方（主要コマンド / 実行例）
-------------------------------

- 監視ループを起動（SystemMonitor を単独でポーリング）
  - python -m kabusys.run_monitoring
  - 補足:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き（デフォルト: 60）
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（監視ログは production DB に保存）

- ExecutionEngine（売買実行）を起動
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper DB（data/paper_trading.db）へ記録して本番 DB と分離
    - 起動時に PID ファイルを書き、KillSwitch 用フラグファイルのクリア設定等を Settings で行えます

- Streamlit ダッシュボード起動
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - read-only で接続するため監視データを参照しやすいです

- Paper Trading 検証レポート生成（CLI）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション: --db PATH で SQLite パスを指定可能（デフォルトは環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）

- AI スコアリング / レジーム判定（プログラム呼び出し）
  - news scoring:
    from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date, api_key="...")
  - regime scoring:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key="...")
  - ※ OpenAI API キーが必要。詳細は該当モジュールの docstring を参照してください。

重要な環境変数
----------------
- KABUSYS_ENV: 起動環境 (development | paper_trading | live). デフォルト: development。
  - paper_trading: run_execution が paper DB / MockBroker を使用
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）。デフォルト 60。1 未満の値は無効扱いでデフォルトにフォールバック。
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須: 使用箇所がある場合）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う際に必要）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager の LINE 通知設定
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PID_FILE_PATH: ExecutionEngine 用 PID ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH: KillSwitch フラグファイル（デフォルト data/kill.flag）
- PAPER_FILL_MODE: paper_trading 用 MockBroker の約定モード（instant|partial|never|reject）

設定自動読み込み
----------------
- ルートの .env / .env.local をプロジェクト起点で自動ロードします（OS 環境変数は保護されます）。  
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py — パッケージ定義・バージョン
- config.py — 環境変数 / Settings 管理（.env 自動読み込みロジック含む）
- run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト

kabusys/monitoring/
- monitoring_db.py — monitoring 用 SQLite スキーマ初期化 / DB ラッパー
- system_monitor.py — CPU/MEM/DISK/データ鮮度監視
- trade_monitor.py — 注文滞留 / 約定異常検出
- risk_monitor.py — ドローダウン / 保有数監視
- kill_switch.py — フラグファイルによる停止トリガ
- alert_manager.py — LINE 通知
- monitoring_engine.py — 各モニタの統合ループ
- streamlit_dashboard.py — 監視ダッシュボード（Streamlit）

kabusys/execution/
- order_manager.py, reconciler.py, ... — 注文管理・リコンシリエーション・ExecutionEngine 関連（発注ロジック）

kabusys/portfolio/
- portfolio_builder.py — 候補選定・重み算出
- position_sizing.py — 株数算出ロジック
- risk_adjustment.py — セクターキャップ・レジーム乗数

kabusys/research/
- factor_research.py — Momentum/Volatility/Value の計算（DuckDB を利用）
- feature_exploration.py — 将来リターン / IC / 統計ユーティリティ

kabusys/ai/
- news_nlp.py — ニュースセンチメント（OpenAI 呼び出し、バッチ・リトライ・検証ロジック）
- regime_detector.py — マクロ + ETF MA200 のレジーム判定（OpenAI 使用）

kabusys/tools/
- paper_verification_report.py — Paper Trading の検証レポート生成 CLI

kabusys/utils/
- process_priority.py — プラットフォーム差分を吸収したプロセス優先度 / CPU affinity 設定ユーティリティ

注意事項 / 運用上のポイント
----------------------------
- 監視（run_monitoring）は常時稼働させることを想定しており、MONITOR_POLL_INTERVAL に従って定期的にチェックします。プロセス優先度を高めに設定します（set_process_priority）。
- ExecutionEngine の起動時に PID ファイルを作成します。SystemMonitor は PID ファイルを見てプロセスが生存しているかを確認します（stale PID 検出と削除）。
- Paper Trading 環境は本番 DB と完全分離されるよう設計されています（settings.is_paper により paper_sqlite_path を使用）。
- AI 機能は OpenAI を呼び出します。API 呼び出しはリトライや失敗時フォールバックを備えていますが、API キーの管理・料金に注意してください。
- DB マイグレーション: init_monitoring_db は冪等的にテーブル作成および簡易マイグレーション（カラム追加）を行います。
- CLI ツールやモジュールの docstring に使い方の詳細が書かれています。必要に応じて各モジュールの docstring を参照してください。

開発 / テストに関するヒント
--------------------------
- unit tests（存在する場合）やモジュール単体での動作確認は、環境変数を隔離して行ってください（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 等）。
- OpenAI 呼び出しのテストはモック (unittest.mock.patch) を使用して外部依存を除外できます（モジュール内の _call_openai_api を差し替え可能）。
- DuckDB / SQLite はファイルベースなのでテスト用の一時ファイルを用いると簡単に独立したテストが可能です。

付録: 典型的な起動例
--------------------
1) 監視起動（デフォルトパス使用）
   export KABUSYS_ENV=development
   python -m kabusys.run_monitoring

2) Execution 起動（Paper Trading で起動）
   export KABUSYS_ENV=paper_trading
   export PAPER_FILL_MODE=instant
   python -m kabusys.run_execution

3) 検証レポート
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

4) Streamlit ダッシュボード
   streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

最後に
------
この README はコードの意図と主要な使い方をまとめたものです。各モジュール内の docstring に詳細な設計意図や注意点が書かれているため、必要に応じて参照してください。追加で README に含めたい具体的なコマンドや設定（例: systemd ユニット例、Dockerfile、CI 設定など）があれば教えてください。必要に応じて追記します。