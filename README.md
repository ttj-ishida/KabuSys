# KabuSys

日本株向け自動売買システム KabuSys のコードベース README（日本語）。

このドキュメントはリポジトリ内のスクリプト・モジュールから自動で抽出した情報に基づき、セットアップ・実行方法やディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買（バックテスト／ペーパートレード／本番運用を想定）を支援するアプリケーション群です。主な目的は以下：

- 発注/約定を管理する ExecutionEngine
- システム稼働状況・データ鮮度・注文状態・リスクを監視する Monitoring
- ポートフォリオ構築（銘柄選定・重み計算・ポジションサイズ）
- 研究用ファクター計算・特徴量探索（DuckDB を用いた解析）
- ニュースを LLM（OpenAI）でスコアリングして AI スコアを生成する機能
- ペーパートレードの検証レポート生成ツール
- 環境設定ウィザード・設定検証ツール
- 統一されたログ設定・プロセス優先度ユーティリティ等のユーティリティ群

設計上の注意点：
- DuckDB / SQLite をデータレイヤに使用（分析用と監視用で分離）
- 環境変数 / .env で設定管理、.env は自動読み込み（必要に応じて無効化可）
- Paper Trading は本番 DB と完全分離（別 SQLite ファイル）
- LLM 呼び出しはフェイルセーフ（失敗時にスキップまたは安全側の値で継続）

---

## 機能一覧（抜粋）

- Execution
  - ExecutionEngine の起動スクリプト（run_execution.py）
  - Broker クライアントの切替（KABUSYS_ENV=paper_trading 時は Mock）
  - リスクマネージャ、OrderManager、Reconciler などの組立て
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor をまとめる MonitoringEngine
  - SQLite への監視ログ永続化（monitoring_db.py）
  - Kill Switch（条件により data/kill.flag を書き込み、Engine を停止）
  - run_monitoring.py によるポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定可）
- Portfolio
  - 銘柄選定（select_candidates）
  - 重み計算（等重・スコア重み）
  - セクター制約適用、レジーム乗数
  - ポジションサイズ算出（lot 単位丸め、aggregate cap 対応）
- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB 接続で SQL 実行）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- AI
  - ニュース NLP スコアリング（OpenAI API 経由、JSON mode 利用）
  - 市場レジーム判定（ETF MA + マクロニュース LLM スコア合成）
- Tools
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report.py）
- Config
  - .env 対話式ウィザード（config_setup.py）
  - 起動前設定検証 CLI（validate_config.py）
- Utils
  - 簡易ログ設定（TimedRotatingFileHandler を含む統一設定）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 必要要件（概略）

- Python 3.9+
- 外部パッケージ（主なもの）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証のための任意依存）
- SQLite（標準ライブラリで利用可）

インストール例：
- 仮想環境作成後に最低限：
  pip install duckdb psutil openai

PyYAML を使う場合：
  pip install pyyaml

（実際の requirements.txt はリポジトリに合わせて用意してください）

---

## セットアップ手順

1. リポジトリをクローン / チェックアウト
2. 仮想環境を作成・有効化（例: python -m venv .venv）
3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - （任意）pip install pyyaml
4. .env の作成
   - 対話式ウィザードを使う（推奨）:
     python -m kabusys.config_setup
   - もしくは .env.example を参考に手動作成
   - 自動ロードはデフォルトで有効。テスト等で無効にする場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
5. 設定の検証（起動前チェック）
   - python -m kabusys.validate_config
   - 本番でより厳格にチェックする場合:
     python -m kabusys.validate_config --strict
6. データディレクトリ作成（必要に応じて）
   - デフォルトの DB / PID / フラグファイルパスは data/ 以下
   - ログディレクトリは logs/（自動作成されます）

---

## 主要な環境変数（抜粋）

（必須/推奨のものを列挙、デフォルト値がある場合は併記）

- JQUANTS_REFRESH_TOKEN — 必須（J-Quants API）
- KABU_API_PASSWORD — 必須（kabuステーション API）
- KABUSYS_ENV — 実行環境（development / paper_trading / live、デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（デフォルト: INFO）
- LOG_DIR — ログ保存先（デフォルト: logs/）
- OPENAI_API_KEY — OpenAI を使う機能で必要
- PAPER_FILL_MODE — ペーパートレード時の約定挙動（instant|partial|never|reject, デフォルト: instant）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリア（0/1、デフォルト 0）
- PID_FILE_PATH / KILL_FLAG_PATH — ファイルパス（デフォルト data/execution.pid, data/kill.flag）

（config_setup.py のウィザードで主要設定を生成できます）

---

## 使い方（起動 / 主なコマンド）

- 環境設定ウィザード（.env 作成・更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱いで終了コード 1

- ExecutionEngine を起動（発注エンジン）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading.db に記録（本番 DB と分離）
    - 起動中は data/execution.pid ファイルを利用
    - data/stop_requested.flag または data/kill.flag 等で停止制御（stop フラグを検知して安全停止）

- Monitoring を起動（ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き可能（デフォルト 60）
  - Monitoring は設定に関わらず monitoring 用 sqlite_path（通常は data/monitoring.db）を使用します

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 簡易レポート（稼働率、成功率、レイテンシ等）を標準出力に出力

- AI 関連の利用例（プログラムから呼び出す）
  - 例: ニューススコアを生成する
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, date(2026, 4, 1), api_key="YOUR_OPENAI_KEY")

  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, date(2026,4,1), api_key="YOUR_OPENAI_KEY")

補足:
- 多くの API（OpenAI など）は API キーを環境変数 OPENAI_API_KEY または関数引数で受け取ります。
- DuckDB 接続オブジェクト（duckdb.connect(...)）をモジュール関数に渡して解析／書込みを行います。

---

## 監視・停止の仕組み（要点）

- kill.flag（デフォルト: data/kill.flag）
  - KillSwitch によって書き込まれるファイル。存在すると ExecutionEngine に停止シグナルを送る運用を容易にします。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアされます（本番では 0 推奨）。

- stop_requested.flag（run_monitoring, run_execution が監視するファイル）
  - run_monitoring/run_execution はプロジェクトルートの data/stop_requested.flag を監視し、存在を検知するとループを抜けて終了します（安全終了用）。

- PID ファイル（data/execution.pid）
  - ExecutionEngine が PID ファイルを管理し、プロセス状態の判定などに利用します。

---

## ログについて

- 共通のログ設定ユーティリティを提供（kabusys.utils.logging_setup.setup_logging）。
- デフォルトでは stdout と logs/<app_name>.log（1 日ごとローテーション、30 日保持）に出力。
- LOG_DIR 環境変数または setup_logging の引数で保存先を変更可能。

---

## ディレクトリ構成（主要ファイル・モジュール）

リポジトリの src/kabusys 以下を抜粋した構成例:

- run_monitoring.py
- run_execution.py
- config.py
- config_setup.py
- validate_config.py
- __init__.py

- ai/
  - news_nlp.py
  - regime_detector.py
- monitoring/
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py (存在しない場合あり)
- execution/
  - execution_engine.py
  - broker_factory.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py
- research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py
  - process_priority.py
  - __init__.py
- data/ (実行時に使用されることが多いディレクトリ)
  - monitoring.db (デフォルト SQLite)
  - paper_trading.db (paper_trading 用)
  - kabusys.duckdb (分析用)
  - kill.flag, stop_requested.flag, execution.pid など

（実際のツリーはリポジトリによって多少異なることがあります）

---

## 運用上の注意 / ベストプラクティス

- 本番環境（KABUSYS_ENV=live）では設定ミスによる誤発注を防ぐため validate_config を実行し、LINE 通知設定などを確認してください。
- .env は絶対に Git にコミットしないでください（config_setup でもヘッダに警告あり）。
- Paper Trading は本番 DB と分離されますが、運用で使用する DB パスは .env で明示してください。
- LLM（OpenAI）利用機能は API 呼び出し回数やエラーに留意し、API キーと料金管理を行ってください。
- ログディレクトリのパーミッションやディスク容量監視を行ってください（logging_setup が自動作成しますが、環境によっては作成失敗することがあります）。
- kill.flag / stop_requested.flag を手動で操作すると稼働中のエンジンが停止するため、運用ルールを明確にしておくことを推奨します。

---

必要に応じて README の各セクションをリポジトリ固有の情報に合わせて補足してください（依存パッケージ一覧、実行ユーザ・サービス定義、systemd / supervisor 用の起動スクリプト例など）。