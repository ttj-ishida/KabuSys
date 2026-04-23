# KabuSys — 日本株自動売買システム

このリポジトリは、日本株向けの自動売買プラットフォーム（KabuSys）のコアライブラリ群です。
戦略・ポートフォリオ構築、モニタリング、実行エンジン、AI を使ったニュース解析などのコンポーネントを含みます。

以下はこのコードベースの概要・セットアップ・使い方・ディレクトリ構成の説明です。

---

## プロジェクト概要

KabuSys は以下の機能を備えた自動売買基盤です。

- 株価データ（DuckDB）を用いたファクター計算・リサーチ（momentum, value, volatility 等）
- ポートフォリオ構築（候補選定、重み計算、株数決定、セクター制約、レジーム乗数）
- ExecutionEngine（発注管理、リスク管理、リコンシリエーション） — 本番 / ペーパートレード切替対応
- 監視サブシステム（SystemMonitor、TradeMonitor、RiskMonitor、KillSwitch、MonitoringEngine）
- AI モジュール：ニュースのセンチメント評価（OpenAI を利用）、市場レジーム判定
- ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード・検証）
- Paper Trading 用の検証レポート生成ツール

設計方針の一部：
- DuckDB / SQLite をローカルデータベースとして使用
- 本番・ペーパートレード DB を分離可能
- 環境変数 / .env による設定管理（自動ロード機能あり）
- LLM 呼び出しは冪等性・リトライ・バリデーションを考慮して実装

---

## 主な機能一覧

- 環境設定ウィザード: python -m kabusys.config_setup
- 設定検証 CLI: python -m kabusys.validate_config
- 実行エンジン起動スクリプト: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録
- 監視プロセス起動スクリプト: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を調整可能（デフォルト 60 秒）
- Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report
- ニュース NLP による銘柄別センチメントスコアリング（OpenAI）
- 市場レジーム判定（ETF MA とマクロニュースの合成）
- ポートフォリオ構築ユーティリティ（候補選定、等重/スコア加重、位置サイズ計算）
- 監視 DB（SQLite）を使った system_status / trade_logs / positions / risk_logs / dashboard の管理

---

## 要件（主要な依存パッケージ）

少なくとも以下をインストールしてください（バージョンは任意だが最新安定推奨）:

- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config/*.yaml の内容検証を行う場合）
- （必要に応じて）その他 Execution/Broker 関連の依存

インストール例:
pip install duckdb psutil openai PyYAML

（プロジェクトに requirements.txt がない場合は上記を個別にインストールしてください）

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動

2. Python 仮想環境を作成・有効化（推奨）
   python -m venv .venv
   source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   pip install duckdb psutil openai PyYAML

4. 対話式で .env を作成（推奨）
   python -m kabusys.config_setup
   - ウィザードで必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を設定します。
   - .env は絶対に Git にコミットしないでください。

5. 設定検証（任意）
   python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit(1)）になります。

6. データディレクトリの準備
   - デフォルトでは以下のファイル・ディレクトリが使われます:
     - data/kabusys.duckdb（DuckDB、デフォルト: DUCKDB_PATH）
     - data/monitoring.db（SQLite 監視 DB、デフォルト: SQLITE_PATH）
     - data/paper_trading.db（ペーパートレード DB、PAPER_TRADING_SQLITE_PATH）
     - logs/（ログ出力先）
   必要に応じて .env でパスを上書きして下さい。

7. OpenAI API を使用する機能を使う場合は OPENAI_API_KEY を設定
   - .env に OPENAI_API_KEY=your_key を追加するか、実行時に環境変数を渡してください。

補足:
- 自動で .env を読み込む仕組みがあります（.env / .env.local）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## 重要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN （必須）
- KABU_API_PASSWORD （必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading: MockBrokerClient を使用、ペーパートレード用 DB に記録
  - live: 本番モード（慎重に設定してください）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード DB、デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレードの約定挙動）
- LOG_LEVEL（デフォルト: INFO）
- LOG_DIR（デフォルト: logs/）
- OPENAI_API_KEY（AI 機能使用時に必要）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（本番起動時に kill.flag を自動クリアするか、0/1）

簡単な .env の例:
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=your_openai_key

---

## 使い方（代表的なコマンド）

- 環境設定ウィザード（.env を作成/更新）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合はペーパートレードモードで動作します。
  - 起動時に data/stop_requested.flag が存在すると起動をしない。
  - 停止シグナルは data/stop_requested.flag によって送れます（監視プロセスからの停止など）。

- 監視プロセス起動（SystemMonitor をポーリング）
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で指定可能。
  - 監視は production 用 sqlite_path を環境に関わらず使用します（監視データは本番 DB に保存）。

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB は data/paper_trading.db。--db で別 DB を指定できます。

- ログ
  - logs/<app_name>.log に日次ローテーションでログが出力されます。
  - setup_logging() が root ロガーに StreamHandler（stdout）と TimedRotatingFileHandler を設定します。

---

## 停止・Kill フラグの仕組み

- data/stop_requested.flag
  - run_execution / run_monitoring のループを終了させるために使用。存在を検知するとプロセスは安全に終了します。

- data/kill.flag
  - KillSwitch（監視サブシステム）が条件を満たした場合に書き込まれ、ExecutionEngine に停止を促します。
  - KillSwitch はドローダウン超過やポジション数上限などの条件に基づいて flag を書き込みます。

- PID ファイル
  - 実行エンジンは data/execution.pid を使用して PID を書きます（設定で上書き可能）。

---

## 開発・テストの補助

- 自動 .env 読み込みを無効化:
  KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してテスト時に外部の .env に影響されないようにできます。

- ロギングをカスタマイズ:
  setup_logging(app_name="execution", log_dir=Path("mylogs"), level="DEBUG") を呼ぶことで出力先・レベルを変更できます。

- OpenAI 呼び出しのモック:
  tests やローカル検証では kabusys.ai.news_nlp._call_openai_api 等をパッチしてテスト可能です（モジュール内で明示的にテストフレンドリーに設計されています）。

---

## ディレクトリ構成（主なファイル/モジュール）

（以下は src/kabusys 以下を想定）

- kabusys/
  - __init__.py
  - config.py                 — 環境変数/.env 読み込み・Settings クラス
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - ai/
    - __init__.py
    - news_nlp.py              — ニュースセンチメント（OpenAI）関連
    - regime_detector.py      — 市場レジーム判定（MA + マクロニュース）
  - research/
    - __init__.py
    - factor_research.py      — momentum / value / volatility 等のファクター計算（DuckDB）
    - feature_exploration.py  — 将来リターン / IC / 統計サマリ
  - portfolio/
    - __init__.py
    - portfolio_builder.py     — 候補選定・重み計算
    - risk_adjustment.py       — セクター制約・レジーム乗数
    - position_sizing.py       — 株数計算・制約・ラウンド
  - monitoring/
    - monitoring_db.py        — SQLite access 層（system_status, trade_logs, positions, risk_logs, dashboard）
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - system_monitor.py       — システム状態・データ鮮度チェック
    - risk_monitor.py         — ドローダウン・ポジション上限チェック
    - kill_switch.py          — kill.flag 管理
    - trade_monitor.py        — （発注・約定に関する監視、コード内で参照）
    - alert_manager.py        — （通知送信の抽象化、コード内で参照）
  - execution/
    - execution_engine.py     — ExecutionEngine 本体（発注ループ等）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py       — ブローカークライアント生成（本番/Mock 切替）
  - data/                      — 実行時生成される DB やフラグファイル（例: data/*.db, data/kill.flag）
  - utils/
    - logging_setup.py        — 統一的なログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定
    - その他ユーティリティ

（上記はコード内の import / ファイル名に基づいた抜粋です）

---

## 備考・運用上の注意

- 本番運用（KABUSYS_ENV=live）では .env の内容を厳格に管理し、LINE 通知等のアラート設定を有効にしてください。
- kill.flag や stop_requested.flag の取り扱いは慎重に。KILL_FLAG_CLEAR_ON_START=1 は本番では推奨されません（Kill Switch が誤ってクリアされる恐れがあるため）。
- OpenAI や外部 API を使う処理はネットワークエラーや API エラーを考慮してリトライ・フォールバック実装がされていますが、API キーやクォータを監視してください。
- データベースファイル（SQLite / DuckDB）は定期的なバックアップを推奨します。
- 実装の一部（Execution 関連や TradeMonitor / AlertManager）については、ユーザーの実運用環境に合わせたブローカークライアントの実装や通知設定が必要です。

---

もし README に含めたい追加項目（例: サンプル .env の完全版、運用チェックリスト、デプロイ手順、CI 設定など）があれば教えてください。必要に応じて追記・調整します。