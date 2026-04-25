# KabuSys

日本株向け自動売買システムのコアライブラリ群（リサーチ、ポートフォリオ構築、監視、Execution/ペーパートレード用ユーティリティなど）。

このリポジトリは、戦略研究（ファクター計算・特徴量解析）、ポートフォリオ構築、注文発行（本番 / ペーパートレード分離）、監視＆アラート、ニュースの NLP スコアリング（OpenAI）など、実運用を想定したコンポーネントを含みます。

バージョン: 0.1.0

----

## 主な機能

- research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- portfolio
  - 候補選定、等重・スコア重み付け、セクター上限適用、レジーム乗数
  - ポジションサイズ計算（risk-based / equal / score）
- execution（発注系）
  - ExecutionEngine の起動スクリプト（本番 / ペーパートレードの分離）
  - ブローカークライアントファクトリ（paper_trading 時は Mock）
  - リスク管理、オーダーリポジトリ、調整ロジック
- monitoring（監視）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - SQLite ベースの監視 DB（system_status, trade_logs, positions, risk_logs, dashboard）
  - KillSwitch による停止シグナル、停止フラグ管理
- ai
  - ニュース NLP（OpenAI）による銘柄ごとのセンチメントスコア化
  - 市場レジーム判定（ETF MA + マクロニュースの LLM スコア統合）
- tools
  - Paper Trading の検証レポート生成ツール

----

## 動作要件（主な依存）

- Python 3.9+（型アノテーションに Path|None 等を使用）
- 必須パッケージ（例）
  - duckdb
  - psutil
  - openai
- 任意 / 推奨
  - PyYAML（config/*.yaml の検証に使用）
- 標準ライブラリ: sqlite3, logging, threading, datetime, pathlib など

（実際の requirements.txt は本リポジトリに含まれていない場合があるので、pip install 時に不足を補ってください）

----

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール（例）
   ```
   pip install duckdb psutil openai
   # PyYAML が欲しい場合:
   pip install pyyaml
   ```

4. 環境設定ファイル (.env) の作成
   - 対話式ウィザードを使用:
     ```
     python -m kabusys.config_setup
     ```
     ウィザードは .env（デフォルト: プロジェクトルート/.env）を生成します。作成後、`python -m kabusys.validate_config` で検証してください。

   - .env の自動ロード:
     - 起動時、プロジェクトルートの `.env` および `.env.local` が自動で読み込まれます（OS 環境変数優先）。
     - 自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

5. DB ディレクトリ作成（必要に応じて）
   - デフォルトで `data/`、`logs/` を使用します。権限が必要な場合は事前に作成してください。

----

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN — J-Quants API リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabuステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（ai モジュールで必要）
- KABUSYS_ENV — 実行環境（development / paper_trading / live、デフォルト: development）
  - paper_trading の場合、発注系は MockBroker を使用し DB は分離（data/paper_trading.db）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite ファイルパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR — ログ出力ディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE — ペーパートレードの約定挙動（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリア（1=クリア、0=しない。production は 0 推奨）

詳細は `kabusys.config.Settings` を参照してください。

----

## 起動・実行方法（代表的な CLI）

- 環境設定ウィザード（.env 生成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証（.env / config/*.yaml）
  ```
  python -m kabusys.validate_config
  # 警告もエラー扱いにする (--strict)
  python -m kabusys.validate_config --strict
  ```

- 監視サービス起動（SystemMonitor のポーリングループ）
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を秒単位で上書きできます（デフォルト 60 秒）。
  - 停止はプロジェクトルートの `data/stop_requested.flag` を作成するとループが終了します（または Ctrl+C）。

- ExecutionEngine 起動（発注エンジン）
  ```
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を使用し `data/paper_trading.db` に履歴を記録します（本番 DB と分離）。
  - 停止フラグ `data/stop_requested.flag` が存在すると起動しない、実行中にフラグが立つと停止します。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - `--db` で別 DB を指定できます。環境変数 `PAPER_TRADING_SQLITE_PATH` も参照します。

- AI / 研究系はライブラリ API として利用
  - 例（Python REPL やスクリプト内）:
    ```
    import duckdb
    from datetime import date
    from kabusys.ai import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, date(2026, 4, 10), api_key="sk-...")
    ```
  - market regime:
    ```
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, date(2026,4,10), api_key="sk-...")
    ```

----

## ログとファイルパス

- ログ:
  - デフォルト: logs/<app_name>.log（例: logs/execution.log, logs/monitoring.log）
  - 日次ローテーション（30日保持）
  - LOG_DIR 環境変数で変更可能
- PID / フラグ:
  - 実行用 PID ファイル: data/execution.pid（path は Settings.pid_file_path で上書き可）
  - 停止リクエスト: data/stop_requested.flag（run_* スクリプトでポーリングして検知）
  - Kill Switch の出力: data/kill.flag（KillSwitch が書き込むと ExecutionEngine 停止を促します）

----

## ディレクトリ構成（主要ファイル）

（パスはリポジトリの root が src 配下を含む場合の想定）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定管理（.env 自動ロード、Settings）
  - config_setup.py — .env 生成ウィザード（CLI）
  - validate_config.py — 設定検証 CLI
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - data/ (モジュール、未表示)
  - strategy/ (戦略関連、未表示)
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py (未表示)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (未表示)
  - research/
    - factor_research.py
    - feature_exploration.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py

（上記は主要モジュールの抜粋です。実際のファイル一覧はリポジトリを参照してください。）

----

## 運用上の注意 / トラブルシューティング

- .env の自動ロード
  - デフォルトでプロジェクトルートの `.env` と `.env.local` が読み込まれます。テストなどで自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DB の切り分け
  - paper_trading 環境は本番の SQLite DB を使わず `PAPER_TRADING_SQLITE_PATH` を使用するため、誤って本番データを上書きするリスクが低くなっています。ただし環境変数の設定ミスに注意してください。
- OpenAI API
  - API キー未設定だと ai モジュールは例外を出します。運用では `OPENAI_API_KEY` を .env に設定してください。
  - レート制限や一時的なエラーは内部でリトライ・フェイルセーフ処理がありますが、失敗時は部分的にスキップされることがあります。
- ログディレクトリの作成に失敗するとファイルハンドラは無効化され、コンソールのみの出力にフォールバックします（警告が出ます）。
- monitor / execution の停止
  - `data/stop_requested.flag` を作成すると run_monitoring / run_execution は安全に停止または起動中断します。
  - KillSwitch は `data/kill.flag` を作成し、ExecutionEngine に停止を指示します（production では KILL_FLAG_CLEAR_ON_START=0 を推奨）。

----

## 開発に関するメモ

- 各モジュールは副作用を最小化する設計（DB への書き込みは明示的、LLM 呼び出しは再利用可能な関数に分離）です。
- DuckDB を用いた分析/研究用クエリが豊富に実装されています。テストデータを用意して関数を個別に実行・検証してください。
- PyYAML がない場合、config/*.yaml の内容検証はスキップされます（validate_config が警告を出します）。

----

## 貢献 / ライセンス

README 上では省略。社内向け / プライベート開発用リポジトリ想定。

----

必要であれば、README に「インストール用 requirements.txt」「サービスの systemd ユニット例」「実行時のサンプル .env.example」などのサンプルを追加できます。どの情報を追記したいか教えてください。