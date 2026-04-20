# KabuSys

日本株自動売買システムのコアライブラリ群と起動スクリプト群。  
このリポジトリには、発注エンジン（ExecutionEngine）、監視系（Monitoring）、ポートフォリオ構築・リサーチ・AI モジュールなどが含まれます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の機能を含むモジュール群です。

- 発注エンジン（ExecutionEngine）と注文管理（OrderManager / OrderRepository）
- 監視システム（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch）
- ポートフォリオ構築（銘柄選定・重み付け・株数決定）
- リサーチ（ファクター計算、特徴量探索）
- AI 系（ニュース NLP による銘柄センチメント、レジーム判定）
- ユーティリティ（ログ設定、プロセス優先度設定、環境設定ウィザード / 検証ツール）
- Paper Trading 用の検証レポート生成ツール

設計方針として、データアクセスは DuckDB / SQLite を使用し、リサーチは外部発注 API に影響を与えないよう分離されています。AI 呼び出しは OpenAI SDK を利用する設計です。

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py : ExecutionEngine を起動（KABUSYS_ENV に応じて Paper Trading を分離）
  - run_monitoring.py : SystemMonitor のポーリングループを起動（監視ログを SQLite に保存）
- 環境管理
  - config_setup.py : 対話式で `.env` を作成 / 更新するウィザード
  - validate_config.py : .env と config/*.yaml の検証 CLI（--strict オプション）
- 監視
  - monitoring_engine.py / system_monitor.py / trade_monitor.py / risk_monitor.py / kill_switch.py
  - 監視ログ永続化: monitoring_db.py（SQLite）
- ポートフォリオ構築
  - portfolio_builder.py / position_sizing.py / risk_adjustment.py（等重配分、スコア重み、リスクベース等）
- リサーチ
  - research/factor_research.py（モメンタム/ボラティリティ/バリュー）
  - research/feature_exploration.py（将来リターン、IC、統計概要）
- AI
  - ai/news_nlp.py : raw_news を LLM に投げて銘柄ごとのスコアを ai_scores に保存
  - ai/regime_detector.py : ETF の MA とマクロニュースを用いた市場レジーム判定
- ツール
  - tools/paper_verification_report.py : Paper Trading の検証レポート生成

---

## セットアップ手順

注意: ソースの型注釈（`X | None` など）から Python 3.10 以上を想定しています。

1. リポジトリをクローンし、仮想環境を作成・有効化
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要なパッケージをインストール  
   依存はプロジェクトで使用されている主要ライブラリです（requirements.txt がない場合は手動で）。
   - 推奨パッケージ:
     - duckdb
     - psutil
     - openai
     - PyYAML (config yaml 検証を行う場合)
   - 例:
     - pip install duckdb psutil openai PyYAML

3. .env の作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - または手動で `.env` を作成。必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 任意:
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート通知）
     - KABUSYS_ENV（development / paper_trading / live）
     - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH 等

4. 設定の検証（起動前推奨）
   - python -m kabusys.validate_config
   - 警告を厳格に扱う場合:
     - python -m kabusys.validate_config --strict

5. データディレクトリの初期化
   - デフォルトは `data/` 配下に DB ファイルやフラグファイルが配置されます。必要に応じ作成してください（多くの処理は自動作成します）。

---

## 使い方

基本的な起動方法とよく使うコマンド例を示します。各スクリプトはモジュールとして実行できます（ワーキングディレクトリはプロジェクトルート推奨）。

- ExecutionEngine を起動（本番/開発/ペーパートレードは KABUSYS_ENV により制御）
  - KABUSYS_ENV を設定して起動:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - 特記事項:
    - paper_trading モード時は `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）を使い、本番 SQLite と分離します。
    - 起動時に `data/stop_requested.flag` が存在すると起動しません。
    - 実行中は `data/execution.pid` に PID を書きます。

- 監視ループを起動
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（秒、デフォルト 60）
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は常に本番の sqlite_path（Settings.sqlite_path）を使用して監視ログを保存します。
  - run_monitoring はプロセス優先度を "high" に設定し、定期的に SystemMonitor.check_once() を呼びます。
  - 停止フラグ: プロジェクトルート/data/stop_requested.flag を作成すると監視ループが終了します。

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（警告をエラー扱い）:
    - python -m kabusys.validate_config --strict

- Paper Trading 検証レポートの生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI / バッチ処理（ライブラリ関数として利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続（duckdb.connect(...)）を引数に取り、DB のテーブルを読み書きします。
  - OPENAI_API_KEY を環境変数または引数で指定してください。

- ログ設定
  - 各スクリプトの起動時に `kabusys.utils.logging_setup.setup_logging(app_name="...")` を呼び出して統一ログ出力を行います。
  - 環境変数 `LOG_DIR` または引数でログディレクトリを指定できます（デフォルト logs/）。

- Kill Switch / 停止フラグ
  - KillSwitch は監視モジュールから起動上のリスクが検出された際に `data/kill.flag` を書き込みます。
  - ExecutionEngine は起動時／ループ中に `data/stop_requested.flag` をチェックして安全にシャットダウンします。

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN （必須）
- KABU_API_PASSWORD （必須）
- KABUSYS_ENV : development | paper_trading | live （デフォルト development）
- OPENAI_API_KEY : OpenAI API キー（AI 機能）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH : 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH : paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL : ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL : run_monitoring のポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等

.env の自動読み込み:
- プロジェクトルートに `.env` / `.env.local` がある場合、自動的に環境に読み込まれます（OS 環境変数を優先）。
- 自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

---

## ディレクトリ構成

以下は `src/kabusys` の主要ファイル・ディレクトリ構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動読み込み含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - monitoring/
    - monitoring_db.py       — SQLite スキーマ / 永続化層
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (参照される)
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
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
  - utils/
    - logging_setup.py
    - process_priority.py

（注）リストは主要なファイルを抜粋したもので、実際のリポジトリにはさらにモジュールや補助的なコードが含まれます。

---

## 補足・運用ノウハウ

- Paper Trading と Live を明確に分離しています。KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB に記録されます。
- 監視系は DB にログを保存し、Kill Switch により自動停止をサポートします。運用時は `data/kill.flag` / `data/stop_requested.flag` の存在を把握してください。
- OpenAI を使う機能は API コストとレイテンシが関わります。`OPENAI_API_KEY` を設定し、必要に応じバッチサイズやリトライ設定を調整してください。
- DuckDB の SQL を用いてリサーチ処理を行うため、prices_daily / raw_financials / raw_news 等のテーブル整備が前提です。

---

README はここまでです。必要であれば以下の追加を作成できます:
- requirements.txt の提案（バージョン固定）
- systemd / supervisor 向けのサンプルユニットファイル（run_execution / run_monitoring 用）
- 詳しい DB スキーマ説明や config/*.yaml の生成手順

どれを優先して追加しますか？