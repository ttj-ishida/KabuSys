# KabuSys — README

簡潔な説明書。日本株自動売買 / 研究 / 監視を行うモジュール群を含むパッケージです。  
この README はプロジェクト概要、主な機能、セットアップ手順、実行方法、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを支援する Python パッケージです。主要な責務は以下のとおりです。

- 戦略研究・ファクター計算（DuckDB を利用）
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- ExecutionEngine（発注、リスク管理、注文管理）
- Monitoring（システム稼働性、注文状況、リスク監視、Kill Switch）
- AI 補助（ニュースの NLP スコアリング、レジーム判定）
- ユーティリティ・ツール（設定ウィザード、設定検証、紙トレード検証レポート生成）

設計上のポイント：
- 環境変数および .env ファイルで設定を管理（自動ロード機能あり）
- 本番・ペーパートレード DB の分離
- フェイルセーフ（API 失敗時のフォールバック、部分失敗時の永続化保護）
- ロギング/プロセス優先度設定など運用に配慮したユーティリティを提供

---

## 機能一覧

- 設定管理
  - .env 自動読み込み（プロジェクトルートの .env / .env.local）
  - 設定ウィザード（対話式で .env を生成）
  - 設定検証 CLI（必須環境変数や config/*.yaml の存在チェック）
- Execution
  - Broker クライアントの抽象化（paper_trading では MockBrokerClient を使用）
  - OrderManager / RiskManager / Reconciler / ExecutionEngine の実装
  - PID ファイル / stop フラグによるデーモン制御
- Monitoring
  - SystemMonitor（CPU/Mem/Disk、データ鮮度、プロセス監視）
  - TradeMonitor（注文の滞留や異常約定検出）
  - RiskMonitor（ドローダウン、ポジション上限監視）
  - KillSwitch、AlertManager と連携して安全停止を行う
  - 永続化用の SQLite テーブル群（system_status, trade_logs, positions, risk_logs, dashboard）
- Research / Data
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 特徴量探索（将来リターン、IC 計算、統計サマリー）
  - DuckDB 接続での高速分析
- AI（OpenAI）
  - ニュース NLP による銘柄ごとのセンチメント付与（ai_scores への書き込み）
  - 市場レジーム判定（ETF MA とマクロニュースの組合せ）
- ツール
  - `.env` 生成ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
  - Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report

---

## セットアップ手順（簡易）

1. リポジトリをクローンし、パッケージのルートに移動。

2. Python 仮想環境を作成して有効化（任意だが推奨）。
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール。
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 主要な依存例（プロジェクト内から推測）:
     - pip install duckdb psutil openai
   - YAML 検証（任意）:
     - pip install PyYAML

4. .env の準備（推奨: ウィザードを使用）
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 生成後、必須環境変数が設定されているか検証:
     - python -m kabusys.validate_config
     - --strict を付けると警告も失敗扱いになります

5. 環境変数について（主要なもの）
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - OPENAI_API_KEY（AI 機能を使う場合）
   - KABUSYS_ENV（development | paper_trading | live）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（monitoring 用: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB: data/paper_trading.db）
   - PAPER_FILL_MODE（instant | partial | never | reject、デフォルト: instant）
   - LOG_LEVEL（DEBUG|INFO|WARNING|ERROR|CRITICAL）
   - LOG_DIR（ログ出力先ディレクトリ）
   - MONITOR_POLL_INTERVAL（監視ループの秒間隔、デフォルト: 60）
   - KILL_FLAG_CLEAR_ON_START（本番で自動クリアしないことを推奨。0 または 1）

6. データディレクトリ作成
   - data, logs 等を作成（logging_setup は logs ディレクトリを作成しようとします）
   - 例: mkdir -p data logs

注意: config は .env（および .env.local）から自動ロードされます（プロジェクトルートが検出できた場合）。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（実行例）

実行スクリプトはパッケージ内のモジュールとして起動できます。基本的には Python モジュールとして起動します。

- Monitoring の起動
  - python -m kabusys.run_monitoring
  - 仕様:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60 秒）
    - 停止にはプロジェクトルート/data/stop_requested.flag の作成（存在検出でループ終了）
    - 監視は Settings.sqlite_path（monitoring DB）を使用（環境にかかわらず本番 sqlite_path を参照）

- ExecutionEngine の起動
  - python -m kabusys.run_execution
  - 仕様:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録
    - 起動時に data/stop_requested.flag が存在すると起動せず終了
    - 実行中は data/execution.pid に PID を書き、stop フラグの検出で engine.stop() を呼び安全停止
    - Monitoring が KillSwitch を作動させると data/kill.flag が作成され、ExecutionEngine 側で停止判定に利用できる

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告も失敗）:
    - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH 環境変数の代替）

ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力されます。コンソール（stdout）にも出力されます。

---

## 運用上のファイル/フラグ

- data/stop_requested.flag
  - 手動で作成すると run_monitoring / run_execution は起動・実行ループを終了するトリガーになります。
- data/kill.flag
  - Monitoring の KillSwitch が危険検知時に作成します。ExecutionEngine の安全停止要求に使用。
- data/execution.pid
  - ExecutionEngine 起動時に書き込まれる PID ファイル（run_execution が使用）。
- ログ
  - デフォルト保存先: logs/
  - LOG_DIR 環境変数で変更可能

---

## 主要な設定 / 環境変数（まとめ）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意・重要:
- KABUSYS_ENV = development | paper_trading | live
- OPENAI_API_KEY（AI 機能を使用する場合）
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（data/paper_trading.db）
- PAPER_FILL_MODE（instant|partial|never|reject、デフォルト instant）
- LOG_LEVEL（デフォルト INFO）
- LOG_DIR（ログ保存先）
- MONITOR_POLL_INTERVAL（監視間隔、秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（本番では 0 推奨）

---

## ディレクトリ構成（主なファイルと説明）

ルート: src/kabusys 以下を中心に記載します。

- __init__.py
  - パッケージのエントリ。バージョン情報など。

- config.py
  - 環境変数と .env の自動読み込み、Settings クラス（各種設定プロパティ）を提供。

- config_setup.py
  - 対話式 .env 作成ウィザード。

- validate_config.py
  - 設定検証 CLI（環境変数・config/*.yaml 等のチェック）。

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト。

- run_execution.py
  - ExecutionEngine の起動スクリプト（paper_trading をサポート）。

- monitoring/
  - monitoring_db.py — SQLite テーブルの作成と MonitoringDB クラス（読み書きユーティリティ）
  - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - trade_monitor.py — (注文監視ロジック、コード中に定義あり)
  - risk_monitor.py — ドローダウン・ポジション上限チェック
  - kill_switch.py — kill.flag の作成・管理
  - monitoring_engine.py — 各モニタを束ねる実行エンジン
  - alert_manager.py — アラート送信（LINE 等。コードベースに実装がある想定）

- execution/
  - execution_engine.py — ExecutionEngine 本体
  - broker_factory.py — BrokerClient の生成（paper_trading 用 mock を含む）
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 発注・注文管理・リスク管理の各コンポーネント

- portfolio/
  - portfolio_builder.py — 候補選定、等重/スコア重み計算
  - position_sizing.py — 株数決定ロジック（単元丸め、aggregate cap）
  - risk_adjustment.py — セクター制限、レジーム乗数

- research/
  - factor_research.py — モメンタム/ボラティリティ/バリューの計算
  - feature_exploration.py — 将来リターン、IC、統計サマリ
  - __init__.py に高レベル API をエクスポート

- ai/
  - news_nlp.py — ニュースを OpenAI でスコアリングして ai_scores に書き込む
  - regime_detector.py — マクロセンチメント + ETF MA を使った市場レジーム判定
  - __init__.py

- utils/
  - logging_setup.py — 統一的なロギング設定（stdout + 日次ローテートファイル）
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト

- data/
  - （実行時に作成される SQLite / DuckDB / flag / pid ファイルなどを置くディレクトリ）

---

## 運用上の注意点（抜粋）

- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にして自動クリアを無効にすることを推奨します。
- Monitoring は Settings.sqlite_path（monitoring DB）を常に使用します。環境にかかわらず監視ログは同じ DB に記録される設計になっています。
- ペーパートレードは本番 DB と分離されます（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI 等外部 API キーは .env に安全に保存し、Git に .env をコミットしないこと。
- ログディレクトリ作成に失敗した場合、ファイル出力は無効化されコンソールのみになります。適切なパーミッションとディスク容量を確保してください。

---

必要であれば、README に例示する systemd / supervisor サービスファイル例や、より詳細な依存関係（requirements.txt）を追加できます。追加希望があれば対象の項目を教えてください。