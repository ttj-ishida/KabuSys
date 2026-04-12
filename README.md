# KabuSys

日本株向けの自動売買システム（KabuSys）のコードベース。  
本リポジトリは発注実行（Execution）、監視（Monitoring）、ポートフォリオ構築（Portfolio）、リサーチ（Research）、AI（ニュースNLP / レジーム判定）などの機能を含むモジュール群で構成されています。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 実行方法（使い方）
- 環境変数 / 設定一覧（重要）
- ディレクトリ構成（主要ファイルの説明）
- 補足・運用メモ

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したモジュール式のシステムです。以下の観点を重視して設計されています。

- 本番 / 検証（Paper Trading）を分離して扱える設計
- DuckDB / SQLite を用いたオンメモリ／軽量DB操作
- 監視と自己停止（kill flag）による安全性確保
- LLM（OpenAI）を用いたニュースセンチメントや市場レジーム判定の組み込み（オプション）
- ポートフォリオ構築・サイズ計算・セクター制約などの純粋関数群を提供

---

## 主な機能一覧

- Execution（発注実行）
  - ExecutionEngine / OrderManager / RiskManager / Reconciler 等による発注、リスク管理、再起動時の自動復旧
  - BrokerClientFactory により本番ブローカーと MockBroker（paper_trading 用）を切り替え
- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/ディスク、Execution プロセスの存在、株価データ鮮度を監視
  - TradeMonitor: 滞留注文や約定価格の異常を検出
  - RiskMonitor: ドローダウンやポジション数上限を監視、risk_logs へ記録
  - KillSwitch: 条件を満たした場合、フラグファイルを書いて Execution を停止させる仕組み
  - AlertManager: LINE Messaging API を使って一方向の通知
  - Streamlit ベースの簡易監視ダッシュボード
- Portfolio（ポートフォリオ構築）
  - 候補選定、等重／スコア重み、セクター制約、ポジションサイズ計算（単元株丸め、aggregate cap 対応）
- Research
  - factor_research: Momentum / Volatility / Value 等のファクター計算（DuckDB 上で完結）
  - feature_exploration: 将来リターン計算、IC（スピアマンランク相関）、統計サマリ等
- AI
  - news_nlp: raw_news を集約して OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを算出し ai_scores に書き込み
  - regime_detector: ETF（1321）の MA200 とマクロニュースの LLM センチメントを合成して日次レジーム判定を行う
- ツール
  - Paper Trading 検証レポート出力スクリプト（期間指定可）
  - DB 初期化は run_* スクリプト内で行われる（init_monitoring_db）

---

## セットアップ手順

前提
- Python 3.10 以上（typing の | union などを使用）
- Git リポジトリのルートに .env / .env.local を配置する前提（自動読み込み機能あり）

1. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリのインストール（最小）
   - pip install duckdb psutil openai requests streamlit
   - 実際の運用では requirements.txt を用意している場合はそれを利用してください。

3. データディレクトリ作成
   - mkdir -p data

4. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（詳細は後述）。
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. データベース
   - monitoring 用の SQLite（デフォルト: data/monitoring.db）や DuckDB（デフォルト: data/kabusys.duckdb）は最初の run_* スクリプト実行時に必要なテーブルが自動作成されます（init_monitoring_db）。
   - Paper Trading を使う場合は paper DB（data/paper_trading.db）を利用します（作成は自動）。

---

## 使い方

主要なエントリポイント（いずれもモジュールとして実行可能）:

- 監視ループ（常駐）
  - python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）。1 未満や不正値は無視されデフォルトにフォールバック。
  - 備考:
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用します（監視は本番 DB を見る設計）。
    - 実行開始直後にプロセス優先度を "high" に設定しようとします（psutil を使用、権限がない場合は警告）。

- 実行エンジン（Execution）
  - python -m kabusys.run_execution
  - KABUSYS_ENV により動作が変化:
    - paper_trading: MockBrokerClient を使用し、SQLite は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に接続して本番 DB と分離。
    - live / development: 本番用 DB を使用（設定に依存）
  - 実行時にプロセス優先度を "high" に設定します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - オプション --db で DB パスを指定できます（環境変数 PAPER_TRADING_SQLITE_PATH より優先される）。
  - 指標: 稼働率、注文成功率、送信率、P95 レイテンシ などを算出し PASS/FAIL を判定します。

- Streamlit ダッシュボード（監視）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは monitoring DB を読み取り専用で開きます（?mode=ro）。

- AI 関連（プログラムから呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続（DuckDBPyConnection）を渡し、指定日用のニュースセンチメントを ai_scores に書き込みます。
    - api_key を省略すると環境変数 OPENAI_API_KEY を参照します（未設定だと ValueError）。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 市場レジーム判定を行い market_regime テーブルへ書き込みます。

実行中止 / 停止
- MonitoringEngine や ExecutionEngine は KeyboardInterrupt で安全に停止します。
- KillSwitch は条件を満たすと Settings.kill_flag_path（デフォルト data/kill.flag）へ理由を書き込み、Execution 側がそれを検出して停止する流れを想定しています。

---

## 環境変数 / 設定（主なもの）

設定は kabusys.config.Settings 経由で取得されます。自動的にプロジェクトルートの `.env` / `.env.local` を読み込みます（OS 環境変数が優先。`.env.local` は上書き）。

- KABUSYS_ENV: 起動環境（development / paper_trading / live）。デフォルト: development
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）。デフォルト: INFO
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API 用（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時に必要）
- LINE_CHANNEL_ACCESS_TOKEN: LINE 通知用トークン（AlertManager）
- LINE_USER_ID: LINE 通知先ユーザ ID
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring）パス（デフォルト data/monitoring.db）※Monitoring は常に本番 sqlite を使用
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: Paper Trading の約定モード（instant|partial|never|reject、デフォルト "instant"）
- PID_FILE_PATH: Execution の PID ファイルパス（デフォルト data/execution.pid）
- KILL_FLAG_PATH: Kill flag ファイルパス（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag をクリアするフラグ（"1" で有効）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値（%）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: "1" にすると .env 自動ロードを無効化

.env 例（簡易）
```
KABUSYS_ENV=development
LOG_LEVEL=INFO
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
```

---

## ディレクトリ構成（主要ファイルの説明）

（ルート: src/kabusys 以下を想定）

- src/kabusys/__init__.py
  - パッケージ宣言、__version__ 等

- src/kabusys/config.py
  - 環境変数 / .env の自動読込と Settings クラス（アプリ内での設定取得を一元化）

- src/kabusys/run_monitoring.py
  - SystemMonitor をポーリングするデーモンスクリプト。MONITOR_POLL_INTERVAL を参照

- src/kabusys/run_execution.py
  - ExecutionEngine 起動スクリプト。paper_trading 時は MockBroker を利用し DB を分離

- src/kabusys/monitoring/
  - monitoring_db.py: SQLite のテーブル作成・MonitoringDB ラッパ（system_status, trade_logs, positions, risk_logs, dashboard 等）
  - system_monitor.py: システム・データ鮮度監視
  - trade_monitor.py: 注文滞留・約定異常監視
  - risk_monitor.py: ドローダウン・ポジション数監視
  - kill_switch.py: kill.flag の書き込み・管理
  - alert_manager.py: LINE 通知用
  - monitoring_engine.py: 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py: Streamlit ベースの監視 UI

- src/kabusys/execution/
  - order_manager.py, order_repository.py, execution_engine.py, reconciler.py など
  - 発注、状態遷移、再起動時リコンシリエーションの実装

- src/kabusys/portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
  - 銘柄選定、重み計算、ポジションサイズ、セクター制約、レジーム乗数 等

- src/kabusys/research/
  - factor_research.py: Momentum / Volatility / Value ファクター計算（DuckDB）
  - feature_exploration.py: 将来リターン、IC、統計サマリ等

- src/kabusys/ai/
  - news_nlp.py: raw_news をまとめて OpenAI に投げ、ai_scores を更新
  - regime_detector.py: ETF MA とマクロニュースで市場レジーム判定

- src/kabusys/tools/
  - paper_verification_report.py: Paper Trading の検証レポート生成スクリプト

- src/kabusys/utils/
  - process_priority.py: psutil を用いたプロセス優先度 / CPU affinity 設定ユーティリティ

そのほか、細かなユーティリティや DB マイグレーション処理が含まれます（例: monitoring_db は既存 schema に対する列追加マイグレーションを行います）。

---

## 補足・運用メモ

- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に行われます。配布後やテスト環境で挙動を変えたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。
- Monitoring は「監視」側の DB（monitoring.db）への永続化とアラートに重点を置き、本番の発注 DB とは分離して運用できるよう設計されています。
- run_execution は起動時に Reconciler 等で未確定注文の整合を取る想定です。Paper Trading モードでは本番 DB とは完全に分離された SQLite（PAPER_TRADING_SQLITE_PATH）へ記録します。
- AI（OpenAI）連携は外部サービス依存のため、ネットワークエラーや API の失敗に対してフェイルセーフに設計されています（リトライやスキップ、フォールバック値）。
- プロセス優先度設定・CPU affinity はプラットフォーム差（Windows / POSIX）を吸収するユーティリティを提供しますが、権限不足により設定できない場合は警告でスキップされます。
- LINE 通知は AlertManager がクールダウンをメモリ内で管理します。必要に応じて設定してください。

---

この README はコードベースの主要機能と運用上の注意点をまとめたものです。個別のモジュールや関数の詳細はソース内の docstring とコメントを参照してください。追加のドキュメント（たとえば PortfolioConstruction.md、StrategyModel.md 等）が存在する場合はそちらも参照してください。