# KabuSys

日本株向け自動売買システムのリポジトリ（軽量版）。  
本 README はソースツリー内の主要モジュールに基づき、導入・運用に必要な情報（概要、機能、セットアップ、使い方、ディレクトリ構成）を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は次を目的としたモジュール群で構成された自動売買フレームワークです。

- 戦略開発向けのリサーチ（ファクター計算、特徴量探索）
- ポートフォリオ構築（候補選定、重み付け、株数決定）
- 実際の発注ロジック（ExecutionEngine）およびペーパートレード分離
- システム稼働監視（SystemMonitor / MonitoringEngine）、Kill Switch による安全停止
- ニュース NLP / LLM を使ったスコアリング・レジーム判定
- 運用補助ツール（.env ウィザード、設定検証、ペーパートレード検証レポート）

設計上のポイント：
- DB は DuckDB（分析）と SQLite（監視 / 注文履歴）を併用
- Paper Trading（検証）は本番 DB と分離される
- OpenAI を用いた NLP 機能は API キーで制御
- .env による設定管理 + 対話式ウィザード / 検証 CLI を備える

---

## 主な機能一覧

- 起動スクリプト
  - 起動・監視ループ: `kabusys.run_monitoring`
  - 発注エンジン: `kabusys.run_execution`（`KABUSYS_ENV=paper_trading` では MockBroker）
- 設定関連ツール
  - `.env` 対話式ウィザード: `kabusys.config_setup`
  - 設定検証 CLI: `kabusys.validate_config`
- モニタリング
  - SystemMonitor: CPU/メモリ/ディスク/プロセス監視、データ鮮度チェック
  - TradeMonitor / RiskMonitor / MonitoringEngine / KillSwitch
  - 監視ログ永続化: SQLite（`monitoring_db.py`）
- ポートフォリオ構築
  - 銘柄選定、重み付け（等金額/スコア加重）、ポジションサイジング、セクター制限、レジーム乗数
- リサーチ（DuckDB を利用）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン、IC（Information Coefficient）、統計サマリー
- AI（OpenAI）
  - ニュースのセンチメントスコアリング（`kabusys.ai.news_nlp`）
  - 市場レジーム判定（`kabusys.ai.regime_detector`）
- 運用ツール
  - Paper Trading 検証レポート生成（`kabusys.tools.paper_verification_report`）

---

## 必要条件（推奨）

- Python 3.10+
- 必要パッケージ（代表例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証でオプション）
- SQLite は標準ライブラリで使用可

pip での例（環境に合わせて調整してください）:
```
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン / コピーしてプロジェクトルートに移動
2. Python 仮想環境を作成・有効化（推奨）
3. 依存ライブラリをインストール（上記参照）
4. 環境変数の初期化:
   - 対話式で `.env` を生成する:
     ```
     python -m kabusys.config_setup
     ```
     ウィザードが `.env` を作成します（既存の .env を読み込んで更新することも可能）。
   - もしくは `.env.example` を参考に手動で `.env` を作成してください。
5. 設定検証（推奨）:
   ```
   python -m kabusys.validate_config
   ```
   問題がある場合はメッセージに従って修正します。警告も厳密に扱う場合は `--strict` を付けます。

環境変数のうち必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要な環境変数（代表）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: 分析 DB（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API を使う機能で必要
- LOG_LEVEL, LOG_DIR 等（ログ制御）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）

注意:
- Paper Trading 起動時は `KABUSYS_ENV=paper_trading` を設定してください。これにより発注処理は MockBroker を用い、ペーパートレード DB に記録されます（本番 DB と分離）。

---

## 使い方（主要コマンド）

基本的にモジュールはモジュール実行形式で起動できます。プロジェクトルートで実行してください。

- 環境ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 発注エンジン起動（ExecutionEngine）
  - 本番 / 開発 / ペーパートレードはいずれも `KABUSYS_ENV` に依存
  ```
  # 例: ペーパートレードで起動（PAPER_TRADING_SQLITE_PATH を .env で設定しておく）
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```
  実行中に `data/stop_requested.flag` が作成されているとエンジンは終了します。エンジンは PID ファイルを `data/execution.pid`（デフォルト）に書きます。

- 監視プロセス起動（SystemMonitor のポーリング）
  ```
  # ポーリング間隔を環境変数で上書き（秒）
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  デフォルトのポーリング間隔は 60 秒。監視は常に本番用の sqlite_path を使って監視データを書き込みます（環境にかかわらず）。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  または DB パスを明示:
  ```
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI 機能（プログラム経由で呼び出す例）
  - ニューススコアを書き込む:
    ```python
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    count = score_news(conn, target_date, api_key="YOUR_OPENAI_KEY")
    ```
  - レジーム判定:
    ```python
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date, api_key="YOUR_OPENAI_KEY")
    ```
  - OpenAI API キーは環境変数 `OPENAI_API_KEY` または関数引数で指定可能です。

停止 / Kill Switch:
- Monitoring 側が条件を満たすと `data/kill.flag` を書き込み、ExecutionEngine 側で検出して安全に停止できます。
- 明示的停止は `data/stop_requested.flag` を作成することで行えます（run_* スクリプトはこのフラグを監視して graceful shutdown します）。
- 起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定していると Kill Flag を自動クリアしますが、本番では `0` を推奨します。

ログ:
- `kabusys.utils.logging_setup.setup_logging` により stdout と日次ローテートファイル（logs/<app_name>.log）へログ出力します。
- ログディレクトリは環境変数 `LOG_DIR`、ログレベルは `LOG_LEVEL` で制御可能です。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                      — 環境変数読み込み / Settings
    - config_setup.py                — .env 対話式ウィザード
    - validate_config.py             — 設定検証 CLI
    - run_execution.py               — ExecutionEngine 起動スクリプト
    - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
    - utils/
      - logging_setup.py
      - process_priority.py
    - execution/                      — 発注関連（BrokerFactory, Engine, OrderManager 等）
      - execution_engine.py
      - broker_factory.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py
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
    - data/ (実行時に作成される想定)
      - monitoring.db (デフォルト SQLITE_PATH)
      - paper_trading.db (ペーパートレード用 DB)
      - stop_requested.flag, kill.flag, execution.pid
    - logs/ (デフォルトログ出力先)

---

## 運用上の注意（重要）

- 本番（KABUSYS_ENV=live）では設定値を慎重に確認してください。`validate_config` は live 時のガードチェックを行いますが最終的な責任は運用者にあります。
- Kill Switch は想定外の損失を回避するための最後の防御策です。`KILL_FLAG_CLEAR_ON_START=1` を本番で使うのは危険です（自動で Kill Flag を消してしまうため）。
- OpenAI API を使う処理は外部通信に依存し、失敗時はフェイルセーフでスコア 0 やスキップ動作を行うよう設計されていますが、API 利用料やレート制限には留意してください。
- データファイル（DB / PID / flag / logs）は適切にバックアップ・権限管理してください。

---

## 開発者向け補足

- DuckDB 接続を使うモジュールは SQL と Python を組み合わせて高速な分析処理を行います。prices_daily / raw_financials / raw_news 等のテーブルが前提です。
- ポートフォリオ・ポジションサイジングは純粋関数として実装されており、単体テストしやすい設計です。
- ロギングは全モジュールで統一セットアップを呼ぶことを想定しており、`setup_logging(app_name=...)` を一貫して使ってください。

---

この README は現在のソースコード（src/kabusys 以下）に基づいて作成しています。追加の操作方法や運用ルールが必要であれば、どの項目を拡張したいか教えてください。