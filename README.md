# KabuSys — README（日本語）

本リポジトリは日本株自動売買システム「KabuSys」の一部実装です。本 README ではプロジェクト概要、主な機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめます。

注意: 実行には外部ライブラリ（duckdb, psutil, openai 等）が必要です。下記「セットアップ手順」を参照してください。

---

## プロジェクト概要

KabuSys は日本株の自動売買と関連する監視・リサーチ機能を提供するシステムです。本コードベースには以下の主要コンポーネントが含まれます。

- ExecutionEngine（発注実行エンジン）: ブローカークライアント経由で発注を行う。`KABUSYS_ENV=paper_trading` の時はモックで発注をシミュレートし、paper_trading 用 DB に記録します。
- Monitoring（監視）: システム稼働状況、発注ログ、リスク指標などを定期的にチェックして、Kill Switch（停止フラグ）や通知を発動します。
- Portfolio / Research: 銘柄選定、配分計算、ファクター計算、特徴量解析などの純粋関数群。
- AI モジュール: ニュースを LLM（OpenAI）で解析してセンチメントやレジーム判定を行う機能。
- ユーティリティ: 設定、ログ設定、プロセス優先度設定、設定ウィザード・検証 CLI、リポート生成ツール等。

バージョンは src/kabusys/__init__.py の __version__ で管理されています（例: 0.1.0）。

---

## 主な機能一覧

- 環境設定管理
  - .env 自動ロード（プロジェクトルート検出）
  - 対話式ウィザードで .env を生成・更新（kabusys.config_setup）
  - 起動前に環境・設定ファイルを検証（kabusys.validate_config）

- 発注・実行
  - ExecutionEngine を起動して注文管理、リスク管理、リコンシリエーションを実行（run_execution）
  - 本番/ペーパートレード環境を分離（paper_trading 用 DB）

- 監視・アラート
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせた MonitoringEngine（run_monitoring）
  - Kill Switch（条件により data/kill.flag を書き込み、Execution を停止）
  - 監視履歴は SQLite（デフォルト: data/monitoring.db）に永続化

- ポートフォリオ構築
  - 候補選定、等配分・スコア配分、リスク調整（セクター上限、レジーム乗数）
  - ポジションサイジング（単元丸め、aggregate cap スケーリング等）

- リサーチ・ツール
  - DuckDB を使ったファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン算出、IC 計算、統計サマリ
  - Paper Trading 検証レポート生成ツール（kabusys.tools.paper_verification_report）

- AI 支援
  - ニュースの LLM センチメント評価と ai_scores への書き込み
  - マクロニュース + ETF MA200 を合成して市場レジーム判定

---

## 前提・依存関係

最低限必要な Python ライブラリ例（バージョンは適宜選択）:

- python >= 3.10
- duckdb
- psutil
- openai (LLM 機能を使う場合)
- PyYAML（config/*.yaml の内容検証を行う場合）
- （任意）その他ライブラリ（テスト用等）

pip でインストールする例:

```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

requirements ファイルがある場合はそれに従ってください。

---

## セットアップ手順

1. リポジトリをクローン・チェックアウト
2. 仮想環境の作成・依存パッケージをインストール（上記参照）
3. `.env` の作成
   - 対話式ウィザードを使用:
     ```
     python -m kabusys.config_setup
     ```
     ウィザードで入力した内容はプロジェクトルートの `.env` に保存されます（既存の .env は上書きしません）。
   - 必須環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - そのほかのキーやデフォルトはウィザード/例を参照してください。

4. 設定検証（起動前確認）
   ```
   python -m kabusys.validate_config
   # 警告もエラー扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

5. 必要に応じてデータディレクトリ作成（logs, data 等は自動作成されることが多いですが、権限等で失敗する場合があります）。

---

## 使い方（起動コマンドと主要オプション）

- ExecutionEngine を起動（発注エンジン）

  - 本番相当（KABUSYS_ENV を .env で設定しておく）
    ```
    python -m kabusys.run_execution
    ```

  - ペーパートレード（.env で KABUSYS_ENV=paper_trading を設定）
    - このモードでは MockBrokerClient が使われ、デフォルトで data/paper_trading.db に記録され、本番 DB と分離されます。

  - 停止/制御
    - 実行中のエンジンは kill.flag（Kill Switch）や stop_requested.flag により停止されます。
    - `data/stop_requested.flag` があると起動を抑止したりループを抜けて終了します（run_execution / run_monitoring が利用）。
    - KillSwitch が条件を満たすと `data/kill.flag` が書き込まれ、ExecutionEngine に停止シグナルを送ります。
    - 起動時に必要なら kill.flag をクリア:
      ```
      rm -f data/kill.flag
      ```

- Monitoring を起動（監視ループ）
  - デフォルト 60 秒間隔でポーリング（環境変数で上書き可能）
    ```
    python -m kabusys.run_monitoring
    ```
  - ポーリング間隔を変更:
    ```
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring
    ```
  - 注: Monitoring は KABUSYS_ENV にかかわらず本番用の sqlite_path（SQLITE_PATH）を使用します。

- 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report
  # 期間指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB 指定
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

---

## 主要な環境変数（代表例）

- 必須（少なくとも設定が必要）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 運用 / 振る舞い制御
  - KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
  - LOG_LEVEL: ログレベル（"DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"）
  - LOG_DIR: ログファイルの保存先（デフォルト: logs/）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
  - PAPER_FILL_MODE: ペーパートレード時の約定モード ("instant"|"partial"|"never"|"reject")
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（デフォルト: 60）
  - PID_FILE_PATH / KILL_FLAG_PATH 等は Settings から参照されます（デフォルトは data/ 配下）。

- OpenAI（AI 機能を使う場合）
  - OPENAI_API_KEY

設定の詳細は `src/kabusys/config.py` に実装があります。`.env.example` 等がある場合はそれを参考にしてください。

---

## ロギング

- 共通ロギング初期化関数: `kabusys.utils.logging_setup.setup_logging(app_name="...")`
  - stdout（StreamHandler）と日次ローテーションするファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定します。
  - ログディレクトリは `LOG_DIR` 環境変数またはデフォルト `logs/` を使用します。
  - ログファイル名は `<log_dir>/<app_name>.log`（例: logs/execution.log）。

---

## データベースと永続化

- DuckDB: 分析用 DB（prices_daily, raw_financials などを格納）
  - PATH は `DUCKDB_PATH`
- SQLite: 監視ログ・取引ログ（MonitoringDB）
  - デフォルト `data/monitoring.db`
  - MonitoringDB は起動時にテーブル（system_status, trade_logs, positions, risk_logs, dashboard）を冪等的に作成・マイグレーションします。
- ペーパートレードは `PAPER_TRADING_SQLITE_PATH`（デフォルト data/paper_trading.db）で完全に分離されます（Execution 起動時に使用）。

---

## 停止 / 制御ファイル

- data/stop_requested.flag: run_monitoring / run_execution がチェックする「停止要求」フラグ。存在するとループを抜け起動を終了します。
- data/kill.flag: KillSwitch が作成するファイル。ExecutionEngine に対する停止要請（存在を確認して停止処理を実行）。`KILL_FLAG_CLEAR_ON_START=1` の場合は起動時に自動で削除されますが、本番では 0 を推奨します。
- PID ファイル: execution の PID を `data/execution.pid` に書きます（Settings.pid_file_path を参照）。

---

## ディレクトリ構成（主要ファイルと説明）

以下は src/kabusys の主要モジュールと簡単な説明です。

- src/kabusys/__init__.py
  - パッケージ定義、__version__

- 起動スクリプト
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプト（スレッドでエンジン実行、停止フラグ監視）
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で制御）
  - src/kabusys/validate_config.py
    - 設定検証 CLI
  - src/kabusys/config_setup.py
    - .env 対話式ウィザード

- 設定
  - src/kabusys/config.py
    - Settings クラス、.env 自動読み込みのロジック、検証用ユーティリティ

- monitoring（監視関連）
  - src/kabusys/monitoring/monitoring_db.py
    - SQLite に対する永続化層（テーブル作成/CRUD）
  - src/kabusys/monitoring/system_monitor.py
    - システム状態・データ鮮度監視
  - src/kabusys/monitoring/trade_monitor.py
    - 発注ログやステート監視（該当ファイル参照）
  - src/kabusys/monitoring/risk_monitor.py
    - ドローダウン/ポジション上限監視
  - src/kabusys/monitoring/kill_switch.py
    - kill.flag の書き込み/判定
  - src/kabusys/monitoring/monitoring_engine.py
    - 個々のモニタを束ねるエンジン
  - src/kabusys/monitoring/alert_manager.py
    -（アラート通知用、該当ファイルが存在すれば）LINE など通知の管理

- execution（発注関連）
  - src/kabusys/execution/* （BrokerClientFactory, ExecutionEngine, OrderManager, RiskManager 等）

- portfolio（ポートフォリオ構築）
  - src/kabusys/portfolio/portfolio_builder.py
  - src/kabusys/portfolio/position_sizing.py
  - src/kabusys/portfolio/risk_adjustment.py
  - src/kabusys/portfolio/__init__.py

- research（ファクター計算・解析）
  - src/kabusys/research/factor_research.py
  - src/kabusys/research/feature_exploration.py
  - src/kabusys/research/__init__.py

- ai（LLM を使った機能）
  - src/kabusys/ai/news_nlp.py
    - ニュースを LLM でセンチメント解析して ai_scores に書き込む
  - src/kabusys/ai/regime_detector.py
    - マクロニュース + ETF MA200 を用いた市場レジーム判定

- tools
  - src/kabusys/tools/paper_verification_report.py
    - ペーパートレード検証レポート生成スクリプト

- utils（汎用ユーティリティ）
  - src/kabusys/utils/logging_setup.py
  - src/kabusys/utils/process_priority.py
  - src/kabusys/utils/__init__.py

その他、data/ や logs/ などのランタイムディレクトリは実行時に自動作成されることが多いです。

---

## 追加の注意点 / 運用上のヒント

- 環境（KABUSYS_ENV）が `live` の場合は慎重に扱ってください。validate_config は live 時に追加警告を出します（LINE 通知設定など）。
- Monitoring は（ソース内コメントのとおり）KABUSYS_ENV にかかわらず本番 sqlite_path を使う設計になっているので、ペーパートレードで監視を分離したい場合は注意が必要です。
- LLM（OpenAI）系の API 呼び出しはリトライやフェイルセーフを実装していますが、API キーや利用上限に注意してください。
- ログディレクトリの作成に失敗するとファイルハンドラが無効化され、出力は stdout のみになります。権限などに注意してください。
- `KILL_FLAG_CLEAR_ON_START=1` を本番で設定すると危険です（起動時に kill.flag が自動クリアされるため）。本番では 0 を推奨します。

---

これで README の基本項目は以上です。実際に運用・拡張する際は、各モジュール内のドキュメントコメント（docstring）やソースコードを参照してください。必要であれば README に追加したい項目（例: API スペック、DB スキーマ詳細、デプロイ手順）を指示してください。