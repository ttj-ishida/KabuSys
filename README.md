# KabuSys

日本株自動売買システムのライブラリ / 起動スクリプト群

このリポジトリは、シグナル生成・ポートフォリオ構築・発注（ExecutionEngine）・監視（Monitoring）・研究用ユーティリティを含む自動売買基盤の一部を実装しています。  
README はコードベース（src/kabusys 以下）から抽出した使用方法・セットアップ手順・ディレクトリ構成を日本語でまとめたものです。

---

目次
- プロジェクト概要
- 機能一覧
- 前提（依存関係）
- セットアップ手順
- 使い方（主なコマンド）
- 環境変数一覧（主要なもの）
- 一時停止 / 停止フラグについて
- ディレクトリ構成（抜粋）

---

## プロジェクト概要

KabuSys は日本株の自動売買を目的としたシステム群です。  
主なコンポーネントは以下です。

- ExecutionEngine: ブローカーと連携して注文を出す実行エンジン（本番/ペーパー両対応）。
- Monitoring: システム稼働状況、注文状況、リスクを定期チェックして通知・Kill Switch を管理。
- Portfolio 建構築モジュール: 候補選定、重み付け、ポジションサイズ計算、セクター調整など。
- Research: ファクター計算・特徴量探索・IC 計算等の研究用ユーティリティ（DuckDB を利用）。
- AI モジュール: ニュースの NLP スコアリング（OpenAI）や市場レジーム判定。
- CLI ユーティリティ: .env 設定ウィザード、設定検証、ペーパートレード検証レポート生成 等。

設計方針として、DB（SQLite / DuckDB）や環境変数で柔軟に切り替え可能、外部 API 呼び出し（OpenAI 等）は明示的にキーを指定して使用する形を取っています。

---

## 機能一覧

主要な機能（抜粋）:

- .env 対話式ウィザード（kabusys.config_setup）
- 起動前設定検証ツール（kabusys.validate_config）
- Execution 起動スクリプト（kabusys.run_execution）
  - KABUSYS_ENV=paper_trading の場合はペーパートレード用の MockBroker を使用し DB を分離
  - プロセス優先度を調整し、PID ファイルを出力
- Monitoring 起動スクリプト（kabusys.run_monitoring）
  - 定期ポーリングで System / Trade / Risk モニタを実行
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）
- MonitoringDB（SQLite）: system_status, trade_logs, positions, risk_logs, dashboard テーブルの作成・操作
- Kill Switch（KillSwitch）: リスク閾値を超えた場合 data/kill.flag を書き込み Execution を停止
- Paper Trading 検証レポート生成ツール（kabusys.tools.paper_verification_report）
- Research モジュール: momentum / volatility / value などのファクター計算（DuckDB 経由）
- AI モジュール:
  - news_nlp.score_news: OpenAI を用いたニュースセンチメント集計 → ai_scores テーブルへ
  - regime_detector.score_regime: ma200 とマクロニュースを用いた市場レジーム判定

---

## 前提（依存関係）

最低限必要なライブラリ（代表例、requirements.txt はリポジトリに含めてください）:

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- pyyaml（config 検証で YAML 内容をチェックする場合に任意で使用）

インストール例:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

（実際の requirements はプロジェクトで管理してください）

---

## セットアップ手順

1. リポジトリをクローン、ソースルートを確認（src がパッケージルート）
2. 仮想環境を作成して依存ライブラリをインストール
3. 初期 .env を作成・編集
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
   - もしくはプロジェクトルートに `.env` を作成し、必要な環境変数を設定
4. 設定検証（起動前チェック）:
   ```
   python -m kabusys.validate_config
   # --strict を付けると警告でも exit(1) にする
   python -m kabusys.validate_config --strict
   ```
5. 必要な DB ディレクトリ・ファイルは起動スクリプトが自動作成することが多いですが、data/ ディレクトリを作成しておくと安心です:
   ```
   mkdir -p data logs
   ```

---

## 使い方（主なコマンド）

- ExecutionEngine を起動（通常はプロダクション or ペーパートレード切替は KABUSYS_ENV で）:
  ```
  # paper_trading を使う例
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  # 本番起動
  KABUSYS_ENV=live python -m kabusys.run_execution
  ```

  - run_execution は起動時に process priority を "high" に設定し、SQLite / DuckDB に接続します。
  - paper_trading の場合、paper_sqlite_path（デフォルト: data/paper_trading.db）を使用します。

- Monitoring を起動:
  ```
  # デフォルト 60 秒間隔（環境変数で上書き可）
  python -m kabusys.run_monitoring

  # ポーリング間隔を 30 秒にする例
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

  - Monitoring は monitoring DB（settings.sqlite_path、デフォルト: data/monitoring.db）を初期化・使用します。
  - 監視ループ中、data/stop_requested.flag が存在すると終了します。

- .env 対話式ウィザード:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する場合
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 関連（プログラムから利用）:
  - ニューススコアリング:
    - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
    - api_key を省略すると環境変数 OPENAI_API_KEY を参照
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## 環境変数（主要なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（Settings.jquants_refresh_token が要求）
- KABU_API_PASSWORD — kabuステーション API パスワード

主なオプション / デフォルト:
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（デフォルト: INFO）
- LOG_DIR — ログの保存先ディレクトリ（デフォルト: logs）
- OPENAI_API_KEY — OpenAI API キー（AI 機能で使用）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知設定（任意）
- KILL_FLAG_PATH — KillSwitch 用フラグファイルパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag をクリアするか（"1" でクリア、デフォルト "0"）
- PID_FILE_PATH — Execution 側の PID ファイル（デフォルト: data/execution.pid）
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE — paper_trading の MockBroker の fill モード（instant|partial|never|reject、デフォルト: instant）

詳細は kod内の Settings クラス（src/kabusys/config.py）を参照してください。

---

## 一時停止 / 停止フラグについて

- stop_requested.flag
  - パス: project_root/data/stop_requested.flag
  - run_execution/run_monitoring はループ内でこのファイルの存在をチェックし、存在すると安全に終了します。
  - 手動で停止したい場合はこのファイルを作成してください。

- kill.flag（Kill Switch）
  - パス（デフォルト）: data/kill.flag（Settings.kill_flag_path で変更可）
  - Monitoring の KillSwitch は特定のリスク閾値（例: ドローダウン超過・ポジション上限超過）を検出するとこのファイルを書き込み、ExecutionEngine に停止を促します。
  - ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時にクリアされますが、本番では注意が必要です。

---

## ログ

- ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力されます（TimedRotatingFileHandler、30日保持）。
- コンソール出力は stdout に行われます（stderr ではない点に注意）。

ログ設定は kabusys.utils.logging_setup.setup_logging を通じて行われます。起動スクリプトはアプリ名（"execution", "monitoring" など）を渡してログを初期化します。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 配下の主要ファイル・ディレクトリの抜粋です。実際のリポジトリにはさらに多くのファイルが含まれる想定です。

- src/
  - kabusys/
    - __init__.py
    - config.py                   — 環境変数 / Settings 管理
    - config_setup.py             — .env 対話式ウィザード
    - validate_config.py          — 起動前設定検証 CLI
    - run_execution.py            — ExecutionEngine 起動スクリプト
    - run_monitoring.py           — Monitoring 起動スクリプト
    - monitoring/
      - monitoring_db.py          — SQLite テーブル初期化・永続化層
      - monitoring_engine.py      — 各 Monitor を束ねるエンジン
      - system_monitor.py         — システム状態・データ鮮度監視
      - trade_monitor.py          — （注文関連監視ロジック、本リポジトリ内に存在）
      - risk_monitor.py           — ドローダウン等リスク監視
      - kill_switch.py            — Kill Switch 実装
      - alert_manager.py          — （通知周りの実装）
    - execution/
      - execution_engine.py       — 実行エンジン（参照あり）
      - broker_factory.py         — ブローカークライアント生成
      - order_manager.py
      - order_repository.py
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
      - news_nlp.py               — ニュース NLP スコアリング（OpenAI）
      - regime_detector.py        — 市場レジーム判定（OpenAI）
    - tools/
      - paper_verification_report.py
    - utils/
      - logging_setup.py
      - process_priority.py
      - ...

（上記は本コードベースから抽出した主要ファイルの一覧です）

---

## 運用上の注意

- KABUSYS_ENV を "live" に設定すると本番動作になります。LINE 通知・Kill Switch 設定などを十分確認の上運用してください。
- .env ファイルは絶対にバージョン管理にコミットしないこと（config_setup でも警告あり）。
- OpenAI を利用する機能は API 使用料金が発生します。API キーの管理とコストに注意してください。
- process_priority の設定は OS に依存します。権限不足等で設定できない場合は警告を出してスキップします。
- DuckDB / SQLite への書き込みはそれぞれのパスに対して行われます。バックアップ・権限に注意してください。

---

以上がコードベース（src/kabusys）に基づく README です。必要であれば、README に含める実際の依存パッケージ一覧（requirements.txt）や systemd / supervisor 用の起動ユニット例、より詳細な設定項目の説明（全環境変数の網羅）なども追記できます。どの情報を追加しますか？