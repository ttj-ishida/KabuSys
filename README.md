# KabuSys

日本株自動売買システムのコアライブラリと起動スクリプト群です。  
この README はリポジトリ内の主要コンポーネント・セットアップ・実行方法・ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システム（バックエンド/エンジン/モニタリング/リサーチ/補助ツール群）です。  
主な設計方針は次のとおりです。

- 発注ロジック（ExecutionEngine）と監視（Monitoring）は分離され安全（kill switch 等）を考慮。
- リサーチ・ポートフォリオ構築は DuckDB を用いたオフライン解析で行い、本番発注系と分離。
- Paper Trading モードでは本番 DB と完全に分離された専用 SQLite DB を使用。
- OpenAI を利用したニュースセンチメント／レジーム判定機能を提供（API キー必須、オプション）。

バージョン: 0.1.0

---

## 機能一覧

- 起動スクリプト
  - run_execution: ExecutionEngine を起動（本番 / ペーパー切替）
  - run_monitoring: SystemMonitor を定期ポーリング
- 設定管理
  - config_setup: 対話式 .env ウィザード (.env の生成/更新)
  - validate_config: .env と config/*.yaml の整合性検証 CLI
- 監視・アラート
  - MonitoringDB: 監視ログ永続化（SQLite）
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine
  - KillSwitch: リスク閾値超過時に flag ファイルを書いて Execution を停止
- 発注関連（Execution 系）
  - Broker クライアントファクトリ、ExecutionEngine、OrderManager、RiskManager 等（実装は execution ディレクトリ）
- ポートフォリオ構築（純粋関数群）
  - 候補選定、重み計算、ポジションサイズ決定、セクター制限、レジーム乗数
- リサーチ
  - factor_research: momentum / value / volatility 等のファクター計算（DuckDB 使用）
  - feature_exploration: 将来リターン計算、IC 計算、統計サマリー
- AI モジュール（OpenAI）
  - news_nlp: ニュース記事のセンチメントを LLM でスコア化して ai_scores に保存
  - regime_detector: ma200 とマクロセンチメントを合成して市場レジーム判定
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成
- ユーティリティ
  - logging_setup: 統一ログ設定（stdout + 日次ローテーション）
  - process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈で | 演算子等を使用）
- Git, SQLite（標準インストール済み）

推奨: 仮想環境を作成して作業してください。

1. リポジトリをクローン
   - git clone ... ; cd <repo>

2. 仮想環境作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - requirements.txt がある場合: pip install -r requirements.txt  
   ない場合は最低限次をインストールしてください:
     - duckdb
     - psutil
     - openai  （AI 機能を使う場合）
     - PyYAML（config/*.yaml の中身検証を行いたい場合）
   例:
     - pip install duckdb psutil openai PyYAML

4. 初期設定ファイル (.env) を作成
   - 対話式ウィザードの実行:
     - python -m kabusys.config_setup
   - または .env.example を参考に手動で `.env` を作成
   - .env はプロジェクトルートに配置します（自動で読み込まれます）
   - 自動ロードを無効化する場合:
     - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

5. 設定検証
   - python -m kabusys.validate_config
   - 本番として厳密にチェックする場合: python -m kabusys.validate_config --strict

6. データディレクトリ
   - デフォルトで使用されるディレクトリ: `data/`, `logs/`
   - 必要に応じて環境変数でパスを変更できます（下記参照）

注意:
- Paper Trading を行う場合、実際の発注は行われません。KABUSYS_ENV を `paper_trading` に設定すると専用 DB（デフォルト: data/paper_trading.db）を使用します。

---

## 環境変数（主なもの）

以下は主要な環境変数と説明・デフォルト値の一覧です。

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能利用時に必須)
- KABUSYS_ENV: 実行環境。development / paper_trading / live（デフォルト: development）
- PAPER_FILL_MODE: paper_trading の MockBroker の約定モード（instant | partial | never | reject）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ出力先（デフォルト: logs/）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch の flag ファイル（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"1" でクリア、デフォルト: "0"）

※ .env は環境変数より低優先度で読み込まれます。OS 環境変数が優先されます。

---

## 使い方（重要なコマンド）

- 設定ウィザード（.env を生成/更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- モニタリング（SystemMonitor のポーリングを起動）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する場合:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

  run_monitoring はプロセス優先度を high に設定し、MonitoringDB（SQLite） と DuckDB に接続します。`data/stop_requested.flag` が存在するとループを抜けて終了します。

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient が使用され、Paper 用 DB に記録されます（data/paper_trading.db）。
  - run_execution は `data/stop_requested.flag` の存在を監視し、存在すれば起動しないか実行中のエンジンを停止します。PID ファイルは data/execution.pid に書かれます。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（ニューススコア等）
  - OPENAI_API_KEY を設定後、ライブラリ関数を呼び出します（例）:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key=None)  # api_key None で環境変数を参照

注意事項:
- AI (OpenAI) 呼び出しは API キーと通信が必要です。コストとレート制限に注意してください。
- kill.flag / stop_requested.flag / data/* ファイルによりプロセスの起動・停止が制御されます。手動でフラグを操作する場合は意図を明確にしてください。

---

## 開発者向け：ライブラリの利用例

- ポートフォリオ構築（等重み）
  - from kabusys.portfolio import select_candidates, calc_equal_weights
  - candidates = select_candidates(buy_signals, max_positions=10)
  - weights = calc_equal_weights(candidates)

- ファクター計算（DuckDB 接続を渡す）
  - from kabusys.research import calc_momentum
  - records = calc_momentum(duckdb_conn, target_date)

- ログ設定（スクリプトの先頭で呼ぶ）
  - from kabusys.utils.logging_setup import setup_logging
  - setup_logging(app_name="execution")

---

## 停止 / フラグについて

- run_monitoring / run_execution の停止
  - プロセスを安全に停止する方法:
    - run_monitoring/run_execution はそれぞれプロジェクトルートの `data/stop_requested.flag` の存在を監視しています。ファイルを作成すると次のポーリングまたはループで終了します。
- Kill Switch（自動停止）
  - 監視コンポーネントが条件を満たすと `KILL_FLAG_PATH`（デフォルト: data/kill.flag）を書き込み、ExecutionEngine に停止指示を送ります。`KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に自動クリアされますが本番では推奨されません。
- PID ファイル
  - ExecutionEngine は PID を `data/execution.pid` に書きます（設定で変更可能）。

---

## ディレクトリ構成

(src 以下をルートとする主要ファイル / ディレクトリ)

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動ロード機能含む）
  - config_setup.py          — 対話式 .env ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading の検証レポート
  - utils/
    - __init__.py
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite テーブル初期化 / DB アクセスラッパ
    - system_monitor.py
    - trade_monitor.py       — （参照されるが省略）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       — （参照されるが省略）
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - execution/
    - （ExecutionEngine / OrderManager / BrokerFactory 等の実装）
  - data/                    — 実行時に使用される SQLite / PID / flag 等（リポジトリには含まれない場合あり）
  - logs/                    — デフォルトのログ出力先

（上記はコードベースの代表的ファイルのみ抜粋しています。実際のリポジトリではさらに多数ファイルが存在する場合があります。）

---

## 注意事項 / 運用上のヒント

- production (KABUSYS_ENV=live) の場合は LINE などの通知設定を必ず確認してください（validate_config の警告・チェックを参照）。
- .env は機密情報を含むため Git 管理に含めないでください。
- DuckDB / SQLite のファイルパスは環境変数で変更可能です。バックアップや永続化に注意してください。
- run_monitoring/run_execution はログ出力（logs/）と flag ファイルによって外部監視／ジョブ制御が容易です。運用環境では systemd / supervisor / cron 等と組み合わせて利用してください。
- OpenAI を使う機能は API 呼び出しに失敗した場合にもフェイルセーフ設計がなされていますが、API コストとレート制限に注意してください。

---

必要であれば、README のサンプル .env（テンプレート）、systemd ユニットの例、または docker-compose 構成例なども作成できます。どの情報を追加したいか教えてください。