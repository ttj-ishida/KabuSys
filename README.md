# KabuSys

日本株向け自動売買システム（ライブラリ & 起動スクリプト群）

このリポジトリは、シグナル生成 → ポートフォリオ構築 → 発注（実/ペーパー）までを想定したモジュール群と、監視・アラート・レポート作成用のツール群を含みます。実行スクリプトは Python モジュールとして提供され、環境変数（.env）で動作を制御します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（コマンド例）
- 環境変数（主要）
- 停止 / Kill Switch の仕組み
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は、日本株の自動売買を想定したコンポーネント群です。主要コンポーネントは以下のとおりです。

- ExecutionEngine（発注エンジン）
  - 本番 / ペーパートレード（MockBroker）を切り替え可能
  - リスク管理（ポジション上限、ドローダウン等）
- Monitoring（監視）
  - システム状態・データ鮮度・発注ログの監視
  - Kill Switch（致命的条件で Execution を停止）
- Portfolio（ポートフォリオ構築）
  - 候補選定、重み付け、ポジションサイズ算出、セクター上限適用などの純粋関数群
- Research（ファクター計算・特徴量探索）
  - Momentum / Volatility / Value 等のファクター計算
  - IC（Information Coefficient）計算、将来リターン算出
- AI モジュール
  - ニュースの NLP スコアリング（OpenAI を利用）
  - 市場レジーム判定（MA + LLM）
- ツール
  - ペーパートレード検証レポート生成 等

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動（本番 / paper_trading 切替）
  - run_monitoring.py: SystemMonitor（ポーリング）起動（MONITOR_POLL_INTERVAL で間隔指定可）
- 設定関連
  - config_setup.py: .env を対話式で作成/更新するウィザード
  - validate_config.py: .env および config/*.yaml の整合性チェック（--strict オプションあり）
- Monitoring
  - system_monitor / trade_monitor / risk_monitor を統合した MonitoringEngine
  - monitoring_db: SQLite ベースの永続化レイヤ
  - kill_switch: 条件に応じて data/kill.flag を生成
- Portfolio
  - 候補選定、等重・スコア重み、リスクベースのポジション決定、セクター制限など
- Research
  - DuckDB を使ったファクター算出、forward return、IC、統計サマリ
- AI（OpenAI）
  - news_nlp.score_news: ニュースを LLM に投げて銘柄ごとのセンチメントを ai_scores テーブルへ格納
  - regime_detector.score_regime: MA200 とマクロ記事の LLM 結果でレジーム判定
- ツール
  - tools.paper_verification_report: ペーパートレード DB から検証レポートを出力

---

## セットアップ手順

前提: Python 3.10+ を推奨（型ヒントや新しい構文に依存するため）。プロジェクトルートには pyproject.toml がある想定。

1. リポジトリをチェックアウト
   - 任意のディレクトリで git clone する

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 基本的に以下パッケージが必須または推奨:
     - duckdb
     - psutil
     - openai (AI モジュールを使う場合)
     - PyYAML（validate_config の YAML 検証を行うなら）
   - 例:
     - pip install duckdb psutil openai PyYAML

4. .env ファイルの作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - または .env.example を参考に .env を作成する（このプロジェクトでは .env.example は想定されています）

5. 設定の検証（任意だが必須項目のチェックに有用）
   - python -m kabusys.validate_config
   - すべて通す場合は --strict を付けると警告も失敗扱いになる:
     - python -m kabusys.validate_config --strict

6. データディレクトリと DB の初期化
   - 多くのスクリプトは実行時に必要なディレクトリを作成します。デフォルト DB パス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - SQLite (paper trading): data/paper_trading.db

---

## 使い方

実行スクリプトはモジュール実行方式で起動します。各コマンドの例:

- .env を作成:
  - python -m kabusys.config_setup

- 設定を検証:
  - python -m kabusys.validate_config
  - strict モード（警告も FAIL）:
    - python -m kabusys.validate_config --strict

- ExecutionEngine の起動:
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV を "paper_trading" にすると MockBrokerClient が使われ、書き込み先 SQLite は data/paper_trading.db（環境変数で上書き可）になります。

- Monitoring（定期ポーリング）の起動:
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で変更:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring  # 30秒間隔

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を指定する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI モジュールを使った処理（例: ニューススコアリング）
  - 環境変数に OPENAI_API_KEY を設定するか、関数呼び出し時に api_key を渡してください。
  - 例（スクリプトから直接呼ぶ場合）:
    - export OPENAI_API_KEY=sk-...
    - 実装上は Python から kabusys.ai.news_nlp.score_news(conn, date, api_key=None) を呼びます。

ログ
- setup_logging によりログは stdout と logs/<app_name>.log に出力されます（デフォルト logs ディレクトリ、日次ローテーション、30日保持）。

停止方法
- run_execution / run_monitoring はプロジェクトの data/stop_requested.flag を監視します。このファイルを作成するとスクリプトは安全に終了します。
- Kill Switch: リスク条件が成立すると data/kill.flag が書き込まれ、ExecutionEngine はこれを検知して停止します。

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV
  - 値: development | paper_trading | live
  - default: development
  - 動作モードを決定。paper_trading では MockBroker を使用し DB を分離。

- JQUANTS_REFRESH_TOKEN
  - J-Quants API のリフレッシュトークン（必須）

- KABU_API_PASSWORD
  - kabuステーション API のパスワード（必須）

- DUCKDB_PATH
  - DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）

- SQLITE_PATH
  - 監視用 SQLite パス（デフォルト: data/monitoring.db）

- PAPER_TRADING_SQLITE_PATH
  - paper_trading 用 SQLite（デフォルト: data/paper_trading.db）

- LOG_LEVEL
  - ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

- LOG_DIR
  - ログ保存先ディレクトリ（デフォルト: logs/）

- OPENAI_API_KEY
  - OpenAI を利用する AI モジュールで必要

- MONITOR_POLL_INTERVAL
  - run_monitoring のポーリング間隔（秒）。デフォルト 60 秒。

- PID_FILE_PATH
  - ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）

- KILL_FLAG_PATH
  - kill.flag のパス（デフォルト: data/kill.flag）

- KILL_FLAG_CLEAR_ON_START
  - 起動時に kill.flag を自動でクリアするか（0/1、本番では 0 推奨）

- PAPER_FILL_MODE
  - ペーパートレード時の約定挙動（instant/partial/never/reject）

---

## 停止 / Kill Switch の仕組み

- 停止要求（グローバル）
  - data/stop_requested.flag を作成すると run_execution / run_monitoring は検知して安全に終了します。
- Kill Switch（自動停止）
  - monitoring の RiskMonitor 等が危険な状況（例: ドローダウン閾値超過、ポジション数上限超過）を検知すると、kill_switch が data/kill.flag に理由を書き込みます（既存の場合は上書きしない）。ExecutionEngine 起動時や稼働中にこのファイルを検出するとエンジンは停止処理を行います。
- 注意: 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にして、誤ってクリアされないようにしてください。

---

## ディレクトリ構成（主なファイル）

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py  (参照あり、実装ファイルは省略されているが概念あり)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (参照元あり)
  - execution/
    - execution_engine.py (参照あり)
    - broker_factory.py (参照あり)
    - order_manager.py (参照あり)
    - order_repository.py (参照あり)
    - reconciler.py (参照あり)
    - risk_manager.py (参照あり)
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/
    - (上記)
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - data/ (runtime に生成される想定)
    - kill.flag
    - stop_requested.flag
    - execution.pid
    - monitoring.db (デフォルト SQLITE_PATH)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH)

上記は主要ファイルのみ抜粋しています。実際のプロジェクトではさらに execution の細部（Broker クライアント実装など）や data/ に関するスクリプトが存在します。

---

## 注意事項 / 運用上のヒント

- .env は決してバージョン管理にコミットしないでください（README にも警告あり）。
- 本番稼働時は KABUSYS_ENV=live、KILL_FLAG_CLEAR_ON_START=0 を推奨します。
- OpenAI を用いる機能は API 費用が発生します。API キーと呼び出し頻度を運用ポリシーに合わせて管理してください。
- run_execution/run_monitoring は最初にプロセス優先度を "high" に設定します（psutil による実装）。権限によって設定できない場合は警告ログが出ますが処理は継続します。
- DuckDB は分析用途に利用されるため大容量データを想定しています。バックアップや配置場所の設計をしてください。
- validate_config により設定漏れを事前検出できます。CI で呼ぶと安全です。

---

この README はコードベースの主要点をまとめたものです。詳細は各モジュールの docstring（ソースコード内コメント）を参照してください。必要であれば、起動手順の自動化スクリプト（systemd ユニット / Dockerfile / docker-compose）の例も作成できます。