# KabuSys

日本株向け自動売買システムのモジュール群。本リポジトリは、発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築・リスク管理、リサーチ（DuckDBベースのファクター計算）、およびニュースNLP / レジーム判定（OpenAIを利用）などを含みます。

---

## プロジェクト概要

KabuSys は以下の責務を分離して実装した自動売買プラットフォームです。

- ExecutionEngine: ブローカークライアントを用いて発注・注文管理を行う（本番 / ペーパートレード対応）。
- Monitoring: システム状態・注文状況・リスク指標を定期的にチェックし、必要なら Kill Switch を発動。
- Portfolio: 銘柄選定・重み付け・ポジションサイズ算出などの純粋関数群。
- Research: DuckDB 上の株価・財務データを用いたファクター計算・解析ツール。
- AI モジュール: ニュースのセンチメントスコア化（OpenAI）や市場レジーム判定。
- ユーティリティ: ログ設定、プロセス優先度設定、環境設定ウィザード／検証等。

設計上、発注ロジックとデータ解析/監視は明確に分離されており、ペーパートレードは本番 DB と完全に隔離して動作します。

---

## 主な機能一覧

- Execution
  - 本番 / ペーパートレードの切替（KABUSYS_ENV）
  - ブローカークライアント抽象化（BrokerClientFactory）
  - 注文管理・リスク管理・突合せ（Reconciler, RiskManager, OrderManager）
- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス状態 / データ鮮度監視
  - TradeMonitor: 注文の滞留・約定異常検出（trade_logs参照）
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch: 条件で data/kill.flag を書き込み ExecutionEngine を停止
  - AlertManager フック（LINE などへの通知実装を想定）
- Portfolio Construction
  - 候補選定、等金額・スコア加重、セクターキャップ、レジーム乗数、単元株丸め
- Research
  - モメンタム／ボラティリティ／バリュー等のファクター計算（DuckDB）
  - 将来リターン・IC 計算・統計サマリ
- AI
  - ニュースセンチメント（OpenAI を用いた LLM 評価）
  - レジーム判定（ETF MA とマクロセンチメントの組合せ）
- ツール
  - 環境ウィザード（.env 生成）: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config
  - Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report

---

## セットアップ手順

前提:
- Python 3.10+（typing の | 演算子等を使用）
- システムにより追加のネイティブ依存が必要になる可能性あり

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 依存パッケージをインストール
   - 必須例（プロジェクトに requirements.txt がない場合の最小例）:
     ```
     pip install duckdb psutil openai
     ```
   - オプション（YAML 検証等）:
     ```
     pip install pyyaml
     ```

3. データ・ログ用ディレクトリ作成（必要に応じて）
   ```
   mkdir -p data logs
   ```

4. 環境変数の初期設定
   - 対話式ウィザードで .env を生成:
     ```
     python -m kabusys.config_setup
     ```
   - または手動で `.env` を作成。主な環境変数:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (ペーパートレード用 DB、デフォルト: data/paper_trading.db)
     - OPENAI_API_KEY (AI 機能を使用する場合)
     - LOG_LEVEL, LOG_DIR, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
     - PAPER_FILL_MODE (instant|partial|never|reject) — ペーパートレードの約定挙動
     - KILL_FLAG_CLEAR_ON_START (0/1)
   - 自動 .env ロードはデフォルトで有効。無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

5. 設定検証
   ```
   python -m kabusys.validate_config
   # 警告を FAIL 扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

6. DB 初期化
   - 実行スクリプト（run_execution/run_monitoring）が起動時に SQLite テーブルを冪等的に作成します。特別な手順は不要です。

---

## 使い方

- 実行（ExecutionEngine）
  - 本番またはペーパートレードを起動:
    ```
    # 環境変数 KABUSYS_ENV を .env で設定済みであることが前提
    python -m kabusys.run_execution
    ```
  - ペーパートレードに切替えるには KABUSYS_ENV=paper_trading を設定。ペーパートレード時は data/paper_trading.db に記録され、本番 DB と分離されます。

  - 停止方法:
    - 実行中のエンジンはプロセス ID を data/execution.pid に保存します（pid ファイル）。
    - 外部から停止要求を出すにはプロジェクトルートの `data/stop_requested.flag` を作成します（スクリプトはこのファイルの存在を監視して安全に終了します）。
    - Kill Switch による強制停止は `data/kill.flag` が生成されることで行われます（Monitoring が条件を検出すると書き込み）。

- 監視（Monitoring）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能。デフォルトは 60 秒。
  - 監視は KABUSYS_ENV にかかわらず設定された本番 sqlite_path を使用してログを記録します（monitoring は常に本番 DB を見る設計）。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する場合
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 関連
  - ニューススコアリング / レジーム判定は OpenAI API キー (OPENAI_API_KEY) が必要です。
  - 関数としては kabusys.ai.score_news, kabusys.ai.regime_detector.score_regime を呼び出して使用します。

- ログ
  - ログはデフォルトで stdout と logs/<app_name>.log に出力されます。ログ設定は kabusys.utils.logging_setup.setup_logging を通じて行われます。
  - LOG_DIR でログディレクトリを変更できます。

---

## 主要ファイル / ディレクトリ構成

（src/kabusys 以下の主要モジュール）

- run_execution.py
  - ExecutionEngine の起動スクリプト。KABUSYS_ENV に応じて本番/ペーパートレード DB を使い分け。
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL で間隔変更可能。
- config.py
  - 環境変数読み込み・Settings クラス（設定取得ユーティリティ）。
- config_setup.py
  - 対話式 .env ウィザード。
- validate_config.py
  - 設定検証 CLI（.env と config/*.yaml のチェック）。
- utils/
  - logging_setup.py: ログ設定ユーティリティ
  - process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ
- monitoring/
  - monitoring_db.py: SQLite テーブル定義・永続化 API
  - system_monitor.py: システム状態・データ鮮度監視
  - trade_monitor.py, risk_monitor.py, monitoring_engine.py, kill_switch.py 等（監視全般）
- execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py（発注周り）
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py（ポートフォリオ構築）
- research/
  - factor_research.py, feature_exploration.py（ファクター計算・解析）
- ai/
  - news_nlp.py, regime_detector.py（OpenAI を用いた NLP / レジーム判定）
- tools/
  - paper_verification_report.py（ペーパートレード評価レポート）
- __init__.py
  - パッケージエクスポート定義（version 等）

（補足）
- data/: 実行時に使用する pid/flag/db ファイルを置く想定のディレクトリ（プロジェクトルート）
  - data/execution.pid
  - data/kill.flag
  - data/stop_requested.flag
  - data/monitoring.db（デフォルトの monitoring 用 SQLite）
  - data/paper_trading.db（ペーパートレード DB）

---

## 環境変数（主要なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live
- OPENAI_API_KEY: OpenAI を使う場合に必須
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード DB（デフォルト data/paper_trading.db）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant|partial|never|reject）
- LOG_LEVEL / LOG_DIR
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: アラート送信用（任意）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動でクリアするか（0/1）

環境変数は .env ファイル（プロジェクトルート）から自動で読み込まれます。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## トラブルシューティング（よくある注意点）

- 必須環境変数が不足すると validate_config でエラーになります。まずは python -m kabusys.config_setup で .env を作成し、validate_config を実行してください。
- OpenAI 関連機能は API キーがないと動作しません。API 呼び出しはリトライとフォールバック実装が入っていますが、キー未設定は例外となる関数もあります。
- run_monitoring/run_execution はログディレクトリ書き込み権限が必要です。権限エラーが出る場合は LOG_DIR を書き込み可能な場所に変更してください。
- PID / flag ファイルの残存により起動・停止の挙動が変わる場合があるため、手動で操作する場合は data/*.pid / flag を確認してください。
- DuckDB / SQLite ファイルはロックに注意（同一ファイルに複数プロセスで不適切に書き込まれない設計を確認してください）。

---

この README はコードベースの主要な使い方と構成をまとめたものです。各モジュールの詳細な API や拡張ポイントはソース内の docstring とコメントを参照してください。必要であれば、起動・運用手順（systemd / Supervisor 用のサンプル Unit ファイル等）のテンプレートも作成します — 希望があれば教えてください。