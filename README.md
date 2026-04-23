# KabuSys

日本株向けの自動売買システム（KabuSys）のコードベース README（日本語）

以下はこのリポジトリに含まれる主要コンポーネントの概要、セットアップ手順、使い方、ディレクトリ構成の簡潔な説明です。

---

## プロジェクト概要

KabuSys は日本株の自動売買・研究・監視を目的としたモジュール群です。  
主な機能群は以下です。

- 注文実行エンジン（ExecutionEngine）とブローカークライアントの抽象化（paper_trading / live 切替）
- 監視コンポーネント（SystemMonitor / TradeMonitor / RiskMonitor）と Kill Switch（自動停止）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ計算・セクター制約）
- リサーチ（ファクター計算、将来リターン、IC・統計）
- AI を用いたニュースセンチメント（OpenAI API 統合）
- 各種ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード、設定検証）
- ペーパートレード用検証レポート生成ツール

設計方針の抜粋:
- 本番 DB と Paper Trading DB を分離（PAPER_TRADING_SQLITE_PATH）
- ルックアヘッドバイアスを避けるため、日付参照に注意して実装
- 外部 API 呼び出し（OpenAI 等）はフェイルセーフ設計（失敗時はスコア0やスキップなど）

---

## 機能一覧（主なモジュール）

- 実行 / 監視
  - run_execution.py: ExecutionEngine 起動スクリプト（KABUSYS_ENV に応じてモック or 実ブローカー）
  - run_monitoring.py: SystemMonitor ポーリングループ起動（MONITOR_POLL_INTERVAL で調整）
- 設定 / 検証
  - config_setup.py: .env を対話式に作成・更新するウィザード
  - validate_config.py: .env と config/*.yaml の起動前チェック CLI
  - config.py: 環境変数ラッパー（Settings クラス）
- 監視（monitoring）
  - monitoring_db.py: 監視用 SQLite スキーマ（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py, trade_monitor.py, risk_monitor.py, monitoring_engine.py, kill_switch.py, alert_manager など
- ポートフォリオ（portfolio）
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
- リサーチ（research）
  - factor_research.py（モメンタム・バリュー・ボラティリティ）
  - feature_exploration.py（将来リターン・IC・統計）
- AI（ai）
  - news_nlp.py: ニュース記事を OpenAI でスコアリングし ai_scores に格納
  - regime_detector.py: マクロ + ETF MA200 を合成して市場レジーム判定
- ツール
  - tools/paper_verification_report.py: ペーパートレード DB を集計して検証レポート出力
- ユーティリティ
  - utils/logging_setup.py: 統一ログ設定（コンソール + 日次ローテーションファイル）
  - utils/process_priority.py: プロセス優先度 / CPU affinity 設定（Windows / POSIX 対応）
  - その他補助関数群

---

## 必須・推奨環境

- Python 3.10 以上（型注釈に | を使用しているため）
- 推奨パッケージ（代表例）:
  - duckdb
  - psutil
  - openai
  - pyyaml （config YAML 検証を使う場合）
- そのほか、ロギングでファイル出力を行う場合は書き込み権限のあるディレクトリ

例: 仮想環境作成・依存インストール
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

（実プロジェクトでは requirements.txt / poetry / pip-tools 等で依存を管理してください）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ
2. Python 仮想環境を用意し、依存パッケージをインストール
3. 対話式で .env を作成
   ```
   python -m kabusys.config_setup
   ```
   ウィザードは既存 .env があれば読み込み、Enter で既存値を再利用できます。作成される .env のテンプレート例（主なキー）:
   - KABUSYS_ENV (development | paper_trading | live)
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
   - DUCKDB_PATH (default: data/kabusys.duckdb)
   - SQLITE_PATH (default: data/monitoring.db)
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (任意)
   - LOG_LEVEL (DEBUG/INFO/...)
   - KILL_FLAG_CLEAR_ON_START (0/1)

4. 設定検証（起動前チェック）
   ```
   python -m kabusys.validate_config
   # 警告をエラー扱いにしたい場合:
   python -m kabusys.validate_config --strict
   ```

5. 必要に応じて data/ や logs/ ディレクトリを作成（自動作成される箇所もありますが権限に注意）

---

## 使い方（起動・停止・ツール）

- 実行エンジン（Execution）
  - 起動:
    ```
    python -m kabusys.run_execution
    ```
    KABUSYS_ENV 環境変数が `paper_trading` の場合、MockBrokerClient が使用され、paper_trading 用の DB（デフォルト data/paper_trading.db）へ記録します。`live` の場合は実ブローカーを使います。
  - 停止:
    - run_execution はプロジェクトルートの stop フラグ（data/stop_requested.flag）を監視します。ファイルが存在すると起動中のエンジンを停止します。
    - KillSwitch は条件合致時に data/kill.flag を書き込み ExecutionEngine 側で検知して停止できます（Settings.kill_flag_path でパスを指定可能）。KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアされます（本番では 0 推奨）。

- 監視プロセス（Monitoring）
  - 起動:
    ```
    python -m kabusys.run_monitoring
    ```
    デフォルトで 60 秒間隔（環境変数 MONITOR_POLL_INTERVAL で秒数を変更可能: 例 MONITOR_POLL_INTERVAL=30）。
    監視は常に「本番の」sqlite_path（Settings.sqlite_path）を使用して監視ログを記録します（環境に依らず）。
  - 停止:
    - run_monitoring は data/stop_requested.flag を検知するとループを終了します。

- Paper trading 検証レポート
  - ペーパートレード DB から集計してレポートを標準出力に出します:
    ```
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
    DB の指定: `--db PATH` または環境変数 PAPER_TRADING_SQLITE_PATH を使用。デフォルトは data/paper_trading.db。

- ロギング
  - 共通のログ設定ユーティリティ `kabusys.utils.logging_setup.setup_logging` を使用しています。
  - デフォルトログディレクトリ: logs/（環境変数 LOG_DIR で変更可能）
  - アプリケーション名ごとにファイル名が作成されます（例: logs/execution.log, logs/monitoring.log）。

---

## 主要環境変数（抜粋）

- 必須（起動に必要）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 動作モード
  - KABUSYS_ENV: development | paper_trading | live

- データベース
  - DUCKDB_PATH: 分析用 duckdb ファイル（default: data/kabusys.duckdb）
  - SQLITE_PATH: monitoring DB（default: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 sqlite（default: data/paper_trading.db）

- ロギング / 実行
  - LOG_LEVEL: DEBUG/INFO/...
  - LOG_DIR: ログ保存先
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、run_monitoring 用。デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動削除（0=しない, 1=する）

- OpenAI
  - OPENAI_API_KEY: news_nlp / regime_detector で使用（代替として関数引数経由で指定可能）

その他、config_setup.py に記載のキーを参照してください（.env のテンプレートが出力されます）。

---

## データベース（監視）スキーマ（概要）

monitoring_db.init_monitoring_db により作成されるテーブル（冪等）:

- system_status: cpu/memory/disk/process_ok 等のポーリングログ
- trade_logs: 注文イベントログ（event_type: Created / Sent / Filled など）
- positions: 保有ポジション（code を主キー）
- risk_logs: リスクアラートの記録
- dashboard: 集計（常に id=1 の単一行） — portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value

このスキーマは起動時に自動作成・マイグレーション処理（列の追加）を行います。

---

## ディレクトリ構成（抜粋）

リポジトリの主要構造（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (存在する想定)
  - execution/  (実行エンジン・ブローカ周り)
    - execution_engine.py
    - broker_factory.py
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
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py
  - data/  (実行時に生成 / 使用される想定)
  - logs/  (ログ出力先、デフォルト)

（上記は主要ファイルの抜粋です。詳細はソースツリーを参照してください）

---

## 運用上の注意 / ベストプラクティス

- 本番運用（KABUSYS_ENV=live）では .env に機密情報を含めるため Git にコミットしないこと。
- KILL_FLAG_CLEAR_ON_START は本番では 0 を推奨（自動クリアすると Kill Switch が無効化される可能性があります）。
- モニタリングと実行は別プロセスで走らせる想定です（run_monitoring は監視ログ記録と Kill Switch 発火を担当）。
- OpenAI や外部 API を使うコードはリトライ・バックオフ・バリデーション処理が組まれていますが、APIキーや使用制限（レートなど）に注意してください。
- DuckDB / SQLite のファイルはバックアップや権限管理を適切に行ってください。

---

## よく使うコマンドまとめ

- .env を作る（対話式）
  ```
  python -m kabusys.config_setup
  ```

- 設定を検証
  ```
  python -m kabusys.validate_config
  ```

- 実行エンジン起動（paper_trading / live は KABUSYS_ENV で切替）
  ```
  python -m kabusys.run_execution
  ```

- 監視ループ起動（MONITOR_POLL_INTERVAL で秒数指定可能）
  ```
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  ```

- ペーパートレード検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

README はここまでです。必要があれば、以下を追加で生成できます：
- .env.example（テンプレート）
- systemd / Supervisor 用のサービス定義例
- 開発用の Dockerfile / docker-compose 設定
- 詳細な API 仕様（BrokerClient のインターフェース等）

どれを追加しますか？