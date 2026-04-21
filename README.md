# KabuSys

日本株自動売買システムのパッケージ（ドキュメント版 README）。  
この README はリポジトリ内の主要スクリプト・設定・実行手順を分かりやすくまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買（ストラテジー、ポートフォリオ構築、発注、監視、研究用ファクター計算、AI を用いたニュース解析など）を目的としたモジュール群です。  
モジュールは本番（live）、ペーパートレード（paper_trading）、開発（development）向けの分離を念頭に設計されており、SQLite / DuckDB を用いたローカル永続化、OpenAI（ニュース NLP）連携、監視・Kill Switch 機構を備えます。

主要な特徴：
- ExecutionEngine（発注エンジン）と Monitoring（監視）を独立したプロセスで実行可能
- Paper Trading モードで本番 DB と完全分離（data/paper_trading.db）
- DuckDB を用いた研究／ファクター計算（prices_daily / raw_financials 等）
- OpenAI を用いたニュースセンチメント（news_nlp）・レジーム判定（regime_detector）
- kill.flag を使った安全な停止（Kill Switch）
- .env 対話式ウィザード、起動前設定検証 CLI を提供

---

## 機能一覧

- execution
  - 発注エンジン（ExecutionEngine）
  - BrokerClientFactory による実口座 / MockBroker の切替（KABUSYS_ENV=paper_trading）
  - RiskManager / OrderManager / Reconciler 等の実装（発注・リスク管理）
- monitoring
  - SystemMonitor：CPU/メモリ/Disk/プロセス稼働・データ鮮度監視
  - TradeMonitor：滞留注文や約定異常の検出（trade_logs 参照）
  - RiskMonitor：ドローダウン・ポジション上限などの監視とアラート
  - KillSwitch：条件に応じて data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringDB：監視ログ用 SQLite テーブル管理（冪等な init）
- portfolio
  - 候補選定・重み計算・ポジションサイズ算出（等金額・スコア・リスクベース）
  - セクターキャップやレジーム乗数の適用
- research
  - ファクター計算（momentum, volatility, value）
  - 将来リターン、IC、統計サマリー等
- ai
  - news_nlp: raw_news をまとめて OpenAI に送信し ai_scores を書き込む
  - regime_detector: ETF の MA200 とマクロニュースで市場レジーム判定
- tools
  - paper_verification_report: ペーパートレード DB を解析し PASS/FAIL レポート作成
- utils
  - logging_setup（統一ログ設定、日次ローテート）
  - process_priority（優先度・CPU affinity 設定）
- CLI 補助
  - config_setup: .env を対話式で作成/更新
  - validate_config: .env と config/*.yaml の事前検証（--strict オプションあり）

---

## 前提 / 必要要件

（プロジェクトに提供された requirements.txt がない場合の代表的な依存）
- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config YAML 検証に必要だが必須ではない）
- （その他プロジェクト固有の依存があれば requirements.txt を参照）

推奨：仮想環境（venv / virtualenv / poetry 等）を使用してください。

---

## セットアップ手順

1. リポジトリをクローン、またはソースを配置
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （プロジェクトに requirements.txt があれば `pip install -r requirements.txt`）
4. 環境変数の準備
   - 対話式で .env を作成する（推奨）
     - python -m kabusys.config_setup
   - もしくは .env を手動で作る（下記「主要環境変数」を参照）
   - .env 作成後、設定を検証する:
     - python -m kabusys.validate_config
     - 警告を FAIL 扱いにする場合は `--strict` を付ける
5. 初回実行前に data/ と logs/ は自動作成されますが、権限等で失敗する場合は手動で作成してください。

---

## 主要な環境変数（代表例）

- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）デフォルト: development
  - paper_trading: MockBrokerClient を使用、DB は data/paper_trading.db
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（monitoring）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード時の SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant|partial|never|reject、デフォルト: instant）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- OPENAI_API_KEY: OpenAI API キー（news_nlp, regime_detector で必要）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）

自動 .env 読み込みについて:
- プロジェクトルートが特定できる場合、起動時に `.env` と `.env.local` を自動ロードします（OS 環境変数が優先）。
- 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 実行方法（使い方）

プロジェクトルートで以下を実行します。モジュールはパッケージとして実行可能です。

- 設定ウィザード（.env の対話的作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（警告も失敗）
    - python -m kabusys.validate_config --strict

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - オプション
    - ポーリング間隔を環境変数で上書き: `MONITOR_POLL_INTERVAL=30` （デフォルト 60 秒）
  - 注意: Monitoring は環境（KABUSYS_ENV）にかかわらず `Settings.sqlite_path`（デフォルト data/monitoring.db）を使用します。

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、デフォルトで data/paper_trading.db に書き込みます。本番 DB と完全分離されます。
  - 実行プロセス優先度は起動時に "high" に設定されます（set_process_priority）。

- 停止制御
  - 手動で ExecutionEngine を停止したい場合は `data/kill.flag` を作成または書き込みします（KillSwitch の判定により停止）。
  - run_* スクリプトは `data/stop_requested.flag` が存在するとループを終了します（stop フラグ：run_monitoring/run_execution が確認）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 環境変数 `PAPER_TRADING_SQLITE_PATH` または `--db` で DB を指定可能（デフォルト: data/paper_trading.db）

- AI 系（プログラム的に利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡し、ニューススコアを ai_scores テーブルに書き込みます。OPENAI_API_KEY を環境変数に設定するか、api_key を渡してください。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - market_regime テーブルへ日次レジームを書き込みます。OpenAI キーが必要です。

---

## 重要な実装上の注意点 / 運用メモ

- Monitoring は常に `Settings.sqlite_path`（監視 DB）を使用します（paper_trading でも本番の monitoring DB を参照する点に注意）。
- ExecutionEngine は KABUSYS_ENV=paper_trading の場合 `paper_sqlite_path` を使用し、本番 DB と切り離します。
- Stop フラグ:
  - run_monitoring.py / run_execution.py はプロジェクトの data/stop_requested.flag を確認して安全に終了します。
  - Kill Switch（リスクトリガで書き込まれる）: Settings.kill_flag_path（デフォルト data/kill.flag）を用いる。Execution 起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に自動でクリアされる（本番では 0 推奨）。
- ロギング:
  - kabusys.utils.logging_setup.setup_logging() を使って、コンソールと日次ローテートのログ（logs/<app_name>.log）を統一的に出力します。
- プロセス優先度:
  - 起動スクリプトは set_process_priority("high") を呼びます。ただし OS 権限やプラットフォームにより失敗することがあるため、例外はログに落ちてスキップされます。

---

## トラブルシューティング

- .env が正しく読み込まれない、または環境変数が反映されない:
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD` が設定されていないか確認、または .env の場所がプロジェクトルートと一致しているか確認してください。
- OpenAI 関連でエラーが出る:
  - 環境変数 `OPENAI_API_KEY` を確認。API のレート制限やネットワーク障害は内部でリトライ・フェイルセーフ処理がありますが、ログを確認してください。
- DB にテーブルがない等の OperationalError:
  - init_monitoring_db() は冪等に初期化します。必要に応じて手動で DB パスを確認し、マイグレーションでカラム追加が必要な場合はログに従ってください。

---

## ディレクトリ構成（抜粋）

以下はパッケージ内の主要ファイル・ディレクトリ構成の抜粋です（src/kabusys を想定）。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_monitoring.py
    - run_execution.py
    - data/                (実行環境の default path: data/*.db, data/*.flag, data/*.pid)
    - logs/                (ログ出力先)
    - ai/
      - news_nlp.py
      - regime_detector.py
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

注: 実際のファイル一覧はリポジトリ側の完全な tree を参照してください。上記は README 作成時に与えられたコードベースの主要モジュールを抜粋したものです。

---

## 参考コマンドまとめ（例）

- .env ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- 監視プロセス起動
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
- 発注エンジン起動
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要であれば、この README を元に各モジュールの API 使用例（コードサンプル）や、運用手順（デプロイ・systemd/cron での実行例）、より詳しい環境変数一覧を追加できます。どの情報を拡張したいか教えてください。