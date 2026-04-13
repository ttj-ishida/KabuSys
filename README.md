# KabuSys

KabuSys は日本株向けの自動売買システム用ライブラリ／サービス群です。本リポジトリは以下の主要機能を提供します:

- 注文発行・状態管理を行う ExecutionEngine（ブローカー抽象化、リスク管理、再同期機能）
- システム稼働性・注文異常・リスク監視を行う Monitoring コンポーネント（ログ永続化、アラート、kill-switch）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ算出、セクター上限等）
- 研究用モジュール（ファクター計算、将来リターン、IC 計算、統計サマリー）
- AI 補助: ニュースを LLM でセンチメント評価して ai_scores へ格納、レジーム判定（MA とマクロセンチメントの混合）
- 運用支援ツール: Paper Trading 検証レポート生成、Streamlit ベースの監視ダッシュボード
- 小物ユーティリティ（プロセス優先度設定、設定管理、DB マイグレーション等）

以下は開発者／運用者向けの README です。

## 主な機能一覧

- Execution
  - 注文作成 → 送信 → 同期（Reconciler）を扱う OrderManager / ExecutionEngine
  - リスク管理（ポジション上限、ドローダウン等）を行う RiskManager
  - Paper Trading モード（モックブローカー、専用 SQLite を使用）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、Execution プロセスの存否、株価データ鮮度をチェック
  - TradeMonitor: 滞留注文、約定価格異常を検出
  - RiskMonitor: ドローダウン、ポジション上限をチェックしリスクログを記録
  - AlertManager: LINE による通知（トークン設定時）
  - KillSwitch: 条件によりデータ/ファイル経由で ExecutionEngine 停止指示
  - MonitoringEngine: 上記モジュールを束ねたポーリングループ
  - Streamlit ダッシュボードで状況可視化
- Portfolio
  - 候補選定、等重・スコア重み、リスクベースのポジションサイズ算出、セクター制限、レジーム乗数
- Research
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（Spearman）や統計サマリー
- AI
  - news_nlp: raw_news を集約して OpenAI（gpt-4o-mini）でセンチメント評価 → ai_scores へ書込
  - regime_detector: ETF（1321）MA とマクロ記事センチメントを合成して market_regime に書込
- Tools
  - paper_verification_report: Paper Trading の DB を解析して PASS/FAIL レポートを標準出力
  - streamlit_dashboard: 監視 DB を可視化する UI

## 動作前提 / 必要条件

- Python 3.10 以上（型注釈に `X | Y` を多用しているため）
- 環境に応じたパッケージ（以下は代表的なもの）
  - duckdb
  - psutil
  - requests
  - streamlit
  - openai
  - sqlite3（標準ライブラリ）
- OS: Linux / macOS / Windows いずれでも動作するような配慮あり（ただし process priority / cpu affinity の挙動はプラットフォーム依存）

推奨: 仮想環境（venv / virtualenv / pyenv）を使用してください。

例:
- python -m venv .venv
- source .venv/bin/activate
- pip install -r requirements.txt
（requirements.txt はリポジトリにあれば利用、無ければ上記パッケージを個別インストール）

## 環境変数 / 設定（Settings）

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から読み込まれます（OS 環境変数が優先）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数（代表）:

- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API 用（必須）
- OPENAI_API_KEY: OpenAI 呼び出しに必要（AI 機能使用時）
- KABUSYS_ENV: 実行環境（`development` / `paper_trading` / `live`）
  - paper_trading の場合、MockBrokerClient を使用し DB は `PAPER_TRADING_SQLITE_PATH` へ分離されます
- PAPER_FILL_MODE: paper_trading 時の約定モード（`instant` / `partial` / `never` / `reject`）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: Monitoring ポーリング間隔（秒、デフォルト 60） — run_monitoring で参照
- LOG_LEVEL: `DEBUG`/`INFO`... 等

Settings クラスは `kabusys.config.Settings` でラップされています。アプリケーション起動時に値検証（列挙チェック等）を行います。

## セットアップ手順（簡易）

1. リポジトリをチェックアウトして仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate

2. 必要パッケージをインストール
   - pip install duckdb psutil requests streamlit openai

   （プロジェクトで requirements.txt を用意している場合はそれを利用）

3. `.env` を作成（例）
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - OPENAI_API_KEY=...
   - KABUSYS_ENV=development
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

4. data ディレクトリを作成
   - mkdir -p data

5. DuckDB / SQLite 初期化
   - 実行ファイル（Execution / Monitoring）を起動すると必要なテーブルやファイルが自動作成されます（init_monitoring_db 等で冪等に作成）。

## 使い方（主要コマンド）

- ExecutionEngine 起動（本番 / paper_trading 切替）
  - 本番（live）例:
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - Paper Trading 例（ローカル検証）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - Paper Trading は MockBrokerClient を使い、デフォルトで data/paper_trading.db を使用します。

- Monitoring（ポーリングループ）起動
  - python -m kabusys.run_monitoring
  - 環境変数 `MONITOR_POLL_INTERVAL` で秒数を上書きできます（例: MONITOR_POLL_INTERVAL=30）
  - 監視は sqlite の monitoring DB（Settings.sqlite_path）へ永続化します。Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用します。

- Streamlit ダッシュボード（監視 UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間を指定する例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを直接指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 関連（関数呼び出し）
  - ニューススコアリング: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続（kabusys.config.Settings.duckdb_path を開く）を渡して使います。API キーが未設定の場合は ValueError が発生します。

## 監視 DB（monitoring.db）について

- 監視用 SQLite は `kabusys.monitoring.monitoring_db.init_monitoring_db` によって次のテーブルを作成・マイグレーションします:
  - system_status (cpu/memory/disk/process_ok)
  - trade_logs (発注ログ、latency_ms カラム含む)
  - positions (現在ポジション)
  - risk_logs (リスクイベント)
  - dashboard (集計、id=1 の単一行)

- MonitoringDB クラス（kabusys.monitoring.monitoring_db.MonitoringDB）を通じてログ書き込み／upsert が行われます。

## 実装上の注意／運用ノウハウ

- KABUSYS_ENV:
  - development: 開発用（外部ブローカーを使う設定も可能）
  - paper_trading: 発注はモック。DB は paper_sqlite_path で分離される（安全な検証用）
  - live: 本番

- Paper Trading の挙動:
  - PAPER_FILL_MODE により約定挙動を制御（instant / partial / never / reject）

- プロセス優先度:
  - 起動スクリプトは最初に `set_process_priority("high")` を呼び出します。OS により挙動・権限が異なります（権限不足時は警告ログでスキップ）。

- Kill Switch:
  - RiskMonitor が条件を満たした場合、KillSwitch が `data/kill.flag` を書き、ExecutionEngine に停止指示を与える設計です。ExecutionEngine 側はこのフラグを検出して安全に停止する実装が前提です。

- LLM（OpenAI）周り:
  - rate-limit / 5xx / タイムアウトなどに対して指数バックオフでリトライします。API キーは OPENAI_API_KEY または関数引数で渡してください。
  - 出力は JSON を期待して厳密にパース・検証します。パースに失敗した場合は安全にスキップ（フェイルセーフ）されます。

## ディレクトリ構成（抜粋）

以下はソースツリー（src/kabusys 配下）の主要ファイル・ディレクトリと概要です。

- src/kabusys/
  - __init__.py                              — パッケージ定義、バージョン
  - config.py                                — 環境変数 / 設定読み込み（Settings）
  - run_execution.py                         — ExecutionEngine 起動スクリプト
  - run_monitoring.py                        — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py           — Paper Trading 検証レポート CLI
  - utils/
    - __init__.py
    - process_priority.py                    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py                       — monitoring DB 層（初期化・CRUD）
    - system_monitor.py                      — システム状態・データ鮮度監視
    - trade_monitor.py                       — 注文滞留・約定異常監視
    - risk_monitor.py                        — ドローダウン・ポジション上限監視
    - kill_switch.py                         — kill.flag 制御
    - alert_manager.py                       — LINE 通知ラッパー
    - monitoring_engine.py                   — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py                 — Streamlit ダッシュボード
  - execution/
    - order_manager.py                       — 注文の状態遷移 API
    - reconciler.py                          — 起動時の復旧・突合せ処理
    - (その他: broker_factory, order_repository, order_record, execution_engine 等)
  - portfolio/
    - portfolio_builder.py                   — 候補選定・重み付け
    - position_sizing.py                     — 発注株数計算・上限チェック
    - risk_adjustment.py                     — セクター制限・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py                     — ファクター計算（momentum/value/vol）
    - feature_exploration.py                  — 将来リターン・IC・統計サマリー
    - __init__.py
  - ai/
    - news_nlp.py                            — ニュースセンチメント集約/LLM 呼び出し
    - regime_detector.py                     — 市場レジーム判定（MA + マクロセンチメント）
    - __init__.py

（上記は主要ファイルの抜粋です。実運用では execution 下に broker 実装や engine 実装等が含まれます）

## 追加情報 / 参考

- データベース（DuckDB / SQLite）スキーマやマイグレーションは各モジュール内にコメントとして記載されています。monitoring_db.init_monitoring_db は冪等にテーブルやカラムを作成／追加します。
- LLM 呼び出し箇所は外部 API に依存するため、テスト時は API 呼び出し関数（_call_openai_api 等）をモックすることを推奨します。
- Production での実行は適切なプロセス管理（systemd/pm2/サービス化）とログの集約を行ってください。プロセス優先度や PID ファイルを利用する設計になっています。

---

不明点や README に追加してほしい内容があれば教えてください（例: 各モジュールの API ドキュメント、requirements.txt の候補、デプロイ手順のテンプレート等）。