# KabuSys

日本株自動売買フレームワーク（小規模プロダクション / リサーチ用）

このリポジトリは、取引実行（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター研究、AI（ニュースセンチメント / レジーム判定）等の機能を備えた自動売買システムの基盤コード群です。各コンポーネントはモジュール化され、ローカル開発・ペーパートレード・本番（live）での動作を想定しています。

---

## 概要

- 実行エンジン（ExecutionEngine）: ブローカークライアントを介した発注管理、オーダーリポジトリ、リスク制御、再整合（reconciler）等を担当。
- 監視（Monitoring）: システム稼働状況、データ鮮度、発注ログ、リスク指標を定期的に記録・評価し、Kill Switch を発動（flag ファイル）する。アラート通知（LINE 等）も想定。
- ポートフォリオ構築: 候補選定、重み付け、リスク調整、ポジションサイズ計算の純粋関数群（テスト容易）。
- リサーチ: DuckDB を用いたファクター計算（モメンタム／バリュー／ボラティリティ）・将来リターン計算・IC 計算等。
- AI: OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価（ai_scores）およびマクロセンチメントを加味した市場レジーム判定。
- ユーティリティ: ログ設定、プロセス優先度設定、.env ウィザード、設定検証ツール等。

---

## 主な機能一覧

- Execution
  - 実取引 / ペーパートレード切替（KABUSYS_ENV）
  - ブローカー抽象化（BrokerClientFactory）
  - リスク管理（RiskManager）
  - 注文管理／リポジトリ（OrderManager / OrderRepository）
- Monitoring
  - システムリソース監視（CPU/メモリ/ディスク）
  - プロセス死活検知（execution.pid の監視）
  - トレードログ、ポジション、リスクログ、ダッシュボード永続化（SQLite）
  - Kill Switch（条件により data/kill.flag を書き込み）
  - 監視用ポーリングループ（MONITOR_POLL_INTERVAL で間隔指定可）
- Portfolio
  - 候補選定、等金額／スコア重み付け
  - セクター上限チェック、レジーム乗数
  - ポジションサイズ計算（ロット丸め、aggregate cap）
- Research
  - DuckDB ベースのファクター計算（momentum, value, volatility）
  - 将来リターン／IC／ファクター統計
- AI
  - ニュースを LLM でスコア化し ai_scores テーブルに保存
  - マクロニュース + ETF MA200 乖離から日次レジーム判定
- Tools
  - .env 設定ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成（tools.paper_verification_report）

---

## セットアップ手順

前提:
- Python 3.10+（型アノテーションや機能が想定）
- DuckDB、psutil、openai 等の Python パッケージが必要

1. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb psutil openai
   - 開発用途で YAML 検証をする場合: pip install PyYAML
   - （requirements.txt がある場合はそれを使用）

3. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 生成された .env を設定（機密値は非コミット）
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - そのほか（任意/デフォルトがあるものも含め）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_LEVEL, LOG_DIR など
   - AI を使う場合:
     - OPENAI_API_KEY を設定（news_nlp / regime_detector で使用）

4. 設定検証（起動前推奨）
   - python -m kabusys.validate_config
   - 問題がある場合は出力を確認して .env / config/*.yaml を修正

5. データディレクトリの作成（自動で作成される場合が多いですが事前に作ると安全）
   - mkdir -p data logs

---

## 使い方（実行方法）

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV に依存:
    - paper_trading: MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録して本番 DB と分離
    - live: 本番用ブローカークライアントを使用（要設定）
  - 起動時、data/stop_requested.flag が存在すると起動を中止します
  - data/execution.pid に PID を書きます（設定: Settings.pid_file_path）

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒、デフォルト 60）
  - 監視は本番 sqlite_path を使う（KABUSYS_ENV に関わらず）
  - 停止方法: data/stop_requested.flag を作成するとループを終了

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - データベース指定: --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

- AI モジュール（プログラム的に呼び出す）
  - ニューススコア:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key=None)  # api_key 無指定なら環境変数 OPENAI_API_KEY を使用
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=None)

- 設定検証 CLI
  - python -m kabusys.validate_config
  - --strict をつけると警告も失敗扱い（exit 1）

- 環境設定ウィザード
  - python -m kabusys.config_setup

---

## 主要な環境変数（抜粋）

- 必須（最低限）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 動作モード / ログ / DB
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
  - LOG_DIR: ログ保存ディレクトリ（デフォルト: logs）
  - DUCKDB_PATH: data/kabusys.duckdb（DuckDB）
  - SQLITE_PATH: data/monitoring.db（監視 DB）
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用 DB）
  - PID_FILE_PATH: data/execution.pid

- Paper/Mock 関連
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）

- AI
  - OPENAI_API_KEY（news_nlp / regime_detector）
  - OPENAI の使用には API key が必要

- 監視関連
  - MONITOR_POLL_INTERVAL: 監視ループ間隔（秒、デフォルト 60）
  - KILL_FLAG_PATH: data/kill.flag（Kill Switch のパス）
  - KILL_FLAG_CLEAR_ON_START: 1 にすると起動時に kill.flag を自動でクリア（本番では危険）

---

## 停止 / Kill Switch の仕組み

- 停止フラグ
  - data/stop_requested.flag を作成すると run_execution / run_monitoring のループが検知して終了します（主に外部プロセスで停止指示するため）。
- Kill Switch
  - 監視で重大なリスク（ドローダウン超過、ポジション数上限超過等）を検出した場合、data/kill.flag に理由を書き込むことで ExecutionEngine に停止を促します（実行エンジンは起動時に kill.flag の存在をチェックし、必要に応じて起動を中止／停止動作を行います）。

---

## ログ / データファイル

- ログ: デフォルト logs/ ディレクトリに日次ローテートで保存（TimedRotatingFileHandler）。コンソールは stdout 出力。
- SQLite（監視）: data/monitoring.db（Settings.sqlite_path）
- DuckDB（分析）: data/kabusys.duckdb（Settings.duckdb_path）
- Paper Trading DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）
- フラグファイル: data/stop_requested.flag, data/kill.flag
- PID ファイル: data/execution.pid

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定読み込みロジック
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
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

（上記以外にも補助モジュール・コードが含まれます）

---

## 開発 / 貢献メモ

- 各モジュールは単体テストしやすい純粋関数／クラス設計を志向しています。DB や外部 API はインタフェースで抽象化し、テスト用にモックできます。
- AI 呼び出し部分はリトライやフォールバック（API失敗時は安全側にフォールバック）を組み込んでいますが、プロダクションでの使用時はレート制限やコストに注意してください。
- .env は絶対にソース管理にコミットしないでください（config_setup の注記参照）。

---

必要であれば、この README に「詳細な起動例」「環境変数の完全一覧」「よくあるトラブルシューティング」などを追加します。どの項目を拡張しますか？