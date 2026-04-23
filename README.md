# KabuSys

日本株自動売買システムのコアライブラリ群および起動スクリプト群です。  
このリポジトリには、発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI（ニュース NLP / レジーム判定）などの主要コンポーネントが含まれます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買を支援するコンポーネント群です。主な役割は以下の通りです。

- 実運用/ペーパートレードの ExecutionEngine（ブローカークライアント経由で発注）
- システム状態・データ鮮度・注文/リスク監視とアラート（Monitoring）
- ポートフォリオ選定・重み付け・株数決定（Portfolio construction）
- DuckDB を用いたファクター計算・リサーチ機能（Research）
- OpenAI を利用したニュースセンチメント・市場レジーム判定（AI）
- .env 対話式ウィザードと設定検証 CLI、ツールスクリプト（設定支援・検証・レポート）

設計方針として、運用系（発注）と解析系（DuckDB/リサーチ）は明確に分離され、ペーパートレード用 DB を分けるなど安全策が取られています。

---

## 主な機能一覧

- Execution
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - BrokerClient 抽象化（mock を含む）
  - RiskManager / OrderManager / Reconciler 等による注文管理
- Monitoring
  - SystemMonitor（CPU/Mem/Disk、プロセス死活、データ鮮度）
  - TradeMonitor（注文滞留・約定異常検出）
  - RiskMonitor（ドローダウン・ポジション上限検出）
  - KillSwitch（フラグファイルによる Engine 停止）
  - MonitoringEngine：複数モニタの定期実行とアラート連携
- Portfolio
  - 候補選定・等重/スコア重み付け
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ計算（lot 単位、リスクベース等）
- Research
  - DuckDB を用いた Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（情報係数）計算、統計サマリ
- AI
  - OpenAI を用いたニュースセンチメント（news_nlp）
  - マクロニュース + ETF MA による市場レジーム判定（regime_detector）
- ユーティリティ
  - .env 対話式作成ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成（tools.paper_verification_report）
  - 統一ロギング設定、プロセス優先度 / CPU affinity ユーティリティ
- DB
  - SQLite（監視ログなど）と DuckDB（分析・リサーチ）を併用

---

## 動作前提 / 必要環境

- Python 3.10+
- 必須ライブラリ（例）
  - duckdb
  - psutil
  - openai
  - （オプション）PyYAML（config ファイル検証時）
- SQLite（標準モジュールで利用）
- .env に API キー等を設定
- （実運用時）kabuステーション等のブローカー API が必要

pip インストール例（仮）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

※ requirements.txt がある場合はそちらを利用してください。

---

## セットアップ手順（クイックスタート）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境作成 & 依存インストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb psutil openai PyYAML
   ```

3. .env を対話式で作成（推奨）
   ```bash
   python -m kabusys.config_setup
   ```
   - J-Quants トークン、kabu API パスワード、KABUSYS_ENV 等を対話で入力できます。
   - .env は Git に絶対にコミットしないでください。

4. 設定検証
   ```bash
   python -m kabusys.validate_config
   # 警告もエラー扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

5. ログ用ディレクトリ（自動作成されますが手動で作る場合）
   ```bash
   mkdir -p logs data
   ```

---

## 主要な環境変数（概要）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

主な任意 / 推奨:
- KABUSYS_ENV — 実行モード: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR）
- OPENAI_API_KEY — OpenAI API キー（AI モジュール利用時）
- PAPER_FILL_MODE — ペーパートレードでの fill 挙動（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、本番では 0 推奨）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）

運用関連ファイル:
- data/kill.flag — KillSwitch が書き込む停止フラグ
- data/stop_requested.flag — run_*.py の外部停止トリガー（停止要求ファイル）
- data/execution.pid — 実行エンジンの PID を保存するファイル（run_execution が使用）

---

## 使い方（起動コマンド例）

注意: package が適切にパスにある（src を PYTHONPATH に含めるか pip install -e . を実行）前提です。

- ExecutionEngine（通常の起動）
  ```bash
  # 本番/ペーパーは KABUSYS_ENV により切り替わる
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 DB（data/paper_trading.db）に記録します。
  - 起動前に data/stop_requested.flag があると起動しません（外部停止要求検出）。
  - 実行中に stop flag が作成されるとエンジン停止を試みます。

- Monitoring（監視プロセス起動）
  ```bash
  # ポーリング間隔を上書きする例（秒）
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  - デフォルトポーリング: 60秒
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視 DB は一意に保持）。

- .env 対話ウィザード
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または DB パスを明示
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI / Research 等はモジュール関数として利用
  - 例: news NLP を実行するには programmatic に DuckDB 接続を作成して呼び出します（OpenAI APIキーが必要）。
    ```python
    import duckdb
    from datetime import date
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026,4,20), api_key="sk-...")
    ```

---

## 停止・Kill スイッチ（運用の注意）

- KillSwitch はリスク条件に応じて data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。
- 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアしますが、本番では 0 を強く推奨します（誤動作で自動クリアされるリスク）。
- 外部から即時停止要求を行う場合は data/stop_requested.flag を作成すると run_* スクリプトは検出して終了処理を行います。

---

## ディレクトリ構成（主なファイル）

以下は src/kabusys 以下の主要ファイル・モジュール一覧と簡単な説明です。

- kabusys/
  - __init__.py — パッケージ定義（__version__ 等）
  - config.py — 環境変数 / .env 自動読み込みと Settings クラス
  - config_setup.py — .env 対話式ウィザード CLI
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor のポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成ツール
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）による銘柄別センチメントスコア付与
    - regime_detector.py — 市場レジーム判定（マクロ + ETF MA）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - risk_adjustment.py — セクターキャップ・レジーム乗数
    - position_sizing.py — 株数決定・資金配分
  - research/
    - factor_research.py — Momentum/Volatility/Value ファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - monitoring/
    - monitoring_db.py — SQLite 監視 DB のスキーマ管理と DB 操作ラッパー
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — （注文系監視ロジック）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — フラグファイルによる停止シグナル発行
    - monitoring_engine.py — 各モニタの連携とポーリング制御
    - alert_manager.py — （アラート送信管理）
  - execution/
    - execution_engine.py — ExecutionEngine 本体
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py — 発注周りのコンポーネント群
  - data/ （実行時に使用されるファイル置き場、リポジトリには含まれないことが推奨）
    - monitoring.db（デフォルト）
    - kabusys.duckdb（デフォルト）
    - paper_trading.db（ペーパートレード用）
  - utils/
    - logging_setup.py — ログ設定ユーティリティ（コンソール + 日次ローテートファイル）
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

（省略されているファイルや補助モジュールが存在する場合がありますが、上記が主要なものです）

---

## 開発者向けメモ

- DuckDB は分析処理用に利用。prices_daily / raw_financials 等のテーブルを前提にしているため、リサーチ実行前にデータ投入が必要です。
- Monitoring の初期化は init_monitoring_db(sqlite_conn) で行います（冪等）。
- AI 呼び出しは API 制限・失敗に備えたリトライ実装・フォールバックを組み込んでいますが、API キーやコスト管理に注意してください。
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力されます。ログディレクトリ作成に失敗した場合、コンソール出力のみになります。

---

## よくあるコマンドまとめ

- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- Execution 起動: python -m kabusys.run_execution
- Monitoring 起動: MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
- Paper 検証レポート: python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

---

もし README に追加したい項目（例: サンプル .env、詳細な API 使用法、CI/CD の手順、Docker 化など）があれば教えてください。必要に応じて追記・整備します。