# KabuSys

日本株向け自動売買システムのモジュール群（ライブラリ & 起動スクリプト群）。

このリポジトリはトレード実行エンジン、監視（Monitoring）コンポーネント、研究用ファクター計算、ポートフォリオ構築、AI を用いたニュース評価などを含む集合的なコードベースです。各コンポーネントは比較的独立しており、ライブラリとして呼び出すことも、スクリプトとして起動することもできます。

バージョン: 0.1.0

---

## 概要

主な目的は「日本株の自動売買を安全かつ運用しやすく行うためのモジュール群および運用用スクリプトの提供」です。運用面の配慮（ログ、優先度設定、Kill Switch、監視ログの永続化、ペーパートレード分離など）が充実しています。

主要な特徴:

- ExecutionEngine（発注エンジン）とそれを監視する Monitoring 系コンポーネント
- Paper Trading（ペーパートレード）を本番 DB から分離する仕組み
- DuckDB を使った研究・ファクター計算モジュール（prices_daily / raw_financials 参照）
- OpenAI を使ったニュースセンチメント（news_nlp）と市場レジーム判定（regime_detector）
- ポートフォリオ構築、ポジションサイズ算出、セクターキャップ等の純粋関数群
- 環境設定ウィザード（.env 作成）、設定検証ツール、運用ツール（ペーパートレード検証レポート）
- ログ出力はコンソール＋日次ローテートファイル（logs/*.log）

---

## 機能一覧（概観）

- 起動スクリプト
  - run_execution.py — ExecutionEngine 起動（KABUSYS_ENV により paper_trading を分離）
  - run_monitoring.py — SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔上書き）
- 設定
  - config_setup.py — 対話式で .env を生成・更新するウィザード
  - validate_config.py — .env と config/*.yaml の事前検証 CLI（--strict あり）
  - config.Settings — 環境変数をラップする設定クラス
- 監視（monitoring）
  - monitoring_db — SQLite による監視ログ永続化（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor, trade_monitor, risk_monitor — 各種チェックロジック
  - monitoring_engine — 各 Monitor を束ねて定期実行・アラート判定
  - kill_switch — 条件を満たせば data/kill.flag を書き込む Kill Switch
- 実行（execution）
  - ブローカーファクトリ、OrderManager、RiskManager、ExecutionEngine（発注処理の中核）
- ポートフォリオ（portfolio）
  - 候補選択、重み付け、リスク調整、ポジションサイズ算出（単元丸め・集約キャップ等）
- 研究（research）
  - factor_research: momentum / volatility / value 等のファクター計算（DuckDB 経由）
  - feature_exploration: 将来リターン計測、IC 計算、統計サマリ
- AI（ai）
  - news_nlp: raw_news から銘柄別センチメントを OpenAI に問い合わせ、ai_scores テーブルへ書き込む
  - regime_detector: ETF とマクロニュースを用いて日次市場レジーム判定を行い market_regime に保存
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成（稼働率・注文成功率・レイテンシ等）
- ユーティリティ
  - utils.logging_setup: 共通のログ設定（stdout + TimedRotatingFileHandler）
  - utils.process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 前提・要件

- Python 3.10 以上（型ヒントに | を使用しているため）
- 必要なパッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証をフルに行いたい場合）
- 標準ライブラリ: sqlite3, logging, threading, datetime, pathlib 等

（実際の運用では requirements.txt を用意して pip install -r することを推奨します。上記は最低限の候補です。）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repository-url>
   - cd <repository-root>

2. 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # macOS / Linux
   - .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール
   - 例:
     - pip install duckdb psutil openai PyYAML

   （実運用ではプロジェクト用の requirements.txt を用意してその通りにインストールしてください。）

4. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に手動で作成（必須キーは下記参照）

5. 必須環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
   - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
   - KABUSYS_ENV — 実行環境（development | paper_trading | live）。省略時は development
   - OPENAI_API_KEY — AI 機能を使用する場合に必要
   - その他（任意／デフォルトあり）:
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB）
     - LOG_LEVEL（DEBUG|INFO|...）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート通知用）

6. DB 初期化
   - run_execution / run_monitoring の起動時に SQLite テーブル作成（init_monitoring_db）が自動実行されます。事前に何かする必要はありません。

---

## 使い方（主要スクリプト）

- 環境設定ウィザード
  - python -m kabusys.config_setup
    - .env を対話的に作成・更新します。

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（警告も失敗扱い）:
    - python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録（本番 DB と分離）
    - 起動時に data/stop_requested.flag が既にあれば起動を中止
    - 実行中に data/stop_requested.flag が作成されるとエンジンを停止

- Monitoring（SystemMonitor）起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト: 60）
  - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用して監視ログを記録

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定（オプション）:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

- AI / 研究モジュールのプログラム的利用例
  - ニューススコア付け（プログラム呼び出し例）
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")
  - 市場レジーム判定
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

- 停止・Kill Switch
  - kill_switch は条件に応じて data/kill.flag を書き、ExecutionEngine のプロセスを止める仕組みを持ちます。
  - 手動停止用フラグ:
    - data/stop_requested.flag — run_* スクリプトはこのファイルの存在を検知して停止
    - data/kill.flag — ExecutionEngine に対する安全停止（kill switch）

---

## 主要環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
- LOG_LEVEL — デフォルト: INFO
- OPENAI_API_KEY — AI 機能使用時に必要
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START — ExecutionEngine 起動時に kill.flag を自動クリアするか（1=クリア, 0=クリアしない。production では 0 推奨）

.env は自動ロードされます（プロジェクトルートに .env / .env.local が存在する場合）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ログ・ファイル

- ログ: logs/<app_name>.log（日次ローテーション・30日保持）とコンソール（stdout）
  - app_name には `execution` や `monitoring` などを設定して呼び出します（setup_logging の app_name 引数）
- データ/フラグ:
  - data/monitoring.db（監視 SQLite、デフォルト）
  - data/paper_trading.db（ペーパートレード用 SQLite）
  - data/execution.pid（ExecutionEngine の PID ファイル）
  - data/stop_requested.flag（run_* スクリプトの停止フラグ）
  - data/kill.flag（KillSwitch）

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — Settings / .env 自動読み込み処理
  - config_setup.py          — 対話式 .env ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート
  - ai/
    - news_nlp.py             — ニュース NLP → ai_scores
    - regime_detector.py      — 市場レジーム判定
    - __init__.py
  - monitoring/
    - monitoring_db.py        — SQLite テーブル初期化／永続化層
    - system_monitor.py       — システム／データ鮮度監視
    - trade_monitor.py        — （発注ログ監視等）
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - monitoring_engine.py    — 各 Monitor を束ねるポーリングエンジン
    - kill_switch.py
    - alert_manager.py
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
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/                    — 実行時に使用するファイル群（logs/, data/ 等はリポジトリ外で管理することを推奨）

---

## 運用上の注意点

- 本番（KABUSYS_ENV=live）では設定（LINE 通知、KILL フラグ設定など）を慎重に確認してください。validate_config は本番フラグ時に追加の警告を出します。
- .env は機密情報を含むため絶対に Git にコミットしないでください（config_setup も警告を出します）。
- OpenAI API を利用する機能は API 利用料金・レート制限に注意してください。news_nlp はバッチ処理・リトライ・スコア検証を組み込んでいますが、失敗時はフェイルセーフでスキップする設計です。
- run_execution は停止フラグ・PID ファイルを見て動作します。手動でプロセスを停止する際は stop flag を作成するか、プロセスに対して安全に停止命令を出してください。
- Monitoring は本番 sqlite_path を参照します（環境に依らず監視ログは本番 DB に記録される点に注意）。

---

## 開発・拡張のヒント

- research モジュールは DuckDB 接続を受け取り SQL で処理するため、データが揃っていればローカル環境でもそのまま試せます。
- AI 関連関数は API 呼び出し部分を分離しているため、テスト時は _call_openai_api をモックして動作検証できます。
- logging_setup と process_priority を各スクリプトの冒頭で実行することで、運用時のログ一貫性や OS に依存した優先度設定を担保しています。

---

必要であれば README に含めるサンプル .env テンプレート、requirements.txt の候補、または起動例（systemd ユニット / Dockerfile など）のサンプルも作成します。どの情報を追加したいか教えてください。