# KabuSys

日本株向け自動売買システムのリポジトリ（ライブラリ＋起動スクリプト群）。  
この README はコードベースの主要コンポーネント、セットアップ方法、使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は以下の機能を持つ自動売買プラットフォームの一部実装です（ライブラリ + 実行スクリプト）:

- 戦略のリサーチ（ファクター計算・特徴量解析）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ決定）
- Execution Engine（発注管理／リスク管理／注文照合）
- Monitoring（システム監視・トレード監視・リスク監視・Kill Switch）
- AI モジュール（ニュースの NLP スコアリング、レジーム判定）
- ユーティリティ（ログ設定・プロセス優先度設定・設定ウィザード・設定検証）
- ツール（Paper Trading 検証レポート生成）

主にローカル環境（開発／ペーパートレード）と本番（live）向けに設計されています。

---

## 主な機能一覧

- 設定管理
  - .env 自動読み込み（プロジェクトルートの .env / .env.local）
  - 対話式設定ウィザード（`kabusys.config_setup`）
  - 設定検証 CLI（`kabusys.validate_config`）

- Execution / 発注関連
  - ExecutionEngine（Broker クライアント、OrderManager、RiskManager、Reconciler 等）
  - paper_trading 環境では MockBrokerClient を使用し、paper 用 SQLite に記録して本番 DB と分離

- Monitoring
  - SystemMonitor（CPU/Memory/Disk・プロセスの生死・データ鮮度）
  - TradeMonitor / RiskMonitor（滞留注文、約定異常、ドローダウン・ポジション上限）
  - KillSwitch（条件により data/kill.flag を作成）
  - MonitoringEngine（各モニタの統合ポーリング）
  - 永続化用 SQLite（`monitoring_db.py`）

- Research / Portfolio
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 特徴量解析（forward returns、IC、統計サマリ）
  - ポートフォリオ構築（候補選定、等重/スコア重み、リスク調整、ポジションサイズ算出）

- AI（OpenAI）
  - ニュース NLP によるセンチメントスコア（`kabusys.ai.news_nlp`）
  - マクロと ETF による市場レジーム判定（`kabusys.ai.regime_detector`）
  - OpenAI API を利用（API キー必要）

- ツール
  - Paper Trading 検証レポート（`kabusys.tools.paper_verification_report`）

- ユーティリティ
  - ログ設定（コンソール + 日次ローテートファイル）
  - プロセス優先度・CPU affinity 設定

---

## 前提・必須ソフトウェア

- Python 3.10+
- SQLite（標準の sqlite3）
- 推奨パッケージ（main 機能で必要）:
  - duckdb
  - psutil
  - openai
  - PyYAML（設定ファイル検証時に任意だが推奨）

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

（実際の requirements.txt がない場合は上記を参考にしてください）

---

## セットアップ手順

1. リポジトリをクローンしてプロジェクトルートへ移動
2. 仮想環境を作成・有効化し、必要パッケージをインストール（上記参照）
3. 環境変数を用意する
   - 対話式で .env を作る:
     ```bash
     python -m kabusys.config_setup
     ```
   - または .env を手動で作成（下の「重要な環境変数」を参照）

4. 設定検証（起動前に推奨）
   ```bash
   python -m kabusys.validate_config
   # 警告も FAIL としたい場合
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリ／ログディレクトリを作成（必要に応じて）
   - デフォルトの DB / ログパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
     - ログディレクトリ: logs/

---

## 重要な環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: 実行環境（development / paper_trading / live） デフォルト: development
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視 DB）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR） デフォルト: INFO
- LOG_DIR: ログ保存ディレクトリ（デフォルト: logs/）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 本番での通知に使用（任意）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時に必須）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、本番では 0 推奨）
- PAPER_FILL_MODE: paper_trading 時の mock fill モード（instant / partial / never / reject）
- MONITOR_POLL_INTERVAL: SystemMonitor のポーリング間隔（秒、デフォルト 60）

注意:
- .env ファイルは絶対に Git にコミットしないでください。

---

## 使い方（主要スクリプト/コマンド）

- 環境設定ウィザード（.env 作成）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- ExecutionEngine 起動
  - 起動:
    ```bash
    python -m kabusys.run_execution
    ```
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper 用 DB に記録して本番 DB と完全分離します。
    - 起動時にプロセス優先度を "high" に設定します。
    - 停止はプロジェクトルート/data/stop_requested.flag を作成して行います（実行スクリプトはこのファイルを見て停止）。
    - Execution は data/execution.pid に PID を書きます。

- Monitoring 起動
  ```bash
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書きできます（デフォルト 60）。
  - Monitoring は KABUSYS_ENV に関わらず本番の sqlite_path を使用します（監視ログは本番 DB に保存される想定）。
  - 停止はプロジェクトルート/data/stop_requested.flag を作成して行います。

- Paper Trading 検証レポート生成（ツール）
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示的に指定する場合
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI モジュール（プログラムから呼び出す）
  - ニュースセンチメントを付与して DB に書き込む:
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026, 4, 10), api_key="sk-...")
    ```
  - レジーム判定:
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026, 4, 10), api_key="sk-...")
    ```

---

## 停止・Kill Switch について

- Execution の停止要求
  - 実行中のプロセスはプロジェクトルート/data/stop_requested.flag の存在を監視しているため、このファイルを作成すると起動中の run_execution/run_monitoring は優雅に停止します。

- Kill Switch
  - リスク条件（ドローダウン、ポジション上限など）に応じて `data/kill.flag` が書き込まれます。Execution 起動時にこの kill.flag があれば起動を抑制します。
  - `KILL_FLAG_CLEAR_ON_START=1` を .env に設定すると起動時に kill.flag を自動でクリアしますが、本番では 0 を推奨します。

---

## ディレクトリ構成（主なファイル・モジュール）

src/kabusys の主要構成（抜粋）:

- kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings クラス、自動 .env 読み込み
  - config_setup.py              — 対話式 .env ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py                — ニュース NLP（OpenAI 呼び出し含む）
    - regime_detector.py         — 市場レジーム判定（OpenAI 使用）
  - monitoring/
    - monitoring_db.py           — SQLite 永続化層（テーブル作成・CRUD）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/ (実行時に作成される想定)
    - monitoring.db (SQLite)
    - paper_trading.db (SQLite: paper_trading 用)
    - kabusys.duckdb (DuckDB)
    - execution.pid, stop_requested.flag, kill.flag などのフラグ／PIDファイル

（実際のリポジトリではさらに細かいファイルがあります。上記は主要なポイントの抜粋です）

---

## 開発時の注意点 / 備考

- DuckDB と sqlite3 を併用しています（分析は DuckDB、監視/トレードログは SQLite）。
- AI モジュールを利用する場合は `OPENAI_API_KEY` が必要です。エラー時はフォールバックやスキップを行う実装になっていますが、正しく動作させるにはキーが必須です。
- run_monitoring は監視ログを記録するため本番用 sqlite_path（SQLITE_PATH）を使用する点に注意してください（KABUSYS_ENV に依存しません）。
- run_execution は KABUSYS_ENV=paper_trading のときに paper_trading 用 SQLite を使い、本番 DB とは分離されます。
- ログは既定で `logs/` に日次ローテーションで保存されます。ログディレクトリが作れない場合はコンソール出力のみになります。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を探索して決定）に基づき行われます。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください。

---

## よく使うコマンドまとめ

- .env 作成（対話式）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- Execution 起動（本番 or ペーパートレードは KABUSYS_ENV で切替）
  ```bash
  python -m kabusys.run_execution
  ```

- Monitoring 起動
  ```bash
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- Paper Trading 検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要に応じて README の各セクションをもっと詳細に（起動フロー図、DB スキーマ、API 使用例、テストの実行方法など）拡張できます。どの部分を深掘りしたいか教えてください。