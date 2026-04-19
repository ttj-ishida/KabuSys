# KabuSys

日本株自動売買システムの軽量コアライブラリ（README）。  
本ドキュメントはこのコードベースの概要、機能、セットアップ方法、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買を支援するためのモジュール群です。  
主要機能は以下のとおりです。

- 発注エンジン（ExecutionEngine）と監視サブシステム（Monitoring）
- ペーパートレード（paper_trading）モードのサポート（実口座と分離された DB）
- ファクター計算・研究用ユーティリティ（DuckDB を使ったファクター計算）
- ニュースに基づく AI（OpenAI）によるセンチメント評価・レジーム検出
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ計算）
- 監視ログの永続化（SQLite）と監視エンジン、Kill Switch（停止フラグ）

設計上のポイント:
- 環境変数 / .env による設定管理
- DuckDB（分析用）と SQLite（監視・履歴用）の併用
- 本番/ペーパーのデータ分離（paper_trading モード）
- LLM（OpenAI）統合箇所は外部キー（OPENAI_API_KEY）で制御。失敗耐性あり

---

## 主な機能一覧

- 実行（Execution）
  - ExecutionEngine（発注・リスク管理・オーダー管理）
  - BrokerClientFactory により実ブローカーまたは MockBroker を切替え
  - paper_trading モード時は `data/paper_trading.db`（デフォルト）へ記録

- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/ディスク使用率、データ鮮度、実行プロセス生存確認
  - TradeMonitor: 注文滞留／約定異常等の監視（trade_logs に基づく）
  - RiskMonitor: ドローダウン、保有銘柄上限の監視とダッシュボード更新
  - KillSwitch: 危険状態で `data/kill.flag` を書き、ExecutionEngine を停止可能
  - MonitoringEngine: 各モニタを束ねて定期実行、アラート通知連携

- 研究/ファクター
  - momentum / volatility / value 等のファクター計算（DuckDB）
  - forward returns, IC（情報係数）、統計サマリー

- AI
  - news_nlp: OpenAI を用いたニュースのセンチメント集計 → ai_scores へ保存
  - regime_detector: ETF の MA + マクロニュースの LLM スコアでレジーム判定

- ユーティリティ
  - 環境設定ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ログ設定ユーティリティ（logging_setup）
  - プロセス優先度・CPU affinity 設定（process_priority）
  - Paper Trading 検証レポート生成スクリプト

---

## セットアップ手順

前提:
- Python 3.9+（コードは型注釈で 3.9+ を想定）
- 仮想環境を作成して依存をインストールすることを推奨

1. リポジトリをクローン / 配布パッケージを展開

2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール  
   ※ requirements.txt は無い想定のため、主要ライブラリの例を示します:
   - pip install duckdb psutil openai PyYAML

   使用する機能によってはさらに依存が必要です（例: OpenAI クライアント、DuckDB, psutil, PyYAML）。

4. 環境変数（.env）を作成
   - 対話式ウィザードで生成:
     - python -m kabusys.config_setup
   - もしくはプロジェクトルートに `.env` を手動作成
   - 最低限設定が必要な環境変数（validate_config がチェックします）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - その他主要な環境変数:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH (例: data/kabusys.duckdb)
     - SQLITE_PATH (例: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB)
     - OPENAI_API_KEY (news_nlp / regime_detector 使用時)
     - LOG_LEVEL / LOG_DIR
     - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか。開発用）

   - .env を絶対にリポジトリにコミットしないでください（README 内にも警告あり）。

5. 設定検証（オプション）
   - python -m kabusys.validate_config
   - 警告を FAIL 扱いにする場合:
     - python -m kabusys.validate_config --strict

6. データディレクトリやログディレクトリを作成（自動作成される場合もありますが権限等で失敗することがあるため確認推奨）
   - mkdir -p data logs

---

## 使い方（実行例）

- 環境の確認
  - python -m kabusys.validate_config

- .env の作成/更新（対話式）
  - python -m kabusys.config_setup

- ExecutionEngine（発注エンジン）の起動
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し、paper_trading 用 DB に書き込みます。
    - 起動時に `data/stop_requested.flag` が存在すると起動を中止します。
    - 実行中は `data/execution.pid` に PID を書きます（停止フラグや外部停止に利用）。

- Monitoring（監視ループ）の起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書きできます（デフォルト 60）。
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は常に本番 sqlite_path を参照します（環境にかかわらず）。

- Kill Switch（外部から Execution を止める）
  - KillSwitch は `data/kill.flag` を作成すると Execution 側が検知して停止します（監視側が書き込む想定）。
  - ExecutionEngine 側は起動時に `KILL_FLAG_CLEAR_ON_START` の設定が 1 であれば `kill.flag` をクリアする挙動を持つ可能性があります（要確認）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは `--db PATH` または環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。

- AI 関連
  - news_nlp.score_news / regime_detector.score_regime は Python API として利用できます。例:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")
  - OpenAI API キーが必要です（環境変数 OPENAI_API_KEY または引数で指定）。

- ログ
  - 共通のロギング設定関数: kabusys.utils.logging_setup.setup_logging(app_name="execution")
  - ログファイルはデフォルトで logs/<app_name>.log（1日ローテーション、30 日保管）

停止・強制終了:
- run_* スクリプトは KeyboardInterrupt をハンドルして安全に終了します。
- 外部から停止を要求したい場合は `data/stop_requested.flag` を作成すると run_monitoring/run_execution のループが終了します。

---

## よく使う環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境（development / paper_trading / live）
- DUCKDB_PATH — 分析用 DuckDB ファイルパス（例: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（例: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 専用 SQLite DB（paper_trading モード）
- OPENAI_API_KEY — OpenAI を使うモジュールで必要（news_nlp, regime_detector）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒）

.env の例（略式）
- KABUSYS_ENV=development
- JQUANTS_REFRESH_TOKEN=your_token_here
- KABU_API_PASSWORD=your_password_here
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- LOG_LEVEL=INFO

（実際には python -m kabusys.config_setup を使うことを推奨）

---

## ディレクトリ構成（主要ファイル）

以下は `src/kabusys` 配下の主要モジュール構成（抜粋）です。

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env の自動ロード・Settings 定義
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート生成
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - execution/               — 発注エンジン関連（order_manager 等）※詳細は該当ディレクトリへ
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - monitoring/
    - monitoring_db.py       — SQLite のスキーマと DB ラッパー
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

ログやデータ:
- data/ — データファイル群（SQLite / PID / flag 等）
  - data/monitoring.db (デフォルト)
  - data/paper_trading.db (paper_trading 用)
  - data/execution.pid
  - data/stop_requested.flag
  - data/kill.flag
- logs/ — ログファイル（app_name による分離）

---

## 開発時の注意点・運用ノウハウ

- .env は秘匿情報を含むため絶対に Git にコミットしないでください。
- 本番運用時は KABUSYS_ENV=live を設定する前に validate_config を実行して注意事項を確認してください。
- OpenAI 連携機能は API レートやコストがかかるため、運用ポリシー（頻度 / バッチサイズ）を検討してください。
- monitoring は execution プロセスの稼働確認とデータ鮮度チェックを行い、重大事象は kill.flag を書き込み Execution を停止できます。kill.flag の自動クリア設定は本番では無効（0）を推奨します。
- DuckDB は分析用途のため、適切にテーブルをロードしておく必要があります（prices_daily / raw_financials 等）。

---

必要があれば README にサンプル .env ファイルのテンプレート、さらに詳しい起動手順（systemd / supervisor / Docker の設定例）や API の簡易ドキュメントを追加できます。どの情報を優先して追記したいか教えてください。