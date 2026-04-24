# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ向け README（日本語）

概要、機能、セットアップ手順、使い方、ディレクトリ構成をまとめています。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買／リサーチ基盤です。  
主な機能は以下のとおりです。

- 発注エンジン（ExecutionEngine） — ブローカーに発注し、リスク管理を行う
- 監視（Monitoring） — システム状態、注文・約定、リスクを定期的に監視しアラートや Kill Switch を管理
- ポートフォリオ構築（Portfolio） — 候補選定、重み付け、株数計算、セクターキャップ等の純粋関数群
- 研究（Research） — ファクター計算、将来リターン計算、IC 等の解析ユーティリティ（DuckDB を利用）
- AI モジュール — ニュース NLP によるセンチメント（OpenAI）やレジーム判定のスコアリング
- ツール類 — ペーパートレード検証レポート生成など
- 環境ウィザード / 設定検証（.env 操作、config YAML の簡易チェック）

設計方針の一部：
- DuckDB / SQLite を用いたデータ永続化（分析・監視用）
- paper_trading（ペーパートレード）は本番 DB と完全分離
- 外部 API 呼び出し（OpenAI など）は明示的な API キー管理
- ログは統一的に設定（stdout + 日次ローテーションファイル）

---

## 機能一覧（主要コンポーネント）

- run_execution.py
  - ExecutionEngine を起動。KABUSYS_ENV によって実ブローカー／MockBroker を切り替え。
  - paper_trading モードでは data/paper_trading.db に記録。
  - プロセス優先度を高く設定し、停止フラグ（data/stop_requested.flag）で停止可能。

- run_monitoring.py
  - SystemMonitor のポーリングループを起動（デフォルト 60 秒）。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能。
  - 監視ログは SQLite（デフォルト data/monitoring.db）へ永続化。

- monitoring/
  - system_monitor, trade_monitor, risk_monitor, monitoring_engine, kill_switch, monitoring_db
  - Kill Switch（data/kill.flag）を管理し、条件に応じた停止シグナル発行。

- portfolio/
  - 候補選定（select_candidates）、重み計算、ポジションサイズ決定（calc_position_sizes）、セクター制限 等

- research/
  - ファクター計算（momentum, volatility, value）、特徴量探索（IC, forward returns）等（DuckDB 接続を受け取る）

- ai/
  - news_nlp（ニュースセンチメントの OpenAI 解析）、regime_detector（市場レジーム判定）

- tools/
  - paper_verification_report — ペーパートレードの検証レポート生成

- config_setup.py / validate_config.py
  - .env の対話式生成ウィザード、設定検証 CLI

- utils/
  - logging_setup（ログ一元設定）
  - process_priority（プロセス優先度 / CPU affinity）

---

## 必要要件（依存ライブラリ）

最低限の主な依存パッケージ例：

- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（設定ファイル検証時にあると便利）

インストール例（仮想環境推奨）:
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# requirements.txt がない場合の例:
pip install duckdb psutil openai pyyaml
```

（実際の requirements.txt はプロジェクトに合わせて作成してください）

---

## 初期セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ
2. Python 仮想環境を作成して依存をインストール
3. .env の作成（対話式ウィザード推奨）

対話式で .env を作る:
```
python -m kabusys.config_setup
```

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境（development | paper_trading | live）デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（paper_trading モード時）
- OPENAI_API_KEY — OpenAI を使う場合に設定
- LOG_LEVEL — ログレベル（DEBUG/INFO/…）

.env の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。
自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. 設定検証（任意）
```
python -m kabusys.validate_config
# 警告もエラー扱いにする場合:
python -m kabusys.validate_config --strict
```

5. ディレクトリ確認
- data/（デフォルト DB / フラグファイル等）
- logs/（ログ出力先。存在しなければ自動作成される）

---

## 使い方（起動例）

- ExecutionEngine を起動
  - 本番 / ペーパーの切り替えは KABUSYS_ENV 環境変数で制御
  - 起動:
    ```
    python -m kabusys.run_execution
    ```
  - 停止:
    - プロセスの標準的な停止（CTRL+C）
    - もしくはプロジェクトルートの data/stop_requested.flag を作成すると監視ループ / 実行ループが検知して終了します
    - Kill Switch（モニタ側からの停止要求）は data/kill.flag を作成します（ExecutionEngine は起動時にこのフラグを検出して起動を回避する設定も有り）

- Monitoring を起動
  - デフォルトのポーリング間隔は 60 秒。変更するには環境変数 MONITOR_POLL_INTERVAL を設定（秒）
  - 起動:
    ```
    python -m kabusys.run_monitoring
    ```
  - 例: 30 秒間隔で起動（シェルで）
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```

- Paper Trading 検証レポートを生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを指定する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- ログ設定
  - すべての起動スクリプトは kabusys.utils.logging_setup.setup_logging を呼び出し、stdout と logs/<app_name>.log に出力します。
  - LOG_DIR 環境変数でログディレクトリを変更可能。

- AI 機能（プログラム呼び出し）
  - OpenAI キーを設定している前提で、news_nlp.score_news や regime_detector.score_regime をプログラムから呼び出せます。
  - 例（概念）:
    ```
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, date(2026, 4, 20), api_key="sk-...")
    ```

---

## 運用上の注意 / キーファイル

- data/stop_requested.flag
  - run_execution/run_monitoring がループ内で存在をチェックし、存在した場合は安全に停止します（手動停止用フラグ）。

- data/kill.flag
  - Monitoring の KillSwitch により書かれることがある停止理由フラグ（ExecutionEngine は起動時にこのフラグを検出して起動しない等のロジックを組めます）。

- PID ファイル
  - ExecutionEngine は data/execution.pid を利用（Settings.pid_file_path で変更可能）

- Paper Trading
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に履歴を残します。本番 DB と完全分離されます。

- ログとファイルパーミッション
  - ログディレクトリや data ディレクトリは実行ユーザーが書込可能であることを確認してください。

---

## ディレクトリ構成（抜粋）

```
src/
  kabusys/
    __init__.py
    config.py
    config_setup.py
    validate_config.py
    run_execution.py
    run_monitoring.py
    utils/
      logging_setup.py
      process_priority.py
    monitoring/
      monitoring_db.py
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      monitoring_engine.py
      kill_switch.py
      alert_manager.py  # （実装ファイルは含まれる想定）
    execution/
      broker_factory.py
      execution_engine.py
      order_manager.py
      order_repository.py
      reconciler.py
      risk_manager.py
    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
    research/
      factor_research.py
      feature_exploration.py
    ai/
      news_nlp.py
      regime_detector.py
    tools/
      paper_verification_report.py
    data/         # 実行時に生成される（DB / フラグ / pid）
    logs/         # ログファイル（ログ設定で作成）
```

（上記はリポジトリの主要ファイルを抜粋したものです）

---

## よく使う環境変数（まとめ）

- KABUSYS_ENV: execution モード（development | paper_trading | live）
- JQUANTS_REFRESH_TOKEN: J-Quants API（必須）
- KABU_API_PASSWORD: kabuステーション API（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード DB（paper_trading 時）
- OPENAI_API_KEY: OpenAI を利用する場合
- LOG_LEVEL: ログレベル（例: INFO）
- LOG_DIR: ログ保存ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（1 = 有効、開発用）

---

## トラブルシューティング（短く）

- DB が作成されない / 書き込みエラー
  - data ディレクトリのパーミッションを確認。設定された SQLITE_PATH / DUCKDB_PATH の親ディレクトリが存在するか確認。

- OpenAI 関連エラー
  - OPENAI_API_KEY が正しく設定されているか、ネットワーク接続を確認。API の rate limit に注意。

- 監視が想定どおり動かない
  - MONITOR_POLL_INTERVAL の値を確認（0 以下は無効）。logs/<app>.log を確認。

---

必要に応じてこの README をプロジェクト固有の手順（デプロイ、サービス化 systemd / supervisor、CI/CD、テスト方法等）で拡張してください。質問や追加のドキュメント化が必要なら教えてください。