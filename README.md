# KabuSys

日本株向け自動売買システムのコアライブラリ群および起動・運用用スクリプト群です。  
本リポジトリには、発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ（ファクター計算）、AI ベースのニュース解析／レジーム判定などの主要機能が含まれます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は次のような目的で設計されたモジュール群です。

- 日次・リアルタイムの自動発注を行う ExecutionEngine（本番 / ペーパートレード対応）
- ExecutionEngine の稼働状況、注文・約定ログ、リスク指標を記録・監視する Monitoring 系機能
- ファクター計算や特徴量探索などの Research ツール（DuckDB を利用）
- ニュースを LLM（OpenAI）でスコアリングし、銘柄別センチメントを生成する AI モジュール
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ算出、セクター制限等）
- 運用を支援する CLI ツール（.env ウィザード、設定検証、Paper Trading 検証レポート 等）

設計方針の要点:
- 本番 DB とペーパートレード DB は明確に分離される（KABUSYS_ENV による切替）
- DuckDB を分析用途で利用し、SQLite は監視および発注ログ保存に利用
- OpenAI を使った機能は API キー必須だが、失敗時はフェイルセーフで継続する実装
- 自動的な .env ロード機能を持ち、プロジェクトルート基準で .env/.env.local を読み込む

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py — ExecutionEngine を起動（KABUSYS_ENV に応じて本番または Paper Trading）
  - run_monitoring.py — SystemMonitor のポーリングループを起動

- 構成・運用ツール
  - config_setup.py — .env 対話式ウィザード（初期設定）
  - validate_config.py — .env と config/*.yaml の起動前検証
  - tools/paper_verification_report.py — Paper Trading の検証レポート生成

- 監視（monitoring）
  - monitoring_db.py — SQLite を用いた監視ログの永続化層
  - system_monitor.py, trade_monitor.py, risk_monitor.py, monitoring_engine.py — 各種監視ロジック
  - kill_switch.py — 条件に応じた停止フラグ書き込み（data/kill.flag）

- Execution（発注周り）
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py 等（エンジン本体／責務分離）

- ポートフォリオ（portfolio）
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py — 候補選定、重み、株数決定、セクター制限 等

- Research（リサーチ）
  - factor_research.py, feature_exploration.py — ファクター計算、将来リターン、IC、統計サマリー

- AI（OpenAI を利用）
  - ai/news_nlp.py — ニュースを LLM でセンチメント化して ai_scores に保存
  - ai/regime_detector.py — マクロ + ETF MA200 から日次レジーム判定

- ユーティリティ
  - utils/logging_setup.py — 統一的なログ設定（stdout + 日次ローテートファイル）
  - utils/process_priority.py — プラットフォーム横断でのプロセス優先度設定

---

## 動作要件（概略）

- Python 3.10+
- 必須 Python パッケージ（代表例）
  - duckdb
  - psutil
  - openai
- 任意 / 推奨
  - PyYAML（config の YAML パース検証用）
- OS: Linux/macOS/Windows（ただし一部のプロセス優先度設定・CPU affinity は OS に依存）

実際のインストール手順では requirements.txt を用意して pip install することを推奨します。開発環境では仮想環境（venv）を使用してください。

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成して有効化します。

   例:
   python -m venv .venv
   source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストールします（例）:

   pip install duckdb psutil openai

   （PyYAML があると validate_config の YAML 検証が有効になります）

3. 初期設定 (.env) を作成します（対話ウィザード推奨）:

   python -m kabusys.config_setup

   ウィザードの指示に従って J-Quants トークン、kabuステーションのパスワード、データベースパス等を設定します。
   既存の .env がある場合は読み込まれ、Enter で既存値を再利用できます。

4. 設定検証:

   python -m kabusys.validate_config
   # 警告も FAIL 扱いにする厳格モード:
   python -m kabusys.validate_config --strict

5. データディレクトリの確認:
   - デフォルトの DB / ファイルパスは .env（または以下デフォルト）に従います:
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - PID ファイル: data/execution.pid
     - Kill flag: data/kill.flag
   必要に応じて .env で上書きしてください。

6. OpenAI を利用する機能を使う場合:
   - OPENAI_API_KEY を環境変数または明示的引数で与える必要があります。
   - news_nlp/ regime_detector は API 呼び出しを行います（クォータ／料金に注意）。

---

## 使い方（起動例）

- ExecutionEngine を起動（本番/ペーパーは KABUSYS_ENV で切替）:

  KABUSYS_ENV=development python -m kabusys.run_execution
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  KABUSYS_ENV=live python -m kabusys.run_execution

  補足:
  - paper_trading 時は MockBrokerClient を使用し、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録されます。
  - 起動時に data/stop_requested.flag が存在する場合は起動を行わず終了します。
  - 実行中は data/execution.pid に PID が書かれます。

- 監視ループ（SystemMonitor）を起動:

  python -m kabusys.run_monitoring

  オプション:
  - ポーリング間隔を環境変数で上書き: MONITOR_POLL_INTERVAL（秒、デフォルト 60）
    例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

  補足:
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用して監視ログを記録します。
  - 停止は data/stop_requested.flag を作成することで行えます（run_monitoring はこのファイル検出でループを終了）。

- Paper Trading 検証レポートを生成:

  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを指定する場合
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- .env 設定ウィザード:

  python -m kabusys.config_setup

- 設定検証:

  python -m kabusys.validate_config

---

## 主要環境変数（サンプル）

必須（例: .env に設定）
- JQUANTS_REFRESH_TOKEN=your_jquants_token
- KABU_API_PASSWORD=your_kabu_password

推奨 / 任意
- KABUSYS_ENV=development|paper_trading|live
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- LOG_LEVEL=INFO
- LOG_DIR=logs
- OPENAI_API_KEY=sk-xxxx
- LINE_CHANNEL_ACCESS_TOKEN=（アラート用、任意）
- LINE_USER_ID=（アラート用、任意）
- MONITOR_POLL_INTERVAL=60

注意点:
- KILL_FLAG_CLEAR_ON_START=1 にすると ExecutionEngine 起動時に kill.flag を自動クリアします。production では 0 を推奨。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると .env の自動読み込みを無効化できます（テスト用途）。

---

## ログと監視

- ログ: utils/logging_setup.py により stdout と日次ローテーションなファイルログ（デフォルト logs/<app_name>.log）に出力されます。
- デフォルトでログディレクトリは `logs/`。必要に応じて LOG_DIR 環境変数で変更。
- Monitoring は system_status, trade_logs, positions, risk_logs, dashboard の各テーブルへ記録します（SQLite）。

---

## 注意事項・運用メモ

- Paper Trading 用の DB は本番 DB と分離されています（PAPER_TRADING_SQLITE_PATH）。誤って本番 DB を上書きしないよう注意してください。
- OpenAI 絡みの機能は API 負荷・コストが発生します。大量リクエストの管理・レート制御を運用側で行ってください。
- run_execution / run_monitoring は stop flag や kill flag を利用して外部から安全に停止できます（data/stop_requested.flag, data/kill.flag）。
- process_priority の設定は最初に行われますが、権限不足等で変更できない場合は警告が出てスキップされます。
- DuckDB と SQLite のパスは .env で指定可能です。データ保存先のディレクトリ作成とバックアップポリシーを運用で整備してください。

---

## ディレクトリ構成

リポジトリの主要ファイルおよびモジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings 管理（.env 自動読み込み含む）
  - config_setup.py              — .env 対話ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor 起動スクリプト

  - execution/
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py

  - monitoring/
    - monitoring_db.py
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

  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py

- data/                          — 実行時に使用するデータ/フラグ/PID 等（デフォルト）
- logs/                          — ログ出力（デフォルト）

---

## 開発・テストについて

- 自動 .env ロードは config.py の機能で、プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を読み込みます。テスト時に自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し部分はモジュール内で明確に分離されており、ユニットテストでは該当関数をモック（patch）してテストできます（各ファイル内に _call_openai_api 等の切替対象関数あり）。
- validate_config は YAML パーサーが存在すれば config/*.yaml の構文チェックを行います（PyYAML があるとより厳密）。

---

## よくあるコマンド早見表

- .env 作成:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Execution 起動:
  python -m kabusys.run_execution

- Monitoring 起動:
  python -m kabusys.run_monitoring

- Paper Trading レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

README は随時更新してください。運用開始前には .env と config/*.yaml の内容を十分に検証し、ログ／バックアップ／DB 保全の運用手順を確立してください。質問や追加のドキュメント要望があれば教えてください。