# KabuSys

日本株自動売買システムの参考実装（ライブラリ / 実行スクリプト群）

このREADMEはリポジトリに含まれる主要なモジュール群と起動方法、セットアップ手順をまとめたものです。

> 注意: 実運用に使う場合は各種設定・認証情報の管理と十分なテストを行ってください。  
> 本リポジトリは設計・実装例を示す目的のコードベースです。

---

目次
- プロジェクト概要
- 機能一覧
- 必要条件（依存ライブラリ）
- セットアップ手順
- 使い方（起動・CLI）
- 主要環境変数（例）
- 停止・Kill Switch の仕組み
- ディレクトリ構成（抜粋）
- 補足・注意点

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したシステム実装例です。  
戦略の研究・ファクター計算、ポートフォリオ構築、発注エンジン、監視・アラート、AI を用いたニュース評価などのコンポーネントを含みます。  
DuckDB を用いた時系列 / 財務データ分析、SQLite による監視ログ保存、OpenAI API を使ったニュースセンチメント評価などを組み合わせています。

主な設計方針:
- モジュール化（research / portfolio / execution / monitoring / ai / utils）
- 本番とペーパートレード（paper_trading）を分離
- 監視・Kill Switch による安全停止
- ロギングとプロセス優先度設定を統一

---

## 機能一覧

- 環境設定ウィザード（.env 生成 / 更新）: kabusys.config_setup
- 設定検証 CLI（.env + config/*.yaml の検証）: kabusys.validate_config
- Execution エンジン起動スクリプト: run_execution.py
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使いデータは paper_trading.db に記録
  - プロセス優先度設定、PID 管理、停止フラグ検出
- Monitoring（監視）起動スクリプト: run_monitoring.py
  - システムリソース、データ鮮度、取引・リスクの監視
  - Kill Switch（条件を満たしたら data/kill.flag を作成）
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能
  - 監視用の SQLite は環境に関係なく本番の sqlite_path を使用する設計
- MonitoringDB: SQLite を用いた監視ログの永続化（system_status / trade_logs / risk_logs / positions / dashboard）
- Risk モニタ、Trade モニタ、System モニタ、アラート管理（AlertManager は別実装）
- Research: ファクター計算（momentum / volatility / value）や特徴量探索（IC 等）
- Portfolio: 候補選定、重み計算、ポジションサイズ計算、セクター制約やレジーム乗数
- AI:
  - news_nlp: ニュースを集約して OpenAI に投げセンチメントを ai_scores テーブルへ記録
  - regime_detector: MA とマクロニュースを合成して市場レジーム判定、market_regime へ保存
- ツール: Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

---

## 必要条件（依存ライブラリ）

代表的な依存（プロジェクトに requirements.txt は含まれていないため適宜インストールしてください）:
- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config ファイル検証を行う場合）
- （その他、実装の execution/broker 関連で追加の依存が必要になる場合があります）

例:
pip install duckdb psutil openai pyyaml

---

## セットアップ手順

1. リポジトリをクローン／配置し、仮想環境を作成して有効化します。
   - python -m venv .venv
   - source .venv/bin/activate  （Windows は .venv\Scripts\activate）

2. 必要パッケージをインストールします（上記参照）。

3. .env を作成する
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - または手動で .env を作成（例は下記「主要環境変数（例）」参照）

4. 設定の検証（任意）
   - python -m kabusys.validate_config
   - 警告まで厳格にチェックしたい場合は --strict を付与

5. データディレクトリ作成（必要に応じて）
   - デフォルトでは data/ や logs/ が使用されます（コードが自動的に作成する場合もある）

---

## 使い方

主要な実行コマンド例:

- ExecutionEngine（取引実行）起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）を使用
    - 起動時に data/stop_requested.flag を検出すると起動を中止
    - 実行中は data/execution.pid に PID を書きます
    - 停止は stop flag（data/stop_requested.flag）を書けば検出して停止

- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング秒数を上書き（デフォルト 60 秒）
    - 監視は環境に関係なく settings.sqlite_path（デフォルト data/monitoring.db）を使用
    - 監視ループは data/stop_requested.flag の存在で終了

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間を指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

ログ:
- デフォルト出力先: logs/<app_name>.log （app_name は "execution" / "monitoring" 等）
- コンソールは標準出力（stdout）に出ます

停止方法（運用上の操作）:
- 実行プロセスに対して即時停止を必要とする場合は data/stop_requested.flag を作成すると run_* スクリプトは検出して終了します。
- リモートで ExecutionEngine に停止を伝えたい場合は Kill Switch（data/kill.flag）を作成するしくみがあります（監視モジュールが評価して作成することが主）。

---

## 主要環境変数（例）

必須:
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
- KABU_API_PASSWORD=your_kabu_api_password_here

推奨／オプション（デフォルト値を示す）:
- KABUSYS_ENV=development|paper_trading|live  （デフォルト: development）
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- LOG_LEVEL=INFO
- LOG_DIR=logs
- OPENAI_API_KEY=（AI 機能を使う場合に必要）
- MONITOR_POLL_INTERVAL=60（run_monitoring のポーリング秒数を上書き）

その他:
- PAPER_FILL_MODE=instant|partial|never|reject（paper_trading 用の約定モード）
- KILL_FLAG_CLEAR_ON_START=0|1 （ExecutionEngine 起動時に kill.flag を自動クリアするか）
- PID_FILE_PATH（デフォルト data/execution.pid）

.env の例（機密情報はマスクしてください）:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

---

## 停止・Kill Switch の仕組み

- stop_requested.flag（data/stop_requested.flag）
  - run_execution / run_monitoring のメインループはこのフラグファイルの存在を定期チェックし、存在すれば安全に終了します（外部運用からプロセスを終了する安全な手段）。

- kill.flag（data/kill.flag）
  - 監視（MonitoringEngine / KillSwitch）が重大なリスク（ドローダウン閾値超過、ポジション上限超過等）を検出した場合に作成されます。
  - ExecutionEngine は起動時・運用中に kill.flag の存在を検査して安全停止する実装があります（設定による自動クリア動作に注意）。

- PID ファイル
  - ExecutionEngine は data/execution.pid を使用して自身の PID を保存します。stale PID 検出などの仕組みに利用します。

---

## ディレクトリ構成（抜粋）

プロジェクトルート（src ディレクトリがパッケージのルート）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py        — ログ設定
    - process_priority.py     — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py        — SQLite テーブル初期化 / 操作
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py        — （取引監視、コードベースに実装あり）
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py        — （アラート送信の抽象・実装場所）
  - execution/                — Execution エンジン周辺（ブローカーファクトリ等）
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
  - monitoring/monitoring_db.py
  - tools/
    - paper_verification_report.py

その他:
- config/ （yaml 設定ファイル群: system_config.yaml 等）
- data/ （デフォルトの DB / フラグ / pid 等。実行時に生成される）
- logs/ （ログ出力先、デフォルト）

---

## 補足・注意点

- 監視用 SQLite（monitoring.db）は run_monitoring が KABUSYS_ENV にかかわらず settings.sqlite_path を使用します。つまり監視データは paper_trading と本番で分離されない設計になっている部分に注意してください（設計での意図的な仕様）。
- run_execution は KABUSYS_ENV=paper_trading の場合 paper_sqlite_path（data/paper_trading.db）を使用し、本番 DB と完全に分離して動作します。
- OpenAI を使う機能（news_nlp / regime_detector）を利用するには OPENAI_API_KEY を設定してください。API 呼び出しはリトライ・フェイルセーフ（失敗時はスコアを 0.0 にフォールバック等）の実装がありますが、利用時はコストとレート制限に注意してください。
- .env やシークレットは決してリポジトリにコミットしないでください（config_setup のヘッダーにも警告があります）。
- 実環境で運用する際は必ず十分なテストとリスク管理を行ってください。特に KABUSYS_ENV=live では実際に発注が行われます。

---

問題・拡張・貢献
- バグ報告や機能追加提案は Issue を作成してください。Pull Request も歓迎します。
- 実運用で使う場合は監査・追加の安全ガード（テスト注文、モニタリング強化、冗長化）を行うことを推奨します。

---

以上。README の内容で不足があれば、特に知りたい操作（例: ExecutionEngine の詳細な起動オプションや monitoring の設定方法）を指定してください。必要に応じてコマンド例や .env テンプレートを追加で作成します。