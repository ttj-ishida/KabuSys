# KabuSys

日本株向け自動売買システムのコードベースです。ここに含まれるモジュール群は、注文発行・約定管理・モニタリング・ポートフォリオ構築・ファクター研究・AI ニュース解析などの機能を提供します。

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（起動例・コマンド）
- 環境変数（主な設定項目）
- 停止・キルフラグについて
- ディレクトリ構成（主要ファイル説明）

---

## プロジェクト概要

KabuSys は以下の目的で設計されたモジュール群です。

- シグナル → 注文 → 約定 のライフサイクル管理（ExecutionEngine / OrderManager 等）
- 注文・約定・ポジションの永続化（SQLite）
- システム稼働監視およびリスク監視（Monitoring）
- ポートフォリオ構築、ポジションサイズ計算（portfolio パッケージ）
- ファクター計算・研究（research パッケージ、DuckDB を使用）
- ニュースを LLM で解析して銘柄別スコア化（ai.news_nlp / ai.regime_detector）
- Paper Trading 環境の検証・レポート生成ツール

設計方針として、外部副作用を抑えた純粋関数群（ポートフォリオ系や研究系）と、DB / API 等との結合ロジックを分離しています。また、ルックアヘッドバイアス防止のため日付参照に注意した実装がされています。

---

## 主な機能一覧

- Execution
  - OrderManager / ExecutionEngine / Reconciler による発注および再同期処理
  - paper_trading 環境での MockBroker サポート（本番 DB と分離）
- Monitoring
  - SystemMonitor: CPU/Mem/Disk / データ鮮度 / 実行プロセス監視
  - TradeMonitor: 滞留注文・約定異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視（kill スイッチ連動）
  - AlertManager: LINE を使った通知（任意）
  - Streamlit ダッシュボードで監視状況を可視化
- Portfolio
  - 候補抽出、重み計算（等重・スコア加重）
  - セクター制約、レジーム乗数、ポジションサイズ計算（単元株丸め・利用可能現金考慮）
- Research
  - Momentum / Volatility / Value のファクター計算（DuckDB）
  - 将来リターン・IC（Information Coefficient）計算・統計サマリ
- AI
  - ニュースの LLM ベースセンチメントスコア化（OpenAI）
  - マクロ + ETF MA による市場レジーム判定（LLM と価格情報の合成）
- Tools
  - Paper Trading 検証レポート生成ツール（kabusys.tools.paper_verification_report）

---

## セットアップ手順

基本的には Python 環境（3.9+ 推奨）で動作します。以下は最小セットアップ例です。

1. リポジトリをクローン／展開
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要ライブラリをインストール（例）
   - pip install duckdb psutil requests openai streamlit
   - （実際のプロジェクトでは requirements.txt を用意している場合はそれを使用してください）

4. 環境変数（.env）を用意
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（既存 OS 環境変数を上書きしない）。
   - 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

デフォルトで利用するデータパス
- SQLite (monitoring): data/monitoring.db
- SQLite (paper trading): data/paper_trading.db
- DuckDB: data/kabusys.duckdb
- PID・フラグ: data/execution.pid, data/stop_requested.flag, data/kill.flag

（data ディレクトリは必要に応じて作成されます）

---

## 使い方

以下は主要な実行方法・コマンド例です。いずれもプロジェクトルートから実行します。

- 監視ループを起動（SystemMonitor を単独でポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数: MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可（デフォルト 60 秒）。
  - 監視は Settings.sqlite_path（本番用 path）を常に使用します（KABUSYS_ENV に依らず）。

- Execution Engine（注文実行エンジン）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を指定すると MockBrokerClient を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）へ記録します。

- Streamlit ダッシュボード（監視画面）を起動
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - --db /path/to/paper_trading.db
  - レポートは稼働率・注文成功率・送信率・レイテンシ等を計算します。

- AI 機能（プログラム的利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーは引数で渡すか環境変数 OPENAI_API_KEY を設定してください。

注意事項
- run_monitoring は Monitoring 用 DB（Settings.sqlite_path）に対して init_monitoring_db() を呼び出してテーブル作成・マイグレーションを行います。
- run_execution は paper_trading モード時に本番 DB と分離して paper_trading_db を使用します。

---

## 環境変数（主なもの）

Settings クラスで定義された主要な環境変数例とデフォルト:

- KABUSYS_ENV: 起動環境（development | paper_trading | live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabus API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（AlertManager）
- DUCKDB_PATH: DuckDB のパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: Paper Trading における約定モード（instant|partial|never|reject。デフォルト: instant）
- PID_FILE_PATH: 実行エンジンの PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag をクリアするか（"1" で有効）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60）

.env ファイルの自動読み込みについて
- プロジェクトルート（.git または pyproject.toml を基準）にある .env / .env.local を自動読み込みします。
- OS 環境変数を保護するため、.env の値は既存の OS 環境変数を上書きしません（.env.local は override=True として上書き可能）。
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## 停止・キルフラグについて

- 手動停止フラグ（実行と監視の単純停止）
  - data/stop_requested.flag を作成すると、run_monitoring / run_execution のループが停止シグナルとして検出して終了します。
  - これは運用者が手動で停止を要求するためのフラグです。

- Kill Switch（監視により自動的に停止要求を出す）
  - KillSwitch (kabusys.monitoring.kill_switch) は KABUSYS のリスク検知（例: ドローダウン超過、ポジション上限超過）により `Settings.kill_flag_path`（デフォルト data/kill.flag）へ理由を書き込みます。
  - kill.flag は冪等に書き込まれ、存在していれば is_flagged() が True になります。
  - ExecutionEngine 側では起動時や監視ロジックでこのフラグを参照して停止を行う設計になっています（実行ループ / PID ファイルの監視等を通じて）。
  - kill.flag は KillSwitch.clear() で削除できます（エンジン起動前のクリーンアップ等に利用）。

---

## DB スキーマ（監視 DB の概要）

init_monitoring_db() によって以下のテーブル等が作成されます（主な列のみ抜粋）:

- system_status
  - recorded_at, cpu_percent, memory_percent, disk_percent, process_ok
- trade_logs
  - logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms
- positions
  - code (PK), qty, avg_price, current_price, updated_at
- risk_logs
  - logged_at, event_type, metric_name, metric_value, threshold, detail
- dashboard
  - id=1 固定行: updated_at, portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value

マイグレーションも一部おこないます（例: peak_value / latency_ms カラムの追加など）。

---

## ディレクトリ構成（主なファイル）

以下は src/kabusys 以下の主要モジュールとその役割です。

- kabusys/
  - __init__.py — パッケージ定義・バージョン
  - config.py — 環境変数 / Settings 管理（.env 自動ロードロジック含む）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成ツール（CLI）
  - monitoring/
    - monitoring_db.py — monitoring DB の初期化・読み書きラッパー（MonitoringDB）
    - system_monitor.py — システム状態 / データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の作成 / 管理
    - alert_manager.py — LINE 通知
    - monitoring_engine.py — 各 Monitor を束ねる実行エンジン
    - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
  - execution/
    - order_manager.py — OrderManager（状態遷移・作成・同期）
    - reconciler.py — 起動時の再同期・ポジション照合
    - （その他 broker / order_repository / engine 等は Execution の中に存在）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・ロット丸め・利用可能資金のスケール調整
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリ等
  - ai/
    - news_nlp.py — raw_news を LLM でスコア化して ai_scores に書き込む
    - regime_detector.py — ETF MA + マクロ記事 LLM による市場レジーム判定
  - utils/
    - process_priority.py — プラットフォーム差分を吸収したプロセス優先度設定ユーティリティ

（上記は主要ファイルの抜粋です。実装はさらに多くのモジュールに分かれています。）

---

## 運用上の注意

- 重要な環境変数（API キー等）は .env.example を参考に安全に保管してください。
- Paper Trading モードは本番 DB と分離されますが、運用時は path を必ず確認してください。
- OpenAI 呼び出しはレート制限やネットワークエラーに備えてリトライ処理が入っているものの、API キー漏洩やコストには注意してください。
- monitoring 系は長時間稼働を想定しており、ログや disk 使用量に注意してください。
- process priority / cpu affinity の設定はプラットフォーム依存で権限不足によりスキップされる場合があります（ログに警告が出ます）。

---

この README はコードベースの主要な使い方と構成をまとめたものです。実装の詳細（API、クラス仕様、追加の CLI オプション等）は各モジュールのドキュメント文字列とソースコードをご参照ください。必要であれば .env.example の雛形や requirements.txt の作成、運用手順書（systemd ユニット例など）も追記できます。希望があれば追加で作成します。