# KabuSys

日本株向け自動売買・リサーチ基盤のコアライブラリおよび起動スクリプト群です。  
本リポジトリは、発注エンジン（ExecutionEngine）、監視モジュール（Monitoring）、ポートフォリオ構築・ポジション計算、リサーチ用ファクター計算、OpenAI を用いたニュース NLP / レジーム判定などを含みます。

以下はリポジトリの使い方、セットアップ、主要機能およびディレクトリ構成のまとめです。

---

目次
- プロジェクト概要
- 機能一覧
- 動作要件（依存関係）
- セットアップ手順
- 環境変数（.env）と主要設定
- 実行方法（起動スクリプト・ツール類）
- 停止・Kill スイッチについて
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株を対象とした自動売買システムのコアライブラリ群です。  
設計方針として「本番 DB とペーパートレード DB の分離」「外部 API 呼び出しを明示的に扱う」「時系列データ解析は DuckDB を利用」などが採られています。各処理はユニット化されており、CLI ウィザードや検証ツールも提供しています。

---

## 機能一覧

- Execution
  - ExecutionEngine を起動して注文処理を行う（本番／ペーパートレード切替）
  - ブローカークライアントの抽象化（MockBrokerClient を paper_trading 用に用意）
  - リスク制御（RiskManager）、注文管理（OrderManager）、照合（Reconciler）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク・データ鮮度・プロセス監視
  - TradeMonitor / RiskMonitor: 発注ログ・ドローダウン・ポジション上限監視
  - KillSwitch: 一定条件で停止フラグを書き込み ExecutionEngine を安全停止
  - MonitoringEngine: 各モニタを束ねたポーリングループ、アラート連携
- Portfolio
  - 候補選定、等分配・スコア重み配分、ポジションサイズ計算（lot 単位丸め等）
  - セクター上限適用、レジームに応じた投入資金乗数
- Research
  - DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（Information Coefficient）計算、特徴量サマリ
- AI（OpenAI）
  - ニュースのセンチメント解析と銘柄別スコア化（news_nlp）
  - マクロニュースと ETF MA200 を組み合わせた市場レジーム判定（regime_detector）
  - 両者は OpenAI API（gpt-4o-mini 想定）を利用。API キーは環境変数で指定
- ツール
  - 環境設定ウィザード（.env 作成 / 更新）
  - 設定検証 CLI（.env + config/*.yaml の妥当性チェック）
  - Paper Trading 検証レポート生成ツール（過去期間の稼働率・成功率・レイテンシ等）

---

## 動作要件（依存関係）

最低限の依存（抜粋）:
- Python 3.10+
- duckdb
- psutil
- openai （AI 機能を使う場合）
- PyYAML （config/*.yaml の解析を行う場合）
- sqlite3（標準ライブラリで同梱）

インストール例:
- 仮想環境作成・有効化
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- 必要パッケージをインストール（requirements.txt がない場合は個別に）
  - pip install duckdb psutil openai PyYAML

（プロジェクトに requirements.txt がある場合はそれを利用してください）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. Python 仮想環境を作る（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows では .venv\Scripts\activate)

3. 依存ライブラリをインストール
   - pip install duckdb psutil openai PyYAML

4. .env を作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードに従って J-Quants トークンや Kabu API パスワード、DB パス等を設定してください。
   - 生成された .env は絶対に Git にコミットしないでください。

5. 設定検証
   - python -m kabusys.validate_config
   - 警告も含めて厳密にチェックする場合: python -m kabusys.validate_config --strict

6. DB 初期化
   - 起動スクリプトが起動時に監視 DB（SQLite）や DuckDB を初期化します。手動での作成は不要です。

---

## 環境変数（.env）と主要設定

主な環境変数（必須 / 任意、デフォルトを含む）:

必須（最低限設定してください）
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API パスワード

主要オプション / デフォルト:
- KABUSYS_ENV: 実行環境。development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、MockBrokerClient を利用し paper_trading.db に記録（本番 DB と分離）
- DUCKDB_PATH: 分析用 DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- LOG_DIR: ログ出力先ディレクトリ（デフォルト: logs）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- PAPER_FILL_MODE: paper_trading の注文約定モード（instant | partial | never | reject、デフォルト: instant）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト: 0。本番では 0 推奨）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring の環境変数で上書き可能。デフォルト 60）

設定ウィザードで主要項目は対話的に入力できます。生成後は python -m kabusys.validate_config で検証してください。

---

## 実行方法（起動スクリプト・ツール）

各モジュールはモジュール実行（-m）形式で起動できます。プロジェクトルートで以下を実行してください。

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（警告も失敗扱い）: python -m kabusys.validate_config --strict

- ExecutionEngine を起動（発注エンジン）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
  - run_execution は data/stop_requested.flag を見ることで外部から停止要求を検出します。
  - 起動時に data/execution.pid に PID を書きます。

- Monitoring（監視ループ）を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - 監視は常に（KABUSYS_ENV に関わらず）本番用 sqlite_path を使用して監視ログを記録します（Settings.sqlite_path）。
  - 監視の停止は data/stop_requested.flag の作成により実行スクリプトに検知されます。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH でも DB パスを指定できます。

- AI / Research の関数（ライブラリ利用）
  - news_nlp.score_news(conn, target_date, api_key=None) などはライブラリ API です。直接 CLI は用意していませんが、スクリプトや cron から呼び出して使用してください。
  - OpenAI API を使用する際は OPENAI_API_KEY を設定してください。

---

## 停止・Kill スイッチについて

- stop_requested.flag
  - 実行スクリプト（run_execution.py, run_monitoring.py）は data/stop_requested.flag の存在を見てメインループを終了します。手動で停止させたい場合はこのファイルを作成します（例: touch data/stop_requested.flag）。
- kill.flag（KillSwitch）
  - 監視モジュールがリスク条件（ドローダウンやポジション上限など）を検知した場合、data/kill.flag を書き込むことで ExecutionEngine に停止を促します。
  - KillSwitch は冪等にファイルを作成し、既存の場合は再作成しません。ExecutionEngine 側は起動時に KILL_FLAG_CLEAR_ON_START 設定で自動クリアの挙動を制御できます。
- PID ファイル
  - run_execution は data/execution.pid に PID を出力します。管理用に使用できます。

---

## ログ設定

- ログはデフォルトで stdout（コンソール）とファイル（logs/<app_name>.log）へ出力されます。日次ローテーションで 30 日保持されます。
- ログレベルは LOG_LEVEL で制御します（デフォルト: INFO）。
- ログディレクトリは LOG_DIR またはデフォルトの logs/。ディレクトリ作成に失敗した場合はファイル出力は無効化されコンソールのみ出力します。

---

## ディレクトリ構成（抜粋）

以下は主要なファイル・モジュールの一覧（src/kabusys 以下）。実際のリポジトリにはさらにファイルが含まれる可能性があります。

- src/kabusys/
  - __init__.py
  - __version__ = "0.1.0"
  - config.py                — 環境変数・設定管理（.env 自動読み込みロジック含む）
  - config_setup.py          — 対話式 .env ウィザード
  - validate_config.py       — 起動前チェック CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading 検証レポート
  - utils/
    - __init__.py
    - logging_setup.py       — 共通ロギング設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite ベースの永続化層（DB 初期化・CRUD）
    - system_monitor.py
    - trade_monitor.py       — （実装ファイルは省略）
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py       — （実装ファイルは省略）
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
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - data/                    — 実行時に作られることが想定されるディレクトリ（DB・PID・フラグファイル等）
  - logs/                    — ログ出力先（デフォルト）

---

## 開発時のヒント / 注意点

- paper_trading モードは本番 DB と完全分離されるよう設計されています。ペーパートレード時は PAPER_TRADING_SQLITE_PATH を使用してください。
- OpenAI API を用いる処理は外部サービスに依存するため、APIキーやレート制限に注意してください。リトライやフォールバックが各モジュールに実装されていますが、費用や呼び出し頻度は運用で管理してください。
- .env は機密情報（API キー等）を含むため、絶対に Git にコミットしないでください。
- 設定検証（validate_config）は起動前の必須チェックとして有用です。--strict モードで警告も失敗扱いにできます。
- ローカルで実行する場合、psutil のプロセス優先度設定や CPU affinity の呼び出しで権限が必要になる場合があります。権限不足は警告ログとなり無視されます。

---

必要であれば README にサンプル .env のテンプレートやよく使うコマンド群（systemd ユニット例や cron ジョブ例）、CI 用のチェックフローなども補足できます。どの情報を追加したいか教えてください。