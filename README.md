# KabuSys — 日本株自動売買システム（README）

このリポジトリは日本株向け自動売買システム「KabuSys」の一部実装です。
本ドキュメントはコードベース（src/kabusys 以下）をもとに、プロジェクト概要・機能・セットアップ・使い方・ディレクトリ構成を日本語でまとめた README.md です。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（起動・ツール）
- 環境変数（主な設定）
- 内部DB / テーブル
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株自動売買のためのコンポーネント群を提供する Python パッケージです。
- 主要機能:
  - 戦略（ファクター計算、特徴量探索）
  - ポートフォリオ構築（候補選定・重み付け・株数算定・セクター制約）
  - 実運用向け ExecutionEngine（ブローカークライアント経由の発注・リコンシリエーション）
  - 監視/アラート（システム状態、注文滞留、リスク監視）
  - AI 補助（ニュース NLP によるセンチメント集約、レジーム判定）
  - 開発・検証ツール（Paper Trading 検証レポート、Streamlit ダッシュボード等）

主な機能一覧
- execution
  - OrderManager / Reconciler / 発注ロジック（クラッシュ耐性を考慮した状態遷移）
  - BrokerFactory による実口座 / Paper Trading の切り替え
- monitoring
  - SystemMonitor: CPU/メモリ/Disk/データ鮮度/実行プロセスの監視
  - TradeMonitor: 注文滞留・約定異常の検出
  - RiskMonitor: ドローダウン・ポジション上限の監視、kill flag の発行
  - AlertManager: LINE Push による通知（クールダウン管理）
  - MonitoringEngine: 上記を束ねたポーリングエンジン
  - StreamlitDashboard: 監視データの可視化（簡易UI）
- portfolio
  - 候補選定（スコア順）、等金額/スコア加重、リスク制御（セクター上限、レジーム乗数）、ポジションサイズ計算（lot 単位丸め、aggregate cap）
- research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン・IC（情報係数）・統計サマリ
- ai
  - news_nlp: OpenAI を用いたニュースセンチメントの集計 → ai_scores
  - regime_detector: ETF MA とマクロニュースで市場レジーム判定
- tools
  - paper_verification_report: Paper Trading 用検証レポート生成ツール

セットアップ手順（開発環境想定）
1. Python 環境準備（推奨: 3.10+）
   - 仮想環境作成例:
     ```
     python -m venv .venv
     source .venv/bin/activate  # Unix/macOS
     .venv\Scripts\activate     # Windows
     ```
2. 必要なパッケージをインストール
   - 実際の requirements.txt はこの抜粋に含まれていませんが、少なくとも次のパッケージが必要になります:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit (ダッシュボード利用時)
   - インストール例:
     ```
     pip install duckdb psutil requests openai streamlit
     ```
3. プロジェクトルートに .env を用意（下記サンプル参照）
   - 環境変数は .env / .env.local / OS 環境変数の順で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能）。
4. データディレクトリ
   - デフォルトでは data/ 以下に DB や pid/flag ファイルを置きます（存在しない場合は作成してください）。
   - duckdb, sqlite のファイルパスは環境変数で上書きできます（下記参照）。

使い方（主要スクリプト）
- 実行方法（パッケージモード）
  - run_monitoring（監視ループ起動）
    ```
    python -m kabusys.run_monitoring
    ```
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定可能（デフォルト 60 秒）。
    - 監視は本番用 sqlite_path を常に使用します（KABUSYS_ENV に依らない）。

  - run_execution（ExecutionEngine 起動）
    ```
    python -m kabusys.run_execution
    ```
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使用され、データは data/paper_trading.db（または PAPER_TRADING_SQLITE_PATH）に保存され本番 DB と分離されます。

  - Streamlit ダッシュボード（監視 UI）
    - 起動例（README にある起動例をそのまま使用）:
      ```
      streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
      ```
    - read-only URI 接続で DB を開き、Overview / Positions / Orders / System タブを提供します。

  - Paper Trading 検証レポート
    ```
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
    - デフォルト DB: data/paper_trading.db。--db で上書き可能。

主な環境変数（抜粋）
- KABUSYS_ENV: 起動環境 ("development" | "paper_trading" | "live")。デフォルト "development"。
  - paper_trading の場合、Execution は専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用。
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / ai.regime_detector が必要）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（未設定時は送信がスキップされる）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: Paper Trading の約定挙動（"instant" | "partial" | "never" | "reject"、デフォルト "instant"）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH: Kill flag ファイル（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動削除するか（"1" で有効）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視の閾値（%）
- LOG_LEVEL: ログレベル ("DEBUG"/"INFO"/..."CRITICAL")

例: .env のサンプル
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=yyyy
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
MONITOR_POLL_INTERVAL=60
```

内部 DB / テーブル（監視用 SQLite）
- init_monitoring_db(conn) により以下のテーブルが作成されます（冪等）:
  - system_status: cpu/memory/disk/process_ok の時系列ログ
  - trade_logs: 注文イベントログ（latency_ms カラムあり）
  - positions: 保有ポジション（code を主キー）
  - risk_logs: リスク検出イベント
  - dashboard: ダッシュボード集計（id=1 に1行）
- MonitoringDB クラスが DB 読み書きをラップ（log_system_status, log_trade_event, upsert_position, log_risk_event, upsert_dashboard, get_dashboard など）

注意点 / 実運用フロー（抜粋）
- Execution 起動時に PID ファイルを作成し、SystemMonitor が PID 存在をチェックする仕組み。
- RiskMonitor はハイウォーターマーク（peak_value）を内部で保持し、ドローダウン超過時に risk_logs にイベントを記録し kill.flag を作成するフローがある。
- KillSwitch はファイルベースのシグナリング（data/kill.flag）を採用。Execution は起動時や定期チェックでこのフラグを検出して安全に停止することを想定。
- AI モジュール（news_nlp / regime_detector）は OpenAI API を利用。API 失敗時はフェイルセーフ（0.0 など）で処理を継続する設計。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数 / .env 読み込み・Settings
  - run_monitoring.py                — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py                 — ExecutionEngine 起動スクリプト
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュース NLP（OpenAI 呼び出し・バッチ処理）
    - regime_detector.py             — 市場レジーム判定（MA + マクロニュース）
  - monitoring/
    - __init__.py
    - monitoring_db.py               — 監視用 SQLite のスキーマ/ラッパー
    - system_monitor.py              — システム状態チェック / データ鮮度チェック
    - trade_monitor.py               — 注文滞留 / 約定異常検出
    - risk_monitor.py                — ドローダウン・ポジション上限監視
    - kill_switch.py                 — kill.flag の作成 / 管理
    - alert_manager.py               — LINE Push 通知
    - monitoring_engine.py           — MonitoringEngine（各 Monitor を束ねる）
    - streamlit_dashboard.py         — Streamlit による簡易監視ダッシュボード
  - execution/
    - reconciler.py                  — 起動時リコンシリエーション
    - order_manager.py               — 発注の高レベル API / State Machine
    - (その他の execution モジュールはこの抜粋に一部のみ掲載)
  - portfolio/
    - __init__.py
    - portfolio_builder.py           — 候補選定 / 重み計算
    - risk_adjustment.py             — セクターキャップ / レジーム乗数
    - position_sizing.py             — 株数決定・単元丸め・集計上限処理
  - research/
    - __init__.py
    - factor_research.py             — Momentum / Volatility / Value の計算
    - feature_exploration.py         — 将来リターン / IC / 統計
  - tools/
    - __init__.py
    - paper_verification_report.py   — Paper Trading 検証レポート生成ツール
  - utils/
    - __init__.py
    - process_priority.py            — プロセス優先度 / CPU affinity ユーティリティ

開発上の補足
- 多くの関数は DuckDB 接続や sqlite 接続を引数で受け取り、外部副作用を抑えた純粋関数的な実装を意識しています（テスト容易性）。
- OpenAI 呼び出し部分はリトライやエラー時のフォールバックを組み込んでいるため、API の一時障害に対して堅牢に設計されています。
- Paper Trading 用データは本番 DB とは分離されるため（PAPER_TRADING_SQLITE_PATH）、検証で本番データへの影響を防げます。

ライセンス / 貢献
- 本リポジトリのライセンス情報や貢献方法はこの抜粋に含まれていません。実運用や配布の際は LICENSE を付与してください。

---

この README はコードベースの主要な点を要約しています。実際に運用する際は各モジュールの docstring や関数コメント（ソースコード）を参照し、適切なテスト・運用手順（プロセスマネージャー・サービス登録・ログ管理）を整備してください。