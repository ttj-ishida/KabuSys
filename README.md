# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買システム（KabuSys）のコアライブラリです。バックテスト／リサーチ用のファクター計算、ポートフォリオ構築、発注エンジン、監視・Kill Switch、AI ベースのニュースセンチメント評価などを含みます。

---

## プロジェクト概要
- 自動売買実行エンジン（ExecutionEngine）とそれを監視する Monitoring 系コンポーネントを提供します。
- Paper Trading（モックブローカー）と Live（実発注）を環境切替でサポートします。
- DuckDB（時系列・分析データ）と SQLite（監視ログ / 発注履歴）を併用します。
- ニュースセンチメントや市場レジーム判定に OpenAI（gpt-4o-mini）を利用する機能を持ちます（任意）。

---

## 主な機能一覧
- execution
  - ExecutionEngine（発注エンジン）
  - BrokerClientFactory（紙上/実ブローカー切替）
  - OrderRepository / OrderManager / RiskManager / Reconciler
- monitoring
  - SystemMonitor（プロセス・リソース・データ鮮度監視）
  - TradeMonitor（滞留注文・約定異常検出）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - MonitoringEngine（上記を束ねるポーリングエンジン）
  - KillSwitch（条件成立時に data/kill.flag を書き込む）
- portfolio
  - 候補選定 / 重み付け / ポジションサイジング / セクター制約
- research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン・IC 計算等の探索ユーティリティ
- ai
  - news_nlp: ニュースを LLM に送って銘柄別センチメントを算出し ai_scores に書き込む
  - regime_detector: ETF とマクロニュースを組み合わせて市場レジーム判定
- tools
  - paper_verification_report: Paper Trading の検証レポート出力
- utils
  - process_priority: プロセス優先度・CPU affinity 設定ユーティリティ
- 設定・運用ツール
  - config_setup: .env 対話ウィザード（.env の作成・更新）
  - validate_config: .env / config/*.yaml 検証 CLI

---

## 必要な依存パッケージ（抜粋）
- Python 3.9+
- duckdb
- psutil
- openai（AI 機能使用時）
- PyYAML（config/*.yaml の検証時に任意）
- （その他 標準ライブラリ）

インストール例:
- pip install duckdb psutil openai PyYAML

---

## セットアップ手順

1. リポジトリをクローン・展開
   - プロジェクトルートは .git または pyproject.toml を基準に自動検出されます。

2. Python 環境を作成して依存をインストール
   - python -m venv .venv
   - source .venv/bin/activate
   - pip install -r requirements.txt もしくは上記依存を個別インストール

3. 環境変数ファイル（.env）を作成
   - 対話ウィザードを利用:
     - python -m kabusys.config_setup
   - 手動で作成する場合は .env.example を参照してください。
   - 自動ロード:
     - デフォルトでパッケージ import 時にプロジェクトルートの `.env` を読み込みます（OS 環境変数が優先）。
     - `.env.local` が存在する場合は `.env` の値を上書きします。
     - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

4. 必須環境変数（最低限）
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - OPENAI_API_KEY（AI 機能を使う場合）

5. 主要データベースパス（デフォルト）
   - DuckDB: data/kabusys.duckdb （環境変数: DUCKDB_PATH）
   - SQLite (監視): data/monitoring.db （環境変数: SQLITE_PATH）
   - Paper Trading 用 SQLite: data/paper_trading.db （環境変数: PAPER_TRADING_SQLITE_PATH）

---

## 使い方（実行/運用）

- 設定検証
  - python -m kabusys.validate_config
  - 警告をエラー扱いにする: python -m kabusys.validate_config --strict

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 挙動:
    - 環境変数 KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使用し、専用 SQLite (`PAPER_TRADING_SQLITE_PATH` / default: data/paper_trading.db) に記録します（本番 DB と分離）。
    - エンジンはデーモンスレッドで run_session を実行し、data/stop_requested.flag の作成で停止要求を受け付けます。
    - 実行中は pid ファイル（デフォルト: data/execution.pid）を出力します。

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒）を上書き（デフォルト 60 秒）。1 以上の整数を指定してください。無効な値を与えるとデフォルトにフォールバックします。
  - 挙動:
    - プロセス優先度を "high" に設定し（set_process_priority）、MonitoringEngine により system/trade/risk 各 Monitor をポーリングします。
    - 停止は data/stop_requested.flag を作成することで行います（存在を検知するとループ終了）。
    - Monitoring は常に本番 sqlite_path を使用します（環境にかかわらず監視 DB は本番用パスを参照）。

- Kill Switch
  - KillSwitch は RiskMonitor 等の結果に基づき data/kill.flag を書き込み、ExecutionEngine 停止を促します。
  - 本番での自動クリアは危険（KILL_FLAG_CLEAR_ON_START=1 は開発専用。デフォルト推奨は 0）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB は環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db。

---

## よく使う環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- KABUSYS_ENV (development / paper_trading / live) — デフォルト development
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- SQLITE_PATH (デフォルト data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、デフォルト data/paper_trading.db)
- OPENAI_API_KEY（AI 機能で必須）
- LOG_LEVEL (DEBUG/INFO/...)
- MONITOR_POLL_INTERVAL（run_monitoring 用、秒）

---

## 運用メモ / 注意点
- Monitoring と Execution はそれぞれ stop フラグ（data/stop_requested.flag）および kill.flag を用いて相互作用します。flag ファイルの取り扱いに注意してください。
- process_priority 設定は psutil を介して行います。権限や OS によっては設定できない場合があり、その場合は警告ログが出ます。
- AI 機能（news_nlp, regime_detector）は OpenAI API を呼び出します。API エラーや 5xx、429 等はリトライ処理がありますが、失敗時はフォールバック動作（無視または中立値）を行う設計です。
- DuckDB のバージョン差異や executemany の空リスト取り扱いに注意（コード内で対応処理あり）。

---

## ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py — パッケージ定義（version 等）
  - config.py — 環境変数 / .env 自動読み込み / Settings クラス
  - config_setup.py — .env 対話ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - execution/  (発注エンジン関連)
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - order_record.py
  - monitoring/
    - monitoring_db.py — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - data/ （ランタイムに生成される、デフォルト DB 等）
    - monitoring.db (SQLite／デフォルト)
    - paper_trading.db (Paper Trading 用)
    - kabusys.duckdb (DuckDB)
    - execution.pid / kill.flag / stop_requested.flag など

---

## 開発者向けヒント
- 設定チェック: python -m kabusys.validate_config
- .env の初期化: python -m kabusys.config_setup
- モニタリングの一回実行（テスト用）: MonitoringEngine を unit-test で run_once() を呼ぶ
- AI 部分をユニットテストする際は _call_openai_api をモックしてください（コード内で想定）。

---

README は概略です。各モジュールの詳細な使い方や API はソースコード内の docstring とモジュールコメントを参照してください。必要であれば特定モジュール（例: ExecutionEngine、AI モジュール、ポートフォリオ関数）の詳細なドキュメントを追加します。