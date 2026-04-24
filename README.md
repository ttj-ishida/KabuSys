# KabuSys

日本株向けの自動売買システム（モジュール群）のリポジトリ用 README（日本語）

---

## プロジェクト概要

KabuSys は日本株の自動売買／リサーチ／監視を目的とした Python 製モジュール群です。  
主な機能はシグナル生成・ポートフォリオ構築・発注（ExecutionEngine）・監視（Monitoring）・ペーパートレード検証・AI を使ったニュースセンチメント評価などを含みます。設計方針として、DB（SQLite / DuckDB）を用いたデータ永続化、環境変数ベースの設定、フェイルセーフ／冪等性を重視しています。

---

## 機能一覧

- Environment / 設定管理
  - .env 読み込み（.env / .env.local、自動ロード）
  - 設定ウィザード（対話式で .env を作成）
  - 起動前設定検証ツール（必須環境変数・config/*.yaml チェック）

- Execution（発注）
  - ExecutionEngine による注文管理（本番 / ペーパートレードの分離）
  - ブローカークライアント抽象化（実ブローカーと Mock の切替）
  - OrderManager / RiskManager / Reconciler 等の組合せ起動

- Monitoring（監視）
  - SystemMonitor：プロセス生存・CPU/メモリ/ディスク・データ鮮度監視
  - TradeMonitor：発注/約定ログ監視（滞留／異常検出）
  - RiskMonitor：ドローダウン／ポジション上限監視、Kill Switch（停止フラグ書き込み）
  - MonitoringEngine：上記モニタを束ねたポーリングループ

- Portfolio（構築）
  - 候補選定、等加重／スコア加重、ポジションサイジング（単元丸め）
  - セクター上限・レジーム係数の適用

- Research
  - DuckDB を用いたファクター計算（Momentum / Value / Volatility）
  - 将来リターン計算・IC 計測・特徴量サマリー

- AI（オプション）
  - ニュース NLP（OpenAI を利用した銘柄別センチメント -> ai_scores）
  - レジーム判定（MA + マクロニュースセンチメント合成 -> market_regime）

- ユーティリティ
  - ロギング設定（stdout + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定
  - Paper Trading 検証レポート生成ツール

---

## 前提条件

- Python 3.9+（ソースは typing | match 機能は使っていませんが、最新の安定版を推奨）
- 必要な外部ライブラリ（例: duckdb, psutil, openai, PyYAML 等）をインストールしてください。
  - requirements.txt がない場合は、使用機能に応じて個別にインストールしてください。
    - 例: pip install duckdb psutil openai PyYAML

- OpenAI を使う機能（news_nlp / regime_detector）は環境変数 OPENAI_API_KEY が必要です。

---

## セットアップ手順（基本）

1. リポジトリをクローン
   - git clone ...

2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - （requirements.txt が無い場合は必要なパッケージを個別にインストール）

4. .env の初期設定（対話式ウィザード）
   - python -m kabusys.config_setup
     - 対話で J-Quants トークン、kabu API パスワード等を入力します。
     - 生成された .env をプロジェクトルートに保存します（注意: .env を Git にコミットしない）。

5. 設定の検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

6. 必要ディレクトリ作成（自動では作成される部分もありますが、手動で作っておくと安心）
   - data/ （デフォルト DB 等）
   - logs/ （ログ出力先）

---

## 環境変数（主要）

必須（validate_config により検出）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要オプション:
- KABUSYS_ENV: execution モード
  - 値: development / paper_trading / live（デフォルト: development）
  - paper_trading の場合は発注は MockBrokerClient に切替え、専用 SQLite（data/paper_trading.db）を使用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
- PAPER_FILL_MODE: ペーパートレードの成行/部分約定等の挙動（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"1" = クリア）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、run_monitoring 用。デフォルト 60秒）

ファイルフラグ:
- data/kill.flag: Kill Switch（Monitoring が基準を満たすと書き込まれる。ExecutionEngine はこの存在をチェックして停止）
- data/stop_requested.flag: 手動で監視/エンジンの停止を要求する際に使用（run_* スクリプトで参照）
- data/execution.pid: ExecutionEngine の PID（実行中に書き込み）

---

## 使い方（起動例・コマンド）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine の起動（発注エンジン）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB に記録されます。
  - 停止は data/stop_requested.flag を作成するか、プロセスに SIGINT（Ctrl-C）を送る。

- Monitoring（監視ループ）の起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト 60）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数の代わりに指定可能）

- AI 関連（ニュース NLP / レジーム判定）
  - OpenAI API キー（OPENAI_API_KEY）が必要。
  - kabusys.ai.news_nlp.score_news / kabusys.ai.regime_detector.score_regime を呼び出して使用。

---

## ロギング

- 共通ロギング初期化: kabusys.utils.logging_setup.setup_logging(app_name="execution" | "monitoring" | ...)
  - stdout（StreamHandler） + 日次ロールファイル（logs/<app_name>.log）
  - 環境変数 LOG_DIR でログ保存先を変更
  - ログレベルは LOG_LEVEL または setup_logging の引数で指定

---

## データベース

- DuckDB（分析用）
  - デフォルト: data/kabusys.duckdb
- SQLite（監視ログ / orders / paper_trading）
  - 監視用: data/monitoring.db
  - ペーパートレード: data/paper_trading.db（KABUSYS_ENV=paper_trading 時に使用される）

Monitoring 用の DB スキーマは init_monitoring_db() によって自動作成（冪等）。マイグレーションも一部自動化されています。

---

## Kill Switch / 停止フラグについて

- KillSwitch（モニタリング側）が重大なリスク（ドローダウン超過、ポジション上限超過など）を検知すると data/kill.flag を書き込みます。ExecutionEngine は Settings.kill_flag_path（デフォルト data/kill.flag）でこのフラグをチェックして停止します。
- 起動時に KILL_FLAG_CLEAR_ON_START=1 をセットすると起動時に kill.flag を自動クリアします（本番環境では危険なので推奨しません）。
- 手動停止リクエストには data/stop_requested.flag を作成します（run_execution / run_monitoring が検知して終了します）。

---

## ディレクトリ構成（主要ファイル）

例: src/kabusys 以下の主要ファイル・サブパッケージ

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリング起動スクリプト

  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
    - __init__.py

  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
    - trade_monitor.py       (ファイルはリストに含まれています)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       (アラート管理、外部通知用)
    - __init__.py

  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
    - __init__.py

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

（上記は主要モジュールの一覧。実際のファイルや追加モジュールが存在する可能性があります。）

---

## 開発・運用の注意点（抜粋）

- .env は機密情報を含むため決して Git にコミットしないでください。
- KABUSYS_ENV=live の場合は本番運用になります。LINE 通知等の設定が正しいか事前に validate_config で確認してください。
- Monitoring は監視用テーブルを環境にかかわらず本番 sqlite_path に書き込みます（run_monitoring の実装に基づく）。
- Paper trading は本番 DB と分離されます（settings.paper_sqlite_path を使用）。
- OpenAI を利用する処理は外部 API 通信に依存するため、API エラーはフェイルセーフとして処理される設計ですが、API キーと使用量に注意してください。
- run_execution と run_monitoring はプロセス優先度を "high" に試みます（psutil による設定。権限不足の場合は警告が出ます）。

---

## よく使うコマンド（まとめ）

- 環境作成 / 依存インストール
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install -r requirements.txt

- .env 作成（ウィザード）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行（本番/ペーパートレード）
  - python -m kabusys.run_execution

- 監視（常駐ポーリング）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要に応じて README の不足箇所（依存関係の正確なリストやデプロイ手順、systemd / Supervisor 用のユニット定義など）を補足します。追加で含めたい項目や出力例があれば教えてください。