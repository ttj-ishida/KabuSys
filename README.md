# KabuSys

日本株向け自動売買システムの一部を抜粋したコードベース向け README。  
このドキュメントはローカル開発 / 運用を始めるための概要、セットアップ手順、主要コマンドとディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買を支援するモジュール群です。本リポジトリには以下の主要機能が含まれます（抽出）:

- 注文生成・送信・状態管理（ExecutionEngine 周辺）
- リコンシリエーション（再起時の同期）
- ポートフォリオ構築（候補選定、重み付け、株数決定）
- リスク調整（セクター上限、レジーム乗数）
- モニタリング（システム状態、注文異常、リスク監視、アラート）
- Research / ファクター計算（DuckDB を用いたファクター計算）
- AI モジュール（ニュースセンチメント / レジーム判定、OpenAI を利用）
- 運用補助ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

設計上の特徴:
- DuckDB / SQLite をデータ層に使用（ローカルファイルベース）
- 本番と Paper Trading を分離（paper_trading 用 DB を用意）
- 環境変数／.env による設定管理（自動ロード）
- 外部 API（kabuステーション、J-Quants、OpenAI）をプラガブルに扱う

---

## 機能一覧（要点）

- Execution
  - 注文の作成・送信・同期（OrderManager, Reconciler）
  - リスク管理（RiskManager）や order repository（SQLite）
  - Paper Trading 対応（KABUSYS_ENV による切替、独立 DB）

- Portfolio
  - 候補選定（スコア順）
  - 等配分 / スコア重み / リスクベースによるポジションサイズ決定
  - セクター上限、レジーム乗数などのリスク調整

- Monitoring
  - SystemMonitor: CPU/Memory/Disk、プロセス存在チェック、データ鮮度
  - TradeMonitor: 滞留注文、約定異常価格の検出
  - RiskMonitor: ドローダウン・ポジション上限の監視
  - KillSwitch / AlertManager: 条件による停止フラグ書き込み、LINE 通知
  - Streamlit ダッシュボード（読み取り専用で監視情報表示）
  - monitoring DB 初期化ユーティリティ（テーブル／マイグレーション）

- Research / AI
  - ファクター計算（momentum, volatility, value）
  - Feature exploration（forward returns, IC, summary）
  - ニュースの LLM ベースセンチメント分析（OpenAI）
  - レジーム判定（MA200 と マクロニュースの合成）

- Tools
  - Paper Trading 検証レポート生成スクリプト（成功率・稼働率・レイテンシ等）

---

## セットアップ手順

前提:
- Python 3.9+（型アノテーションの仕様に依存）
- システムに pip が使えること

1. リポジトリをクローン / チェックアウト

2. 依存ライブラリをインストール（代表例）
   - 必要な主なパッケージ:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit (ダッシュボード利用時)
   - 例:
     pip install duckdb psutil requests openai streamlit

   （プロジェクトに requirements.txt がある場合はそれを使ってください）

3. 環境変数 / .env
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（OS 環境変数が優先されます）。
   - 自動ロードを無効化する場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 重要な環境変数（抜粋）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - OPENAI_API_KEY（AI 機能を使う場合）
     - PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading の約定挙動）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（Paper Trading 用 DB、デフォルト: data/paper_trading.db）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（AlertManager 用）
     - PID_FILE_PATH（デフォルト: data/execution.pid）
     - KILL_FLAG_PATH（デフォルト: data/kill.flag）

   - 簡易例 (.env):
     KABUSYS_ENV=development
     SQLITE_PATH=data/monitoring.db
     DUCKDB_PATH=data/kabusys.duckdb
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=...

4. データディレクトリ準備
   - デフォルトで `data/` 以下のファイルを読み書きします。必要なら作成してください。
   - monitoring の初回起動時に SQLite テーブルは自動生成されます（init_monitoring_db が実行されます）。

---

## 使い方（主要スクリプト）

下記はプロジェクト内の起動スクリプト・ツールの実行例です。

1. Monitoring ポーリングループを起動
   - 実行:
     python -m kabusys.run_monitoring
   - 説明:
     - SystemMonitor を定期実行して system_status / risk_logs / dashboard 等を更新します。
     - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）。
     - 起動時にプロセス優先度を "high" に設定しようとします（psutil の権限に依存）。

2. ExecutionEngine を起動（実際の発注処理）
   - 実行:
     python -m kabusys.run_execution
   - 説明:
     - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）に対して動作します。本番 DB と完全分離されます。
     - ブローカークライアントの生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立ててセッションを実行します。

3. Streamlit 監視ダッシュボード（読み取り専用）
   - 実行例:
     streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 説明:
     - monitoring.db を読み取り専用で開いてダッシュボード表示します。MonitoringEngine を先に起動してデータを作成してください。

4. Paper Trading 検証レポート生成ツール
   - 実行例:
     python -m kabusys.tools.paper_verification_report
     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     # DB を指定する場合:
     python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
   - 説明:
     - PAPER_TRADING_SQLITE_PATH（または --db）で指定した SQLite DB を読み、稼働率・注文成功率・レイテンシ等の指標を出力します。
     - 判定基準（閾値）はスクリプト内に定義されています（例: uptime >= 99% 等）。

5. AI 機能（ニュース NLP / レジーム判定）
   - 関数単位で利用:
     - kabusys.ai.score_news（news_nlp.score_news）
     - kabusys.ai.regime_detector.score_regime
   - 注意:
     - OpenAI API キー（OPENAI_API_KEY）または関数引数 api_key が必要です。
     - API 呼び出しはリトライ処理や失敗時のフェイルセーフ（スコア 0.0 等）を備えていますが、API 利用料が発生します。

---

## 設定（Settings）について（重要ポイント）

- 環境変数は自動で .env / .env.local をロード（OS 環境が優先）
- KABUSYS_ENV の有効値: development | paper_trading | live
  - paper_trading の場合、発注動作は MockBrokerClient を利用し、書き込み先 DB を分離
- PAPER_FILL_MODE の有効値: instant | partial | never | reject（Paper Trading の約定挙動）
- PID ファイル・kill flag:
  - Settings.pid_file_path（デフォルト data/execution.pid）に実行中プロセスの PID を残す挙動あり（ExecutionEngine 側）
  - KillSwitch は Settings.kill_flag_path（デフォルト data/kill.flag）へ理由を書き込み、ExecutionEngine に停止を指示します
- .env 読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

---

## ディレクトリ構成（主要ファイル）

（パッケージは `src/kabusys` 配下）

- src/kabusys/
  - __init__.py
  - config.py               — 設定 / .env 自動ロード / Settings クラス
  - run_monitoring.py       — SystemMonitor のポーリング起動スクリプト
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - data/                   — 想定するデータディレクトリ（DuckDB / SQLite 等）
  - execution/
    - order_manager.py
    - reconciler.py
    - order_repository.py (参照あり)
    - ... (ブローカー関連インターフェース等)
  - monitoring/
    - monitoring_db.py      — monitoring 用 SQLite テーブル定義・操作
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py           — OpenAI を使ったニュースセンチメント処理
    - regime_detector.py    — レジーム判定（MA200 + マクロニュース）
  - tools/
    - paper_verification_report.py

- data/
  - （デフォルトファイル）
  - kabusys.duckdb           — DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - monitoring.db            — SQLITE_PATH（デフォルト: data/monitoring.db）
  - paper_trading.db         — PAPER_TRADING_SQLITE_PATH（Paper Trading 用）

---

## 運用上の注意 / ベストプラクティス

- 本番運用時は KABUSYS_ENV=live を設定してください。paper_trading は必ず別 DB に分離されます。
- OpenAI を利用する機能は API 使用料が発生します。テスト時はモック化を推奨します（news_nlp._call_openai_api 等をパッチ）。
- psutil による優先度/affinity 設定は権限に依存します。実行ユーザーの権限不足時は警告が出てスキップされます。
- monitoring の DB（SQLite）は単一ファイルへの書き込みです。複数プロセスで同時書き込みを行う場面では注意（通常は Monitoring / Execution の役割分担を行う）。
- .env に機密値（API キー・パスワード）を保存する場合はファイル権限に注意してください。

---

## よく使うコマンド（要約）

- 依存インストール（例）
  pip install duckdb psutil requests openai streamlit

- Monitoring 起動
  python -m kabusys.run_monitoring

- Execution 起動
  python -m kabusys.run_execution

- Streamlit ダッシュボード
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper 検証レポート
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

この README はコードベースの主要部分に基づいてまとめたものです。実運用や拡張の際は各モジュール内の docstring や設定チェック（config.py）を参照してください。必要であれば、インストール用の requirements.txt、より詳細な運用手順（systemd / supervisor のユニット例やログ出力設定）も追加で作成できます。