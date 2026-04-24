# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買 / 研究 / 監視機能を備えたシステム（KabuSys）の実装です。本 README はリポジトリ内の主要モジュールを対象に、プロジェクト概要、機能、セットアップ、起動方法、ディレクトリ構成を日本語でまとめたものです。

注意: 実行には外部サービスの API キーやネイティブライブラリが必要になる場合があります（例: OpenAI、psutil、duckdb など）。本 README はソースコードの構成に基づく利用手順を説明します。

---

## プロジェクト概要

KabuSys は以下を目的とした Python ベースのシステムです。

- ファクター計算・リサーチ（DuckDB を用いた時系列ファクター計算）
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- Execution エンジン（実取引 / ペーパートレードを切り替え可能）
- 監視（システム稼働状況・注文状態・リスク監視）と Kill Switch
- ニュース NLU（OpenAI を使ったニュースセンチメント集計）
- 各種ツール（ペーパートレード検証レポート生成など）

設計方針の一部:
- 本番/ペーパートレードの DB は分離（ペーパートレードは data/paper_trading.db）
- .env による設定管理をサポート（対話式ウィザードあり）
- ロギングは統一的に setup_logging を使用（ログは logs/ に日次ローテート保存）
- DuckDB を分析 DB、SQLite を監視・注文ログ用 DB として使用

---

## 主な機能一覧

- Research / Factor 計算
  - momentum, volatility, value などのファクター計算（duckdb 接続で SQL + Python）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- Portfolio construction
  - 候補選定（スコア/ランクベース）
  - 等配分 / スコア加重 / リスクベースのポジションサイズ計算
  - セクターキャップ適用、レジーム乗数

- Execution
  - ExecutionEngine（実取引 or ペーパートレード）
  - BrokerClientFactory によるブローカークライアント抽象化（KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用）
  - RiskManager / OrderManager / Reconciler 等の主要コンポーネント

- Monitoring
  - SystemMonitor（CPU/メモリ/ディスク、データ鮮度、実行プロセス監視）
  - TradeMonitor（滞留注文、約定の異常検知 等）
  - RiskMonitor（ドローダウン / ポジション上限監視）
  - MonitoringEngine：複数 Monitor を束ね、KillSwitch 判定や AlertManager 通知
  - 監視ログの永続化（SQLite、monitoring_db.py）

- AI（任意）
  - ニュースを LLM（gpt-4o-mini 等）でセンチメント化し ai_scores に書き込み（news_nlp）
  - マクロニュース + ETF ma200 で市場レジーム判定（regime_detector）

- ツール
  - config_setup.py: .env 初期作成 / 対話式ウィザード
  - validate_config.py: .env と config/*.yaml の検証
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成

---

## セットアップ手順（開発者向け）

以下は一般的なセットアップ例です。環境や好みに応じて適宜読み替えてください。

1. リポジトリをクローンして作業ディレクトリへ移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate    # macOS / Linux
   .venv\Scripts\activate       # Windows
   ```

3. 必要なパッケージをインストール
   - 代表的な依存（実行に必要なもの）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config の検証で任意）
   - 例:
     ```
     pip install duckdb psutil openai pyyaml
     ```
   - requirements.txt がある場合はそれを使用してください（本サンプルコードには含まれていません）。

4. 環境設定 (.env) を用意
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは .env を手動で作成（例: .env.example を参照）。必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - オプション:
     - OPENAI_API_KEY （AI 機能を使う場合必須）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（通知用）
     - KABUSYS_ENV（development / paper_trading / live）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB, デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード DB, デフォルト: data/paper_trading.db）
     - LOG_LEVEL（デフォルト: INFO）
     - LOG_DIR（デフォルト: logs/）

5. 設定検証
   ```
   python -m kabusys.validate_config
   ```
   --strict オプションで警告もエラー扱いにできます。

6. データディレクトリの作成（必要に応じて）
   ```
   mkdir -p data logs
   ```

---

## 使い方（起動 / 実行例）

各起動スクリプトはパッケージモジュールとして実行できます。

- Execution（取引エンジン）起動
  - 本番/ペーパーは KABUSYS_ENV による切替:
    - ペーパートレード:
      ```
      export KABUSYS_ENV=paper_trading
      python -m kabusys.run_execution
      ```
      ペーパートレード時は MockBrokerClient を用い、DB は PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に記録します。
    - 本番:
      ```
      export KABUSYS_ENV=live
      python -m kabusys.run_execution
      ```

  - 実行中の停止はプロジェクトルートの data/stop_requested.flag を作成することで行えます（run_execution は起動時にこのフラグをチェックします）。Kill Switch は data/kill.flag によって ExecutionEngine に停止指示を送ります。

- Monitoring（監視ループ）起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）でオーバーライド可能（デフォルト: 60）。
  - Monitoring は環境にかかわらず本番 sqlite_path を使用して監視ログを記録します。
  - 停止には data/stop_requested.flag を作成します（run_monitoring はこのファイルを検知してループを終了します）。

- 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- ペーパートレード検証レポート生成（ツール）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  デフォルト DB は data/paper_trading.db。別パス指定は --db オプションで可能。

- AI 機能（ニューススコア / レジーム判定）
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY）
  - プログラムから呼び出す例:
    ```
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026,4,10), api_key="sk-...")
    ```
  - 同様に regime_detector.score_regime() で市場レジーム算出が可能。

ログ出力は logs/<app_name>.log に日次ローテーションで保存されます（ログディレクトリは LOG_DIR 環境変数で変更可能）。

---

## 重要な環境変数（抜粋）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 動作モード
  - KABUSYS_ENV: development | paper_trading | live (デフォルト: development)

- データ / DB
  - DUCKDB_PATH: 分析用 DuckDB（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）

- ログ / デバッグ
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL (デフォルト INFO)
  - LOG_DIR: logs ディレクトリ（デフォルト logs/）

- AI
  - OPENAI_API_KEY: OpenAI を使う機能で必要

- 監視用
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START: 本番時の Kill Flag 自動クリア (0/1)

---

## 停止・制御手順（Kill Switch / stop flag）

- 実行中プロセスの停止（両スクリプト）
  - data/stop_requested.flag を作成すると run_execution/run_monitoring は次のポーリングで終了します。
  - Kill Switch（監視→実行エンジン停止）
    - KillSwitch は条件（ドローダウン超過、ポジション上限超過等）を満たした場合に data/kill.flag を書き込みます。
    - ExecutionEngine は起動時に kill.flag を参照し、存在すれば起動をスキップします（設定に応じて起動時にクリアするオプションあり）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュール一覧（本 README 作成時のコードベースに基づく）。

- src/kabusys/
  - __init__.py (パッケージ定義)
  - config.py (環境変数 / Settings)
  - config_setup.py (対話式 .env ウィザード)
  - validate_config.py (設定検証 CLI)
  - run_execution.py (ExecutionEngine 起動スクリプト)
  - run_monitoring.py (SystemMonitor ポーリング起動スクリプト)

- src/kabusys/execution/
  - execution_engine.py
  - broker_factory.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
  - ...（Execution 関連コンポーネント）

- src/kabusys/monitoring/
  - monitoring_engine.py
  - monitoring_db.py (SQLite スキーマ + 永続化 API)
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - ...（監視関連）

- src/kabusys/portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py

- src/kabusys/research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py

- src/kabusys/ai/
  - news_nlp.py (OpenAI を用いたニューススコアリング)
  - regime_detector.py (市場レジーム判定)
  - __init__.py

- src/kabusys/utils/
  - logging_setup.py (共通ログ設定)
  - process_priority.py (プロセス優先度 / CPU affinity)
  - __init__.py

- src/kabusys/tools/
  - paper_verification_report.py
  - __init__.py

- その他
  - config/ (system_config.yaml 等のテンプレート・生成された設定ファイル）
  - data/ (デフォルトの DB ファイル、pid/flag ファイルなどを配置するディレクトリ)
  - logs/ (ログ出力ディレクトリ)

---

## 補足 / 運用メモ

- DB の分離
  - 監視データ（monitoring）は SQLITE_PATH（デフォルト data/monitoring.db）に記録。ペーパートレードは別 DB に保存されるため本番 DB と完全に分離可能です。

- ログ
  - setup_logging() によりコンソール（stdout）とログファイル（日次ローテーション）が統一的に設定されます。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。

- プロセス優先度
  - 各起動スクリプトは起動直後に set_process_priority("high") を呼びますが、OS の権限やプラットフォームにより効果がない場合があります。

- テスト / 開発
  - 自動ロードされる .env はプロジェクトルート（.git または pyproject.toml を検出）に基づいて行われます。テストで自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- セキュリティ
  - .env ファイルは機密情報を含むため Git にコミットしないでください（config_setup.py もその旨をヘッダに記載しています）。

---

この README はコードベースの主要ポイントを抜粋して記載しています。詳細や API、各モジュールのさらに細かい仕様はソースコード中の docstring やコメントを参照してください。補足説明や特定機能の詳細な README（例: ExecutionEngine の設定、Broker の実装方針、デプロイ手順など）が必要であれば、どの項目を優先して深掘りするか教えてください。