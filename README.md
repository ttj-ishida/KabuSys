# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ向け README（日本語）。

本 README はコードベース（src/kabusys/...）を参照して作成しています。起動スクリプトやユーティリティ、研究／ポートフォリオ構築、監視・アラート機能、AI（OpenAI）連携などを含むモジュール群が含まれます。

---

## プロジェクト概要

KabuSys は日本株の自動売買を目的としたシステムです。以下の主要機能を持ち、実運用（live）、ペーパートレード（paper_trading）、開発（development）といった実行環境を切り替えて動作できます。

主な設計方針・特徴:
- 設定は環境変数（.env / .env.local）で管理。自動ロード機能あり（無効化可）。
- Execution（発注エンジン）と Monitoring（監視）は分離されたプロセスとして起動可能。
- Paper trading は本番 DB と分離して専用の SQLite を使用（data/paper_trading.db がデフォルト）。
- DuckDB を用いた調査／ファクター計算モジュール（prices_daily / raw_financials を参照）。
- OpenAI（gpt-4o-mini）を使ったニュース NLP やマクロレジーム判定モジュールを提供（API キー必要）。
- ログはコンソール出力＋日次ローテーションファイル出力で管理（logs/<app>.log）。

---

## 機能一覧

- 環境設定管理
  - .env ファイルの自動読み込み（.env.local で上書き）
  - 対話式ウィザード: `kabusys.config_setup`
  - 設定検証 CLI: `kabusys.validate_config`

- 実行エンジン
  - ExecutionEngine 起動スクリプト: `run_execution.py`
  - 本番 / ペーパーの切り替え（KABUSYS_ENV）
  - BrokerClientFactory により実際のブローカー or Mock クライアントを選択

- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - run_monitoring.py でポーリング監視を起動（デフォルト 60 秒）
  - kill.flag による ExecutionEngine 停止、stop_requested.flag による自プロセス停止

- ポートフォリオ構築
  - 候補選定・重み計算（等分・スコア加重）
  - セクターキャップ、レジーム乗数（ベンチマーク依存）
  - 発注株数決定（リスクベース、等分、スコアベース）、単元株丸め、投下資金スケーリング

- 研究（Research）
  - ファクター計算（Momentum / Value / Volatility）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー

- AI（OpenAI）連携
  - ニュースのセンチメントスコアリング（news_nlp）
  - マクロニュース + ETF MA によるレジーム判定（regime_detector）
  - OpenAI API キーを環境変数 `OPENAI_API_KEY` で指定

- ツール
  - Paper Trading 検証レポート生成スクリプト: `kabusys.tools.paper_verification_report`

- ユーティリティ
  - ログ設定ユーティリティ（stdout + 日次ローテート）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
  - Monitoring 用 SQLite 永続化層（初期化・マイグレーション含む）

---

## 必要パッケージ（例）

プロジェクト実行には以下のパッケージが利用されます。環境に応じて requirements.txt を準備して下さい。

- duckdb
- psutil
- openai
- (任意) PyYAML（`kabusys.validate_config` が config/*.yaml の中身を検証する場合）
- 標準ライブラリ: sqlite3, logging, threading, datetime, pathlib など

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン / 配布済みソースを取得
2. 仮想環境を作成して依存パッケージをインストール（上記参照）
3. 環境変数の準備（.env）
   - 対話式で作成する:
     ```bash
     python -m kabusys.config_setup
     ```
   - もしくはルートに `.env` を作成（.env.example を参考に）。自動ロードはデフォルトで有効。
   - 自動ロードを無効化する場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

4. 必須環境変数（最小セット）
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - KABUSYS_ENV（任意、デフォルト: development）有効値: development / paper_trading / live
   - OPENAI_API_KEY（AI モジュールを使う場合）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（ペーパートレードで上書きしたい場合）

5. データディレクトリ作成（必要に応じて）
   - logs/
   - data/
   ほとんどのモジュールは起動時にディレクトリを作成しようとしますが、アクセス権等で失敗する可能性があります。

---

## 使い方（主要コマンド）

- 環境ウィザード（.env 作成）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証（起動前チェック）
  ```bash
  python -m kabusys.validate_config
  # 警告を FAIL 扱いにする:
  python -m kabusys.validate_config --strict
  ```

- Execution（発注エンジン）起動
  - 本番 / ペーパーは KABUSYS_ENV に依存（paper_trading の場合 MockBroker を利用し、data/paper_trading.db に書き込む）
  ```bash
  python -m kabusys.run_execution
  ```

  動作上のポイント:
  - 起動時に `data/stop_requested.flag` が存在すると起動せず終了します。
  - Execution は `data/execution.pid`（デフォルト）を PID ファイルとして使用します。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると、起動時に kill.flag を自動クリアします（本番では推奨されません）。

- Monitoring（監視）起動
  ```bash
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60）。
  - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使用して monitoring DB を書き込みます（環境に依らず）。
  - 停止は `data/stop_requested.flag` を作成することで次回ループで検知して終了します。
  - システム監視が DRAWDOWN 等の条件を満たした場合に `data/kill.flag` を書き、ExecutionEngine に停止シグナルを送ります（KillSwitch）。

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する場合:
  python -m kabusys.tools.paper_verification_report --db /path/to/data/paper_trading.db
  ```

---

## 主要環境変数（代表）

- KABUSYS_ENV: execution 環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ出力ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパー取引時の約定挙動（instant / partial / never / reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（"1" で有効。注意：本番での設定は推奨しない）

---

## 停止・強制停止の仕組み

- stop_requested.flag
  - run_execution.py / run_monitoring.py はプロジェクトルートの `data/stop_requested.flag` を監視しており、存在すると安全に停止します（手動で停止したい場合に作成）。
- kill.flag
  - Monitoring がリスク条件（例: Drawdown）を検知すると `data/kill.flag` を作成して ExecutionEngine に停止シグナルを送ります（ExecutionEngine 側で kill.flag を検知し停止する設計）。

---

## ログ

- デフォルトで stdout（コンソール）出力とファイルログ（logs/<app_name>.log）を両方に出力します。
- 日次でローテーションされ、バックアップは 30 日分保持します。
- ログディレクトリは `LOG_DIR` 環境変数または `logs/` が使われます。
- logging 設定は `kabusys.utils.logging_setup.setup_logging` を通じ統一的に実施されます。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 配下の主要ファイル / ディレクトリです（全体の一部抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring ポーリングループ起動
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - trade_monitor.py (参照あり)
    - alert_manager.py (参照あり)
  - execution/
    - execution_engine.py (参照あり)
    - order_manager.py (参照あり)
    - order_repository.py (参照あり)
    - reconciler.py (参照あり)
    - broker_factory.py (参照あり)
    - risk_manager.py (参照あり)
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/ (実行時に作成されることが多い)
    - monitoring.db (デフォルトの SQLite)
    - paper_trading.db (ペーパー用)

※ 一部モジュール（例: trade_monitor.py, alert_manager.py, execution.*）は README 作成時点で参照はありますが、ここに寸法だけ記載しています。詳細はソースを参照してください。

---

## 開発時の注意点 / ベストプラクティス

- .env は絶対にリポジトリにコミットしないでください（README、config_setup.pyにも同記載あり）。
- 本番（KABUSYS_ENV=live）で稼働させる前に `python -m kabusys.validate_config` を実行して設定検証を行ってください。
- ペーパートレード (`KABUSYS_ENV=paper_trading`) は本番 DB と完全分離されていますが、データの整合性確認は怠らないでください。
- OpenAI を使う処理（ニュース NLP / レジーム判定）は API 呼び出しの失敗に対してフェイルセーフ（0 フォールバック）を採用しているものの、API 利用料やレート制限に注意してください。
- 長時間稼働させるプロセスは `LOG_DIR`・`data/` の保存先のディスク容量とパーミッションを事前確認してください。

---

## 参考コマンドまとめ

- ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Execution 起動
  ```
  python -m kabusys.run_execution
  ```

- Monitoring 起動
  ```
  python -m kabusys.run_monitoring
  ```

- Paper Trading レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

README の内容はコードベースの該当ファイル（src/kabusys/*.py）を元にまとめています。実際の運用やデプロイ時は環境依存の設定（API キー、DB パス、ログ・データ保存場所、権限）を十分に確認してください。必要であれば README を拡張して運用手順や systemd / supervisor のサービス定義例を追加できます。