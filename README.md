# KabuSys

日本株向け自動売買システムのコアライブラリ群と運用ユーティリティ群です。  
このリポジトリは取引エンジン起動スクリプト、監視（Monitoring）機能、ポートフォリオ構築・リスク調整ロジック、リサーチ（ファクター計算・特徴量探索）、および AI を利用したニュース/レジーム判定モジュールを含みます。

主な設計方針
- 本番・ペーパートレードの分離（環境により使用するDBが変わります）
- ルックアヘッドバイアス防止（APIや日付の参照に注意）
- フェイルセーフ：外部API失敗時は安全側にフォールバックして継続

---

## 機能一覧

- 起動スクリプト
  - run_execution: ExecutionEngine を起動。KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、専用 DB に記録。
  - run_monitoring: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL 環境変数で間隔変更可）。

- 設定関連
  - config_setup: 対話式ウィザードで .env を作成/更新。
  - validate_config: .env と config/*.yaml の基本検証を実行。

- 監視（Monitoring）
  - MonitoringDB: SQLite に監視ログを永続化。
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine: 各種監視、Kill Switch、アラート連携ロジック。
  - KillSwitch: ドローダウンやポジション上限で停止フラグを書き込み ExecutionEngine を停止。

- 発注・実行
  - ExecutionEngine（実装ファイル群は execution パッケージ内にあり、BrokerFactory によるブローカー切替をサポート）
  - OrderRepository / OrderManager / RiskManager / Reconciler 等

- ポートフォリオ構築（純粋関数群、DB 参照なし）
  - 候補選定、等重・スコア加重配分、セクターキャップ、レジーム乗数、株数決定（単元丸め・資金スケールダウン）

- リサーチ
  - ファクター計算（momentum/value/volatility）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー

- AI（OpenAI）
  - news_nlp: ニュースを LLM でスコアリングして ai_scores に書き込み
  - regime_detector: ETF の MA200 と LLM によるマクロセンチメントを合成して market_regime を判定

- ツール
  - paper_verification_report: Paper Trading DB の検証レポートを生成（稼働率、注文成功率、レイテンシ等）

- ユーティリティ
  - logging_setup: 統一的なログ設定（stdout + 日次ローテートファイル）
  - process_priority: OS を吸収したプロセス優先度 / CPU affinity 設定ユーティリティ
  - config: .env 自動ロード、Settings クラスによる設定取得

---

## 前提 / 推奨環境

- Python 3.10 以上（typing の | 演算子等を使用）
- 推奨パッケージ（インストール推奨）
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（validate_config で YAML 中身の検証を行う場合）
- デフォルトのファイルパス（環境変数で上書き可能）
  - DuckDB: data/kabusys.duckdb
  - SQLite (監視): data/monitoring.db
  - Paper-Trade SQLite: data/paper_trading.db
  - ログディレクトリ: logs/
  - PID / flag: data/*.pid, data/kill.flag, data/stop_requested.flag

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動
   - 例: git clone ... && cd <repo>

2. Python 仮想環境を作成・アクティベート
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - Unix/macOS: source .venv/bin/activate

3. 依存パッケージをインストール
   - pip install duckdb psutil openai
   - 追加（検証や YAML を使う場合）: pip install pyyaml

4. .env を作成
   - 対話式: python -m kabusys.config_setup
   - 手動: プロジェクトルートに .env を置き、必要な環境変数を設定
     - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
     - 推奨: KABUSYS_ENV (development | paper_trading | live)
     - AI を使う場合: OPENAI_API_KEY を設定
     - その他: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START など
   - 注意: .env は機密情報を含むため Git にコミットしないでください。

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

6. データディレクトリ作成
   - 必要なら data/ および logs/ を作成（logging_setup は自動作成を試みますが、権限の関係で失敗する場合があります）。

---

## 使い方（主なコマンド）

- 環境ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - メモ:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading 用 SQLite に記録されます（settings.paper_sqlite_path）。
    - 起動前に data/kill.flag が存在する場合は起動せず終了します（kill flag による保護）。
    - 停止は data/stop_requested.flag の作成で行えます（監視プロセスなどから停止指示が可能）。

- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト 60 秒）。
  - 監視は環境に関係なく本番 sqlite_path（data/monitoring.db）を使用します。
  - 停止は data/stop_requested.flag の作成で行えます。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH を使用

- AI 関連（ライブラリ関数）
  - kabusys.ai.score_news(duckdb_conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(duckdb_conn, target_date, api_key=None)
  - OpenAI の API キーは OPENAI_API_KEY 環境変数、または関数引数で渡します。

---

## 運用上の注意

- .env は必ず秘密情報を含むため Git には置かない（config_setup のヘッダにも注意書きあり）。
- 本番環境では KABUSYS_ENV=live とし、KILL_FLAG_CLEAR_ON_START=0 を推奨（自動クリアは危険）。
- ログ: logs/<app_name>.log に日次ローテートで保存（30 日保持）。ログディレクトリ作成に失敗するとコンソールのみになります。
- Kill Switch: RiskMonitor 等の判定により data/kill.flag が書き込まれると ExecutionEngine 側で停止します。KillSwitch は冪等にファイルを書きます。
- paper_trading 環境は本番 DB と完全分離されます（PAPER_TRADING_SQLITE_PATH を使用）。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/.env ロードと Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前の設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite 監視DB 層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py       (アラート送信ロジック等)
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
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

（上記は主要ファイルの抜粋です。詳細はソースツリーを参照してください。）

---

## 参考: 主要な環境変数一覧

- 必須（最低限）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境選択
  - KABUSYS_ENV: development | paper_trading | live

- DB / ログ
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
  - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
  - LOG_DIR

- 監視 / 停止
  - MONITOR_POLL_INTERVAL (run_monitoring のポーリング秒数)
  - KILL_FLAG_CLEAR_ON_START (起動時に kill.flag を自動クリアするか: 0/1)
  - PID_FILE_PATH / KILL_FLAG_PATH（Settings 経由で上書き可能）

- AI
  - OPENAI_API_KEY

（詳細な説明は src/kabusys/config.py を参照してください）

---

## 貢献 / 開発メモ

- テスト: 各モジュールは純粋関数化あるいは外部呼び出しを切り離す設計でテストがしやすくなっています。AI 呼び出しは _call_openai_api をモックすることでテスト可能です。
- マイグレーション: monitoring_db.init_monitoring_db は既存スキーマへ安全にカラム追加する簡易マイグレーションを実装しています。
- ログ/監視: run_* スクリプトは起動時にプロセス優先度を "high" に設定し、統一的なログ設定を行います。

---

不明点や README に追加してほしい情報（例: 起動フロー図、設定例テンプレート、よくあるトラブルシュート）などがあれば教えてください。必要に応じて追記します。