# KabuSys

KabuSys は日本株の自動売買システム実装例です。戦略の研究・ファクター計算・ポートフォリオ構築・発注（Execution）・監視（Monitoring）・AI を用いたニュースセンチメント評価などの主要コンポーネントを含みます。本リポジトリは純粋関数的な計算部分と、DB / ブローカー / 外部 API と連携する実行部分を分離して設計されています。

---

## 概要

- 言語: Python
- 目的: 日本株の自動売買システムの各コンポーネント（研究、ポートフォリオ構築、発注、監視、AI 評価）を提供
- 主な依存:
  - duckdb
  - sqlite3（標準）
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード）
  - その他（環境により追加）

重要なエントリポイント:
- 実行エンジン起動: python -m kabusys.run_execution
- 監視ループ起動: python -m kabusys.run_monitoring
- Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report
- 監視ダッシュボード (Streamlit): streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

## 機能一覧

- Execution（発注）
  - Broker クライアントの抽象化（本番 / Paper Trading 切替対応）
  - OrderManager、RiskManager、Reconciler による発注管理、リスク制御、再同期処理
  - Paper Trading 時は mock ブローカーを利用し DB を分離（data/paper_trading.db）

- Monitoring（監視）
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / PID の監視
  - TradeMonitor: 注文滞留（stale order）、約定価格異常の検出
  - RiskMonitor: ドローダウンやポジション上限の監視とログ記録
  - KillSwitch: しきい値を超えた場合にフラグファイルを書き ExecutionEngine 停止を促す
  - AlertManager: LINE Messaging API を使った通知（クールダウン管理）
  - Streamlit ダッシュボード（リアルタイム参照）

- Research / Data
  - factor_research: モメンタム、ボラティリティ、バリュー等のファクター計算（DuckDB を利用）
  - feature_exploration: 将来リターン計算、IC（Information Coefficient）、統計サマリー

- Portfolio（ポートフォリオ構築）
  - 候補選定、等金額・スコア加重配分
  - セクター集中制限、レジーム乗数
  - ポジションサイジング（単元株丸め、リスクベース配分、aggregate cap）

- AI
  - news_nlp: OpenAI（gpt-4o-mini）でニュース記事を銘柄ごとにセンチメント評価して ai_scores に保存
  - regime_detector: ETF とマクロニュース（LLM）を合成して日次レジーム（bull/neutral/bear）を判定

- ユーティリティ
  - Settings: 環境変数 / .env の読み込み・管理
  - process_priority: プロセス優先度・CPU affinity 設定ユーティリティ
  - tools: Paper Trading 検証レポート生成スクリプトなど

---

## セットアップ手順

1. Python 環境の準備
   - Python 3.9+ を推奨（duckdb / openai 等のサポートに合わせて調整）
   - 仮想環境を作成・有効化:
     - python -m venv .venv
     - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージのインストール
   - 例:
     - pip install duckdb psutil requests openai streamlit

   （プロジェクトに requirements.txt があればそれを使ってください。）

3. プロジェクトルートの .env を作成（自動ロード機能あり）
   - Settings モジュールはプロジェクトルート（.git または pyproject.toml を基準）から .env / .env.local を自動読み込みします。
   - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. 推奨される環境変数（例）
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - OPENAI_API_KEY=...
   - KABUSYS_ENV=development | paper_trading | live
     - paper_trading にすると MockBroker を使い DB は data/paper_trading.db に切り替わります
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   - PID_FILE_PATH=data/execution.pid
   - KILL_FLAG_PATH=data/kill.flag
   - PAPER_FILL_MODE=instant | partial | never | reject
   - MONITOR_POLL_INTERVAL=60  （run_monitoring 用のポーリング間隔、秒）

5. データディレクトリを作成
   - mkdir -p data

注意:
- OpenAI を使う機能（news_nlp, regime_detector）は OPENAI_API_KEY が必要です。
- process_priority の設定は管理者権限が必要な場合があります。失敗すると警告を出してスキップします。

---

## 使い方

- 実行エンジン（ExecutionEngine）を起動する
  - 本番（デフォルト）:
    - python -m kabusys.run_execution
  - Paper Trading:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - Paper Trading の DB は settings.paper_sqlite_path（デフォルト: data/paper_trading.db）に記録されます

- 監視ループを起動する
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書きできます（デフォルト 60）。1 未満や不正値はデフォルトにフォールバックします。
  - 監視は Settings で指定された sqlite_path を使用します（環境に依存せず本番 sqlite_path を参照する設計）。

- Paper Trading 検証レポートを生成する
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または DB を明示的に指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- 監視ダッシュボード（Streamlit）を起動する
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を read-only モードで開いてダッシュボード表示します（MonitoringEngine が先に起動していることを推奨）。

- AI 機能の利用
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼ぶ際には OpenAI API key を設定してください。関数引数にも API キーを渡せます。

ログ・プロセス関連:
- 起動時にプロセス優先度を "high" に変更しようとします（権限がない場合は警告でスキップ）。
- ExecutionEngine は pid ファイル（デフォルト data/execution.pid）を操作します。Monitoring はこの PID を参照してプロセス稼働チェックを行います。
- KillSwitch は settings.kill_flag_path（デフォルト data/kill.flag）に理由文字列を書き込むことで ExecutionEngine 停止を促します。ExecutionEngine はこのフラグの存在をチェックして終了処理を行う設計になっています。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
  - 環境変数と .env の読み込み / Settings クラス
- run_execution.py
  - ExecutionEngine 起動スクリプト（KABUSYS_ENV=paper_trading に対応）
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔変更可）
- data/  (出力先の例: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db)

サブパッケージ:
- ai/
  - news_nlp.py           — ニュースセンチメント評価（OpenAI）
  - regime_detector.py    — 市場レジーム判定（ETF + マクロニュース）
- monitoring/
  - monitoring_db.py      — SQLite テーブルの初期化と永続化ユーティリティ
  - system_monitor.py     — システム状態・データ鮮度監視
  - trade_monitor.py      — 注文滞留・約定異常監視
  - risk_monitor.py       — ドローダウン・ポジション上限監視
  - kill_switch.py        — kill.flag 書き込みユーティリティ
  - alert_manager.py      — LINE への通知機能
  - monitoring_engine.py  — 複数モニタをまとめるエンジン
  - streamlit_dashboard.py— Streamlit ダッシュボード
- execution/
  - reconciler.py         — 起動時の注文/ポジション再同期
  - order_manager.py      — 発注ワークフロー（状態遷移）
  - （その他：broker_factory, order_repository, execution_engine, risk_manager 等は実装の一部）
- portfolio/
  - portfolio_builder.py  — 候補選定 / 重み計算
  - risk_adjustment.py    — セクターキャップ / レジーム乗数
  - position_sizing.py    — 発注株数計算（単元丸め / aggregate cap）
- research/
  - factor_research.py    — Momentum/Volatility/Value 等のファクター計算（DuckDB）
  - feature_exploration.py— 将来リターン / IC / 統計サマリー
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
- utils/
  - process_priority.py   — プロセス優先度 / CPU affinity ユーティリティ

ドキュメント参照:
- 各モジュールの docstring に設計方針、アルゴリズム、注意点が記載されています。特に portfolio と research モジュールは数理的な前提と外部参照（PortfolioConstruction.md, StrategyModel.md）に基づいています（別ドキュメント参照を想定）。

---

## 知っておくべき実装上の注意点 / トラブルシューティング

- Settings はプロジェクトルートの .env を自動ロードします。CI などで自動ロードを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_monitoring は常に「本番用の」sqlite_path を使用して監視ログを書きます（KABUSYS_ENV に依存しません）。Paper Trading と監視データは分離したい場合は設定を調整してください。
- MONITOR_POLL_INTERVAL に 0 や負の値、文字列などを設定すると警告が出て 60 秒にフォールバックします。
- OpenAI 呼び出しはネットワーク・レート制限等を考慮してリトライ・バックオフ実装が入っていますが、API キーが未設定だと例外となるので注意してください。
- プロセス優先度や CPU affinity の設定は OS に依存し、権限不足で設定できない場合があります（警告で継続）。

---

必要であれば、導入手順を自動化するための requirements.txt、簡易の docker-compose や systemd ユニット例、あるいはテスト実行手順（ユニットテスト・モックの使用方法）も追加で作成できます。どの追加情報が必要か教えてください。