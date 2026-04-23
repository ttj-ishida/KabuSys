# KabuSys

日本株自動売買システム（KabuSys）のリポジトリに含まれる主要スクリプト・モジュールの README。  
このドキュメントはプロジェクトの概要、機能一覧、セットアップ手順、操作方法、およびディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買／リサーチ基盤です。  
主な目的は以下：

- 市場データ（DuckDB）を用いたファクター計算・研究（research）
- ポートフォリオ構築（選定・重み算出・ポジションサイズ決定）
- 実際の発注を担う ExecutionEngine（本番/ペーパートレード切替）
- システム監視（Monitoring）と Kill Switch による安全停止
- ニュースを用いた AI（OpenAI）によるセンチメント評価とレジーム判定
- Paper Trading の検証レポート生成ツール

設計方針としては、可能な限り副作用を抑えた純粋関数群（ポートフォリオ・計算）と、DB読み書きや外部API呼び出しを分離したレイヤ構成を採用しています。

---

## 主な機能一覧

- 環境設定ウィザード（.env の対話的作成）: `kabusys.config_setup`
- 設定検証 CLI（.env / config/*.yaml の検証）: `kabusys.validate_config`
- ExecutionEngine 起動スクリプト（本番/ペーパー切替）: `kabusys.run_execution`
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、ペーパートレード専用 DB に記録
- Monitoring 起動スクリプト（周期的に監視を実行）: `kabusys.run_monitoring`
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）
  - 監視は環境にかかわらず本番用 sqlite_path を使用
- 監視サブシステム
  - SystemMonitor: CPU/メモリ/ディスク、Execution プロセス PID、データ鮮度などを監視
  - TradeMonitor: 注文滞留や約定異常などを検出（trade_logs 等を利用）
  - RiskMonitor: ドローダウン、ポジション上限などを監視し risk_logs / dashboard を更新
  - KillSwitch: 条件発生時に `data/kill.flag` を書き込み ExecutionEngine を停止させる
  - MonitoringEngine: 上記を束ねてポーリング＆アラート送信
- AI モジュール
  - news_nlp: OpenAI を用いたニュースセンチメント評価（銘柄別 ai_scores 書き込み）
  - regime_detector: ETF（1321）MA200 とマクロニュースのセンチメント合成による市場レジーム判定
- Research モジュール
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC 計算、統計サマリ
- Portfolio モジュール
  - 候補選定、重み計算（等金額・スコア重み）、セクター制限、ポジションサイズ計算
- ユーティリティ
  - ログ設定ユーティリティ（stdout + 日次ローテーションファイル）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
- ツール
  - Paper Trading 検証レポート生成スクリプト: `kabusys.tools.paper_verification_report`

---

## セットアップ手順

前提: Python 3.9+ を推奨（duckdb, openai, psutil 等のライブラリが必要）。

1. リポジトリをクローン／チェックアウト

2. 仮想環境作成（推奨）
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 必要パッケージのインストール（例）
   ```
   pip install duckdb openai psutil
   ```
   - 任意/状況に応じて:
     - PyYAML（`validate_config` が YAML のパースを行う場合に推奨）
     - その他依存（プロジェクトの requirements.txt があればそれを利用）

4. 環境変数（.env）の初期作成
   - 対話式ウィザードを使う:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは `.env` を手動作成。主に必須な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - 重要設定例:
     - KABUSYS_ENV: development | paper_trading | live
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパー時の DB）
     - LOG_LEVEL（DEBUG/INFO/…）
     - OPENAI_API_KEY（AI 機能を使用する場合）

5. 設定検証（任意）
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict  # 警告も失敗扱い
   ```

6. 初回ディレクトリ作成（必要に応じて）
   - data/ logs/ 等は自動作成されることが多いですが、権限等で失敗する場合は手動作成してください。

---

## 使い方（主要コマンド）

- ExecutionEngine（発注エンジン）を起動
  - 標準:
    ```
    python -m kabusys.run_execution
    ```
  - 補足:
    - KABUSYS_ENV=paper_trading にすると、MockBrokerClient を使い `data/paper_trading.db` に記録する（本番 DB と分離）。
    - 実行中に `data/stop_requested.flag` が作成されると安全に停止します。
    - 実行時に `data/execution.pid` が作成されます（PID 管理）。

- Monitoring を起動（監視ループ）
  - 標準:
    ```
    python -m kabusys.run_monitoring
    ```
  - 環境変数:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒）。デフォルト 60 秒。1 以上の整数を指定。無効値はデフォルトにフォールバック。
  - 停止:
    - `data/stop_requested.flag` を作成すればループが検知して終了します。
    - Kill Switch は `data/kill.flag` を作成して ExecutionEngine 側を停止させます（Monitoring と Execution は別のフラグを使っています）。

- .env の自動ロードについて
  - デフォルトで .env/.env.local をプロジェクトルートから自動読み込みします。
  - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DBパスは `--db` または環境変数 `PAPER_TRADING_SQLITE_PATH` で指定可能（デフォルト: data/paper_trading.db）。

- AI 機能（ニューススコアリング / レジーム判定）
  - OpenAI API キーが必要（環境変数 `OPENAI_API_KEY` または関数引数で提供）。
  - プログラム内部 API:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

- 設定検証 CLI
  ```
  python -m kabusys.validate_config
  ```

---

## 主要環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/…）
- MONITOR_POLL_INTERVAL（監視ポーリング秒）
- PAPER_FILL_MODE（paper_trading 用の約定挙動: instant | partial | never | reject）
- OPENAI_API_KEY（AI 機能利用時）
- KILL_FLAG_CLEAR_ON_START（本番での自動クリアを避けるためデフォルト 0 推奨）

---

## ログ・PID・フラグファイル

- ログ:
  - デフォルトログディレクトリ: logs/
  - 各アプリ名でファイル出力（例: logs/execution.log, logs/monitoring.log）。日次ローテーション・30日保持。
- PID / フラグ:
  - ExecutionEngine の PID: data/execution.pid（パスは Settings.pid_file_path で指定可能）
  - 停止フラグ（プロセス側検出）: data/stop_requested.flag
  - Kill Switch（Execution 停止トリガー）: data/kill.flag
  - これらはファイルベースの簡易インタロック／シグナルとして設計されています。

---

## ディレクトリ構成（主なファイル・モジュール）

以下はリポジトリ内の主要な python モジュールとその簡単な説明です。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数・設定管理。.env 自動読み込みロジック、Settings クラスを提供。
  - config_setup.py
    - .env を対話的に生成／更新するウィザード。
  - validate_config.py
    - 起動前に .env と config/*.yaml を検証する CLI。
  - run_execution.py
    - ExecutionEngine 起動スクリプト。ペーパートレード時の DB 分離処理を含む。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL により秒間隔を制御。
  - monitoring/
    - monitoring_db.py: SQLite による監視ログの永続化層（テーブル作成・読み書きユーティリティ）
    - system_monitor.py: システム状態・データ鮮度の監視
    - trade_monitor.py: 注文・約定に関する監視（ファイル内参照あり）
    - risk_monitor.py: ドローダウンやポジション上限の監視
    - kill_switch.py: kill.flag 書き込みロジック
    - monitoring_engine.py: 複数の Monitor を束ねるポーリングエンジン
    - alert_manager.py:（アラート送信管理、実装あり）
  - execution/
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
      （発注ロジック、リスク管理、ブローカークライアント生成等）
  - portfolio/
    - portfolio_builder.py: 候補選定・重み付け
    - position_sizing.py: 株数算出・集約上限処理
    - risk_adjustment.py: セクターキャップ、レジーム乗数
  - research/
    - factor_research.py: momentum / volatility / value ファクター計算（DuckDB 接続を使用）
    - feature_exploration.py: 将来リターン、IC、統計サマリ
  - ai/
    - news_nlp.py: OpenAI を用いたニュースセンチメント（銘柄別スコア）処理
    - regime_detector.py: ETF MA + マクロニュースで市場レジーム判定
  - tools/
    - paper_verification_report.py: ペーパートレードログから検証レポートを生成
  - utils/
    - logging_setup.py: ログの共通設定（stdout + 日次ファイル）
    - process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 運用上の注意

- 本番（KABUSYS_ENV=live）ではログや kill flag、LINE 通知設定などを十分に検証してください。`validate_config` は live 設定時に警告を出します。
- OpenAI API を使う機能は API コストが発生します。API キー管理と使用頻度に注意してください。
- データベースファイル（DuckDB / SQLite）はデフォルトで `data/` 配下に置かれます。バックアップや権限に注意してください。
- `KILL_FLAG_CLEAR_ON_START=1` は本番で非常に危険です（自動的に kill.flag を消してしまうため）。本番では 0 を推奨します。
- ログディレクトリ作成に失敗するとファイル出力は無効化され、コンソール出力のみになります。

---

## よく使うコマンドまとめ

- .env 作成:
  ```
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```
  python -m kabusys.validate_config
  ```
- Execution 起動:
  ```
  python -m kabusys.run_execution
  ```
- Monitoring 起動:
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
- Paper 検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

この README はコードベースの主要部分を要約しています。詳細は各モジュールの docstring やソースコード内コメントを参照してください。必要であれば、追加の Usage サンプルや設計ドキュメント（PortfolioConstruction.md 等）も作成できます。