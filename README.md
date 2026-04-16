KabuSys — 日本株自動売買システム
===============================

以下はこのコードベース（src/kabusys）の概要と使い方をまとめた README です。  
主に開発者・運用者向けの手順と挙動（環境変数、起動コマンド、DBの場所、監視・停止フラグ等）を記載します。

プロジェクト概要
----------------
KabuSys は日本株自動売買システムのコアライブラリ群です。主な責務は次の通りです。

- シグナルに基づくポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- 注文発行と状態管理（OrderManager / ExecutionEngine）
- 起動時リコンシリエーション（Reconciler）
- 監視機能（SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine）
- アラート（LINE Push）と Kill Switch（フラグファイルで ExecutionEngine を停止）
- Paper Trading 向けテスト用処理（Mock Broker、専用 SQLite）
- 研究用ファクター計算・特徴量解析（DuckDB を利用）
- ニュースの LLM による NLP スコアリング（OpenAI 経由）
- Streamlit ベースの監視ダッシュボード
- 検証レポート生成ツール（paper_verification_report）

主な機能一覧
-------------
- Portfolio construction
  - select_candidates, calc_equal_weights, calc_score_weights
  - calc_position_sizes（risk_based / equal / score）
  - セクターキャップやレジーム乗数の適用
- Execution（実際のブローカー／Mock broker を介して発注）
  - ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager など
- Monitoring
  - SystemMonitor（プロセス生存・CPU/メモリ/ディスク・データ鮮度）
  - TradeMonitor（滞留注文、約定価格異常）
  - RiskMonitor（ドローダウン・ポジション上限）
  - KillSwitch（条件により data/kill.flag を書き込み停止）
  - AlertManager（LINE Push）
  - MonitoringEngine（ポーリングの統合）
- Research / Data
  - DuckDB ベースのファクター計算（momentum/value/volatility）
  - forward returns / IC 計算 / 統計サマリ
- AI
  - news_nlp.score_news（OpenAI へのバッチ送信 + ai_scores へ書込）
  - regime_detector.score_regime（MA200 とマクロニュースを合成）
- Tools
  - paper_verification_report（Paper Trading DB を解析して検証レポートを出力）
- UI
  - Streamlit ダッシュボード（監視データの可視化）

システム要件（主な依存パッケージ）
--------------------------------
（プロジェクトに requirements.txt は含まれていませんが、少なくとも以下が必要になります）

- Python 3.9+
- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボードを使う場合)
- sqlite3（標準ライブラリ）
- その他、開発で必要なパッケージ

セットアップ手順
----------------
1. リポジトリをチェックアウト / 配布を展開
2. 仮想環境を作成して有効化（例: python -m venv .venv; source .venv/bin/activate）
3. 必要パッケージをインストール（例）
   - pip install duckdb psutil requests openai streamlit
   - 実際はプロジェクトで用いるバージョンを固定した requirements.txt を用意することを推奨
4. data ディレクトリ等の作成（必要に応じて）
   - mkdir -p data

設定（環境変数）
----------------
Settings クラス（src/kabusys/config.py）を通じて環境変数から設定を読み込みます。自動で .env / .env.local をプロジェクトルートからロードします（OS 環境変数が優先）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

重要な環境変数（抜粋）
- KABUSYS_ENV: 起動環境。development / paper_trading / live（デフォルト: development）
  - paper_trading のときは Execution 系は MockBrokerClient を使用し、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に分離して記録します。
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API 用（必須）
- OPENAI_API_KEY: OpenAI を使う機能（news_nlp / regime_detector）で必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE）用。未設定だと送信はスキップ
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の注文約定モード（instant|partial|never|reject、デフォルト: instant）
- MONITOR_POLL_INTERVAL: run_monitoring.py のポーリング間隔（秒、デフォルト: 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START：プロセス管理/停止フラグ周り

.env の読み込み順序（優先度）
- OS 環境変数 > .env.local > .env  
（ただし OS 環境変数は保護され、.env.local/.env がそれを上書きしません）

実行方法
--------

1) 監視ループを起動（system monitor 単体スクリプト）
- python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で指定可能（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は「常に本番 sqlite_path（Settings.sqlite_path）」を使用します（KABUSYS_ENV に無関係）
  - 停止はプロジェクトルート/data/stop_requested.flag を作成すると検知して終了します

2) ExecutionEngine を起動（注文実行エンジン）
- python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH にデータを書きます（本番 DB と分離）
  - 起動前に data/stop_requested.flag がある場合は起動しません
  - 実行中に stop flag を作るとエンジンに停止指示が送られます
  - 実行中は data/execution.pid に PID を書きます（stale PID の検出と削除ロジックあり）

3) Streamlit ダッシュボード（監視可視化）
- streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - monitoring.db を読み取り専用で開くため、MonitoringEngine が先に DB を作成している必要があります

4) Paper Trading 検証レポート生成
- python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）

5) AI 関連（ニューススコア / レジーム判定）
- kabusys.ai.score_news（関数として呼ぶ） / kabusys.ai.regime_detector.score_regime
  - OpenAI API キー（OPENAI_API_KEY）必須。未設定だと ValueError を投げます（呼び出し先の関数内でチェック）

停止／停止フラグ
----------------
- 全体停止要求（監視やエンジン）: data/stop_requested.flag をファイルシステム上に作成すると、run_monitoring/run_execution はそれを検知して安全に終了します。
- Kill Switch（自動停止）: リスク条件（ドローダウン超過・ポジション上限超過）成立時に monitoring 側から data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送る設計。Kill Switch は Settings.kill_flag_path（デフォルト data/kill.flag）を使います。
- kill.flag が既にある場合、ExecutionEngine は起動時に自動で起動しない設定になっています（必要に応じて clear してください）。

データベース・ファイル配置（デフォルト）
------------------------------------
- data/monitoring.db        — 監視ログ（MonitoringDB）
- data/paper_trading.db     — Paper Trading 用 SQLite（paper_trading 環境）
- data/kabusys.duckdb       — DuckDB（時系列価格・ファクター等）
- data/execution.pid        — ExecutionEngine の PID（起動時に書き込まれる）
- data/stop_requested.flag  — 手動停止フラグ（run_* が監視）
- data/kill.flag            — KillSwitch が書き込む停止フラグ

注意: モジュールの中には DB スキーマ自動初期化／マイグレーション処理（init_monitoring_db）があり、必要な列やテーブルが無ければ作成します。

ディレクトリ構成（主なファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                     — 環境変数 / 設定読み込みロジック
- run_monitoring.py             — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py              — ExecutionEngine 起動スクリプト
- utils/
  - process_priority.py         — プロセス優先度 / CPU affinity ユーティリティ
- monitoring/
  - __init__.py
  - monitoring_db.py            — SQLite への永続化層（テーブル初期化含む）
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - alert_manager.py
  - kill_switch.py
  - streamlit_dashboard.py
- execution/
  - order_manager.py
  - reconciler.py
  - ... (エンジン・ブローカ実装など)
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- ai/
  - news_nlp.py
  - regime_detector.py
- data/ (実行時に使用される /repo外の data ディレクトリ想定)
- tools/
  - paper_verification_report.py

開発メモ / 実装上のポイント
-----------------------
- Settings は .env の自動ロードを行います（プロジェクトルートを .git または pyproject.toml で検出）。ただしテストなどで無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を使用できます。
- run_monitoring はモニタリング用 DB（sqlite_path）を常に使用します。環境に依らず本番 monitoring DB を参照するため注意してください。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_trading 用 SQLite を使います（データ分離）。
- news_nlp と regime_detector は OpenAI API を利用します。API呼び出しは 429/ネットワーク断/5xx に対して指数バックオフでリトライしますが、最終的にはフェイルセーフとしてスコア=0 やスキップして継続する設計です。
- MonitoringDB はマイグレーションを簡易に行います（カラム追加等）。ただし大きな変更を伴うマイグレーションは別途対応を検討してください。

トラブルシューティング（よくある問題）
---------------------------------
- OpenAI 関連で ValueError: API キーが未設定 が出る → OPENAI_API_KEY を設定してください。
- Streamlit で DB を開けない → MonitoringEngine が DB を作成していないか、パスが間違っています。streamlit 起動時に -- --db パラメータでパスを指定できます。
- run_execution がすぐに終了する（stop flag） → data/stop_requested.flag または data/kill.flag が存在しないか確認してください。
- .env がロードされない → プロジェクトルートの検出（.git / pyproject.toml）に失敗しているか、KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されています。

サンプル .env（例）
------------------
# KABUSYS の最小設定例（本番運用では機密情報の管理に注意）
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
SQLITE_PATH=data/monitoring.db
DUCKDB_PATH=data/kabusys.duckdb
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
PAPER_FILL_MODE=instant
MONITOR_POLL_INTERVAL=60

ライセンス / 貢献
-----------------
（このリポジトリのライセンス情報や貢献ルールがある場合はここに追記してください）

以上。運用や導入時に不明点があれば、どの機能（監視 / 実行 / AI / DB 初期化 等）について知りたいか指定してください。詳細手順や例コマンドを追加で提供します。