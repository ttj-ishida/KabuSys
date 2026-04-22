# KabuSys

日本株向け自動売買システムのパッケージ実装（README）。  
以下はこのリポジトリの主要モジュール・起動方法・設定手順・ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は、日本株の自動売買を目的とした複合的なシステムです。  
主な機能は以下のカテゴリに分かれます:

- 実行エンジン (ExecutionEngine)：ブローカ API と連携して注文を発行・管理
- 監視系 (Monitoring)：システム稼働状況や注文状態、リスク指標の定期チェックとログ記録
- ポートフォリオ構築：銘柄選定、重み算出、ポジションサイズ決定、セクター制約などの純粋関数群
- リサーチ / ファクター計算：DuckDB 上の価格・財務データから各種ファクターを計算
- AI（ニュース NLP / レジーム判定）：OpenAI を利用したニュースセンチメント評価と市況レジーム判定
- ユーティリティ：ログ設定、プロセス優先度設定、設定ウィザード、設定検証ツール 等
- 開発/運用ツール：Paper Trading 検証レポート生成など

設計方針として、DB（SQLite / DuckDB）とロギングを中心にフェイルセーフを重視し、ペーパートレードと本番を分離できる構成になっています。

---

## 機能一覧（抜粋）

- ExecutionEngine（発注・約定管理、リスク管理、再調整機能）
- MonitoringEngine（SystemMonitor / TradeMonitor / RiskMonitor の束ね）
- Kill Switch（条件発動で data/kill.flag を書き込み、ExecutionEngine を停止）
- Monitoring DB（SQLite）初期化・永続化（system_status / trade_logs / positions / risk_logs / dashboard）
- Paper Trading モード：MockBrokerClient を使用し、別 SQLite（デフォルト data/paper_trading.db）へ記録
- ログ設定ユーティリティ：stdout と日次ローテーションファイル（logs/<app>.log）
- Process priority / CPU affinity 設定ユーティリティ（psutil ベース）
- DuckDB を用いたファクター計算（momentum / volatility / value 等）
- OpenAI を使ったニュースセンチメント集約（ai.news_nlp）とレジーム判定（ai.regime_detector）
- 設定ウィザード（python -m kabusys.config_setup）
- 環境/設定検証（python -m kabusys.validate_config）
- Paper Trading 検証レポート生成ツール（python -m kabusys.tools.paper_verification_report）

---

## 必要条件（想定）

- Python 3.10+
- SQLite（標準ライブラリ）
- pip install で以下パッケージ等が必要
  - duckdb
  - psutil
  - openai
  - PyYAML（config ファイル検証時に任意）
- 任意: systemd / cron / Supervisor 等でプロセス管理

（プロジェクトに requirements.txt がある場合はそちらを使用してください）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリに移動
   - 例: git clone ... && cd <repo>

2. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate

3. 依存パッケージのインストール
   - pip install duckdb psutil openai
   - 開発・検証用: pip install PyYAML

   （requirements.txt があれば pip install -r requirements.txt を実行）

4. .env を作成
   - 対話型ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - または手動でプロジェクトルートに .env を作成し、最低限以下を設定：
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - KABUSYS_ENV=development|paper_trading|live
     - OPENAI_API_KEY=... （AI 機能を使う場合）
     - 他: DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / LOG_LEVEL 等

   自動ロード: config.py はプロジェクトルートの .env を自動で読み込みます（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

5. 設定検証
   - python -m kabusys.validate_config
   - 問題がある場合は出力される WARNING / ERROR に従って修正

6. 初期データディレクトリ作成（必要に応じて）
   - デフォルト DB 等は data/ 配下を想定します。logs/ も作成されますが、logging_setup が自動作成します。

---

## 使い方（主な起動方法）

- 監視ループを起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き（デフォルト 60）
  - 監視は Settings.sqlite_path（デフォルト data/monitoring.db）を使用（monitoring は環境に関係なく本番 sqlite_path を参照）

- 実行エンジンを起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録し、本番 DB と完全に分離されます
  - 実行中は data/execution.pid が作成されます
  - data/stop_requested.flag を置くと起動済みループが検知して停止します

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict をつけると WARNING も失敗扱い（exit 1）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD（開始日）
    - --to YYYY-MM-DD（終了日）
    - --db PATH（SQLite DB パスを直接指定）

---

## 停止 / Kill Switch / フラグ管理

- 停止フラグでの終了:
  - data/stop_requested.flag を作成すると run_monitoring や run_execution が検知して順次終了します（冪等に処理）。
- Kill Switch（リスクトリガ）:
  - KillSwitch コンポーネントが条件を満たすと data/kill.flag を書き、ExecutionEngine の停止を誘導します。
  - Settings.kill_flag_clear_on_start が "1" に設定されていると起動時に kill.flag を自動クリアします（本番では "0" 推奨）。
- PID ファイル:
  - 実行エンジンは data/execution.pid（デフォルト）に PID を書きます。

---

## ログ

- ログは以下の2箇所へ出力されます:
  - 標準出力（stdout）: コンソール監視・デバッグ用
  - 日次ローテートファイル: logs/<app_name>.log（デフォルト）
- 環境変数 LOG_DIR でログディレクトリを上書きできます。ログ保持日数は 30 日。

ログのセットアップは kabusys.utils.logging_setup.setup_logging(app_name="...") で統一されます。

---

## データベース

- DuckDB: 分析用データベース（デフォルト data/kabusys.duckdb）
- SQLite（監視）: 監視ログ用（デフォルト data/monitoring.db） — monitoring DB スキーマは init_monitoring_db() により初期化される
- SQLite（ペーパートレード）: PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用して本番データと分離可能

監視 DB の主なテーブル:
- system_status
- trade_logs
- positions
- risk_logs
- dashboard

monitoring_db.py はテーブル作成・マイグレーション（列追加）と基本的な読み書きを提供します。

---

## 開発者向けメモ / 設計上の注意

- .env 自動ロード:
  - config.py はプロジェクトルートを .git または pyproject.toml を基準に探索し .env/.env.local を読み込みます。
  - テストなどで自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を用いて実行履歴を paper_trading.db に書きます（本番 DB と分離）。
  - PAPER_FILL_MODE（instant/partial/never/reject）で模擬約定挙動を制御します。
- AI モジュール:
  - ai.news_nlp と ai.regime_detector は OpenAI API（gpt-4o-mini を想定）を利用します。API キーは OPENAI_API_KEY または関数引数で渡してください。
  - API 呼び出しはリトライやフォールバック（失敗時は安全側の値）を実装しています。
- プロセス優先度:
  - run_monitoring/run_execution 起動時に set_process_priority("high") を実行します。psutil の権限不足時はワーニングでスキップされます。
- テスト / CI:
  - AI 呼び出し箇所は _call_openai_api をパッチしてモック可能です（単体テスト対応）。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 配下の主要ファイル・ディレクトリと説明です（本 README は配布コードのスナップショットに基づく）:

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン情報
  - config.py — 環境変数 / 設定取得ロジック（Settings クラス）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py — ログ初期化ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite 監視 DB の初期化・アクセスラッパ
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス生存監視
    - risk_monitor.py — ドローダウン・ポジション数監視
    - trade_monitor.py — （注文監視ロジック, 別ファイル）
    - monitoring_engine.py — 各 Monitor を束ねて定期実行
    - kill_switch.py — kill.flag 制御
    - alert_manager.py — （通知管理, 別ファイル）
  - execution/
    - execution_engine.py — ExecutionEngine・EngineConfig（別ファイル）
    - broker_factory.py — BrokerClientFactory（別ファイル）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 発注/リスク関連
  - portfolio/
    - portfolio_builder.py — 候補選定・重みづけ
    - position_sizing.py — 株数決定・資金スケーリング
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — momentum / volatility / value 等の計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC /統計サマリ
  - ai/
    - news_nlp.py — ニュースを LLM でスコア化して ai_scores に書き込む
    - regime_detector.py — レジーム判定（MA + マクロセンチメント）
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成スクリプト
  - data/ （実行時に作成される想定）
    - execution.pid, stop_requested.flag, kill.flag, monitoring.db, paper_trading.db など

（上記は主要ファイルのみ抜粋。実際のリポジトリにはさらに細分化されたモジュールや補助スクリプトが含まれる可能性があります。）

---

## 例：よく使うコマンド

- .env を対話式で作成
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- 実行エンジン起動
  - python -m kabusys.run_execution
- 監視ループ起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10

---

## トラブルシューティング / 注意点

- 環境変数不足は validate_config で早期検出できます。必須の環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を確認してください。
- OpenAI を使用する機能は API キー（OPENAI_API_KEY）が必要です。API 呼び出しは課金対象となるためテストではモックすることを推奨します。
- run_monitoring は監視用 SQLite を必ず本番 sqlite_path で開きます（設定上の分離を意図）。
- run_execution は KABUSYS_ENV が paper_trading のとき別 DB に記録します。
- ログディレクトリの作成に失敗しても stdout ログは出力されます（ファイル出力はスキップされるためログ確認に注意）。

---

以上がこのコードベースの主要な README 内容です。必要があれば次の内容を追加できます：
- requirements.txt に対応した具体的なインストール手順
- 各 API（broker）や ExecutionEngine の詳細な設定例
- DB スキーマの完全な説明（SQL 定義）
- サンプル .env.example ファイル

どの情報を追加したいか教えてください。