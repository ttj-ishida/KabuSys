# KabuSys

日本株向け自動売買システムのリポジトリ（ライブラリ + 起動スクリプト群）。  
このドキュメントはコードベースの概要、機能、セットアップ方法、使い方、ディレクトリ構成をまとめた README.md です。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の機能群を提供するシステムです。

- データパイプライン / DuckDB を用いた分析向けテーブル参照
- ファクター計算、特徴量探索、ポートフォリオ構築（純粋関数群）
- ExecutionEngine（発注・注文管理・リスク管理）と、そのための BrokerFactory
- Monitoring（システム状態・注文状態・リスク監視）と Kill Switch
- AI を使ったニュースセンチメント評価（OpenAI）およびレジーム判定
- ペーパートレード用の分離された DB と検証ツール

設計上のポイント：
- 本番とペーパートレードは DB を分離（paper_trading 用 DB を使用）
- .env による環境変数で設定を管理（対話式ウィザードあり）
- ログは stdout とローテートファイル（logs/*.log）で出力
- フラグファイル（data/kill.flag / stop_requested.flag）によるプロセス制御

---

## 主な機能一覧

- run_execution.py: ExecutionEngine を起動（実取引 or ペーパートレード切替）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録
- run_monitoring.py: SystemMonitor をポーリング起動（MONITOR_POLL_INTERVAL で間隔制御）
- monitoring:
  - system_monitor: CPU/メモリ/ディスク/プロセスの監視、データ鮮度チェック
  - trade_monitor: 注文の滞留/約定異常チェック（trade_logs を参照）
  - risk_monitor: ドローダウン・ポジション数の監視、dashboard 管理
  - kill_switch: しきい値越えで data/kill.flag を作成して Execution を停止
  - monitoring_db: SQLite に監視ログを永続化（テーブル作成・マイグレーション含む）
- portfolio: 銘柄選定、重み計算、ポジションサイズ決定、セクター制限、レジーム乗数
- research: ファクター計算（Momentum/Value/Volatility）、Forward returns、IC 計算
- ai:
  - news_nlp: raw_news を OpenAI に送り銘柄別センチメントを ai_scores に保存
  - regime_detector: ETF（1321）MA200 とマクロニュースの LLM センチメントを合成して市場レジーム判定
- tools/paper_verification_report.py: ペーパートレード DB から検証レポートを生成
- 設定ユーティリティ:
  - config_setup.py: .env を対話式で作成/更新するウィザード
  - validate_config.py: .env と config/*.yaml の事前検証 CLI

---

## セットアップ手順

前提
- Python 3.9+ を想定（duckdb / psutil 等の互換性を確認してください）
- OS によりプロセス優先度設定で権限が必要な場合があります

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # POSIX
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   - 最低限必要なパッケージ（例）:
     ```bash
     pip install duckdb psutil openai
     ```
   - 追加で便利なもの:
     - PyYAML（`validate_config.py` が YAML の構文検証を行う場合に必要）
       ```bash
       pip install pyyaml
       ```

   ※ requirements.txt があればそちらを使ってください（本例では明示ファイルがない想定）。

4. .env を用意
   - 最初に対話式ウィザードを使うことを推奨：
     ```bash
     python -m kabusys.config_setup
     ```
   - 生成後、設定内容を検証：
     ```bash
     python -m kabusys.validate_config
     # 警告も FAIL 扱いにする場合:
     python -m kabusys.validate_config --strict
     ```

5. データディレクトリの準備（自動作成される場合もありますが確認推奨）
   - デフォルト DB / ログ / フラグのパス：
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - logs/: ログファイル保存ディレクトリ
     - data/execution.pid / data/stop_requested.flag / data/kill.flag

6. OpenAI を使う機能を利用する場合:
   - 環境変数 `OPENAI_API_KEY` を設定するか、関数呼び出し時にキーを渡してください。

---

## 使い方

ここでは主要な起動方法とオプションを例示します。

- ExecutionEngine 起動（本番 / ペーパートレード切り替えは KABUSYS_ENV に依存）
  ```bash
  # .env で KABUSYS_ENV=development|paper_trading|live を設定済み
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録し、本番 DB と分離します。
  - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
  - Execution 用の PID は data/execution.pid に書き込まれます。

- Monitoring 起動（SystemMonitor のポーリング）
  ```bash
  # 環境変数 MONITOR_POLL_INTERVAL で秒数を上書き可能（デフォルト: 60）
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  - 監視は常に本番用 sqlite_path を使用（環境にかかわらず）。
  - 停止は data/stop_requested.flag を作成することで行えます（ファイルの作成を監視して終了します）。

- ペーパートレード検証レポート
  ```bash
  # DB パスは --db で指定、指定なければ PAPER_TRADING_SQLITE_PATH 環境変数、さらに無ければ data/paper_trading.db
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

- .env の生成・更新（ウィザード）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- AI 機能（ニュース NLP / レジーム判定）
  - OpenAI API キーを環境変数 `OPENAI_API_KEY` に設定するか関数に渡す必要があります。
  - news_nlp.score_news や regime_detector.score_regime は DuckDB 接続と target_date を受け取り、DB に書き込みを行います。

- Kill Switch / Stop フラグ
  - Kill Switch は monitoring の評価で `data/kill.flag` を書き込みます（Settings.kill_flag_path で上書き可能）。
  - 人的に Execution を止めたい場合は `data/stop_requested.flag` を作成すると run_execution/run_monitoring が終了します。逆に消去すると無効化されます。
  - Execution 起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動クリアします（本番では 0 推奨）。

---

## 主要な環境変数（抜粋とデフォルト）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能を使う場合に必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- LOG_LEVEL (デフォルト: INFO)
- MONITOR_POLL_INTERVAL (run_monitoring 用、秒、デフォルト: 60)
- PAPER_FILL_MODE (paper_trading 時の fill 動作: instant|partial|never|reject、デフォルト: instant)
- KILL_FLAG_CLEAR_ON_START (0 or 1、デフォルト: 0)

詳細は `kabusys.config.Settings` の各プロパティを参照してください。

---

## ディレクトリ構成

（ソースツリーの主要ファイル / モジュールを抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                -- 環境変数 / Settings
    - config_setup.py          -- .env 対話式ウィザード
    - validate_config.py       -- 設定検証 CLI
    - run_execution.py         -- ExecutionEngine 起動スクリプト
    - run_monitoring.py        -- SystemMonitor ポーリング起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py  -- ペーパートレード検証レポート生成
    - ai/
      - __init__.py
      - news_nlp.py            -- ニュースセンチメント（OpenAI 連携）
      - regime_detector.py     -- 市場レジーム判定（AI + MA200 合成）
    - monitoring/
      - monitoring_db.py       -- SQLite 用永続化層（テーブル作成・CRUD）
      - system_monitor.py
      - trade_monitor.py       -- 注文滞留や約定異常検出（ファイル内に存在）
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py       -- 通知（LINE等）管理（コード内に想定あり）
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
      - logging_setup.py       -- ログ初期化ユーティリティ
      - process_priority.py    -- プロセス優先度 / CPU affinity 設定
      - __init__.py
    - monitoring/ (上で説明)
    - execution/ (実行エンジン関連: Engine, BrokerFactory, OrderManager 等は同階層に存在)
    - data/ (実際はプロジェクトルートの data/ に DB/flag/pid 等を置く想定)
  - その他ライブラリ / スクリプト等

補足:
- 実際の発注ロジックや BrokerClient 実装は execution/* にあります（本 README の範囲外）。
- monitoring_db.init_monitoring_db は初回起動時にテーブル作成と簡単なマイグレーションを行います。

---

## 運用上の注意・ベストプラクティス

- 本番（KABUSYS_ENV=live）では .env の内容（APIキー等）を厳重に管理し、Git にコミットしないでください。
- Kill Switch（data/kill.flag）や stop_requested.flag を用いた停止は冪等に設計されていますが、運用中の処理整合性（未処理注文など）に注意してください。
- OpenAI API 呼び出しはレート制限やエラーに対してリトライ処理が実装されていますが、APIキーの権限やコストに注意して運用してください。
- logs/ ディレクトリのローテーション設定は utils.logging_setup で日次ローテーション（30 日保持）になっています。ディスク容量に注意してください。

---

この README はリポジトリの主要機能と運用上のポイントをまとめたものです。詳細な実装や追加設定は各モジュールの docstring / ソースを参照してください。質問や追加ドキュメント（設定例、デプロイ手順、CI 設定等）が必要ならお知らせください。