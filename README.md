# KabuSys

日本株向けの自動売買フレームワーク（小規模プロダクション向け）。  
ポートフォリオ構築、発注エンジン、監視／アラート、リサーチ用ファクター計算、AI によるニュースセンチメントなどを含むモジュール群で構成されています。

## 概要
KabuSys は以下の関心事を分離して実装しています。
- 発注ロジック（ExecutionEngine / OrderManager / BrokerClient）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager）
- ポートフォリオ構築（候補選定・重み付け・株数決定・リスク調整）
- リサーチ（ファクター計算、特徴量探索）
- AI モジュール（ニュースの NLP スコアリング、レジーム判定）
- DB 層：監視ログは SQLite（デフォルト `data/monitoring.db`）、分析は DuckDB（`data/kabusys.duckdb`）

設計上の特徴：
- 環境変数／.env による設定管理（自動ロード機能あり）
- Paper Trading と Live を明確に分離（Paper 用 DB を使用）
- フェイルセーフ（API 失敗時のフォールバック、リトライ、部分失敗時の局所的書き換え）
- テスト容易性を意識した純粋関数や抽象化（DB 依存の少ない関数群）

## 主な機能一覧
- ExecutionEngine: ブローカー連携・注文管理・リスク制御・リコンシリエーション
- MonitoringEngine: システム状態、注文滞留、約定異常、ドローダウン監視、Kill Switch 判定、LINE 通知
- Portfolio モジュール: 候補選定、等配分／スコア配分、リスク調整、株数計算（単元丸め等）
- Research モジュール: Momentum / Volatility / Value 等のファクター計算、将来リターン・IC 計算
- AI モジュール: ニュースのセンチメント集計（OpenAI 使用）、市場レジーム判定
- ツール: Paper Trading 検証レポート生成、Streamlit ベースの監視ダッシュボード

## セットアップ手順（開発用）
1. リポジトリをクローンしてプロジェクトルートへ移動
2. Python 仮想環境を作成・アクティベート（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール（代表例）
   - pip install psutil duckdb openai requests streamlit
   - （実際の requirements.txt がある場合はそれを利用してください）
4. .env の用意
   - プロジェクトルートに .env（または .env.local）を配置して環境変数を設定します。
   - 自動ロードはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 例: `.env` に JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY などを設定。
5. data ディレクトリの作成（必要に応じて）
   - mkdir -p data
   - 初回は monitoring DB / duckdb ファイルは存在しないため、起動時に作成・マイグレーションされます。

## 主要な環境変数（抜粋）
- KABUSYS_ENV: 起動モード（development / paper_trading / live）。デフォルト: development
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: Paper broker の約定挙動（instant | partial | never | reject）。デフォルト: instant
- OPENAI_API_KEY: OpenAI を利用する機能に必須
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須となる箇所あり）
- KABU_API_PASSWORD: kabuステーション API 用（必須となる箇所あり）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: monitoring のポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START など監視関連のパス設定

※ Settings クラスで未設定必須キーを参照すると ValueError を送出します。

## 使い方（よく使うコマンド例）
- 監視ループの起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 補足: 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書きできます（例: `MONITOR_POLL_INTERVAL=30`）。
  - run_monitoring は Monitoring 用 DB と DuckDB に接続して SystemMonitor を定期実行します。監視停止にはプロジェクトルートの `data/stop_requested.flag` を作成してください。

- 発注エンジンの起動（Execution）
  - python -m kabusys.run_execution
  - Paper Trading を使う場合:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - paper_trading モードでは MockBrokerClient を使用し、データは `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）へ書き込みます。
  - 実行中の停止は `data/stop_requested.flag` を作成してください。Execution は `data/execution.pid` を PID 管理に使います。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db /path/to/paper_trading.db  （環境変数 PAPER_TRADING_SQLITE_PATH が優先されます）

- 監視ダッシュボード（Streamlit）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用 URI を使って DB を開きます。MonitoringEngine が記録していることが前提です。

## 注意事項 / 実運用メモ
- Kill Switch / Stop フラグ
  - `KillSwitch` は監視結果に応じて `data/kill.flag` を書き込み、ExecutionEngine に停止シグナルを送ります（Execution は起動時にフラグの有無をチェック）。
  - 手動停止用に `data/stop_requested.flag` を用意してあり、run_* スクリプトはこの存在を確認して安全終了します。
- DB マイグレーション
  - monitoring DB の初期化処理（init_monitoring_db）は冪等で、既存 DB に不足カラムがあれば ALTER TABLE で追加します（例: trade_logs.latency_ms, dashboard.peak_value）。
- OpenAI 利用
  - news_nlp / regime_detector は OpenAI API（gpt-4o-mini を指定）を使います。API キーが必須で、コスト・レート制限・失敗時のフォールバック（0.0 等）を考慮してください。
- プロセス優先度
  - run_* スクリプトは起動直後にプロセス優先度を "high" に設定しようとします（psutil を使用、権限により失敗する場合あり）。
- Paper Trading の分離
  - `paper_trading` 環境では発注や DB が本番と完全に分離されるよう設計されています。必ず KABUSYS_ENV を切り替えて利用してください。

## ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py (パッケージ定義)
  - config.py (環境・設定管理)
  - run_monitoring.py (監視ループ起動スクリプト)
  - run_execution.py (発注エンジン起動スクリプト)
  - ai/
    - news_nlp.py (ニュース NLP スコアリング)
    - regime_detector.py (市場レジーム判定)
  - monitoring/
    - monitoring_db.py (SQLite 永続化層)
    - system_monitor.py, trade_monitor.py, risk_monitor.py
    - monitoring_engine.py (各 Monitor を束ねる)
    - kill_switch.py, alert_manager.py
    - streamlit_dashboard.py (Streamlit ダッシュボード)
  - execution/
    - order_manager.py, reconciler.py, ...（発注・リコンシリエーション関連）
  - portfolio/
    - portfolio_builder.py (候補選定／重み)
    - position_sizing.py (株数計算)
    - risk_adjustment.py (セクター制限等)
  - research/
    - factor_research.py (ファクター計算)
    - feature_exploration.py (IC/統計)
  - monitoring/ (上記)
  - tools/
    - paper_verification_report.py
  - utils/
    - process_priority.py (プロセス優先度／CPU affinity ユーティリティ)
  - data/ (実行時生成を想定)
    - monitoring.db (デフォルト)
    - kabusys.duckdb (デフォルト)
    - paper_trading.db (paper_trading 用)

※ 上記はソースルート（src）配下の構成です。

## よくある運用ワークフロー（例）
1. 開発環境で DuckDB に株価・財務データをロード
2. `python -m kabusys.run_monitoring` を起動して監視ログを記録
3. Paper Trading で挙動確認:
   - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
   - 取引ログを `data/paper_trading.db` で確認
4. 検証:
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
5. Streamlit で監視ダッシュボードを起動して状態確認

## 開発・テストに関する補足
- .env 読み込み:
  - config.py はプロジェクトルート（.git または pyproject.toml を探索）を基に `.env` / `.env.local` を自動ロードします（既存の OS 環境変数を保護）。テスト等で自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- ログレベルは環境変数 `LOG_LEVEL` で制御可能。
- モジュールは可能な限り副作用を避ける設計になっています。OpenAI など外部 API 呼び出し箇所は明確で、テスト時は呼び出し関数を差し替えやすいようになっています（例: _call_openai_api のパッチ）。

---

README の内容や起動手順について、プロジェクト特有の運用ルールや CI/CD の要件に合わせて加筆します。必要であれば、具体的な .env.example のテンプレートや docker-compose / systemd ユニットのサンプルも用意できます。どの情報を追加したいですか？