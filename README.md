# KabuSys

日本株向け自動売買システムのモジュール群です。  
本リポジトリはトレード実行エンジン、監視・アラート、ポートフォリオ構築、リサーチ（ファクター計算）やAI（ニュースセンチメント／レジーム判定）などを含む実装の集合体です。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の機能を持つモジュール式の自動売買基盤です。

- ExecutionEngine: 発注・注文管理・リスク管理・再調整（reconciler）を行う実行エンジン
- Monitoring: システム稼働状態・注文ログ・リスク監視を行い、Kill Switch（停止フラグ）やアラートを発行
- Portfolio Construction: 候補選定、重み付け、ポジションサイズ計算、セクター制約などの純粋関数群
- Research: DuckDB を使ったファクター計算（Momentum / Value / Volatility 等）、将来リターン・IC計算
- AI モジュール: ニュースを LLM（OpenAI）で評価してスコアを生成（news_nlp）、および市場レジーム判定（regime_detector）
- ユーティリティ: ロギング、プロセス優先度設定、設定ウィザード・検証ツール、運用向けツール（Paper Trading 検証レポート）

設計方針の一部:
- 本番 DB（monitoring.sqlite 等）とペーパートレード DB を分離
- DuckDB を分析用途（prices_daily, raw_financials 等）で使用
- datetime.today()/date.today() に対するルックアヘッドに注意した設計（多くの関数は引数で日付を受け取る）
- フェイルセーフ（API失敗やデータ欠損時に例外で全停止させない）

---

## 機能一覧（主なもの）

- 環境設定ウィザード: `python -m kabusys.config_setup` で `.env` を対話式に生成
- 設定検証: `python -m kabusys.validate_config`（--strict で警告を FAIL 扱い）
- 実行エンジン起動: `python -m kabusys.run_execution`
  - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、ペーパートレード用 DB に記録
  - 実行中は `data/execution.pid` に PID を書く（停止フラグで制御）
- 監視プロセス起動: `python -m kabusys.run_monitoring`
  - ポーリングで System / Trade / Risk チェックを実行し、kill.flag の生成・通知を行う
  - 環境変数 `MONITOR_POLL_INTERVAL` で間隔を上書き可能（デフォルト 60 秒）
  - 監視は環境に関わらず本番 sqlite_path を使用（重要）
- Paper Trading 検証レポート: `python -m kabusys.tools.paper_verification_report`
- AI:
  - ニューススコアリング: `kabusys.ai.news_nlp.score_news`（OpenAI API を使用）
  - レジーム判定: `kabusys.ai.regime_detector.score_regime`（OpenAI と DuckDB を利用）
- ポートフォリオ関連: 候補選定 / 重み計算 / ポジションサイズ計算 / セクターキャップ適用
- ログ設定: `kabusys.utils.logging_setup.setup_logging`（stdout + 日次ローテーションファイル出力）
- プロセス優先度・CPU affinity: `kabusys.utils.process_priority`

---

## セットアップ手順（開発・運用共通）

1. リポジトリをクローンし、Python 仮想環境を作成・有効化します。

   ```
   git clone <repository-url>
   cd <project-root>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. 依存パッケージをインストールします（例: pip）。主要な依存例:

   - duckdb
   - psutil
   - openai
   - PyYAML（設定検証で YAML を検証したい場合）
   - そのほかプロジェクト固有の依存があれば requirements.txt に従ってください。

   例:
   ```
   pip install duckdb psutil openai PyYAML
   ```

3. 初期ディレクトリ作成:

   ```
   mkdir -p data logs
   ```

4. 環境変数を設定します。対話式で `.env` を作るには:

   ```
   python -m kabusys.config_setup
   ```

   `.env` の主な設定例（config_setup が生成する項目の抜粋）:
   ```
   KABUSYS_ENV=development             # development | paper_trading | live
   JQUANTS_REFRESH_TOKEN=your_token
   KABU_API_PASSWORD=your_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   LOG_LEVEL=INFO
   KILL_FLAG_CLEAR_ON_START=0
   PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   PAPER_FILL_MODE=instant            # instant|partial|never|reject
   ```

5. 設定を検証:

   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict
   ```

6. 初回起動前に DB 用ディレクトリやファイルを配置すると安心です（必要に応じて）。起動スクリプトは不足するディレクトリを自動作成する場合があります。

---

## 使い方（主要コマンド）

- 実行エンジンを起動（本番 or paper_trading は KABUSYS_ENV で切替）:

  ```
  # 既に .env で KABUSYS_ENV を設定している前提
  python -m kabusys.run_execution
  ```

  実行の挙動:
  - プロセス優先度を "high" に試行して設定
  - settings に応じて本番 DB または paper_trading 用 DB に接続
  - BrokerClientFactory によって実ブローカー or モックを生成
  - Engine は別スレッドで run_session を開始する（メインスレッドは stop フラグの監視）
  - 停止方法: プロジェクトルートの `data/stop_requested.flag` を作成すると安全に停止

- 監視プロセスを起動:

  ```
  python -m kabusys.run_monitoring
  ```

  オプション/環境:
  - MONITOR_POLL_INTERVAL（秒）でポーリング間隔上書き（デフォルト 60 秒）
  - 監視プロセスは常に本番の sqlite_path を使用します（KABUSYS_ENV に関係なく）
  - 監視の停止: `data/stop_requested.flag` を作成

- 環境設定ウィザード:

  ```
  python -m kabusys.config_setup
  ```

- 設定検証:

  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成:

  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または環境変数で DB を指定:
  PAPER_TRADING_SQLITE_PATH=data/paper_trading.db python -m kabusys.tools.paper_verification_report --from 2026-04-01
  ```

- AI スコアリング（プログラムから呼ぶ）:
  - ニューススコアリング:
    ```py
    from kabusys.ai.news_nlp import score_news
    # conn: duckdb connection, target_date: datetime.date, api_key: str | None
    score_news(conn, target_date, api_key="xxx")
    ```
  - レジーム判定:
    ```py
    from kabusys.ai import regime_detector  # 直接 import して利用
    regime_detector.score_regime(conn, target_date, api_key="xxx")
    ```

- ログ:
  - デフォルトで stdout に出力され、ファイルは `logs/<app_name>.log` に日次ローテーションで保存されます。
  - ログ関連は `kabusys.utils.logging_setup.setup_logging` で制御可能（環境変数 `LOG_DIR`, `LOG_LEVEL` が利用される）。

---

## 運用上のポイント

- 停止制御:
  - ExecutionEngine / Monitoring はプロジェクトルート下の `data/stop_requested.flag` の存在を監視し、あれば安全に停止します。
  - Kill Switch（`data/kill.flag`）は RiskMonitor や KillSwitch クラスによって書き込まれ、ExecutionEngine 側での格納・停止トリガーに使われます。`.env` の `KILL_FLAG_CLEAR_ON_START` を `1` にすると起動時に自動クリアしますが、本番では `0` を推奨します。
- データベース:
  - DuckDB: 分析用（prices_daily, raw_financials 等）
  - SQLite (monitoring.db): 監視ログ・trade_logs・positions・risk_logs・dashboard 等
  - paper_trading 用 SQLite（分離）: `PAPER_TRADING_SQLITE_PATH`（paper_trading 環境時に使用）
- モックブローカー:
  - `KABUSYS_ENV=paper_trading` のときは MockBrokerClient を使用して発注をシミュレート（本番口座と完全分離）
- OpenAI:
  - ニュースNLP・レジーム判定は OpenAI を利用します。実行前に `OPENAI_API_KEY` を設定してください（または関数呼び出し時に引数で渡す）。
  - API のエラーはリトライやフォールバック（スコア=0）を行う設計です。

---

## ディレクトリ構成（主要ファイル）

概略:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（自動 .env ロード含む）
  - config_setup.py          — 対話式 .env ウィザード
  - validate_config.py       — 起動前チェック CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py        # (trade 関連監視ロジック)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py        # (アラート送信ロジック)
  - execution/                # ExecutionEngine 本体・OrderManager 等
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
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
  - monitoring/               # 上述の monitoring 配下（再掲）
- data/                      — 実行時データファイル（DB, pid, flags）を置く想定
  - monitoring.db (デフォルト)
  - paper_trading.db (ペーパートレード用)
  - execution.pid
  - stop_requested.flag
  - kill.flag
- logs/                      — ログファイル（apps のログがここに日次で出る）

（実際のリポジトリにあるファイル群を簡潔化して記載しています。詳細はソースを参照してください）

---

## よく使う環境変数（抜粋）

- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: J-Quants API 用
- KABU_API_PASSWORD: kabuステーション API 用パスワード
- KABU_API_BASE_URL: kabuステーション API エンドポイント（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite のパス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ保存ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL: 監視のポーリング間隔（秒、run_monitoring 用）

---

## 開発・拡張のヒント

- DuckDB のスキーマ（prices_daily / raw_financials / raw_news 等）に基づきリサーチ・AI モジュールは実装されているため、分析データを投入すれば即座に機能を試せます。
- AI モジュールは OpenAI を前提に作られているが、API 呼び出し部分は内部関数に集約されており、テスト時はパッチして差し替えられるよう設計されています（ユニットテストを容易にする工夫）。
- 設定ファイル（config/*.yaml）を用いたパラメータ管理を想定したインフラがあります。`python -m kabusys.validate_config` はこれらの存在と妥当性をチェックします。

---

README は以上です。リポジトリ内の各モジュールについてより詳細な使用例や設計ドキュメント（PortfolioConstruction.md、StrategyModel.md 等）があれば合わせて参照してください。動作確認・運用前に必ず `python -m kabusys.validate_config` を実行して設定をチェックすることを推奨します。