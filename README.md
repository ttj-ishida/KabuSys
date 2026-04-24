# KabuSys

日本株自動売買システムのサンプル実装（パッケージ名: kabusys）。  
このリポジトリは、取引エンジン（ExecutionEngine）、監視系（Monitoring）、ポートフォリオ構築、ファクター計算、AIベースのニュースセンチメント評価などの主要機能を含むモジュール群で構成されています。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的としたモジュール式の自動売買基盤です。

- 株価データの分析（DuckDB を使用）
- シグナル → ポートフォリオ構築 → 発注（ExecutionEngine）
- 発注・約定ログと監視（SQLite）
- リスク監視（ドローダウン・ポジション上限）と Kill Switch
- ニュースを LLM（OpenAI）で評価してスコア化
- ペーパートレーディング（テスト）と本番の切替

設計方針として「環境変数による設定」「DB分離（paper_trading と本番）」「フェイルセーフ」「ルックアヘッドバイアス回避」などを重視しています。

---

## 主な機能一覧

- Execution
  - 実際のブローカークライアントとペーパートレード用の MockBrokerClient を切替可能（KABUSYS_ENV）。
  - OrderManager / RiskManager / Reconciler を組み合わせた ExecutionEngine。
  - 発注・約定のログ永続化（SQLite: monitoring DB を補助的に使用）。

- Monitoring
  - SystemMonitor: CPU・メモリ・ディスク・プロセス状態・データ鮮度監視。
  - TradeMonitor: 発注ログの滞留・約定異常検出（trade_logs）。
  - RiskMonitor: ドローダウン・ポジション上限監視とアラート記録。
  - KillSwitch: 一定条件で data/kill.flag を書き込むことで ExecutionEngine を停止。
  - MonitoringEngine: 上記を束ねて定期ポーリング。

- Portfolio / Research
  - 銘柄選定、等配分・スコア配分、リスク調整、ポジションサイジング。
  - ファクター計算（Momentum / Volatility / Value）と将来リターン・IC 計算。

- AI（OpenAI）
  - ニュース記事を LLM（gpt-4o-mini）でセンチメント化して ai_scores に保存（news_nlp）。
  - マクロニュースと ETF の MA を組み合わせ市場レジーム（bull/neutral/bear）を判定（regime_detector）。

- ツール
  - 環境設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）

---

## 前提 / 必要なもの

- Python 3.9+
- 依存ライブラリ（例）
  - duckdb
  - psutil
  - openai
  - （オプション）PyYAML（config 検証で使用）
- ファイル書き込み権限（data/, logs/ ディレクトリ）

環境に応じて仮想環境を作成して必要なパッケージをインストールしてください。

---

## セットアップ手順（クイックスタート）

1. リポジトリをクローンし、仮想環境を作成・アクティベートします。

2. 必要パッケージをインストールします（例）:
   - pip install -r requirements.txt
   - requirements.txt が無ければ主要依存を個別にインストール:
     - pip install duckdb psutil openai

3. .env の作成
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - もしくはプロジェクトルートに `.env` を作成し以下のような最低限必須変数を設定してください:
     - JQUANTS_REFRESH_TOKEN=your_token
     - KABU_API_PASSWORD=your_password
     - KABUSYS_ENV=development|paper_trading|live
     - OPENAI_API_KEY=your_openai_api_key (AI 機能を使う場合)
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db (KABUSYS_ENV=paper_trading 時に使用)

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

5. 初回起動時の DB 初期化
   - Execution/Monitoring 起動スクリプトが起動時に必要テーブルを作成します（init_monitoring_db が自動で実行されます）。

---

## 主要な環境変数（要点）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）
  - paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB に記録されます。
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI を使用する場合に必須
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）
- LOG_DIR: ログ保存ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant|partial|never|reject）
- PID_FILE_PATH / KILL_FLAG_PATH: PID・Kill Flag 関連のパス（Settings で参照）

注意: .env の自動読み込みはプロジェクトルートに .env/.env.local がある場合に行われます。テストで自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## 実行方法（コマンド例）

- ExecutionEngine を起動（本番 or paper_trading の切替は KABUSYS_ENV で制御）
  - python -m kabusys.run_execution

  説明:
  - paper_trading 環境では PAPER_TRADING_SQLITE_PATH に書き込み、本番 DB と完全に分離されます。
  - 起動時に data/stop_requested.flag が既に存在する場合は起動せず終了します。
  - 実行中に data/stop_requested.flag が作成されるとエンジンが停止します（安全停止）。

- Monitoring を起動（監視ループ）
  - MONITOR_POLL_INTERVAL 環境変数で間隔を秒指定（デフォルト 60）
  - python -m kabusys.run_monitoring

  説明:
  - 監視は常に production 用の sqlite_path（Settings.sqlite_path）を使用して監視テーブルを更新します。
  - 停止は project_root/data/stop_requested.flag ファイルの存在で検出します。

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

---

## 実行停止 / Kill Switch

- グレースフル停止（単純）
  - 実行中の run_execution / run_monitoring は project_root/data/stop_requested.flag が存在すると停止処理を行います。停止させたい場合はそのファイルを作成します。
- Kill Switch（自動停止）
  - RiskMonitor が重大なリスク（ドローダウン超過やポジション上限超過）を検出すると Monitoring が KillSwitch を評価し、必要に応じて data/kill.flag を書き込みます。ExecutionEngine は起動時・定期的にこのフラグを参照して停止できます。
- 起動時の Kill Flag クリア
  - KILL_FLAG_CLEAR_ON_START=1 を .env に設定すると ExecutionEngine 起動時に kill.flag を自動でクリアします（本番では通常 0 推奨）。

---

## ロギング

- ログ設定は kabusys.utils.logging_setup.setup_logging を通じて統一されています。
- 出力先:
  - コンソール (stdout)
  - 日次ローテーションファイル: logs/<app_name>.log（デフォルト、30 日分保持）
- log ディレクトリは自動作成されますが、作成に失敗した場合はファイル出力が無効になりコンソールのみの出力になります。

---

## データベースとスキーマ

- SQLite（監視・発注ログ）
  - デフォルト: data/monitoring.db
  - init_monitoring_db がテーブルを冪等に作成します（system_status, trade_logs, positions, risk_logs, dashboard 等）。
  - マイグレーション: 初回起動で不足カラム（例: latency_ms, peak_value）があれば追加します。

- DuckDB（分析用）
  - デフォルト: data/kabusys.duckdb
  - research / ai モジュールは DuckDB 接続を受け取り prices_daily や raw_financials, raw_news 等のテーブルを参照して処理します。

---

## ディレクトリ構成

（src/kabusys 以下の主要ファイル・モジュール）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数・設定管理（Settings クラス）
  - config_setup.py — .env 対話ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring ポーリング起動スクリプト

  - ai/
    - news_nlp.py — ニュースを LLM でスコア化
    - regime_detector.py — マーケットレジーム判定
  - monitoring/
    - monitoring_db.py — SQLite 永続化レイヤ
    - system_monitor.py — システム監視
    - trade_monitor.py — （trade モニタリング）※一部実装を参照
    - risk_monitor.py — リスク監視（ドローダウン等）
    - kill_switch.py — Kill Switch 実装
    - monitoring_engine.py — 各 Monitor を束ねる
    - alert_manager.py — アラート送信（LINE 等）※実装参照
  - execution/
    - broker_factory.py — ブローカークライアント生成
    - execution_engine.py — ExecutionEngine 本体
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, 等
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py

注: リポジトリ全体のファイル構成は上記の抜粋を基に記載しています。実行に必要な追加モジュール（data 関連テーブル定義や broker 実装など）が存在する場合があります。

---

## 開発上の注意点 / 実装の要点

- 環境依存の挙動（本番 / ペーパー）は KABUSYS_ENV で切り替わります。paper_trading は本番 DB と完全分離される設計です。
- LLM（OpenAI）を利用する機能は API キーが必要で、API エラー時はフェイルセーフ（スコア 0.0 など）にフォールバックする実装になっています。
- run_execution / run_monitoring はプロセス優先度を上げる処理を最初に実行します（psutil を使用）。
- monitoring ループや engine の停止はフラグファイル（data/stop_requested.flag）や kill.flag により制御します。外部からの停止指示や自動停止に対応しています。
- .env の読み込みはプロジェクトルートを基準に行われるため、パッケージ配布後も CWD に依存しません。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## よく使うコマンド一覧（まとめ）

- .env を対話式で作る:
  - python -m kabusys.config_setup
- 設定を検証:
  - python -m kabusys.validate_config
- Execution を起動:
  - python -m kabusys.run_execution
- Monitoring を起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## 最後に

この README はコードベースの主要機能と運用上のポイントをまとめたものです。実際に運用する際は .env の機密情報管理、ログ・DB バックアップ、OpenAI の利用規約・コスト管理、本番環境での Kill Switch 設定などを十分に考慮してください。

何か追加で README に含めたい情報（構成図、シーケンス図、サンプル .env ファイル、運用手順など）があれば教えてください。必要に応じて追記します。