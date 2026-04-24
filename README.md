# KabuSys

日本株自動売買システムのコードベース README。  
このドキュメントはリポジトリ内の主要スクリプト・モジュールの概要、セットアップ手順、実行方法、ディレクトリ構成をまとめたものです。

目次
- プロジェクト概要
- 主な機能一覧
- 前提・依存関係
- セットアップ手順
- 使い方（主要コマンド）
- 環境変数（主要なもの）
- 運用メモ（停止/kill フラグ・ログ・DB）
- ディレクトリ構成

---

## プロジェクト概要
KabuSys は日本株向けの自動売買システムの基盤ライブラリおよび実行スクリプト群です。  
主に以下の用途を持ちます：
- 発注 ExecutionEngine（本番 / ペーパートレード切替）
- システム監視（SystemMonitor / MonitoringEngine）
- リスク監視（ドローダウン、ポジション上限等）
- ポートフォリオ構築・配分計算（等配分、スコア加重、リスクベース等）
- 研究用ファクター計算（DuckDB を利用）
- AI（OpenAI）を使ったニュースセンチメント評価やレジーム判定
- ペーパートレード検証レポート生成ツール

設計方針として、DB（DuckDB/SQLite）をデータ層に使用し、外部 API 呼び出し（kabuステーション、J-Quants、OpenAI）は設定に応じて利用します。ペーパートレード時は本番 DB と分離されるよう配慮されています。

---

## 主な機能一覧
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV により実際のブローカ／モック切替（paper_trading では MockBrokerClient を使用）
  - paper_trading 用 DB を分離（data/paper_trading.db がデフォルト）
- Monitoring 起動スクリプト（run_monitoring.py）
  - システムリソース監視（CPU／メモリ／ディスク）
  - データ鮮度・プロセス稼働監視、監視データは SQLite に永続化
  - ポーリング間隔は環境変数で上書き可能（MONITOR_POLL_INTERVAL、デフォルト 60 秒）
- 設定支援ツール
  - 環境設定ウィザード（python -m kabusys.config_setup）で .env を対話的に作成
  - 設定検証 CLI（python -m kabusys.validate_config）
- 研究モジュール
  - ファクター計算（momentum, volatility, value）
  - 将来リターンや IC 計算、統計サマリ等
- ポートフォリオ構築
  - 候補選定、重み計算、ポジションサイズ決定、セクター制約・レジーム乗数
- AI（OpenAI）連携
  - ニュースのセンチメントを LLM で評価して ai_scores に書き込み（news_nlp）
  - マクロセンチメントと ETF MA を合成した市場レジーム判定（regime_detector）
- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

---

## 前提・依存関係
推奨 Python バージョン: 3.10 以降（型注釈に | を使用しているため）

主な依存（抜粋）:
- duckdb
- psutil
- openai
- PyYAML（設定検証時に config/*.yaml を検証する場合のみ必要）
- 標準ライブラリ：sqlite3, logging, datetime など

インストール例（仮）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```
※実際の requirements.txt があればそれを使用してください。

---

## セットアップ手順（簡易）
1. リポジトリをクローンしてワークディレクトリへ移動
2. 仮想環境を作成して依存パッケージをインストール
3. .env を作成
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
   - 生成後、設定を検証:
     ```
     python -m kabusys.validate_config
     ```
     --strict を付けると警告も失敗扱いになります。
4. 必要に応じて DuckDB / SQLite データファイルを配置（デフォルトは data/ 以下に作成されます）
   - デフォルトパス:
     - DuckDB: data/kabusys.duckdb
     - monitoring SQLite: data/monitoring.db
     - paper trading SQLite: data/paper_trading.db
5. ログディレクトリ（logs/）は自動作成されます（書き込み権限が必要）

---

## 使い方（主要コマンド）
- 環境設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine 起動（本番 / ペーパートレード）
  - 本番（KABUSYS_ENV=live）:
    ```
    KABUSYS_ENV=live python -m kabusys.run_execution
    ```
  - ペーパートレード（Mock ブローカー、専用 DB を使用）:
    ```
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
  実行中は data/execution.pid に PID を書くなどの管理を行います。停止は data/stop_requested.flag を作成することで行えます。

- Monitoring 起動
  ```
  python -m kabusys.run_monitoring
  ```
  ポーリング間隔の変更（秒）:
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  DB パスを指定する場合:
  ```
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI 関連（プログラムから呼び出す API）
  - news_nlp.score_news(conn, target_date, api_key=None) — OpenAI API キー required（api_key または OPENAI_API_KEY 環境変数）
  - regime_detector.score_regime(conn, target_date, api_key=None)

---

## 主要な環境変数
（.env に設定する想定。config_setup で生成できます）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主な任意 / 設定:
- KABUSYS_ENV: execution 環境（development / paper_trading / live）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ保存ディレクトリ（デフォルト logs/）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリア（0/1）

設定の検証には python -m kabusys.validate_config を使用してください。

---

## 運用メモ
- 停止制御:
  - run_monitoring/run_execution はプロセス内で data/stop_requested.flag の存在を監視して安全に停止します（スクリプトループ内でチェック）。
  - KillSwitch は data/kill.flag を書き込み、ExecutionEngine 側で kill.flag を見て停止します。kill.flag は明示的に消す必要があります（KILL_FLAG_CLEAR_ON_START を使う設定もありますが、本番では 0 を推奨）。
- ロギング:
  - kabusys.utils.logging_setup.setup_logging を使って統一的にログを設定します。ログは stdout とファイル（logs/<app_name>.log、日次ローテーション）に出力されます。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は起動時に必要テーブル・カラムの存在を保証します（冪等）。既存 DB に対する簡単なカラム追加マイグレーションも内包しています。
- ペーパートレード:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して発注イベントをペーパートレード DB（data/paper_trading.db）に記録します。本番 DB と分離されています。

---

## ディレクトリ構成（抜粋）
以下は主要なモジュール / スクリプトの一覧（src/kabusys 以下中心）。実際のリポジトリにはさらに多くのファイルがある可能性があります。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - config_setup.py          — .env 生成ウィザード（CLI）
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - monitoring/
    - monitoring_db.py       — SQLite 監視ログ永続化層
    - system_monitor.py      — システム状態監視
    - risk_monitor.py        — ドローダウン／ポジション上限監視
    - kill_switch.py         — kill.flag 管理・発動ロジック
    - monitoring_engine.py   — 複数モニタの束ねとポーリング
    - alert_manager.py       — （アラート送信を担う想定）
    - trade_monitor.py       — （滞留注文等の監視）
  - execution/
    - execution_engine.py    — Execution エンジン本体
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py            — ニュースセンチメント評価（OpenAI）
    - regime_detector.py     — 市場レジーム判定（MA + マクロセンチメント）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート

---

## 補足（実践的な Tips）
- 開発環境では KABUSYS_ENV=development を推奨（発注等の副作用を避ける）。ペーパートレード時は paper_trading を使用して処理を分離。
- OpenAI を利用する機能はネットワーク・API 利用に依存するため、API キーとレート制限に注意してください。news_nlp/regime_detector はリトライやフェイルセーフを備えていますが、運用時の監視が必要です。
- ローカルで試す際は .env に DUCKDB_PATH / SQLITE_PATH を設定し、確認用に空の DB ファイルを作成しておくとエラーが減ります。
- run_execution/run_monitoring はプロセス優先度変更 (psutil 経由) を試みますが、権限不足などで失敗する場合は警告を出して継続します。

---

README はここまでです。必要であれば、以下を追加で生成できます：
- 詳細な .env.example（キーと説明を列挙）
- 各 CLI のサンプルユースケース（本番／検証／デバッグ）
- 開発者向けのテスト・デバッグ手順（ユニットテストの実行方法）