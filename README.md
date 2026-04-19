# KabuSys

日本株向けの自動売買 / リサーチ基盤ライブラリ（プロトタイプ）。  
このリポジトリには、注文実行エンジン、監視（Monitoring）、ポートフォリオ構築、ファクター計算、ニュースNLP（OpenAI）、各種ユーティリティが含まれています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構成するモジュール群を提供します。主な責務は次の通りです。

- ExecutionEngine：発注・リスク管理・注文管理の実行
- Monitoring：システム稼働状況・注文・リスク監視、Kill Switch（自動停止）
- Portfolio：銘柄選定、重み計算、ポジションサイズ決定、セクター制限など
- Research：ファクター計算、将来リターン計算、IC 計算など分析用ツール
- AI：OpenAI を使ったニュースセンチメント計算（ニュースNLP）、市場レジーム判定
- Tools：ペーパートレード検証レポート生成など補助ツール
- Utils：ログ設定、プロセス優先度設定、設定読み込みユーティリティ等

設計方針の一部：
- 本番 DB とペーパートレード DB を分離（KABUSYS_ENV による挙動差）
- ルックアヘッドバイアス防止設計（date.today() 等を直接参照しない等）
- フェイルセーフ：API 失敗時は安全側にフォールバックし例外でプロセスを落とさない

---

## 主な機能一覧

- 起動スクリプト
  - run_execution（ExecutionEngine 起動）
  - run_monitoring（SystemMonitor のポーリング）
- 設定関連
  - config_setup（.env 対話ウィザード）
  - validate_config（設定の静的検証）
- 監視
  - MonitoringDB（SQLite テーブル定義 / マイグレーション）
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine
  - KillSwitch（条件に応じた kill.flag 書き込み）
- 発注・リスク（Execution 側の骨組み）
  - BrokerClientFactory 等（ブローカ抽象）
  - OrderManager / Reconciler / RiskManager / ExecutionEngine（起動スクリプトから利用）
- ポートフォリオ構築
  - 銘柄選定（select_candidates）
  - 重み計算（等分・スコア加重）
  - ポジションサイズ計算（risk_based / equal / score）
  - セクターキャップ・レジーム乗数
- リサーチ
  - ファクター計算（momentum, volatility, value）
  - 特徴量探索（forward returns, IC, summary）
- AI
  - news_nlp.score_news：ニュースから銘柄別センチメント算出・ai_scores へ書込
  - regime_detector.score_regime：ETF とマクロニュースを合成して市場レジーム判定
- ツール
  - paper_verification_report：ペーパートレード検証レポート生成

---

## 要件（概略）

必須（本番的に必要な環境変数）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

推奨 / オプションの Python パッケージ（実行機能により必要）
- duckdb
- psutil
- openai
- PyYAML（validate_config の YAML 検証）
- （その他、発注先ブローカ API クライアント等）

requirements.txt がある場合はそちらを利用してください。ない場合は上のライブラリをインストールしてください。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Linux / macOS
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   - もし requirements.txt があれば：
     ```
     pip install -r requirements.txt
     ```
   - 明示的に：
     ```
     pip install duckdb psutil openai PyYAML
     ```

4. ディレクトリの準備
   - デフォルトでは以下のパスを使用します：
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - ログディレクトリ: logs/
   - 必要に応じて `data/` と `logs/` を作成できます（起動時に自動生成される場合もあります）：
     ```
     mkdir -p data logs
     ```

5. .env の作成（対話ウィザード推奨）
   ```
   python -m kabusys.config_setup
   ```
   - 対話形式で必須トークンや環境（KABUSYS_ENV）を設定できます。
   - 生成後、設定検証を実行してください：
     ```
     python -m kabusys.validate_config
     ```
     Strict モード（警告も失敗扱い）:
     ```
     python -m kabusys.validate_config --strict
     ```

6. OpenAI を使う機能を使う場合は環境変数 `OPENAI_API_KEY` を設定してください。

---

## 使い方（起動例）

- 監視プロセス起動（ポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）。
  - run_monitoring は監視用 SQLite に接続します（monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する点に注意）。

- 実行エンジン起動
  - 本番（live / development）:
    ```
    KABUSYS_ENV=live python -m kabusys.run_execution
    ```
  - ペーパートレード（MockBroker を使用し、data/paper_trading.db を使用）
    ```
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
  - 起動時に `data/stop_requested.flag` が存在すると起動せず終了します。実行中に同フラグが作られると安全に停止します。

- ペーパートレード検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - `--db` で SQLite ファイルパスを指定できます（デフォルト: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）。

- 設定ウィザード / 検証
  ```
  python -m kabusys.config_setup
  python -m kabusys.validate_config
  ```

- プログラムから AI スコアリングを呼び出す例（Python REPL またはスクリプト内）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  conn = duckdb.connect('data/kabusys.duckdb')
  cnt = score_news(conn, target_date=date(2026,4,1), api_key='sk-...')
  print("written", cnt)
  ```

  またはレジーム判定：
  ```python
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026,4,1), api_key='sk-...')
  ```

---

## 主要な環境変数

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 代表的な設定（デフォルト値）
  - KABUSYS_ENV: development | paper_trading | live（default: development）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - LOG_LEVEL: INFO
  - OPENAI_API_KEY: OpenAI を使う場合必須（api 呼び出し時に引数で渡すことも可）
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（デフォルト 60）

- Kill Switch / 制御ファイル
  - デフォルト kill flag: data/kill.flag（KillSwitch が発動するとこのファイルを書き込む）
  - 停止フラグ: data/stop_requested.flag（監視/実行ループの停止に使用）
  - PID ファイル: data/execution.pid（ExecutionEngine 起動時に使用）

---

## ロギング

- ログはルートロガーに設定され、標準出力（stdout）と日次ローテートファイル（logs/<app>.log）に出力されます。
- ログレベルは環境変数 `LOG_LEVEL` または setup_logging の引数で設定可能。
- ログディレクトリは `LOG_DIR` 環境変数、またはデフォルト `logs/`。

---

## よくある運用上の注意

- monitoring はコード上で「監視用 DB は環境にかかわらず本番 sqlite_path を使用する」実装になっています。意図的な分離が必要な場合は設定を確認してください。
- run_execution は KABUSYS_ENV=paper_trading のときに専用 DB（PAPER_TRADING_SQLITE_PATH）を使用します。ペーパートレードと本番 DB を混同しないよう注意してください。
- KillSwitch（data/kill.flag）が作られると ExecutionEngine は停止されます。起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定すると自動クリアされますが、本番では 0 を推奨します。
- validate_config は PyYAML がないと config/*.yaml の中身検証をスキップします（警告が出ます）。可能なら PyYAML をインストールしてください。

---

## ディレクトリ構成（抜粋）

（プロジェクトの `src/kabusys` 配下を抜粋）

- kabusys/
  - __init__.py
  - config.py                 — 環境変数/.env ローダー & Settings クラス
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - monitoring/
    - monitoring_db.py        — SQLite テーブル定義 / 永続化 API
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
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
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py

（そのほか、config/*.yaml、.env.example、data/、logs/ などがプロジェクトルートに存在する想定）

---

## トラブルシューティング（簡易）

- .env が読み込まれない / 値が足りない:
  - `python -m kabusys.config_setup` で作成後、`python -m kabusys.validate_config` を実行。
- "OpenAI API キーが未設定です" エラー:
  - 環境変数 `OPENAI_API_KEY` を設定するか、関数呼び出し時に `api_key` 引数を渡す。
- ログファイルが作れない（権限・パス問題）:
  - `LOG_DIR` を writable なディレクトリに設定するか、権限を確認。失敗時はコンソール出力のみで継続されます。
- psutil による優先度設定で権限エラー:
  - 非 root ユーザーだと一部操作が制限されるため警告が出ます（スキップされます）。

---

必要であれば、README にさらに以下を追加できます：
- 具体的な ExecutionEngine の設定例（risk_config / execution_config サンプル）
- CI / テストの実行方法
- 開発者向けのコーディング規約・貢献ガイド

追加希望があれば指示してください。