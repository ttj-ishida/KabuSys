# KabuSys — README

このリポジトリは日本株向けの自動売買・リサーチ基盤（KabuSys）の一部実装です。  
以下はコードベースの主要コンポーネント、使い方、セットアップ手順、ディレクトリ構成の概要です。

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 環境変数（主なもの）
- 使い方（起動・停止・ツール）
- ディレクトリ構成（主要ファイルの説明）

---

## プロジェクト概要

KabuSys は日本株自動売買システムの基盤ライブラリ群です。  
主な領域は実行（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ（ファクター計算）、および AI ベースのニュースセンチメント判定などです。  
設計方針として以下を重視しています：

- 環境変数 / .env による設定管理
- 本番とペーパートレードのデータ分離（paper_trading 用 DB）
- DuckDB を用いたリサーチ用高速集計
- OpenAI（gpt-4o-mini）を用いたニュース NLP（オプション）
- 監視・Kill Switch による安全停止機構

---

## 主な機能一覧

- 設定管理
  - `.env` 自動読み込み、対話式設定ウィザード（config_setup.py）、設定検証 CLI（validate_config.py）
- 実行（Execution）
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - Paper trading 対応（環境 `paper_trading` の場合は MockBroker を使用し専用 DB に記録）
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine（run_monitoring.py 起動）
  - SQLite に監視ログ永続化（monitoring_db.py）
  - KillSwitch（閾値超過で data/kill.flag を作成）
- ポートフォリオ構築
  - 候補選定、等金額・スコア重み、リスク調整、ポジションサイズ計算（純関数群）
- リサーチ
  - DuckDB を用いたファクター計算（モメンタム/バリュー/ボラティリティ等）および特徴量探索
- AI（任意）
  - ニュース記事を LLM でスコアリングして ai_scores テーブルへ保存（news_nlp）
  - 市場レジーム判定（regime_detector）
- ツール
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone ...（リポジトリ URL を指定）

2. Python 環境の準備（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 必要なパッケージ例:
     - duckdb
     - psutil
     - openai  （AI 機能を使用する場合）
     - pyyaml  （config 検証で YAML 検査を行いたい場合）
   - 例:
     - pip install duckdb psutil openai pyyaml

   ※ requirements.txt は付属していないため、必要に応じて上記を pip freeze して固定してください。

4. 初期設定（.env の作成）
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - または手動で `.env` を作成（.env.example を参照して設定してください）

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

6. データディレクトリの作成（必要に応じて）
   - デフォルトの DB/ログパスは `data/`、`logs/` 等です。適宜作成されますが、アクセス権に注意してください。

---

## 環境変数（主要）

- KABUSYS_ENV
  - 値: development | paper_trading | live
  - default: development
  - paper_trading の場合、実行はペーパーブローカー／専用 SQLite を使用

- JQUANTS_REFRESH_TOKEN （必須）
- KABU_API_PASSWORD （必須）
- KABU_API_BASE_URL
  - default: http://localhost:18080/kabusapi

- DUCKDB_PATH
  - default: data/kabusys.duckdb

- SQLITE_PATH
  - default: data/monitoring.db

- PAPER_TRADING_SQLITE_PATH
  - default: data/paper_trading.db（paper_trading 実行時に使用）

- PAPER_FILL_MODE
  - ペーパートレードの約定挙動
  - 有効値: instant | partial | never | reject
  - default: instant

- OPENAI_API_KEY
  - AI（news_nlp / regime_detector）を利用する場合に必要

- LOG_LEVEL
  - DEBUG/INFO/WARNING/ERROR/CRITICAL
  - default: INFO

- LOG_DIR
  - ログ出力ディレクトリ（デフォルト `logs/`）

- MONITOR_POLL_INTERVAL
  - Monitoring のポーリング間隔（秒）
  - default: 60
  - 0 以下や不正な値はデフォルトにフォールバック

- KILL_FLAG_PATH / PID_FILE_PATH 等は Settings 経由で取得可能（デフォルトは data 以下）

---

## 使い方

### 1) 設定の初期化・確認

- 環境設定ウィザード（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

### 2) 実行エンジンの起動（ExecutionEngine）

- 通常起動:
  - python -m kabusys.run_execution

- 動作補足:
  - KABUSYS_ENV が paper_trading の場合、MockBroker（発注は仮想）を使用し、PAPER_TRADING_SQLITE_PATH に記録します。
  - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
  - 実行中は PID ファイル（デフォルト data/execution.pid）を出力します。
  - 終了させたい場合は stop フラグ（stop_requested.flag）を作るか Kill Switch により data/kill.flag が作成されると停止されます。

### 3) 監視ループの起動（Monitoring）

- 起動:
  - python -m kabusys.run_monitoring

- 補足:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定可能（デフォルト 60 秒）
  - 監視は環境にかかわらず本番 sqlite_path を使用（monitoring 用 DB を初期化）
  - 監視中、data/stop_requested.flag が作成されるとループを抜けて終了します

### 4) Kill Switch / 停止制御

- KillSwitch（内部ロジック）により、リスクアラート（ドローダウン超過等）を検出すると `data/kill.flag` を作成します。ExecutionEngine はこのフラグを参照して安全停止します。
- `KillSwitch.clear()` は起動時に Kill Flag をクリアするオプション設定（KILL_FLAG_CLEAR_ON_START）に依存します。※本番環境では自動クリアは推奨されません。

### 5) Paper Trading 検証レポート

- レポート生成:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数を上書きできます）

### 6) AI 機能（ニュース NLP / レジーム判定）

- OpenAI の API キー（OPENAI_API_KEY）が必要です。
- プログラム的に呼び出す例:
  - import duckdb
  - from kabusys.ai.news_nlp import score_news
  - conn = duckdb.connect("data/kabusys.duckdb")
  - score_news(conn, target_date=date(2026,4,1), api_key="...")

- 注意:
  - API 呼び出しはレート制限・一時エラー対策としてリトライロジックがありますが、API キーとコストにご注意ください。

---

## 停止・強制終了の仕組み

- stop_requested.flag
  - run_execution/run_monitoring はこのファイルの存在を監視し、存在した場合にループを抜けて終了します。
  - パス: プロジェクトルート/data/stop_requested.flag（コード内の _STOP_FLAG）

- kill.flag
  - KillSwitch が異常判定時に作成するファイル。実行エンジンはこれを検出して停止します。
  - デフォルトパスは Settings.kill_flag_path（通常 data/kill.flag）

---

## ロギング

- 共通ログ設定は kabusys.utils.logging_setup.setup_logging を使用
- デフォルト出力:
  - コンソール（stdout）
  - ログファイル: logs/<app_name>.log（日次ローテーション、30日保持）
- LOG_LEVEL / LOG_DIR で動作を変更可能

---

## ディレクトリ構成（主要ファイルの説明）

以下は repo の主要なディレクトリ / ファイルとその役割です（src/kabusys 相対）:

- __init__.py
  - パッケージ情報（バージョン等）

- config.py
  - Settings クラス: 環境変数の読み込み・検証・デフォルト値を提供

- config_setup.py
  - 対話式 .env ウィザード

- validate_config.py
  - 起動前の設定検証 CLI

- run_execution.py
  - ExecutionEngine 起動スクリプト（ブローカー生成、エンジン起動、停止フラグ監視）

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔指定）

- utils/
  - logging_setup.py: ログ初期化ユーティリティ
  - process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ

- monitoring/
  - monitoring_db.py: SQLite の監視ログ用テーブル初期化・永続化 API
  - system_monitor.py: CPU/メモリ/ディスク/データ鮮度・プロセスの監視
  - risk_monitor.py: ドローダウン・ポジション上限監視
  - trade_monitor.py: （trade 関連の監視。今回抜粋されているが存在します）
  - kill_switch.py: Kill フラグ作成 / 管理
  - monitoring_engine.py: 複数監視コンポーネントの統合

- execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
  - （実行ロジック・ブローカー抽象・リスク管理）

- portfolio/
  - portfolio_builder.py, risk_adjustment.py, position_sizing.py
  - 候補選定・重み付け・ロット丸め・リスク制約等の純関数群

- research/
  - factor_research.py: DuckDB を用いたファクター計算（momentum, volatility, value）
  - feature_exploration.py: 将来リターン計算、IC（Information Coefficient）等

- ai/
  - news_nlp.py: ニュース記事を LLM でスコアリングして ai_scores に保存
  - regime_detector.py: ETF MA 乖離＋LLM による市場レジーム判定
  - 依存: OpenAI client（openai パッケージ）

- tools/
  - paper_verification_report.py: Paper Trading の検証レポート生成

---

## 開発運用上の注意

- 本番環境（KABUSYS_ENV=live）では kill_flag の自動クリアや .env の管理に注意してください（validate_config で警告が出ます）。
- ペーパートレードは実運用 DB と分離されますが、設定ミスにより実口座へ発注されないようブロックを確認してください。
- OpenAI 使用機能は API コストが発生します。キーと利用ポリシーに注意してください。
- ログディレクトリ・DB ディレクトリについては権限（読み書き）を事前に確認してください。

---

必要であれば、この README をベースに以下の追加を作成できます：
- requirements.txt（依存関係固定）
- .env.example（テンプレート）
- systemd / supervisor / Docker Compose 用の起動設定例

ご希望があれば追加で作成します。