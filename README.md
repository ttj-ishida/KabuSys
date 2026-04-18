# KabuSys — 日本株自動売買システム（README）

以下はこのリポジトリの簡易ドキュメントです。日本語で記載しています。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けライブラリと運用スクリプト群です。戦略のためのファクター計算、ポートフォリオ構築、ポジションサイズ計算、発注実行エンジン、監視（モニタリング）、AI ベースのニュースセンチメント評価などのコンポーネントを含みます。

主な設計方針：
- DuckDB / SQLite を使ったローカルデータ処理（分析用 / 監視用 DB）
- Paper Trading（モックブローカー）と Live（実発注）を切り替え可能
- LLM（OpenAI）を用いたニュースセンチメント / レジーム判定をサポート
- 監視ループ・Kill Switch による安全運用支援
- 設定は .env ファイル / 環境変数で管理

バージョン: 0.1.0（src/kabusys/__init__.py）

---

## 主な機能一覧

- portfolio
  - 候補選定（select_candidates）
  - 重み付け（等金額 / スコア加重）
  - ポジションサイズ計算（lot 単位丸め・リスク制約）
  - セクター集中制限、レジーム乗数

- research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン・IC 計算、統計サマリー

- ai
  - ニュースの LLM によるセンチメントスコアリング（news_nlp.score_news）
  - 市場レジーム判定（regime_detector.score_regime）

- execution（実行エンジン）
  - BrokerClientFactory によるブローカ切替（paper_trading では Mock）
  - OrderManager / RiskManager / Reconciler を統合した ExecutionEngine

- monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor のポーリング統合（MonitoringEngine）
  - DB 永続化（monitoring_db）
  - Kill Switch（data/kill.flag）による実行停止トリガ
  - run_monitoring/run_execution の起動スクリプト

- tools
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）

- utils
  - 統一ログ設定（utils.logging_setup）
  - プロセス優先度・CPU affinity 設定（utils.process_priority）
  - 設定読み込み（config.py）と設定ウィザード（config_setup.py）、設定検証（validate_config.py）

---

## 前提・依存関係（概略）

Python 3.9+ を想定しています。主要な外部ライブラリ例：

- duckdb
- psutil
- openai
- PyYAML（config 検証で任意）

インストール例（仮）:
pip install duckdb psutil openai PyYAML

※ requirements.txt は本リポジトリに含まれていないため、利用環境に合わせて依存を管理してください。

---

## セットアップ手順

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML

3. プロジェクトルートに移動（.git または pyproject.toml があるディレクトリ）
   - 自動で .env を読み込みます（config.py の仕様）。

4. 環境変数（.env）作成
   - 対話式ウィザードを使用:
     - python -m kabusys.config_setup
   - もしくは .env を手動で作成（.env.example を参照して必要項目を設定）。
   - 主要な必須変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - その他（例）:
     - KABUSYS_ENV=development|paper_trading|live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LOG_LEVEL=INFO
     - OPENAI_API_KEY (AI 機能を使う場合)

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります

---

## 使い方（主要スクリプト）

※ いずれのスクリプトもプロジェクトルートで実行してください。

- Execution Engine を起動（本番/ペーパートレード共通エントリ）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録します
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します
  - PID ファイル: data/execution.pid（Settings.pid_file_path）

- Monitoring を起動（ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き（デフォルト 60 秒）
  - 監視は Settings.sqlite_path（data/monitoring.db）を使用（監視は環境にかかわらず本番 sqlite_path を参照）
  - 停止フラグ: data/stop_requested.flag を監視してループを終了します

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db、環境変数 PAPER_TRADING_SQLITE_PATH で指定可
  - レポートは標準出力に表示されます（稼働率 / 成立率 / レイテンシ等）

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - --strict オプションあり

---

## 主要な設定・フラグファイル

- .env / 環境変数（config.py により自動ロード）
- data/kill.flag
  - Kill Switch により生成される停止フラグ。ExecutionEngine に停止シグナルを送る。
  - Settings.kill_flag_clear_on_start=1 を設定すると起動時に自動クリア（本番では非推奨）。
- data/stop_requested.flag
  - run_execution / run_monitoring が監視するノンエレガントな手動停止フラグ（存在するとループを終了）。
- data/execution.pid
  - 実行エンジンの PID ファイル（ExecutionEngine 起動時に使用）

---

## ディレクトリ構成

以下は src/kabusys 以下の主なファイル・モジュール構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理（.env 自動ロード）
  - config_setup.py           — 対話式 .env ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring ポーリング起動スクリプト

  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py

  - monitoring/
    - monitoring_db.py         — SQLite 永続化レイヤ（system_status 等）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py

  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py

  - research/
    - factor_research.py
    - feature_exploration.py

  - ai/
    - news_nlp.py               — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py        — マーケットレジーム判定（OpenAI）

  - monitoring/ (DB helpers, risk etc.)
  - tools/
    - paper_verification_report.py

  - utils/
    - logging_setup.py          — ログ設定（stdout + 日次ファイルローテーション）
    - process_priority.py       — プロセス優先度・CPU affinity

- data/                       — デフォルトの DB / フラグ / pid を配置する想定ディレクトリ
- logs/                       — ログ出力先（デフォルト）

---

## ログ・監視

- ログは utils.logging_setup.setup_logging を通して統一設定されます。
  - コンソール（stdout）と日次ローテーションファイル（logs/<app_name>.log）に出力
  - デフォルトで 30 日分を保持

- run_monitoring/run_execution は起動時に set_process_priority("high") を呼び出して優先度を上げます（OS 権限によっては失敗して警告になることがあります）。

---

## AI 機能について（OpenAI）

- news_nlp.score_news / regime_detector.score_regime は OpenAI API を使用します。
- 環境変数 OPENAI_API_KEY を設定するか、api_key 引数で渡してください。
- レートリミットや一時的エラーに対してはリトライ（指数バックオフ）処理を行いますが、最終的に失敗した場合はフェイルセーフ（諸々 0.0 等で継続）します。
- 出力は厳密な JSON を期待するよう設計されていますが、復元ロジックや検証を行って安全化しています。

---

## 運用上の注意

- KABUSYS_ENV=live の場合は設定ミスが致命的になる可能性があるため validate_config で事前チェックしてください。
- .env は機密情報（API トークン、パスワード）を含むため決して Git へコミットしないでください。
- Paper Trading は本番 DB と分離（PAPER_TRADING_SQLITE_PATH）されています。paper_trading 設定時にも DB パスの確認を推奨します。
- Kill Switch（data/kill.flag）と stop_requested.flag の運用方針をチームで決め、誤って自動クリアされないように注意してください（KILL_FLAG_CLEAR_ON_START）。

---

## よく使うコマンド一覧（まとめ）

- 仮想環境作成
  - python -m venv .venv && source .venv/bin/activate

- 依存インストール（例）
  - pip install duckdb psutil openai PyYAML

- .env 作成（ウィザード）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Execution 起動
  - python -m kabusys.run_execution

- Monitoring 起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要に応じて README を拡張して、セットアップスクリプト（requirements.txt / Dockerfile / systemd ユニット）や運用手順（バックアップ、DB マイグレーション、監視アラート設定）を追加することをおすすめします。質問や追加のドキュメント化希望があれば教えてください。