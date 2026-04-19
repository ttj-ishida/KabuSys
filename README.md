# KabuSys

バージョン: 0.1.0

KabuSys は日本株の自動売買・リサーチ基盤のコアライブラリです。本リポジトリには監視（Monitoring）、発注エンジン（Execution）、ポートフォリオ構築、ファクター計算、AI を用いたニュース NLP などのモジュールが含まれます。

以下はこのコードベースの README（日本語）です。

---

## 概要

KabuSys は以下を目的としたモジュール群を提供します。

- 市場データ（DuckDB）を使ったファクター計算・リサーチ
- ポートフォリオ構築（銘柄選定・重み付け・ポジションサイズ算出）
- 発注エンジン（実口座/ペーパートレード対応）
- システム監視（CPU/メモリ/Disk、プロセス生存確認、データ鮮度）
- リスク監視（ドローダウン／ポジション上限監視）と Kill Switch
- ニュースを LLM（OpenAI）でスコアリングする AI モジュール
- 運用・検証用ツール（設定ウィザード、設定検証、ペーパートレード検証レポート）

設計上のポイント：
- DuckDB を分析用 DB、SQLite を監視・取引ログに使用。
- KABUSYS_ENV により `development` / `paper_trading` / `live` を切り替え。paper_trading は発注をモック化して本番 DB と分離。
- .env/.env.local を自動ロード（必要に応じて無効化可能）。

---

## 主な機能一覧

- 設定管理
  - .env 自動ロード（`.env` / `.env.local`、OS 環境変数優先）
  - interactive ウィザードで .env を生成 (`kabusys.config_setup`)
  - 起動前に設定を検証する CLI (`kabusys.validate_config`)

- 監視 (monitoring)
  - SystemMonitor: CPU/Mem/Disk、実行プロセス生存、データ鮮度を確認
  - TradeMonitor: 発注ログの監視（滞留注文、約定異常など）
  - RiskMonitor: ドローダウン・ポジション上限の監視
  - KillSwitch: しきい値超過時に `data/kill.flag` を書き込むことで ExecutionEngine を停止
  - MonitoringEngine: 上記をまとめて定期実行、アラート送信フックあり

- 発注エンジン (execution)
  - 実口座/ペーパートレード対応（KABUSYS_ENV=paper_trading でモックbroker を使用）
  - RiskManager、OrderManager、Reconciler、ExecutionEngine を備えた実行基盤
  - 発注ログ、positions 等を SQLite に保存

- ポートフォリオ構築（pure functions）
  - 候補選定、等金額/スコア加重配分、リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ算出（単元株丸め、aggregate cap）

- リサーチ（research）
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ

- AI（ai）
  - ニュース NLP（OpenAI）で銘柄別センチメントを算出して ai_scores に保存
  - 市場レジーム判定（ETF MA + マクロニュース LLM スコアを合成）

- ツール
  - Paper Trading の検証レポート生成 (`kabusys.tools.paper_verification_report`)

---

## セットアップ手順

前提：
- Python 3.8+（環境によって duckdb, psutil, openai, pyyaml 等が必要）
- pip 等で必要パッケージをインストールしてください（requirements.txt がない場合は以下を参考に）。

推奨パッケージ（例）:
- duckdb
- psutil
- openai
- pyyaml (設定検証で YAML ファイル検証を行う場合)
- (テスト時に必要なパッケージは別途)

1. リポジトリをクローンして Python 環境を作成
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)
   - pip install -r requirements.txt もしくは個別に pip install duckdb psutil openai pyyaml

2. .env 作成
   - 対話式で作成:
     - python -m kabusys.config_setup
   - または手動で `.env` に必要な環境変数を設定（下記参照）

3. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict をつけると警告もエラー扱いで非ゼロ終了

4. データディレクトリ（data）とログディレクトリ（logs）確認
   - 自動作成されることが多いですが、パーミッション等に注意

主要な環境変数（代表）:
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: 分析用 DuckDB（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 時）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant|partial|never|reject、デフォルト: instant）
- OPENAI_API_KEY: OpenAI を利用する機能で必要
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)

自動 .env ロード:
- デフォルトでプロジェクトルートの `.env` と `.env.local` を自動ロードします。
- 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方

### 共通: ロギング・プロセス優先度
- 起動スクリプトは `kabusys.utils.logging_setup.setup_logging` を呼び出し、stdout および `logs/<app_name>.log` に日次ローテーションで出力します。
- プロセス優先度は `kabusys.utils.process_priority.set_process_priority("high")` で起動時に高優先度へ設定します（OS の権限による制限あり）。

### 設定ウィザード
- python -m kabusys.config_setup
  - .env を対話式に作成・更新します。

### 設定検証
- python -m kabusys.validate_config
  - 環境変数や config/*.yaml の存在・基本妥当性をチェックします。

### 監視 (Monitoring)
- 起動:
  - python -m kabusys.run_monitoring
- 動作:
  - デフォルトのポーリング間隔は 60 秒。環境変数 `MONITOR_POLL_INTERVAL` で秒数を指定して上書き可能（1以上の整数）。
  - 監視は `settings.sqlite_path`（デフォルト data/monitoring.db）を使用してログを永続化します（Monitoring は KABUSYS_ENV にかかわらず本番 sqlite を使います）。
  - 停止: プロジェクトルートの `data/stop_requested.flag` を作成するとループを検知して停止します。

### 発注エンジン (Execution)
- 起動:
  - python -m kabusys.run_execution
- 動作:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して `data/paper_trading.db`（または PAPER_TRADING_SQLITE_PATH）に記録し本番 DB と分離します。
  - 起動中は `data/execution.pid` へ PID を保存（設定により変更可）。停止は `data/stop_requested.flag` または `data/kill.flag` により実行できます（KillSwitch により kill.flag が書き込まれると停止されます）。
  - 起動時に `data/stop_requested.flag` が既にある場合は起動しません。

### AI（ニュース NLP / レジーム判定）
- ニュースセンチメント算出:
  - 関数: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - OpenAI API キー（OPENAI_API_KEY）が必要。
  - raw_news, news_symbols テーブルから記事を集約して LLM に送信し ai_scores に書き込みます。
- レジーム判定:
  - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF 1321 の MA とマクロニュースを組み合わせて市場レジームを判定し market_regime テーブルへ保存します。
- 注意: API 呼び出しはリトライ・フォールバック実装があるため失敗してもシステム全体を停止させませんが、API キーは必須です。

### ペーパートレード検証レポート
- python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- PAPER_TRADING_SQLITE_PATH または `--db` で DB パスを指定できます。
- 稼働率、注文成功率、送信率、レイテンシ（P95）等を集計し PASS/FAIL を判定します。

---

## 主要ファイル・コマンド一覧

- python -m kabusys.config_setup
  - `.env` 対話式作成
- python -m kabusys.validate_config [--strict]
  - 設定検証
- python -m kabusys.run_monitoring
  - 監視ループ起動（MONITOR_POLL_INTERVAL で間隔指定）
- python -m kabusys.run_execution
  - ExecutionEngine 起動（paper_trading モードあり）
- python -m kabusys.tools.paper_verification_report
  - ペーパートレード検証レポート

---

## ディレクトリ構成

リポジトリ内の主要なモジュール構成（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py
    - 環境変数・.env の読み込みロジック、Settings クラス
  - config_setup.py
    - .env 作成ウィザード CLI
  - validate_config.py
    - 設定検証 CLI
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - ai/
    - news_nlp.py
      - ニュースを LLM でスコアリングして ai_scores に書き込み
    - regime_detector.py
      - レジーム判定（MA + マクロニュース）
  - monitoring/
    - monitoring_db.py
      - SQLite の監視テーブル作成・読み書き用ラッパー
    - system_monitor.py
      - CPU/Mem/Disk、プロセス、データ鮮度監視
    - trade_monitor.py
      - 発注ログ監視（滞留、異常約定等） —（実装ファイルあり）
    - risk_monitor.py
      - ドローダウン・ポジション数の監視
    - kill_switch.py
      - kill.flag を書き込むロジック
    - monitoring_engine.py
      - 各 Monitor を束ねる実行エンジン
    - alert_manager.py
      - アラート送信（LINE 等） —（実装ファイルあり）
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - （発注関連のコンポーネント群）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - （ポートフォリオ構築の純粋関数群）
  - research/
    - factor_research.py
    - feature_exploration.py
  - monitoring/ (上記)
  - tools/
    - paper_verification_report.py
  - data/ (実行時に使用されるディレクトリ)
    - monitoring.db (デフォルトの SQLite)
    - paper_trading.db (ペーパートレード用 DB)
    - execution.pid, kill.flag, stop_requested.flag などの制御ファイル
  - logs/ (ログ出力先; ログローテーションあり)

注: 一部ファイル（trade_monitor.py、alert_manager.py、execution 内コンポーネント等）はここでは概要のみ記載しています。実際の実装と合わせてご参照ください。

---

## 運用上の注意

- 本番環境（KABUSYS_ENV=live）では LINE の通知設定（LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID）や KILL_FLAG_CLEAR_ON_START の設定を慎重に確認してください。validate_config は本番時の警告チェックを行います。
- Monitoring は本番 sqlite_path を参照するため、監視 DB のバックアップやディスク容量に注意してください。
- OpenAI を利用する処理は API コストが発生します。API キー管理やコール頻度に注意してください。
- process priority / cpu affinity の設定は OS の権限に依存します。権限が不足している場合は警告が出ますが処理は継続します。
- .env は絶対に Git にコミットしないでください（config_setup.py のヘッダ注記も参照）。

---

必要に応じて README を拡張します。特定のセクション（例: デプロイ手順、テーブルスキーマ、API 仕様、ユニットテストの実行方法）を追加したい場合は教えてください。