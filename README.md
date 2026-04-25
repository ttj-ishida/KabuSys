# KabuSys

日本株向け自動売買システム（パッケージ化されたライブラリ兼実行スクリプト群）

このREADME はリポジトリ内の主要モジュールと、開発 / 実行に必要な手順・使い方をまとめたものです。

注意: 本ドキュメントはコードベースの実装から生成しています。実際に本番で運用する際は .env や各種設定ファイルを慎重に確認してください。

---

## プロジェクト概要

KabuSys は日本株自動売買のためのシステム群で、主な機能は以下です。

- シグナル → ポートフォリオ構築 → 発注までの Execution Engine（発注ロジックは execution パッケージ）
- 監視基盤（System / Trade / Risk の定期チェック、Kill Switch）
- ポートフォリオ構築ユーティリティ（候補選定・重み付け・ポジションサイズ計算）
- リサーチ用ファクター計算（DuckDB を用いたファクター計算）
- AI（OpenAI）を用いたニュースの NLP スコアリングや市場レジーム判定
- Paper Trading 用の検証ツール（レポート生成）
- 環境設定ウィザードおよび設定検証ツール

主要な設計方針として
- 本番用 DB と paper_trading を明確に分離
- ルックアヘッドバイアス防止（date.today() の多用回避など）
- フェイルセーフ（API 失敗・DB エラー時に致命的障害を招かない設計）
などが採用されています。

---

## 機能一覧

- 実行関連
  - run_execution: ExecutionEngine の起動スクリプト。KABUSYS_ENV により paper_trading モードを切替
  - paper_trading は MockBroker を使用し専用 DB（デフォルト: data/paper_trading.db）を使用

- 監視関連
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔指定）
  - MonitoringEngine: System/Trade/Risk 各モニタを束ねアラート・Kill Switch 判定を行う
  - MonitoringDB: SQLite ベースの監視ログ永続化（system_status, trade_logs, positions, risk_logs, dashboard）

- リスク管理 / KillSwitch
  - RiskMonitor: ドローダウンやポジション上限の監視とログ出力
  - KillSwitch: 条件に応じて data/kill.flag を書き込みエンジン停止を誘発

- ポートフォリオ構築
  - 候補選定、等分配・スコア加重配分、リスクに応じた資金割当（単元丸め等）

- リサーチ
  - factor_research: Momentum / Value / Volatility 等のファクター計算（DuckDB）
  - feature_exploration: 将来リターン、IC（Information Coefficient）等の統計解析ユーティリティ

- AI
  - news_nlp: raw_news を OpenAI で解析し ai_scores に書き込む（batch, retry, validation）
  - regime_detector: ETF 指標 + マクロニュースで市場レジームを判定して保存

- ユーティリティ
  - config_setup: 対話式 .env 生成ウィザード
  - validate_config: 起動前チェック（必須環境変数・config YAML 確認等）
  - tools.paper_verification_report: Paper Trading の検証レポート生成

- ロギング / プロセス制御
  - utils.logging_setup: stdout + 日次ローテートファイルの統一ログ設定
  - utils.process_priority: OS（Windows/Linux/Mac）を吸収したプロセス優先度設定、CPU affinity

---

## 必要要件（推奨）

- Python 3.10 以上（PEP 604 の合併型アノテーション等が使用されているため）
- 主要依存パッケージ（抜粋）
  - duckdb
  - psutil
  - openai (AI 機能利用時)
  - PyYAML（validate_config が YAML パースを行う場合に任意で必要）

※ 実際の requirements.txt / poetry 設定がある場合はそちらを使用してください。

---

## セットアップ手順

1. リポジトリをクローン、作業ディレクトリへ移動
   ```
   git clone <repo>
   cd <repo>
   ```

2. 仮想環境を作成して依存パッケージをインストール
   ```
   python -m venv .venv
   source .venv/bin/activate      # Windows: .venv\Scripts\activate
   pip install -U pip
   pip install duckdb psutil openai
   # 任意: pip install PyYAML
   ```

3. .env を作成
   - 対話式ウィザードを使う（推奨）
     ```
     python -m kabusys.config_setup
     ```
   - もしくは手動で .env を用意（必須キーは下記参照）

4. 設定検証
   ```
   python -m kabusys.validate_config
   # 警告を FAIL 扱いにする場合
   python -m kabusys.validate_config --strict
   ```

必須の環境変数（最低限）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要な任意 / 重要な環境変数
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB, デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB, デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI 機能利用時）
- LOG_LEVEL（INFO / DEBUG 等）
- MONITOR_POLL_INTERVAL（run_monitoring の秒間隔）
- PAPER_FILL_MODE（paper_trading の約定挙動: instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか。0/1）

.env は絶対に Git にコミットしないでください。

---

## 使い方（主要コマンド）

- 環境ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- ExecutionEngine 起動（実際に注文を送る／あるいは paper_trading モードで模擬）
  - paper_trading モード例:
    ```
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
  - live / development も同様に設定して起動

  実行挙動:
  - paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録（本番 DB とは分離）
  - 起動時に data/stop_requested.flag が既に存在する場合は起動せず終了
  - 実行中は data/execution.pid に PID を書きます

- Monitoring 起動
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - 監視は環境にかかわらず設定されている sqlite_path（監視 DB）を使用します
  - graceful stop: プロジェクトルート/data/stop_requested.flag を作成するとループが停止します

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB 指定:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI 機能（ニュース NLP / レジーム判定）
  - 実行例（利用箇所はライブラリ関数を呼び出す形が想定）
  - OPENAI_API_KEY を環境変数に設定してください

---

## 停止とフラグ

- run_execution/run_monitoring の停止・制御
  - 順次停止を要求するフラグ: data/stop_requested.flag（run_* スクリプトはこのファイルの存在を検知して終了）
  - Kill Switch（自動停止）: data/kill.flag（KillSwitch が条件検出時に書き込む）
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していると kill.flag を自動でクリアする設定になるため注意（本番では 0 推奨）

---

## ディレクトリ構成（抜粋）

リポジトリの主要なファイル / ディレクトリ構成（src 以下を中心に）

- src/kabusys/
  - __init__.py
  - config.py             — 環境変数・設定管理
  - config_setup.py       — .env 対話ウィザード
  - validate_config.py    — 設定検証 CLI
  - run_execution.py      — ExecutionEngine 起動スクリプト
  - run_monitoring.py     — Monitoring 起動スクリプト

  - ai/
    - news_nlp.py         — ニュース NLP スコアリング
    - regime_detector.py  — 市場レジーム判定
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
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py

- data/    （デフォルトの DB・フラグ保存場所）
- logs/    （デフォルトのログ出力先）

---

## ログ

- デフォルトで stdout（StreamHandler）とファイル（logs/<app_name>.log）に出力します。ファイルは日次ローテーション（30日分保持）。
- LOG_DIR 環境変数、または setup_logging の引数で変更可能。
- LOG_LEVEL は環境変数 LOG_LEVEL または .env で指定（デフォルト INFO）。

---

## 開発上の注意点 / ベストプラクティス

- .env を Git にコミットしないこと（秘密情報が含まれる）
- 本番環境（KABUSYS_ENV=live）では kill_flag_clear_on_start を 0 にすることを推奨
- OpenAI や外部 API のキーは環境変数で管理し、アクセスリミットや料金に注意する
- validate_config を起動前に実行して設定ミスを事前検出する
- paper_trading を利用することで本番 DB やブローカーへの影響を避けて検証可能

---

この README はコードベースの要素に基づいて作成しています。実運用前は config/*.yaml（存在する場合）や環境固有の設定、依存関係を必ず確認してください。質問や README に追加してほしい項目があれば教えてください。