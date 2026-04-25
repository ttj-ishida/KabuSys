# KabuSys

日本株自動売買システム KabuSys の簡易ドキュメント（README）。  
この README はリポジトリ内のコードベース（src/kabusys 以下）を元に作成しています。

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（主要スクリプト／CLI）
- 主要環境変数（よく使う設定）
- ディレクトリ構成（抜粋）
- 補足・運用メモ

---

## プロジェクト概要

KabuSys は日本株向けの自動売買および関連ユーティリティ群をまとめたパッケージです。  
主に以下の責務を持ちます：

- 発注エンジン（ExecutionEngine）の起動・運用（本番／ペーパートレード対応）
- システム監視（SystemMonitor / MonitoringEngine）
- リスク監視（ドローダウン、ポジション上限など）
- ポートフォリオ構築（銘柄選定・重み付け・株数算出）
- リサーチ（ファクター計算、特徴量探索）
- AI を用いたニュースセンチメント／レジーム判定
- 各種ツール（ペーパートレード検証レポート生成等）

設計上の特徴：
- DB：DuckDB（分析）＋SQLite（監視・発注ログ）を利用
- 環境に依存しない .env ベースの設定読み込み（自動ロード）
- 本番と paper_trading の DB/クライアント分離をサポート
- OpenAI API を利用した NLP 機能（任意）

---

## 主な機能一覧

- run_execution: 発注エンジンの起動（KABUSYS_ENV により実際発注 or モック）
- run_monitoring: SystemMonitor のポーリングループ起動
- MonitoringEngine: System / Trade / Risk 各モニタの統合・アラート送出
- KillSwitch: フラグファイルによるエンジン停止機構
- portfolio: 候補選定・重み計算・ポジションサイズ計算・セクター制限等
- research: ファクター計算（Momentum, Volatility, Value）・将来リターン計算・IC
- ai.news_nlp: ニュースを LLM（OpenAI）でスコアリングして ai_scores に保存
- ai.regime_detector: MA とマクロニュースを合成して市場レジーム判定
- tools.paper_verification_report: ペーパートレード結果の検証レポート生成
- config_setup: .env の対話式ウィザード
- validate_config: 起動前の設定検証 CLI

---

## セットアップ手順（開発／実行）

前提：Python 3.9+（パッケージの型ヒントから）、git など

1. リポジトリクローン / 作業ディレクトリへ移動
   - このコードはパッケージが `src/` 配下にある構成です。モジュールを `python -m ...` で実行する場合、`PYTHONPATH=src` を通すかパッケージをインストールしてください。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate

3. 依存パッケージをインストール
   - 最低限必要になる主要パッケージ（例）:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（validate_config が YAML を検証する場合に任意）
   - 例:
     - pip install duckdb psutil openai PyYAML
   - （Requirements ファイルがある場合はそれを使ってください）

4. .env の作成
   - 対話式ウィザード:
     - PYTHONPATH=src python -m kabusys.config_setup
     - デフォルトではプロジェクトルートに `.env` を作成します。
   - 手動作成の主なキー（詳細は下記参照）:
     - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live）
     - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, LOG_LEVEL, OPENAI_API_KEY（AI 利用時）
   - 自動ロード:
     - パッケージ起動時、プロジェクトルートの `.env` / `.env.local` が自動で読み込まれます（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

5. 設定検証（起動前チェック）
   - PYTHONPATH=src python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります。

---

## 使い方（主要スクリプト / CLI）

注意：パッケージ実行時は `PYTHONPATH=src` を通すかパッケージをインストールしてください。

- 発注エンジン（ExecutionEngine）を起動
  - PYTHONPATH=src python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使用され、データは `data/paper_trading.db`（PAPER_TRADING_SQLITE_PATH）に保存されます。
    - PID ファイル: data/execution.pid を使用。
    - 停止は data/stop_requested.flag を作成することで通知。

- 監視ループを起動（SystemMonitor）
  - PYTHONPATH=src python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒）。デフォルト 60。
  - 監視は常に（KABUSYS_ENV にかかわらず）本番の sqlite_path を使用して監視ログを格納します。

- .env 設定ウィザード
  - PYTHONPATH=src python -m kabusys.config_setup

- 設定検証
  - PYTHONPATH=src python -m kabusys.validate_config [--strict]

- Paper Trading 検証レポート生成
  - PYTHONPATH=src python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）

- AI / リサーチ機能（プログラムから直接利用）
  - ニューススコアリング（ai.news_nlp.score_news）
    - 引数: DuckDB 接続、target_date、api_key（省略時は OPENAI_API_KEY を参照）
    - 例（スクリプト内で）:
      - from kabusys.ai.news_nlp import score_news
      - score_news(duckdb_conn, date(2026, 4, 10), api_key="sk-...")
  - レジーム判定（ai.regime_detector.score_regime）
    - 同様に DuckDB 接続と target_date、api_key を渡す
  - リサーチ（factor 計算等）は kabusys.research 配下の関数を呼びます（DuckDB 接続が必要）

---

## 主要環境変数（抜粋とデフォルト）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuステーション API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- DUCKDB_PATH: 分析用 DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログファイルの出力先（デフォルト: logs/）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant, partial, never, reject）

ファイルベースのフラグ／PID:
- data/stop_requested.flag: 外部から監視/実行ループに停止を通知するフラグ
- data/execution.pid: ExecutionEngine の PID ファイル（run_execution が使用）
- data/kill.flag: KillSwitch によって作成される停止理由フラグ（実行エンジン停止用）

自動 .env 読み込み:
- デフォルトでプロジェクトルートの `.env` / `.env.local` を読み込みます。自動読み込みを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（抜粋）

リポジトリは src/kabusys 配下に主要なモジュールを持ちます。主要ファイル・パッケージの一覧（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み・Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py       — SQLite テーブル定義・永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       — （アラート送信を集約するモジュール、存在）
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
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
  - data/                    — 実行時に使用するデータファイル（logs/, data/ 等）

（上記は主要モジュールの抜粋です。詳細はソースツリーを参照してください。）

---

## 補足・運用メモ

- ログは stdout とファイル（logs/<app_name>.log）両方に出ます。ログディレクトリは自動作成されますが、作成に失敗した場合はコンソール出力のみになります。
- モニタリング（run_monitoring）は監視 DB（SQLITE_PATH）に書き込みます。monitoring 自体は KABUSYS_ENV にかかわらず本番 sqlite_path を参照する実装になっています（重要）。
- ペーパートレード時は run_execution が PAPER_TRADING_SQLITE_PATH を使用し、本番 DB と分離されます。
- OpenAI を利用する機能は API エラーやタイムアウトに対してリトライやフォールバックを実装しており、API キーが無い場合は明示的に例外を投げます。AI 機能を運用する場合はレート制限とコストに注意してください。
- データの鮮度チェックやリスクイベントの重複防止（dedup）など、運用上の安全弁が組み込まれていますが、本番運用前に validate_config で設定を必ずチェックしてください。
- 開発用に、.env や .env.local を絶対にリポジトリにコミットしないでください（config_setup のヘッダにも注意喚起があります）。

---

この README はコードの主要点を要約したものです。より詳細な仕様や設計メモはソースコード内の docstring やコメントを参照してください。必要であれば、起動フロー図・各モジュールの詳細ドキュメントを別途作成できます。