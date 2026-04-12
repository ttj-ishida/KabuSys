# KabuSys

日本株自動売買システムの一部を実装した Python パッケージ。  
このリポジトリには、監視・実行・ポートフォリオ構築・リサーチ・AI 補助処理などのモジュール群が含まれます。

次の README はコードベース（src/kabusys 以下）を元に作成しています。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要なコンポーネント群を提供します。主な役割は次の通りです。

- ExecutionEngine（発注エンジン）: ブローカー API と連携して注文の作成・送信・状態管理を行う。
- Monitoring（監視）: システム稼働状況、注文の異常、リスク（ドローダウン、ポジション上限など）をチェックしてログ／通知する。
- Portfolio（銘柄選定とポジション設計）: 候補選定、重み計算、単元株丸め、セクター制約、レジーム乗数など。
- Research（リサーチ）: DuckDB 上の時系列データからファクター計算・特徴量解析を行う。
- AI 補助（news_nlp, regime_detector）: OpenAI を使ったニュースセンチメント評価や市場レジーム判定。
- ユーティリティ: プロセス優先度設定、環境変数読み込みなど。

設計上の方針として、ルックアヘッドバイアス防止（target_date を明示的に渡す等）、部分的にフェイルセーフ（API 失敗時はフォールバック値を採る）などが組み込まれています。

---

## 機能一覧（抜粋）

- system_monitor: CPU / メモリ / ディスク使用率、実行プロセス生存確認、データ鮮度チェック
- trade_monitor: 滞留注文検出、約定価格の異常検出
- risk_monitor: ドローダウン監視、ポジション数上限監視、ダッシュボード更新
- monitoring_engine: 上記モニタを束ねてポーリングし、KillSwitch・AlertManager と連携
- alert_manager: LINE Push API を用いた通知（クールダウン管理付き）
- monitoring_db: 監視用 SQLite スキーマ作成と読み書きユーティリティ
- execution: OrderManager、Reconciler、OrderRepository 等（発注ロジック・復旧処理）
- portfolio: 候補選定・重み計算・ポジションサイズ計算・セクター制約適用
- research: momentum/value/volatility ファクター計算、将来リターン、IC、統計サマリ
- ai:
  - news_nlp: ニュース記事の銘柄別センチメントを OpenAI（gpt-4o-mini）で評価し ai_scores に保存
  - regime_detector: ETF とマクロニュースを合成して日次の市場レジームを判定
- tools:
  - paper_verification_report: Paper Trading DB の簡易検証レポート出力
  - streamlit_dashboard: 監視用 Streamlit ダッシュボード

---

## 前提（依存ライブラリ）

主な実行時依存（ソースから推定）:

- Python 3.8+
- duckdb
- psutil
- requests
- openai
- streamlit（ダッシュボード利用時）
- sqlite3（標準モジュール）

プロジェクトの配布パッケージに requirements.txt / pyproject.toml がある前提で、環境に合わせてインストールしてください。例:

pip install duckdb psutil requests openai streamlit

---

## 環境変数（主要なもの）

※設定は .env / .env.local から自動読み込みされます（プロジェクトルートの .git または pyproject.toml を探索）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

- KABUSYS_ENV: 起動環境（development, paper_trading, live）。デフォルト: development
  - paper_trading の場合、Execution は MockBrokerClient を使い、paper_trading 用の DB に出力します。
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API 用（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール実行時に必要）
- LINE_CHANNEL_ACCESS_TOKEN: LINE 通知用トークン（任意）
- LINE_USER_ID: LINE 通知先ユーザーID（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 SQLite（monitoring）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（default: data/paper_trading.db）
- PID_FILE_PATH: ExecutionEngine の PID ファイル位置（default: data/execution.pid）
- KILL_FLAG_PATH: Kill フラグファイル（default: data/kill.flag）
- PAPER_FILL_MODE: paper_trading のフィルモード（instant|partial|never|reject：default "instant"）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、default 60。0 以下は無効でデフォルトにフォールバック）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、default INFO）
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視閾値（数値）

詳しいキーの振る舞いは src/kabusys/config.py を参照してください。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンし、プロジェクトルートに移動
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)
3. 依存ライブラリをインストール
   - pip install -r requirements.txt
   または最低限:
   - pip install duckdb psutil requests openai streamlit
4. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、環境変数を直接設定します。
   - 例（.env）:
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     OPENAI_API_KEY=...
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     LINE_CHANNEL_ACCESS_TOKEN=...
     LINE_USER_ID=...
5. ディレクトリ作成
   - data/ ディレクトリなど、DB ファイル置き場を作成してください。
     mkdir -p data

初回実行時、Monitoring DB のスキーマは自動作成（init_monitoring_db）されます。

---

## 実行方法

以下は代表的な実行パターンです。プロジェクトのルート（src が見える状態）で実行する前提です。

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - または: python src/kabusys/run_monitoring.py
  - 説明:
    - プロセス優先度を "high" に設定し（可能な場合）、MonitoringDB を初期化して SystemMonitor のポーリングループを開始します。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（秒、デフォルト 60）。

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - または: python src/kabusys/run_execution.py
  - 説明:
    - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使って data/paper_trading.db に記録します（本番 DB と分離）。
    - プロセス優先度を "high" に設定してから起動します。

- Paper Trading 検証レポート生成（CLI）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数またはデフォルト data/paper_trading.db）
  - 出力: 標準出力に検証レポートを表示します（稼働率、注文成功率、レイテンシ等）。

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 説明: 監視用 DB を読み取り専用で開き、ダッシュボードを表示します。

- AI モジュール（ニューススコア / レジーム判定）
  - news_nlp.score_news(conn, target_date, api_key=...)
  - regime_detector.score_regime(conn, target_date, api_key=...)
  - いずれも OPENAI_API_KEY が必要。DuckDB 接続（prices_daily や raw_news 等のテーブルがあること）が前提。

---

## 重要な挙動・注意点

- Monitoring は KABUSYS_ENV に関わらずデフォルトの SQLITE_PATH（data/monitoring.db）を使用します。Execution は paper_trading の場合は専用 DB を使用して本番 DB と明確に分離します。
- run_monitoring と run_execution 実行時にプロセス優先度を "high" に設定しようとします（プラットフォーム依存、設定に失敗してもスキップして継続します）。
- Kill Switch（kill.flag）:
  - RiskMonitor が条件を満たすと kill.flag を作成し、ExecutionEngine に停止シグナルを送ります。flag のパスは Settings.kill_flag_path（デフォルト data/kill.flag）。
  - ExecutionEngine 起動時に kill flag をクリアする設定（KILL_FLAG_CLEAR_ON_START）があります。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db() は冪等で、必要なら既存テーブルにカラムを追加する軽微なマイグレーション処理を行います（例: trade_logs.latency_ms, dashboard.peak_value）。
- AI 呼び出しは外部 API（OpenAI）に依存します。429 / タイムアウト / 5xx 等はリトライロジックがありますが、失敗時はフェイルセーフとして一部処理をスキップまたは 0 にフォールバックします。
- .env のパース実装はシェル風の export 形式、クォート、インラインコメント等に対応しています。ただし完全な互換を保証するものではありません。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定管理
  - run_monitoring.py               — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py                — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py           — プロセス優先度・CPU affinity ユーティリティ
    - __init__.py
  - monitoring/
    - __init__.py
    - monitoring_db.py              — SQLite 監視 DB 層（初期化・読み書き）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他 execution 関連ファイル: broker_factory 等が存在)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - monitoring/ (上記)
  - tools/
    - paper_verification_report.py
    - __init__.py

（必要に応じてリポジトリ全体のファイル構成を参照してください）

---

## 開発メモ / 拡張ポイント

- position_sizing、portfolio_builder、risk_adjustment は純粋関数群でありユニットテストが容易です。
- AI 周り（news_nlp/regime_detector）は外部 API 呼び出し箇所をラップしているため、テスト時は該当関数をモックする設計がされています。
- DuckDB を用いたファクター計算は SQL ベースで高速に処理できるよう設計されています。データ投入後に research モジュールから再利用可能です。

---

必要であれば、README に以下の追加項目も追記できます：

- より詳しいインストール手順（pyproject.toml / poetry / virtualenv など）
- 開発・テストスイートの実行手順
- 実行時のログ設定例・systemd でのサービス定義例
- 各モジュールの API リファレンス（関数引数や戻り値の詳細）

必要な内容を教えてください。