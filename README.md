# KabuSys

日本株向け自動売買システム（ライブラリ + 起動スクリプト群）の README。  
本ドキュメントはリポジトリ内のソースコードを元に作成しています。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したシステム群です。主要機能は以下のとおりです。

- 発注エンジン（ExecutionEngine）：ブローカーとのやり取り、注文管理、リスク管理、約定照合
- 監視（Monitoring）：システム状態・注文状態・リスク監視、Kill Switch 実装
- ポートフォリオ構築（Portfolio）：銘柄選定、配分重み計算、ポジションサイズ決定、セクター制約
- リサーチ（Research）：ファクター計算、特徴量探索、将来リターン計算
- AI 支援（AI）：ニュース NLP によるセンチメントや市場レジーム判定（OpenAI）
- ユーティリティ：ログ設定、プロセス優先度、設定ウィザード、設定検証、レポート生成 等

設計上のポイント：
- DuckDB / SQLite をデータ層として利用（分析用に DuckDB、監視/発注ログは SQLite）
- Paper Trading と Live（本番）を分離（paper_trading は専用 DB を使用）
- 環境変数 / .env による設定管理、対話式ウィザードと検証 CLI を提供
- OpenAI を用いたテキスト解析機能を備える（API キー必須、フェイルセーフ設計）

---

## 主な機能一覧

- Execution
  - Broker クライアントの抽象化（本番 / モック切替）
  - OrderManager / RiskManager / Reconciler
  - ExecutionEngine によるセッション実行と停止制御（kill.flag / stop flag）
- Monitoring
  - SystemMonitor：CPU / メモリ / ディスク、データ鮮度、プロセス生存チェック
  - TradeMonitor：注文滞留や約定異常の検出（trade_logs）
  - RiskMonitor：ドローダウン・ポジション上限の監視、リスクログ出力
  - KillSwitch：条件を満たすと data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringEngine：各監視を周期的に実行しアラートや KillSwitch を運用
- Portfolio
  - 銘柄候補選定（スコア順）
  - 等配分 / スコア重み配分
  - リスクベースのポジションサイズ計算（単元株丸め、aggregate cap）
  - セクターキャップ、レジーム乗数
- Research
  - Momentum / Volatility / Value ファクター算出（DuckDB）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI
  - news_nlp: ニュースを OpenAI でスコアリングして ai_scores テーブルへ保存
  - regime_detector: ETF とマクロニュースを組合せて市場レジーム判定を行い保存
- Tools
  - config_setup: 対話式 .env 生成ウィザード
  - validate_config: 起動前の設定検証 CLI
  - paper_verification_report: ペーパートレード検証レポート生成

---

## 必要環境 / 依存パッケージ（例）

- Python 3.9+
- 必須ライブラリ（例）
  - duckdb
  - psutil
  - openai
- 便利／オプション
  - PyYAML（config/*.yaml を検証する場合）
- SQLite は標準ライブラリに含まれます。

インストール例（プロジェクトに requirements.txt がない場合の最小例）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. 仮想環境の作成（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt   # もし用意されている場合
   # または最低限:
   pip install duckdb psutil openai PyYAML
   ```

2. .env の作成
   - 対話式ウィザードを使用する推奨:
     ```bash
     python -m kabusys.config_setup
     ```
   - 主要環境変数（.env に記載する例）
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
     - LOG_LEVEL (INFO 等)
     - OPENAI_API_KEY（AI 機能を使う場合に必須）
     - MONITOR_POLL_INTERVAL（監視ループ間隔（秒）、デフォルト 60）
     - KILL_FLAG_CLEAR_ON_START（本番での自動クリア防止のためデフォルト 0）
   - 生成後、設定を検証:
     ```bash
     python -m kabusys.validate_config
     python -m kabusys.validate_config --strict
     ```

3. データディレクトリの準備
   - ログディレクトリ（デフォルト: logs/）や data/ は起動時に自動生成されますが、権限等を確認してください。

---

## 使い方（起動・ツール）

- 実行エンジン起動（ExecutionEngine）
  - 通常起動
    ```bash
    python -m kabusys.run_execution
    ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録します。
  - 実行中に data/stop_requested.flag を置くことでエンジンに停止を通知します（停止フラグ検出で安全停止）。

- 監視プロセス起動（Monitoring）
  - 起動
    ```bash
    python -m kabusys.run_monitoring
    ```
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト: 60）。
  - 監視は常に本番用 sqlite_path を参照（監視 DB は環境に依存せず本番パスを使用）。

- 設定ウィザード
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パス指定が必要な場合:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI 機能
  - OpenAI API を利用するためには環境変数 OPENAI_API_KEY を設定してください。
  - news_nlp.score_news, regime_detector.score_regime などの関数はライブラリとして呼び出して利用できます。

---

## 重要なファイル / フラグ

- data/kill.flag — Kill Switch が発動したことを示すファイル。存在すると ExecutionEngine を停止するトリガーになります。
- data/stop_requested.flag — run_execution/run_monitoring の外部的な停止要求に使用される旗。
- data/execution.pid — 実行エンジンの PID ファイル。
- デフォルト DB パス
  - DuckDB: data/kabusys.duckdb
  - SQLite (監視): data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 配下の主要なモジュールと役割（リポジトリのルートが `src/` 配下にある想定）。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数 / .env 自動読み込み、Settings クラス
  - config_setup.py
    - .env 対話式ウィザード
  - validate_config.py
    - 設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリング起動スクリプト
  - execution/
    - order_manager.py, order_repository.py, execution_engine.py, reconciler.py, risk_manager.py, broker_factory.py
  - monitoring/
    - monitoring_db.py — SQLite の永続化層
    - system_monitor.py, trade_monitor.py, risk_monitor.py, kill_switch.py, monitoring_engine.py, alert_manager.py
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py
  - research/
    - factor_research.py, feature_exploration.py
  - ai/
    - news_nlp.py, regime_detector.py
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py, process_priority.py
  - data/ (実行時に生成される)
    - *.db, *.pid, kill.flag, stop_requested.flag
  - logs/ (デフォルトログ出力先。変更可)

---

## サンプル .env（最小例）

以下は .env の例（.env.example を参考に実際の値を設定してください）:

```
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-xxxxxxxxxxxx
KILL_FLAG_CLEAR_ON_START=0
```

注: .env を絶対にリポジトリにコミットしないでください（API キー・秘密情報が含まれます）。

---

## よくある運用上の注意

- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START は 0 を推奨。Kill Switch の自動クリアは危険。
- Paper Trading は専用の SQLite（PAPER_TRADING_SQLITE_PATH）に分離されます。本番データとは混在しません。
- OpenAI 呼び出しはネットワーク障害やレート制限を考慮してリトライ・フォールバック設計になっていますが、API キーの費用とレートに注意してください。
- ロギングは logs/<app_name>.log に日次ローテートで保存されます。LOG_DIR 環境変数で変更可能。
- system_monitor は監視のために本番 sqlite_path を参照する点に注意。監視は環境に関わらず本番 DB を見る設計です。

---

## 開発者向けメモ

- 単体関数群（portfolio/*、research/*）は外部副作用を持たない純粋関数として設計されている箇所が多く、ユニットテストが容易です。
- OpenAI まわりは _call_openai_api を patch / mock することでテスト可能です（各モジュール内で明示的に分離実装あり）。
- DB スキーマは monitoring_db.init_monitoring_db で作成・マイグレーションを行います。既存カラム追加の処理も含まれます。

---

必要に応じて README に追記します。たとえば CI のセットアップ手順、ユニットテストの実行方法、各コンポーネントの詳細設計書（PortfolioConstruction.md 等）へのリンク、README を英語化する等。どれを追加しますか？