# KabuSys

日本株自動売買システムのライブラリ / 実行スクリプト群（抜粋）。  
このリポジトリはシグナル生成、ポートフォリオ構築、発注エンジン、監視・アラート、研究・検証ツール、AI を用いたニュース分析などを含む設計になっています。以下はこのコードベースで提供されている主要な機能と使い方のまとめです。

> 注意: この README は src/kabusys 配下のコードを元に作成しています。実行時には Python パッケージとしてインストールあるいはソースルートから実行してください（例: `python -m kabusys.run_execution`）。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムのコンポーネント群です。主な責務は次の通りです。

- 市場データ（DuckDB）を用いたファクター計算・リサーチ
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ算出）
- ExecutionEngine（発注）および Order 管理（ペーパートレードと本番分離をサポート）
- 監視（System / Trade / Risk）とアラート（LINE）・Kill Switch
- AI（OpenAI）を使ったニュース NLP（銘柄別センチメント）や市場レジーム判定
- 運用支援ツール（.env ウィザード、設定検証、Paper Trading レポート生成）

設計上の要点:

- 設定は .env または環境変数で提供（Settings クラスで管理）
- Paper Trading（`KABUSYS_ENV=paper_trading`）は本番 DB と分離（別 SQLite）
- DuckDB は分析用データ格納、SQLite（monitoring.db / paper_trading.db）は運用ログ・監視用
- 実行スクリプトはプロセス優先度を上げるなどの運用配慮をしている

---

## 機能一覧

- 設定管理
  - .env 自動ロード、Settings クラス（必須/任意の環境変数取得）
  - 対話式 .env 作成ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）

- 実行（entry points）
  - run_execution: ExecutionEngine を起動（paper_trading 時は MockBroker を使用し専用 DB に記録）
  - run_monitoring: SystemMonitor をポーリングして監視ログを記録

- 監視（monitoring）
  - SystemMonitor: CPU / メモリ / ディスク / プロセス PID / データ鮮度をチェック
  - TradeMonitor: 滞留注文・約定価格の異常（リスクイベントログ化）
  - RiskMonitor: ドローダウン監視・ポジション上限監視
  - MonitoringEngine: 上記モニタを束ねて定期実行、KillSwitch 判定、AlertManager 経由で通知
  - MonitoringDB: SQLite を使った永続化レイヤ（system_status, trade_logs, positions, risk_logs, dashboard）

- ポートフォリオ計算（portfolio）
  - 候補選定、等金額/スコア加重の重み計算
  - セクター集中制限（apply_sector_cap）
  - レジーム乗数計算（calc_regime_multiplier）
  - 発注株数計算（position sizing, lot 単位・リスクベース・aggregate cap 等）

- 研究（research）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（スピアマン）計算、因子サマリー

- AI（ai）
  - news_nlp.score_news: raw_news から銘柄ごとのセンチメントを OpenAI（gpt-4o-mini）に問い合わせ、ai_scores に書き込み
  - regime_detector.score_regime: ETF MA200 乖離とマクロニュースの LLM 評価を合成して日次レジーム判定（market_regime へ書込み）

- ツール
  - tools.paper_verification_report: Paper Trading DB を解析して稼働率/注文成功率/レイテンシ等の検証レポートを生成

---

## セットアップ手順

1. Python 仮想環境を作成・有効化（推奨）
   - python3 -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール  
   本リポジトリに requirements.txt がある想定で:
   - pip install -r requirements.txt

   主要な依存:
   - duckdb
   - psutil
   - openai（AI 機能を使う場合）
   - requests（LINE 通知）
   - PyYAML（設定ファイル検証時にあると便利）

   ※ 依存ファイルがない場合は、実行時に ImportError が出ます。必要に応じて上記パッケージを個別にインストールしてください。

3. .env の初期作成（推奨: ウィザードを利用）
   - python -m kabusys.config_setup
   ウィザードに従い J-Quants トークンや kabu API パスワード、DB パスなどを設定します。

   もしくは手動でプロジェクトルートに .env を作成してください（下にテンプレ例あり）。

4. 設定検証
   - python -m kabusys.validate_config
   - 厳密モード（警告を失敗にする）: python -m kabusys.validate_config --strict

5. DB の初期化
   - 実行スクリプト（run_monitoring / run_execution）が起動時に必要テーブルを作成します（MonitoringDB の init_monitoring_db が冪等作成）。

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要（デフォルト有り/任意）:
- KABUSYS_ENV: development | paper_trading | live  (default: development)
- DUCKDB_PATH: 分析用 DuckDB ファイル（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（default: data/paper_trading.db）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL (default: INFO)
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
- PID_FILE_PATH: 実行エンジンの PID ファイル（default: data/execution.pid）
- KILL_FLAG_PATH: Kill Switch 用フラグ（default: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"1" で有効）
- PAPER_FILL_MODE: paper_trading 時の約定挙動（instant|partial|never|reject）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒, default: 60）

簡易 .env テンプレ（例）
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
KILL_FLAG_CLEAR_ON_START=0
PAPER_FILL_MODE=instant

---

## 使い方（実行例）

- 設定ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視プロセス起動（SystemMonitor のポーリングループ）:
  - MONITOR_POLL_INTERVAL 環境変数で秒数を上書きできます（デフォルト 60 秒）。
  - python -m kabusys.run_monitoring

  実行中は monitoring DB（Settings.sqlite_path）に system_status 等を記録します。停止はプロジェクトルートの data/stop_requested.flag を作成するか Ctrl+C。

- 実行（ExecutionEngine）起動:
  - KABUSYS_ENV=paper_trading を指定するとペーパートレードモードになり、paper_trading_db に記録されます。
  - python -m kabusys.run_execution
  - 実行中は data/execution.pid に PID を書きます。停止は data/stop_requested.flag を作成するか ExecutionEngine 内の Kill Switch による停止を受けます。

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 関連（プログラムから利用）
  - ニュース NLP（銘柄別スコア）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...") などで利用
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

  ※ OpenAI API を利用するためには OPENAI_API_KEY を環境変数に設定するか、api_key 引数で渡してください。

---

## 運用上の注意

- Paper Trading と本番データは分離されています（paper_trading モードは paper_trading_db を使用）。
- run_monitoring は KABUSYS_ENV に関係なく常に本番 sqlite_path（monitoring DB）を使用する設計です。
- Kill Switch（kill.flag）や stop_requested.flag、execution.pid は運用上の制御ファイルです。取り扱いに注意してください。
- process priority を上げる処理を含みます（psutil を使う）。権限不足で警告が出る場合がありますが、安全にスキップされます。
- AI 呼び出しは外部 API（OpenAI）に依存するためレート制限・失敗対策が実装されていますが、APIキー漏えいに注意してください。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下、抜粋）

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - utils/
    - __init__.py
    - process_priority.py    — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py       — SQLite テーブル定義 + MonitoringDB
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
  - execution/                — Execution / Broker 関連（参照あり）
    - (OrderRepository, ExecutionEngine 等)  ※実行コード参照
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
  - tools/
    - paper_verification_report.py
    - __init__.py

--- 

## 監視 DB（monitoring_db）の主要テーブル

- system_status: CPU/MEM/DISK/プロセス状態、recorded_at
- trade_logs: 発注イベントログ（event_type: Created/Sent/Filled 等）
- positions: 現在ポジション（code を主キー）
- risk_logs: リスクイベント（DRAWDOWN_ALERT / STALE_ORDER / PRICE_ANOMALY 等）
- dashboard: 集計（portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value）

---

## トラブルシューティング / 開発メモ

- .env 自動ロードはプロジェクトルートの .git または pyproject.toml を基準に行われます。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- MONITOR_POLL_INTERVAL などの数値環境変数が不正な場合、デフォルトにフォールバックしてログに出力します。
- DuckDB / SQLite のパス指定は相対パス（data/...）がデフォルトです。運用環境では絶対パスを推奨します。
- AI 関連は外部 API に依存するためテストではモック化（patch）して利用できるように設計されています。

---

必要に応じて README を拡張します（例: 実行例ログ、CI / デプロイ手順、より詳細な設定項目説明、ExecutionEngine の起動オプションなど）。特に補足してほしいセクションがあれば教えてください。