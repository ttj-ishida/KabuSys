# KabuSys — 日本株自動売買システム

このリポジトリは日本株の自動売買・研究・監視のための内部ライブラリ群と起動スクリプトを含みます。  
README は大まかな概要、機能一覧、セットアップ手順、主な使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群です。

- 自動発注（ExecutionEngine）とリスク管理
- 監視（Monitoring）: システム状態・注文状態・リスクの周期的チェック、Kill Switch
- ポートフォリオ構築（銘柄選定、重み付け、株数決定、セクター制約適用）
- リサーチ（ファクター計算、特徴量探索）
- AI を使ったニュースセンチメント評価（OpenAI）
- Paper Trading 用の検証レポート生成ツール

設計のポイント:
- 設定は環境変数（.env/.env.local）で管理
- Paper Trading は本番 DB と分離（デフォルト: data/paper_trading.db）
- ログは統一的に設定（logs/ 日次ローテート）
- DuckDB を分析用 DB、SQLite を監視・履歴用に利用

---

## 主な機能一覧

- 実行エンジン起動スクリプト
  - run_execution.py: ExecutionEngine を起動、KABUSYS_ENV によって paper_trading モードはモックブローカーを使用
- 監視起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ（MONITOR_POLL_INTERVAL で間隔調整）
- 設定ユーティリティ
  - config_setup.py: 対話式ウィザードで .env を生成・更新
  - validate_config.py: .env と config/*.yaml の基本検証（--strict あり）
- 監視（monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine / KillSwitch
  - MonitoringDB: SQLite スキーマ初期化と読み書き
- 発注関連（execution）
  - BrokerClientFactory（本番/モック分岐）
  - OrderManager, RiskManager, ExecutionEngine, Reconciler, OrderRepository
- ポートフォリオ構築（portfolio）
  - 銘柄選定、等分/スコア加重、ポジションサイズ計算、セクター上限適用、レジーム乗数
- リサーチ（research）
  - ファクター計算: momentum, volatility, value
  - 特徴量探索: forward returns, IC（Information Coefficient）など
- AI（ai）
  - news_nlp: raw_news を OpenAI に渡して銘柄別センチメントを ai_scores に永続化
  - regime_detector: ETF マクロ指標 + LLM で日次レジーム判定
- ツール
  - tools/paper_verification_report.py: Paper Trading DB から Pass/Fail を出す検証レポート生成

---

## 前提・動作環境

- Python >= 3.10（型アノテーションの union 演算子 `X | Y` を使用）
- 推奨パッケージ（最低限）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML の検証を行う場合）
- 作業ディレクトリに `data/` と `logs/` が作られます（スクリプトが自動作成する場合あり）。

requirements.txt がない場合は手動でインストールしてください。例:
```
pip install duckdb psutil openai PyYAML
```

---

## 設定（環境変数）

主な環境変数（デフォルト値・説明）:

- 必須（少なくとも設定が必要）
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード

- 実行環境
  - KABUSYS_ENV: one of `development` | `paper_trading` | `live`（デフォルト: development）

- DB / ファイルパス
  - DUCKDB_PATH: デフォルト `data/kabusys.duckdb`
  - SQLITE_PATH: 監視 DB（デフォルト `data/monitoring.db`）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト `data/paper_trading.db`）
  - PID_FILE_PATH: 実行エンジン PID ファイル（デフォルト `data/execution.pid`）
  - KILL_FLAG_PATH: Kill Switch フラグファイル（デフォルト `data/kill.flag`）

- ログ / レベル
  - LOG_LEVEL: `DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`（デフォルト: INFO）
  - LOG_DIR: ログ保存ディレクトリ（デフォルト `logs/`）

- Paper Trading 挙動
  - PAPER_FILL_MODE: `instant` | `partial` | `never` | `reject`（デフォルト: `instant`）

- OpenAI
  - OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / regime_detector が使用）

- その他
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
  - KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（`0` または `1`、デフォルト 0）

自動読み込み:
- .env および .env.local をプロジェクトルートから自動読み込みします（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化）。

.env の初期作成は `python -m kabusys.config_setup` を推奨します。

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト。

2. Python 仮想環境を作成・有効化（推奨）:
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール:
   ```
   pip install duckdb psutil openai PyYAML
   ```

4. .env を作成（対話式ウィザード）:
   ```
   python -m kabusys.config_setup
   ```
   生成後、`python -m kabusys.validate_config` で検証してください。

5. data/logs ディレクトリが自動作成されますが、必要に応じて手動で作成して権限を調整してください:
   ```
   mkdir -p data logs
   ```

---

## 使い方（主要コマンド例）

各スクリプトはモジュールとして実行します（パッケージ構成に依存しているため module 実行を推奨）。

- 実行エンジン（ExecutionEngine）起動
  - 本番 / 開発 / ペーパートレードは KABUSYS_ENV で切替:
    ```
    # Paper Trading 例
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
  - ペーパートレードでは MockBrokerClient を用い、DB は `PAPER_TRADING_SQLITE_PATH`（デフォルト data/paper_trading.db）を使用します。

- 監視（SystemMonitor）起動
  - デフォルトは 60 秒間隔。MONITOR_POLL_INTERVAL で上書き可能:
    ```
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring
    ```

- 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを指定する場合:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI スコアリング（ライブラリ呼び出し）
  - DuckDB 接続を渡して関数を呼び出します（例: ai.score_news）。
  - 注意: OPENAI_API_KEY が必要です（もしくは引数で api_key を渡す）。

例（Python スクリプト内）:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 4, 10), api_key="sk-...")
```

- Research / Portfolio API（ライブラリとして使用）
  - 例: ファクター計算
    ```
    from datetime import date
    import duckdb
    from kabusys.research import calc_momentum

    conn = duckdb.connect("data/kabusys.duckdb")
    results = calc_momentum(conn, target_date=date.today())
    ```

---

## 監視・停止フローについて

- kill.flag（デフォルト data/kill.flag）を書き込むことで ExecutionEngine に停止シグナルを送る KillSwitch を採用しています。
- run_execution / run_monitoring はそれぞれ data/stop_requested.flag の存在を確認し、見つかった場合は安全に終了します。
- ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動で kill.flag をクリアします（本番では推奨しません）。

---

## ログ

- logs/<app_name>.log に日次ローテートでログが出力されます（デフォルト logs/）。  
- コンソール出力は stdout に出力されます（cron/Task Scheduler での利用を想定）。

---

## ディレクトリ構成（主なファイル）

以下はソースツリー（src/kabusys）の主要ファイルと説明です。

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数・設定読み込みロジック（.env 自動読み込み含む）
  - config_setup.py — 対話式 .env 作成ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト

  - execution/  — 発注関連（Engine・OrderManager 等）
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py

  - monitoring/ — 監視機能
    - monitoring_db.py — SQLite テーブル定義・MonitoringDB
    - system_monitor.py — システム・データ鮮度監視
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py

  - portfolio/ — ポートフォリオ構築
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py

  - research/ — リサーチ（DuckDB ベース）
    - factor_research.py
    - feature_exploration.py

  - ai/ — AI 関連
    - news_nlp.py
    - regime_detector.py

  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート

- data/ — 実行時に生成されるファイル（デフォルト）
  - monitoring.db (SQLITE_PATH)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - kabusys.duckdb (DUCKDB_PATH)
  - execution.pid
  - kill.flag
  - stop_requested.flag

---

## 開発時の注意点 / ヒント

- .env は絶対にリポジトリにコミットしないでください（config_setup はその旨を説明します）。
- 本番（KABUSYS_ENV=live）では LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を確認してください。validate_config でも警告が出ます。
- OpenAI を利用するモジュールは API 呼び出し失敗時にフェイルセーフ設計されていますが、APIキーや料金に注意してください。
- DuckDB のスキーマ（prices_daily / raw_financials / raw_news など）はリサーチ・AI モジュールが前提としています。適切にデータを投入してください。
- psutil によるプロセス優先度変更や CPU affinity は OS によって制約（権限・未実装）があります。実行ユーザーの権限に注意してください。

---

必要であれば、この README をベースに「デプロイ手順（systemd / supervisor / Docker）」や「設定ファイル例（.env.example, config/*.yaml のサンプル）」も作成できます。どの内容を優先して追加しますか？