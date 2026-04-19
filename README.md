# KabuSys

日本株自動売買システムの Python コードベース向け README（日本語）

概要、主な機能、セットアップ手順、使い方、主要ディレクトリ構成をまとめています。

---

## プロジェクト概要

KabuSys は日本株の自動売買・研究・監視を行うためのモジュール群です。  
主な目的は以下です。

- シグナル生成・ポートフォリオ構築・ポジションサイズ決定（portfolio）
- 発注エンジン（ExecutionEngine）とブローカー抽象（本番 / ペーパートレードの分離）
- システム監視（SystemMonitor / MonitoringEngine）と Kill Switch（停止フラグ）
- DuckDB を用いたリサーチ・ファクター計算（research）
- ニュースの NLP による銘柄スコアリング（OpenAI を利用する ai モジュール）
- 運用支援ツール（設定ウィザード、設定検証、ペーパートレード検証レポート）

設計方針としては「運用での安全性（フェイルセーフ）」「ルックアヘッドバイアス回避」「本番とペーパーの分離」を重視しています。

---

## 主な機能一覧

- Execution
  - 実際の発注ロジックを持つ `ExecutionEngine`（run_execution.py から起動）
  - ペーパートレード時は MockBrokerClient を使い、DB は `data/paper_trading.db`（分離）
  - リスク管理 (RiskManager)、オーダー管理、照合（Reconciler）等を備える
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる `MonitoringEngine`
  - system_status / trade_logs / risk_logs / positions / dashboard を永続化する SQLite 層
  - Kill Switch による停止フラグ（data/kill.flag）書き込み
  - `MONITOR_POLL_INTERVAL` 環境変数によるポーリング間隔変更（デフォルト 60 秒）
- Portfolio
  - 候補選定、重み算出（等金額・スコア加重）、ポジションサイズ計算（単元丸め、集約キャップ）
  - セクターキャップ、レジーム乗数などのリスク調整
- Research
  - DuckDB 上でファクター計算（momentum, volatility, value）
  - 特徴量探索・将来リターン計算・IC（Information Coefficient）算出
- AI（OpenAI）
  - ニュースを LLM で評価して銘柄ごとのスコアを ai_scores に書き込む（news_nlp）
  - 市場レジーム判定モジュール（regime_detector）
- ユーティリティ
  - 設定ウィザード（python -m kabusys.config_setup）で .env 作成支援
  - 設定検証 CLI（python -m kabusys.validate_config）
  - ペーパートレード検証レポート生成（python -m kabusys.tools.paper_verification_report）

---

## 要件（代表）

- Python 3.10+（typing 構文等を利用）
- pip パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config の YAML 検証を行う場合）
- SQLite（組み込み）
- （任意）ログ出力先用ディレクトリ書き込み権限

※ requirements.txt はリポジトリにない場合があります。必要に応じて上のパッケージを pip でインストールしてください。

例:
```
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン / 取得
2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix
   .venv\Scripts\activate     # Windows
   ```
3. 必要パッケージをインストール
   ```
   pip install duckdb psutil openai PyYAML
   ```
4. 環境変数設定（.env）
   - 対話型ウィザードで作成:
     ```
     python -m kabusys.config_setup
     ```
   - 生成後、設定を検証:
     ```
     python -m kabusys.validate_config
     # 警告も FAIL にする場合:
     python -m kabusys.validate_config --strict
     ```
   - 重要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、default: data/paper_trading.db）
     - LOG_LEVEL, LOG_DIR（ログ設定）
     - MONITOR_POLL_INTERVAL（監視ポーリング間隔の上書き）
     - PAPER_FILL_MODE（"instant" | "partial" | "never" | "reject"）

5. 必要ディレクトリ（data, logs 等）の作成は自動生成される場合が多いですが、権限等で失敗することがあるため手動作成しておくと安全です。
   ```
   mkdir -p data logs
   ```

---

## 使い方（運用例）

- ExecutionEngine を起動（本番 / 開発 / ペーパーは KABUSYS_ENV に依存）
  ```
  # 例: 開発環境
  KABUSYS_ENV=development python -m kabusys.run_execution

  # 例: ペーパートレード（Mock broker を利用し paper_db に記録）
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```
  実行時の挙動:
  - 起動時にプロセス優先度を `high` に設定（プラットフォーム依存で失敗してもログ警告）
  - ペーパートレード時は `PAPER_TRADING_SQLITE_PATH` の DB を使い、本番 DB と分離
  - `data/execution.pid` に PID を書き込む（設定に応じて変更可能）

- Monitoring を起動
  ```
  python -m kabusys.run_monitoring
  ```
  ポイント:
  - デフォルトで 60 秒間隔でポーリング。環境変数で変更可能:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - Monitoring は KABUSYS_ENV にかかわらず本番の `sqlite_path`（Settings.sqlite_path）を使用して監視テーブルを操作します。
  - 停止: プロセスを終了するか、プロジェクトルートの `data/stop_requested.flag` ファイルを作成するとループが終了します。

- Kill Switch（自動停止）
  - RiskMonitor 等が条件を満たすと `data/kill.flag` を作成します（既存なら上書きしない）。
  - ExecutionEngine は起動時・実行中にこのフラグを確認して停止します。
  - kill.flag の自動クリアは `KILL_FLAG_CLEAR_ON_START=1` で有効にできます（本番では 0 推奨）。

- ペーパートレード検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```
  - デフォルトは `PAPER_TRADING_SQLITE_PATH` 環境変数、なければ `data/paper_trading.db`
  - 稼働率・成功率・レイテンシ等の指標を出力します

- AI / ニューススコアリング（ライブラリ利用）
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY）
  - 関数: `kabusys.ai.score_news(conn, target_date, api_key=None)` を呼び出すと ai_scores テーブルに書き込みます
  - `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)` により市場レジーム判定して `market_regime` テーブルへ保存

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

---

## 主要ファイル / ディレクトリ構成

（src/kabusys 配下の主要モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / .env 自動ロード・Settings クラス
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - data/                     — データ関連（DuckDB/SQLite 用 path デフォルト: data/）
  - logs/                     — ログ出力先（デフォルト）
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - monitoring/
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_db.py
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
  - utils/
    - logging_setup.py
    - process_priority.py

（上記は代表的なファイル一覧です。細かいサブモジュールが他にも存在します）

---

## 運用上の注意 / 実装上の留意点

- DB 分離
  - ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）と監視 DB（SQLITE_PATH）を明確に分離しています。ペーパートレード時は本番 DB を汚さない設計です。
- ロギング
  - 共通の `setup_logging` を使用して stdout と日次ローテーションファイルログ（logs/<app_name>.log）を出力します。ログディレクトリが作成できない場合はファイルログはスキップしてコンソール出力のみになります。
- プロセス優先度
  - 起動スクリプトは最初にプロセス優先度を `high` に設定しようとします（プラットフォーム依存、権限不足時は警告）。
- フェイルセーフ
  - AI API の失敗や一時エラーはリトライ/フォールバック（0 値やスキップ）でフェイルセーフに処理されます。重大な DB 書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で保護されています。
- ルックアヘッドバイアス防止
  - research / ai モジュールは内部で現在時刻を直接参照しない実装方針を持ち、ターゲット日での処理を明確にしています。

---

## よく使う環境変数（一覧）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- OPENAI_API_KEY — AI 機能使用時
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
- LOG_LEVEL — default: INFO
- LOG_DIR — default: logs/
- PID_FILE_PATH — default: data/execution.pid
- KILL_FLAG_PATH — default: data/kill.flag
- KILL_FLAG_CLEAR_ON_START — "0" or "1"
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒）
- PAPER_FILL_MODE — ペーパートレードの約定挙動（instant | partial | never | reject）

---

## トラブルシューティング（簡易）

- .env が読み込まれない
  - プロジェクトルート（.git または pyproject.toml）を認識できないと自動ロードをスキップします。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定していると自動ロードは行われません。`python -m kabusys.config_setup` を利用して .env を作成してください。
- ログファイルが生成されない
  - 権限やディレクトリ作成エラーが起きるとファイル出力は無効化され、コンソールのみになります。`LOG_DIR` を確認して書き込み権限を付与してください。
- 実行がすぐ停止する / 起動しない
  - `data/stop_requested.flag` や `data/kill.flag` が残っている可能性があります。目的に応じて削除してください（kill.flag は慎重に扱うこと）。

---

必要に応じて README に追記します。特定のコマンド出力例、環境変数テンプレート（.env.example）や requirements.txt を追加したい場合はその旨を教えてください。