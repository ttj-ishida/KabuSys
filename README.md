# KabuSys

日本株向け自動売買／リサーチ基盤のコンポーネント群です。  
このリポジトリは発注エンジン、監視、ポートフォリオ構築、リサーチ、AI（ニュース）スコアリングなどのモジュールで構成されています。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方
- ディレクトリ構成（主要ファイル）

---

## プロジェクト概要

KabuSys は日本株の自動売買システム／リサーチ基盤です。主な役割は次のとおりです。

- シグナル → ポートフォリオ構築 → 発注のフロー（ExecutionEngine）
- 実行中システムの監視（SystemMonitor / MonitoringEngine）
- ペーパートレード環境の分離（MockBroker、専用 SQLite）
- ニュースを LLM（OpenAI）でスコアリングするモジュール
- DuckDB を用いたファクター計算・リサーチ機能
- 環境設定ウィザード・設定検証ツール

設計上の特徴：
- 環境変数／.env による設定管理（config モジュール）
- ペーパートレード時は本番 DB と分離（data/paper_trading.db）
- ログは統一的に設定（logs/<app_name>.log、日次ローテーション）
- フラグファイルによる安全停止（data/kill.flag / data/stop_requested.flag）

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine の起動スクリプト（KABUSYS_ENV に応じて MockBroker を使用）
  - run_monitoring.py: SystemMonitor をポーリングで回す監視スクリプト（MONITOR_POLL_INTERVAL 指定可）
- 設定管理
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: .env と config/*.yaml の検証 CLI（--strict オプションあり）
- モニタリング
  - monitoring_engine.py: 各 Monitor（System / Trade / Risk）を束ねる
  - system_monitor.py, risk_monitor.py, kill_switch.py, monitoring_db.py: 監視ロジックと SQLite 永続化
- Execution 系
  - ブローカー抽象（BrokerClientFactory 等）／ExecutionEngine（発注ロジック）
  - ペーパートレード対応（専用 DB / fill_mode 設定）
- ポートフォリオ構築（純粋関数）
  - portfolio_builder.py: 候補選定・重み計算（等配分 / スコア加重）
  - position_sizing.py: 株数計算・単元丸め・投下資金スケーリング
  - risk_adjustment.py: セクターキャップ・レジーム乗数
- リサーチ
  - research.factor_research: momentum / value / volatility ファクター計算（DuckDB）
  - research.feature_exploration: 将来リターン、IC、統計サマリ
- AI（ニュース）
  - ai.news_nlp: raw_news を LLM で評価して ai_scores テーブルへ書き込み
  - ai.regime_detector: MA200 とマクロニュースを組み合わせた市場レジーム判定
- ツール
  - tools/paper_verification_report.py: ペーパートレードの検証レポート生成（期間指定可）

---

## セットアップ手順

前提
- Python 3.10 以上（型ヒントで | 演算子等を使用）
- Git、pip

1. リポジトリをクローン
   ```
   git clone <repository-url>
   cd <repository-root>
   ```

2. 仮想環境を作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール  
   （リポジトリに requirements.txt が無い場合は下記を個別にインストール）
   ```
   pip install duckdb psutil openai
   # 任意 / 推奨
   pip install pyyaml
   ```
   - duckdb: リサーチ用 DB
   - psutil: プロセス優先度・システムメトリクス取得
   - openai: ニュース NLP / レジーム判定で使用
   - pyyaml: validate_config で YAML の検証を行う場合

4. 環境変数（.env）の準備  
   対話式で作成する場合:
   ```
   python -m kabusys.config_setup
   ```
   重要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - KABUSYS_ENV (development | paper_trading | live) — default: development
   - DUCKDB_PATH (default: data/kabusys.duckdb)
   - SQLITE_PATH (default: data/monitoring.db)
   - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, default: data/paper_trading.db)
   - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
   - OPENAI_API_KEY (AI 機能を使う場合必須)
   - PAPER_FILL_MODE (instant | partial | never | reject) — paper_trading の約定挙動

   .env は絶対に Git にコミットしないでください。

5. 設定検証（実行前に推奨）
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict  # 警告も FAILURE 扱い
   ```

---

## 使い方

- ログ設定
  - setup_logging() により logs/<app_name>.log に日次ローテーションで出力されます（デフォルト logs/）。
  - 各スクリプトは app_name を "execution" / "monitoring" 等で呼び出します。

- 実行エンジン起動（ExecutionEngine）
  - 本番またはペーパーを環境変数 KABUSYS_ENV で切り替えます。
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し DB は data/paper_trading.db に保存されます（本番 DB と完全分離）。
  - 起動コマンド:
    ```
    python -m kabusys.run_execution
    ```
  - 終了方法:
    - 実行プロセスは data/stop_requested.flag の存在で停止処理を行います（run_execution/run_monitoring はこのフラグを確認します）。
    - kill.flag は ExecutionEngine を停止させるために監視が書き込むファイル（data/kill.flag）。ExecutionEngine 起動時にクリアするオプション KILL_FLAG_CLEAR_ON_START=1 が設定可能ですが、本番では 0 推奨。

- 監視モジュール起動（SystemMonitor）
  - 監視は常時ポーリングを行います（デフォルト 60 秒）。
  - 環境変数でポーリング間隔を上書き:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 監視は Settings にある sqlite_path（監視 DB）を使って永続化します（monitoring は常に本番 sqlite_path を参照）。

- ペーパートレード検証レポート
  - 期間指定でレポートを生成します（PAPER_TRADING_SQLITE_PATH を指定しない場合は data/paper_trading.db）。
    ```
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
    ```

- AI 機能（ニューススコア・レジーム判定）
  - OpenAI API キーが必要です（OPENAI_API_KEY 環境変数）。
  - news_nlp.score_news(conn, target_date, api_key=None) を呼び出すと ai_scores テーブルに書き込みます。
  - regime_detector.score_regime(conn, target_date, api_key=None) は market_regime テーブルに冪等書き込みします。
  - 利用モデルはソース内で gpt-4o-mini を指定しています。

- プロセス優先度設定
  - 起動直後に set_process_priority("high") を試みます。psutil の権限や OS によっては失敗する場合があります。

- 停止フラグ / PID
  - run_execution は data/execution.pid を書き込みます（PID ファイル）。
  - 停止指示は data/stop_requested.flag（実行中ループがこの存在をチェックして終了）や data/kill.flag（実行停止を意図的にトリガ）で行います。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要ファイルとモジュールの一覧（リポジトリ残滓を簡潔化したツリー）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数/.env の自動読み込み & Settings
  - config_setup.py                — .env 対話式ウィザード
  - validate_config.py             — 設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py             — 共通ログ設定
    - process_priority.py          — プロセス優先度 / CPU affinity
  - execution/                      — Execution 関連（発注・注文管理など）
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - monitoring/
    - monitoring_db.py             — SQLite テーブル定義 + 永続化 API
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
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
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py

data/ と logs/ は実行時に作成されるディレクトリとして想定されています。
- デフォルト DB / ファイルパス（Settings で解決）
  - data/kabusys.duckdb
  - data/monitoring.db
  - data/paper_trading.db
  - data/execution.pid
  - data/kill.flag, data/stop_requested.flag
- ログ:
  - logs/execution.log
  - logs/monitoring.log
  - （それぞれ日次ローテーション）

---

## 注意事項 / 運用上のヒント

- .env は重要なシークレットを含みます（J-Quants トークン / kabu API パスワード / OpenAI キー等）。Git 管理下に置かないでください。
- 本番運用（KABUSYS_ENV=live）の場合は validate_config で警告を確認し、LINE 通知等の設定漏れが無いか確認してください。
- process priority の設定や CPU affinity は OS 権限に依存し、アクセス拒否が生じる場合はログに WARN が出ますが実行自体は継続します。
- OpenAI API を利用する機能は API 頻度制限・コストに注意してください。ニューススコアリングはバッチ化（最大 20 銘柄 / コール）で API を叩きます。
- monitoring_db.init_monitoring_db はテーブルの作成と簡単なマイグレーション（カラム追加）を行います。既存 DB にも冪等的に適用されます。

---

必要に応じて README に追記します。特にデプロイ手順、systemd / supervisor / docker 構成、CI/CD、より詳細な ExecutionEngine の API ドキュメントが必要であれば指示してください。