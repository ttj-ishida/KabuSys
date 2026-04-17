# KabuSys

日本株向け自動売買システムのコアライブラリ群（README）。  
この README はリポジトリ内の主要スクリプト・モジュールに基づいて作成しています。

---

## プロジェクト概要

KabuSys は日本株の自動売買／研究用ライブラリです。  
主な目的は以下です。

- 戦略の研究（ファクター計算、特徴量解析）
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- 実行エンジン（ExecutionEngine）による発注（本番 / ペーパートレード）
- 監視・リスク管理（MonitoringEngine / Kill Switch / アラート）
- AI を用いたニュースセンチメント評価（OpenAI 経由）
- ペーパートレードの検証レポート生成

設計上のポイント：
- DuckDB を用いた時系列ファクター計算、SQLite を用いた監視ログ・ポジション管理
- 環境変数 / .env による設定管理（自動読み込みを持つ）
- 本番とペーパートレードで DB を分離（ペーパートレードは data/paper_trading.db）
- OpenAI を用いる機能は API キー必須、失敗時はフェイルセーフで継続する設計

---

## 機能一覧（主なもの）

- 環境設定ウィザード: python -m kabusys.config_setup
- 設定検証 CLI: python -m kabusys.validate_config
- ExecutionEngine 起動: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、ペーパー用 SQLite に記録
- Monitoring 起動（SystemMonitor のポーリング）: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（デフォルト 60 秒）
- MonitoringEngine（各種モニタの束ね）: system / trade / risk のチェック、Kill Switch 評価、アラート発行
- リサーチモジュール:
  - ファクター計算: calc_momentum, calc_volatility, calc_value
  - 将来リターン・IC 計算など
- ポートフォリオ構築:
  - 候補選定、等重／スコア加重、リスク調整（セクターキャップ、レジーム乗数）
  - 株数決定（単元株丸め・投下資金スケール）
- AI 関連:
  - news_nlp.score_news: raw_news を OpenAI で評価して ai_scores に書き込む
  - regime_detector.score_regime: マクロニュース + ETF MA 乖離で市場レジーム判定
- ツール:
  - Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report

---

## セットアップ手順

前提: Python 3.9+（モジュールアノテーション等使用）

1. リポジトリをクローン／展開する
2. 仮想環境（推奨）を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要なパッケージをインストール
   - 主要依存例（プロジェクトに requirements.txt がない場合は手動で）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証で YAML を検査する場合に必要）
   - 例:
     - pip install duckdb psutil openai PyYAML
4. .env を作成する（推奨: ウィザードを使用）
   - python -m kabusys.config_setup
   - 作成後、設定を検証:
     - python -m kabusys.validate_config
5. データディレクトリを準備
   - デフォルトでは data/ 下に DB や PID/flag ファイルを生成します。
   - 必要に応じて .env で DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を上書き

注意:
- OpenAI を使う機能を利用する場合は環境変数 OPENAI_API_KEY を設定するか、関数引数でキーを渡してください。
- 自動 .env 読み込みはデフォルトで有効。無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

## 使い方（よく使うコマンドと環境変数）

基本コマンド

- 環境セットアップ（対話型）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code 1）
- ExecutionEngine（本番 or ペーパー）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を .env に設定するとペーパートレードモードになる
  - ペーパートレード用 DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）
- Monitoring（常駐監視ループ）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定可能（例: MONITOR_POLL_INTERVAL=30）
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で別 DB を指定可能（優先順位: --db > PAPER_TRADING_SQLITE_PATH > デフォルト）
- AI 機能（例）
  - news_nlp.score_news(conn, target_date, api_key=None)  <-- api_key が None の場合 OPENAI_API_KEY を参照
  - regime_detector.score_regime(conn, target_date, api_key=None)

停止・フラグ制御
- ExecutionEngine / Monitoring の停止には次のフラグファイルが使われます:
  - data/stop_requested.flag: run_monitoring.py / run_execution.py がこのファイルを検知したらループを終了
  - data/kill.flag: KillSwitch が書き込む（ExecutionEngine に対する停止シグナル）
- PID ファイル:
  - デフォルト PID ファイル: data/execution.pid（Settings.pid_file_path で変更可）
  - SystemMonitor は PID の存在や staleness をチェックします

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development / paper_trading / live）
- DUCKDB_PATH（analysis DB、デフォルト data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード用 SQLite）
- OPENAI_API_KEY（AI 機能で必要）
- PAPER_FILL_MODE（ペーパーの成行成約動作: instant|partial|never|reject）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔秒数）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動でクリアするか。production では 0 を推奨）

---

## ディレクトリ構成（主要ファイル）

リポジトリルートの src/kabusys 以下（抜粋）:

- __init__.py
  - パッケージ定義、バージョン

- config.py
  - 環境変数/.env の読み込みと Settings クラス。自動ロードの振る舞い、必須チェック等を実装

- config_setup.py
  - .env を対話式に作成・更新するウィザード

- validate_config.py
  - .env と config/*.yaml 等の基本検証を実行する CLI

- run_execution.py
  - ExecutionEngine を起動するスクリプト
  - Paper Trading の場合は MockBroker を利用し DB を分離

- run_monitoring.py
  - SystemMonitor の単純ポーリングループ起動スクリプト
  - MONITOR_POLL_INTERVAL で間隔を指定

- monitoring/
  - monitoring_db.py
    - SQLite による監視ログの永続化（テーブル作成・Migration 含む）
  - system_monitor.py
    - CPU/メモリ/Disk/プロセス状態・データ鮮度チェック
  - trade_monitor.py
    - 発注滞留・約定異常チェック
  - risk_monitor.py
    - ドローダウン・ポジション上限チェック
  - kill_switch.py
    - Kill Switch（フラグファイル書き込み）
  - monitoring_engine.py
    - 個別 Monitor を束ねてポーリング + アラート連携
  - alert_manager.py
    - （※ファイルの続きを参照してください）アラート送信の集約ロジック

- execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py, order_record.py
  - 実行エンジンや注文周りの実装（発注・リスク管理・約定処理等）

- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - ポートフォリオ構築・重み付け・株数決定・セクター制限の純粋関数

- research/
  - factor_research.py
    - Momentum / Value / Volatility ファクター計算（DuckDB を使用）
  - feature_exploration.py
    - 将来リターン計算・IC・統計サマリー等

- ai/
  - news_nlp.py
    - raw_news を OpenAI でスコアリングして ai_scores に書き込む
  - regime_detector.py
    - ETF MA 乖離 + マクロニュースの LLM 集約で市場レジーム判定

- tools/
  - paper_verification_report.py
    - ペーパートレード DB を解析して PASS/FAIL 判定とサマリを出力

- utils/
  - process_priority.py
    - psutil を使ったプロセス優先度 & CPU affinity 設定ユーティリティ

データ・フラグファイル（実行時に利用／生成）
- data/kabusys.duckdb（デフォルト）
- data/monitoring.db（監視ログ）
- data/paper_trading.db（ペーパートレード用 DB）
- data/execution.pid（ExecutionEngine の PID）
- data/stop_requested.flag（手動で起動済みプロセスを停止するためのフラグ）
- data/kill.flag（KillSwitch が書き込む停止理由）

---

## 運用上の注意 / ベストプラクティス

- 本番運用（KABUSYS_ENV=live）の場合、LINE 通知や kill switch 設定を確実にしておくこと。validate_config で検査できます。
- .env を VCS にコミットしないこと（config_setup.py も警告を出します）。
- OpenAI を使う処理は API 料金が発生するため、本番で自動実行する際はコストとレート制限を想定すること。
- run_execution/run_monitoring は stop フラグ（data/stop_requested.flag）で安全に停止可能。手動でファイルを作成・削除する運用が前提です。
- PID ファイルが stale の場合、SystemMonitor が検知して削除・アラートを残します。
- データ鮮度（prices_daily）に依存する処理が多いため、DuckDB のデータ更新スケジュールは厳格に管理してください。

---

必要に応じて README に追記できます（例: 詳しい設定例、Docker / systemd サービスファイル例、API 使用料管理、モニタリングのアラート送信先設定方法など）。追加してほしいセクションがあれば教えてください。