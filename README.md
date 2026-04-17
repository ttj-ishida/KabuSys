# KabuSys — 日本株自動売買システム（README）

このリポジトリは日本株向けの自動売買システム KabuSys のコアライブラリ群です。
トレーディングの実行エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI を使ったニュース解析などのコンポーネントを含みます。

主な設計方針
- 実行ロジック（発注・状態管理）とデータ永続化（SQLite/DuckDB）を分離
- Paper Trading（シミュレーション）と Live（本番）を環境変数で明確に分離
- 監視は ExecutionEngine 側の停止シグナル検出、稼働率/リスク監視、アラート送信（LINE）を提供
- DuckDB を用いたリサーチ／ファクター計算を想定（外部 API には最低限依存）

以下はこのコードベースを使い始めるためのガイドです。

目次
- プロジェクト概要
- 機能一覧
- 要件
- セットアップ手順
- 使い方（各コンポーネントの起動・主要スクリプト）
- 主要な環境変数（抜粋）
- ディレクトリ構成（主要ファイルの説明）
- 注意事項 / トラブルシューティング

プロジェクト概要
- KabuSys は市場データ（DuckDB）を用いたリサーチ、ポートフォリオ構築、発注エンジン、監視・アラート、AI によるニュース解析を組み合わせた自動売買システムのコアライブラリです。
- 実行（ExecutionEngine）と監視（MonitoringEngine）は別プロセスとして想定され、フラグファイルや pid ファイルを介して連携します。
- Paper Trading 環境を用意して本番 DB と明確に分離できます。

機能一覧
- Execution
  - 発注管理（OrderManager, OrderRepository）
  - 起動時リコンシリエーション（Reconciler）
  - リスク管理（RiskManager）
  - Broker クライアントの抽象化（BrokerFactory 等）→ paper_trading 時は MockBroker を利用
- Monitoring
  - システム監視（CPU / メモリ / ディスク / プロセス検出）
  - 注文監視（滞留注文・約定価格異常）
  - リスク監視（ドローダウン / ポジション数上限）
  - Kill Switch（閾値超過時に data/kill.flag を書き込み ExecutionEngine を停止）
  - LINE によるプッシュ通知（AlertManager）
  - Streamlit によるダッシュボード（read-only 接続）
- Portfolio（純粋関数）
  - 候補選定、等重・スコア重み付け、ポジションサイズ計算、セクター上限処理、レジーム乗数
- Research（DuckDB）
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン・IC 計算・特徴量サマリ
- AI
  - ニュース NLP（OpenAI）を使った銘柄センチメント（ai_scores）生成
  - 市場レジーム判定（ma200 とマクロセンチメントの合成）
- ユーティリティ
  - 環境変数の自動読み込み（.env / .env.local）、Settings クラス
  - プロセス優先度・CPU affinity 設定ユーティリティ
  - Monitoring DB の初期化・マイグレーションユーティリティ

要件（推奨）
- Python 3.10+
- 必要な主なパッケージ（代表例）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード起動時)
- 実行環境によって追加パッケージが必要になる場合があります（Broker クライアント等）。

セットアップ手順（ローカルでの最小セットアップ）
1. リポジトリをクローンしてワークディレクトリへ移動
   - git clone <repo> && cd <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール（例）
   - pip install duckdb psutil requests openai streamlit

   ※ 実際の requirements.txt はプロジェクトに合わせて用意してください。

4. 環境変数の設定
   - プロジェクトルートに .env を作成すると自動で読み込まれます（.env.local は上書きが可能）。
   - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
   - 主要な環境変数の例（.env）:
     - KABUSYS_ENV=development           # development | paper_trading | live
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - PID_FILE_PATH=data/execution.pid

5. data ディレクトリ作成（DB 等の保存先）
   - mkdir -p data

6. DB 初期化
   - 監視用 DB はスクリプト実行時に自動で init_monitoring_db が呼ばれます。手動で作る場合は空の SQLite ファイルを data/monitoring.db として用意しておくと便利です。

使い方（代表的なスクリプト）
- ExecutionEngine を起動（本番/紙取引の切替）
  - 本番（KABUSYS_ENV=live または development）:
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - Paper Trading（Mock Broker、DB: data/paper_trading.db）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 起動時、ExecutionEngine は data/execution.pid を書き、data/stop_requested.flag や data/kill.flag を監視して停止します。

- MonitoringEngine を起動（ポーリング監視）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能。デフォルトは 60 秒。
  - Monitoring は KABUSYS_ENV に関係なく設定された sqlite_path（デフォルト data/monitoring.db）を使用します。

- Streamlit ダッシュボード（監視 UI、読み取り専用）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート生成ツール
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH または --db で上書き可）

- AI 関連
  - kabusys.ai.score_news(conn, target_date, api_key=None)  — raw_news を読み AI で銘柄センチメントを計算して ai_scores に書き込む
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None) — レジーム判定を market_regime に書き込む
  - OpenAI API キーが必要（引数で渡すか OPENAI_API_KEY 環境変数）

主要な環境変数（抜粋）
- KABUSYS_ENV: 開発環境フラグ（development / paper_trading / live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager の LINE 通知用
- SQLITE_PATH: 監視 SQLite DB（デフォルト data/monitoring.db）。Monitoring は常にこの sqlite_path を使用します
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- PID_FILE_PATH: ExecutionEngine の pid ファイルパス（デフォルト data/execution.pid）
- KILL_FLAG_*: Kill Switch 用フラグ設定 (Settings.kill_flag_path 等)
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

ディレクトリ構成（主要ファイルの説明）
- src/kabusys/
  - __init__.py — パッケージ定義（__version__）
  - config.py — Settings クラス、.env 自動ロードロジック、環境変数検証
  - run_execution.py — ExecutionEngine 起動スクリプト（paper_trading での振る舞いも含む）
  - run_monitoring.py — SystemMonitor 起動スクリプト
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py — Monitoring DB のスキーマ初期化と永続化 API（MonitoringDB）
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py — 注文滞留・約定異常検出
    - risk_monitor.py — ドローダウン / ポジション上限検出とログ
    - kill_switch.py — kill.flag 書き込み/クリア用ユーティリティ
    - alert_manager.py — LINE へのアラート送信
    - monitoring_engine.py — 各 Monitor をまとめたポーリングエンジン
    - streamlit_dashboard.py — Streamlit による監視 UI（read-only）
  - execution/
    - order_manager.py, reconciler.py, ... — 発注・同期・リコンシリエーションロジック
    - broker_factory.py, broker_api.py, ... — ブローカークライアント抽象化
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 株数算出・スケール調整
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — Momentum/Volatility/Value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン計算・IC・統計サマリ
  - ai/
    - news_nlp.py — OpenAI を用いたニュースセンチメント集計（ai_scores へ書き込み）
    - regime_detector.py — MA200 とマクロセンチメントの合成によるレジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading データから検証レポートを生成

注意事項 / トラブルシューティング
- .env 読み込み
  - プロジェクトルート（.git または pyproject.toml を基準）にある .env / .env.local を自動で読み込みます。
  - OS 環境変数の優先度が高く、.env.local は .env を上書きします。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading
  - KABUSYS_ENV=paper_trading を指定すると、実行側は MockBroker を使用し DB は PAPER_TRADING_SQLITE_PATH を使います（本番 DB と完全分離）。
- Monitoring
  - Monitoring は Settings.sqlite_path を使用してログを保存します。監視は本番 DB に対して動作する想定です（環境に関わらず同じパスを参照）。
- OpenAI / RateLimit
  - AI 関連は外部 API（OpenAI）に依存します。429 / ネットワーク断 / タイムアウト / 5xx はリトライ戦略が実装されていますが、API キーや使用量にご注意ください。
- 権限・優先度設定
  - set_process_priority() は psutil に依存し、権限不足で失敗する場合は警告ログが出て処理は継続します。
- DB マイグレーション
  - init_monitoring_db() は既存 DB にカラムを追加する簡易マイグレーションを実装しています（例: trade_logs.latency_ms, dashboard.peak_value）。
- PID / STOP フラグ
  - data/execution.pid（PID ファイル）と data/stop_requested.flag / data/kill.flag（停止フラグ／kill スイッチ）はプロセス制御・停止シグナルに利用されます。直接編集する場合は注意して下さい。

開発・拡張のヒント
- DuckDB 接続を渡してローカルで SQL を実行することで、リサーチ関数を手早く検証できます。
- AI モジュールのテストは _call_openai_api をモック化して行うと外部依存を切り離せます。
- portfolio や position sizing のロジックは純粋関数群になっているためユニットテストが容易です。

ライセンス・貢献
- （この README にはライセンス情報が含まれていません。実プロジェクトでは LICENSE ファイルを追加してください。）

以上。必要であれば README に入れる具体的な .env.example や systemd/pm2 用のユニットファイル、起動スクリプト例、動作フロー図なども追記できます。どの情報を追加したいか指示してください。