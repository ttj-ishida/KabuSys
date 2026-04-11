KabuSys — 日本株自動売買システム（README）
======================================

概要
----
KabuSys は日本株向けの自動売買・リサーチ・監視を目的とした Python 製ライブラリ／アプリケーション群です。  
主な責務は次のとおりです。

- シグナルに基づく発注（ExecutionEngine）
- 発注の再同期・リコンシリエーション（Reconciler）
- ポートフォリオ構築・ポジションサイズ計算（portfolio/*）
- ファクター計算・特徴量探索（research/*）
- ニュースを用いた LLM ベースのセンチメント評価（ai/*）
- システム・注文・リスク監視とアラート（monitoring/*）
- 実行プロセスの優先度 / CPU affinity 設定ユーティリティ（utils/*）

機能一覧
--------
主要な機能とモジュールの役割：

- execution
  - ExecutionEngine: シグナル読み込み→Gate 検査→発注（Signal Queue Pull 型）
  - OrderManager / OrderRepository: 注文作成・送信・同期・キャンセルの管理
  - Reconciler: 再起動後の注文・ポジションの突合せ（自動復旧）
  - RiskManager: 発注前の Gate チェック（レート制限・回路遮断等）
- portfolio
  - 候補選定（select_candidates）、等重・スコア重み（calc_equal_weights / calc_score_weights）
  - ポジションサイズ計算（calc_position_sizes）：ロット丸め・資金制約・コストバッファを考慮
  - セクターキャップ・レジーム乗数（apply_sector_cap / calc_regime_multiplier）
- research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
  - DuckDB を使ったオンプレ SQL/Python 実行を前提
- ai
  - news_nlp.score_news: raw_news を OpenAI（gpt-4o-mini）で評価し ai_scores へ保存
  - regime_detector.score_regime: ETF（1321）MA200 とマクロニュースで市場レジーム判定
  - OpenAI 呼び出しはリトライやフェイルセーフを組み込み、安全に失敗を扱う
- monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor：システム健全性、滞留注文、ドローダウン等の検出
  - MonitoringDB: SQLite に監視ログを永続化（system_status, trade_logs, positions, risk_logs, dashboard）
  - MonitoringEngine: 上記 Monitor を束ねてポーリングし、KillSwitch・AlertManager と連携
  - AlertManager: LINE Push によるアラート送信（クールダウン管理）
  - streamlit_dashboard: 監視ダッシュボード（read-only で monitoring DB を表示）
- utils
  - process_priority: Windows / POSIX をラップしてプロセス優先度・CPU affinity を設定

セットアップ手順
----------------
前提
- Python 3.10 以上（型注釈に | が使われているため）
- SQLite（標準ライブラリ）
- 必要な外部ライブラリ（下記）

推奨手順（開発環境）
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate（Windows は .venv\Scripts\activate）

2. 依存パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - （必要に応じて他のテスト用ライブラリ等を追加）

3. パッケージとして編集可能インストール（任意）
   - pip install -e .

環境変数 / .env
- .env ファイルと .env.local をプロジェクトルートで自動ロードします（OS 環境変数が優先）。
- 自動ロードを無効化する場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- 重要な環境変数（例）
  - JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン（必須）
  - KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
  - OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知を使う場合
  - KABUSYS_ENV — 実行環境: development | paper_trading | live（default: development）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/...、default: INFO）
  - DUCKDB_PATH — DuckDB ファイル（default: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（default: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（default: data/paper_trading.db）
  - PID_FILE_PATH / KILL_FLAG_PATH — pid / kill flag のパス
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、既定 60 秒）
  - PAPER_FILL_MODE — paper_trading のモック約定挙動（instant | partial | never | reject）

使い方
------
起動スクリプト（簡易）
- 監視ループを起動（本番用 SQLite を使用、MONITOR_POLL_INTERVAL を参照）
  - python -m kabusys.run_monitoring
  - または python src/kabusys/run_monitoring.py
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き（例: export MONITOR_POLL_INTERVAL=30）
  - 実行時にプロセス優先度を "high" に設定します（psutil による）

- 実行エンジンを起動（paper_trading では MockBroker を使用して data/paper_trading.db に分離）
  - python -m kabusys.run_execution
  - または python src/kabusys/run_execution.py
  - 本番環境: export KABUSYS_ENV=live
  - ペーパー: export KABUSYS_ENV=paper_trading
    - paper_trading の場合は settings.paper_sqlite_path（PAPER_TRADING_SQLITE_PATH）を使用

- streamlit ダッシュボード（read-only）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視データベースを読み取り専用で開くため、監視プロセスが既に書き込んでいる DB を安全に参照できます

AI 機能
- news_nlp.score_news と regime_detector.score_regime は OpenAI API キー（OPENAI_API_KEY）が必須です。  
  キーを明示的に引数で渡すことも可能（関数引数 api_key）。

Kill switch / 停止制御
- KillSwitch は data/kill.flag（デフォルト）に理由を文字列で書き込みます。ExecutionEngine は起動時・ループ中にこのファイルの存在を検出して安全に停止します。
- KILL_FLAG_CLEAR_ON_START を 1 にすると起動時に kill.flag を自動でクリアできます（Settings.kill_flag_clear_on_start）。

ログ・監視
- MonitoringDB（data/monitoring.db）に system_status / trade_logs / positions / risk_logs / dashboard を保存します。
- AlertManager は LINE push を送信します（TOKEN 未設定時はログのみ）。
- MonitoringEngine は SystemMonitor / TradeMonitor / RiskMonitor を定期的に実行して、必要時に Alert と KillSwitch 発動を行います。

開発時の便利なポイント
- Settings モジュールはプロジェクトルート（.git または pyproject.toml）を探索して .env を自動読み込みします。CI・テストで自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使ってください。
- DuckDB 接続を各 research/ai 関数に注入する設計なので、テスト時はテスト用 DuckDB を渡せます。
- OpenAI 呼び出し部は個別関数に抽象化されており、unittest.mock.patch によるモックが容易です。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要ファイル・モジュールの一覧（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / Settings
  - run_monitoring.py               — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py                — ExecutionEngine 起動スクリプト
  - utils/
    - __init__.py
    - process_priority.py           — プロセス優先度 / CPU affinity ユーティリティ
  - portfolio/
    - __init__.py
    - portfolio_builder.py          — 候補選定・等重/スコア重み
    - position_sizing.py            — 株数算出・スケールダウン・ロット丸め
    - risk_adjustment.py            — セクターキャップ・レジーム乗数
  - research/
    - __init__.py
    - factor_research.py            — momentum / volatility / value 計算
    - feature_exploration.py        — 将来リターン / IC / summary
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュース→LLM→ai_scores 書込み
    - regime_detector.py            — マクロ + MA200 による市場レジーム判定
  - execution/
    - execution_engine.py
    - order_manager.py
    - reconciler.py
    - order_repository.py (非抜粋)
    - broker_factory.py (非抜粋)
    - broker_api.py (非抜粋)
    - risk_manager.py (非抜粋)
  - monitoring/
    - __init__.py
    - monitoring_db.py              — SQLite スキーマ・永続化 API
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
    - streamlit_dashboard.py

注意事項 / 運用上のポイント
--------------------------
- Paper trading は本番 DB と完全に分離されます（default: data/paper_trading.db）。間違って本番 DB を上書きしないよう KABUSYS_ENV を適切に設定してください。
- .env の自動読み込みはプロジェクトルートの検出に依存します。実行環境に応じてパスや CWD を確認してください。
- OpenAI や外部 API を使う機能はネットワーク障害時にフェイルセーフ（多くはスコアを無視または中立値で継続）を備えていますが、API キーの漏洩には注意してください。
- process priority や cpu affinity の設定は OS 権限に依存します。権限不足時は警告ログが出ますが処理は継続します。

サンプル .env（例）
------------------
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
OPENAI_API_KEY=...
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
MONITOR_POLL_INTERVAL=60
PAPER_FILL_MODE=instant

ライセンス・貢献
----------------
- README 内ではライセンス情報は記載していません。実際のプロジェクトでは LICENSE ファイルを追加してください。  
- バグ報告・プルリクエスト歓迎です。テスト、型安全、及び API 呼び出し部分のモック化を意識した貢献が助かります。

補足
----
この README はコードベース（src/kabusys 内の各モジュール）を基にした概要・使い方・運用ガイドです。追加で必要な項目（例: 詳細な環境変数一覧、CI 手順、テスト手順、requirements.txt）を教えていただければ追記します。