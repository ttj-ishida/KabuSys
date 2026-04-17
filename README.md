# KabuSys

KabuSys は日本株向けの自動売買システムのモジュール群です。取引実行（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI（ニュース NLP / レジーム判定）などの主要機能を持ち、ローカル SQLite / DuckDB を用いてデータを永続化します。

以下はこのリポジトリの README です。

---

## プロジェクト概要

- 自動売買実行エンジン（ExecutionEngine）と発注管理（OrderManager / OrderRepository / Reconciler）
- 監視コンポーネント（SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine）
- ポートフォリオ構築ユーティリティ（候補選定・重み付け・ポジションサイズ計算・リスク調整）
- リサーチ用ファクター計算（momentum, volatility, value）と特徴量解析ユーティリティ
- AI モジュール（ニュースのセンチメント評価、マクロレジーム判定） — OpenAI を利用
- 運用ツール（Paper Trading 検証レポート生成、Streamlit ダッシュボード）
- プロセス優先度・CPU affinity 設定などユーティリティ群

設計指針としては「本番 DB と paper_trading の分離」「ルックアヘッドバイアス排除」「LLM 呼び出しのフェイルセーフ」「簡潔な永続化（SQLite/DuckDB）」などが採用されています。

---

## 主な機能一覧

- Execution
  - 発注の作成・送信・状態同期（OrderManager）
  - ブローカー同期と再起動時のリコンシリエーション（Reconciler）
  - Paper Trading モード（MockBroker を利用し本番 DB と分離）
- Monitoring
  - システムリソース監視（CPU / メモリ / ディスク）
  - データ鮮度監視（DuckDB の最終価格日付）
  - 注文滞留チェック・約定価格異常検出
  - ドローダウン・ポジション数監視（KillSwitch による停止指示）
  - LINE 通知（AlertManager）
  - Streamlit ベースの監視ダッシュボード
- Portfolio
  - 候補選定（score / rank ベース）
  - 等金額・スコア加重配分
  - リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（ロット丸め、aggregate cap）
- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB クエリベース）
  - 将来リターン、IC（Information Coefficient）、統計サマリー
- AI
  - ニュースセンチメント（OpenAI）→ ai_scores テーブル書込
  - マクロニュース + ETF MA200 を用いたレジーム判定（market_regime テーブル）
- Tools
  - paper_verification_report: Paper Trading の検証レポート生成（コマンドラインツール）
  - streamlit_dashboard: 監視ダッシュボード（Streamlit）

---

## セットアップ手順

前提:
- Python 3.9+（コードは型ヒント等を利用しています。お使いの環境に合わせて調整してください）
- Git レポジトリをクローン済み

推奨的なセットアップ手順:

1. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate   (Unix/macOS) / .venv\Scripts\activate (Windows)

2. 必要パッケージをインストール
   - 依存ライブラリ（主要なもの）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit (ダッシュボード利用時)
   - 例:
     - pip install duckdb psutil requests openai streamlit

   （開発用の extras や固定バージョンが別途ある場合は pyproject / requirements を参照してください）

3. データディレクトリの準備
   - data ディレクトリを作成:
     - mkdir -p data
   - 初回は監視 DB 等が存在しないため、run_monitoring / run_execution 実行時に自動作成されます。
   - 必要に応じて空のファイル stop_requested.flag や kill.flag は作らないでください（停止用フラグ）。

4. 環境変数の設定
   - 簡単にはプロジェクトルートに `.env` または `.env.local` を作成して設定できます。
   - 自動読み込みはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）。
   - 主要な環境変数の例（.env）:
     - KABUSYS_ENV=development         # development | paper_trading | live
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - MONITOR_POLL_INTERVAL=60

5. DB 初期化（任意）
   - run_monitoring または run_execution を実行すると monitoring DB のテーブルが自動で作成されます（init_monitoring_db）。

---

## 使い方

### 実行エンジン（ExecutionEngine）の起動

- 本番 / 開発 / Paper Trading の切り替えは KABUSYS_ENV で行います。

例: Paper Trading（MockBroker を使用、paper DB に記録）
- KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- または（環境をエクスポートして）:
  - export KABUSYS_ENV=paper_trading
  - python src/kabusys/run_execution.py

- 停止方法:
  - run_execution はプロジェクトの data/stop_requested.flag を監視しています。停止したい場合は stop_requested.flag を作成すると起動スレッドが検知して安全に停止します（file path: <project_root>/data/stop_requested.flag）。
  - KillSwitch が条件を満たすと data/kill.flag を書き込み、Engine 側が検出して停止します（KillSwitch は監視側で評価されます）。

### 監視ループの起動

- python -m kabusys.run_monitoring
- オプション:
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書きできます（デフォルト 60 秒）。
    - export MONITOR_POLL_INTERVAL=30

- run_monitoring は常に本番の sqlite_path（Settings.sqlite_path）を使用して monitoring DB を操作します（監視は本番 DB を参照します）。

### Streamlit ダッシュボード

- 起動例:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- ダッシュボードからは positions / recent orders / system status / risk logs / dashboard summary を確認できます（read-only で DB に接続します）。

### Paper Trading 検証レポート

- コマンド:
  - python -m kabusys.tools.paper_verification_report
  - 指定期間:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

出力: 稼働率 / 注文成功率 / 送信率 / レイテンシ（P95）などをまとめたレポートを標準出力に表示します。

### AI モジュール（OpenAI 利用）

- NEWS NLP（kabusys.ai.news_nlp.score_news）と regime_detector.score_regime は OpenAI API キーを要求します。
  - API キーは引数で渡すか、環境変数 OPENAI_API_KEY に設定してください。
- 大量呼び出し時はレート制限やネットワークエラーをバックオフして再試行する実装が含まれます。

---

## 主要な環境変数

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒）
- OPENAI_API_KEY: OpenAI API キー（AI 機能に必須）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- PAPER_FILL_MODE: paper_trading の約定モデル（instant|partial|never|reject、デフォルト instant）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite パス（デフォルト data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（monitoring.db、デフォルト data/monitoring.db）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH: KillSwitch が書き込むフラグファイルパス（デフォルト data/kill.flag）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

---

## ディレクトリ構成

（プロジェクトの src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数・設定の読み込みと Settings クラス
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート CLI
  - execution/
    - order_manager.py
    - order_repository.py
    - execution_engine.py
    - broker_factory.py
    - reconciler.py
    - ...（order_record, broker_api など）
  - monitoring/
    - monitoring_db.py        — SQLite スキーマと簡易永続化 API
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
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - data/                     — 実行時に利用されるデータディレクトリ（例: DB ファイル、flag ファイル）
  - utils/
    - process_priority.py      — プロセス優先度・CPU affinity 設定ユーティリティ
    - __init__.py

---

## 運用上の注意 / 補足

- Paper Trading は本番 DB と物理的に分離されるように設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- 監視プロセスは本番 monitoring DB を参照するため、適切なパスと権限を確認してください。
- KillSwitch により自動で停止フラグ（kill.flag）を書き込むと ExecutionEngine の停止トリガーになります。manual 停止は stop_requested.flag を作成する方法が使われます。
- OpenAI を利用する機能は外部 API 呼び出しが伴うため、API キー管理とコストに注意してください。
- process priority / CPU affinity の設定は psutil を使います。権限不足や OS 非対応時は警告ログが出て処理は継続します。
- DuckDB のクエリはリサーチ・AI でパフォーマンス要件が高くなる場合があるため、適切なマシンリソースで実行してください。

---

この README はコードベースの主要点をまとめたものです。実運用や拡張を行う際は各モジュールのドキュメント（モジュール内 docstring）や設定ファイル（.env.example）を参照し、必要に応じて追加の安全策・監査・テストを導入してください。