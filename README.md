# KabuSys

日本株自動売買システム（パッケージ内部用 README）

このリポジトリは KabuSys と呼ばれる日本株向けの自動売買・リサーチ・監視ツール群の実装です。  
以下はコードベース（src/kabusys）に基づく概要、機能、セットアップ手順、使い方、ディレクトリ構成の説明です。

---

## プロジェクト概要

KabuSys は以下の機能を持つモジュール群から構成されています。

- ExecutionEngine：発注ロジック、リスク管理、オーダー管理、ブローカークライアントとのインタフェース
- Monitoring：システム状態、注文ログ、リスク（ドローダウン・ポジション上限）を監視し、Kill Switch を発動
- Portfolio：銘柄選定、重み付け、ポジションサイズ計算、セクター制約やレジーム調整
- Research：DuckDB を使ったファクター計算・特徴量探索
- AI（news_nlp / regime_detector）：OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価・市場レジーム判定
- Tools：Paper Trading の検証レポート生成などの補助スクリプト
- 設定ユーティリティ：.env ウィザード（config_setup）、設定検証（validate_config）

設計方針の要点：
- 本番用データベース（monitoring.sqlite 等）とペーパートレーディングDBを分離可能
- DuckDB を分析用 DB として利用
- OpenAI API 呼び出しはリトライ等の堅牢化を施し、失敗時は安全側にフォールバックする設計
- デバッグしやすいログ出力（コンソール + 日次ローテートファイル）

---

## 主な機能一覧

- Execution
  - 本番 / ペーパートレード切替（KABUSYS_ENV=paper_trading）
  - ブローカークライアントの抽象化（BrokerClientFactory）
  - リスク管理（RiskManager）、リコンシリエーション（Reconciler）
  - PID / stop フラグによるプロセス制御

- Monitoring
  - システムリソース監視（CPU / メモリ / ディスク）
  - データ鮮度チェック（DuckDB の prices_daily 参照）
  - 監視ログの永続化（SQLite）
  - リスク監視（ドローダウン・ポジション上限）と Kill Switch の発動
  - アラート送信フック（AlertManager 経由）

- Portfolio
  - 候補選定（スコア / 上位 N）
  - 重み付け（等配分 / スコア加重）
  - ポジションサイズ計算（リスクベース／等配分／スコアベース）
  - セクターキャップ・レジーム乗数

- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - 将来リターン計算、IC（Information Coefficient）計算、ファクター統計

- AI（OpenAI）
  - ニュースを銘柄別に集約してセンチメント評価（ai_scores テーブルへ書込）
  - マクロニュース + ETF MA を組み合わせて市場レジーム判定（market_regime テーブルへ書込）

- Tools
  - Paper Trading 検証レポート生成（期間指定可）

---

## セットアップ手順（開発環境）

※ Python 3.10+ を想定（`|` 型ヒント等を使用しているため）。

1. リポジトリをクローンしてワークディレクトリへ移動
   - 例: git clone ... && cd <repo>

2. 仮想環境の作成と有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージをインストール
   - 最小例（プロジェクトに応じて調整してください）:
     - pip install duckdb openai psutil
   - 追加推奨（設定検証で YAML を使う場合）:
     - pip install PyYAML

   （requirements.txt がある場合はそれを使用してください）

4. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
     - ウィザードに従って必要な環境変数（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD など）を設定します。
   - ウィザード完了後、設定を検証:
     - python -m kabusys.validate_config
     - 必要に応じて --strict を付けて警告も失敗扱いにできます。

5. ディレクトリ作成（必要な場合）
   - data/ と logs/ は自動作成されますが、手動で用意して権限を整えておくと確実です。

---

## 環境変数（主要）

(詳しくは src/kabusys/config.py を参照)

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

重要なオプション（よく使うもの）:
- KABUSYS_ENV: execution モード
  - development / paper_trading / live
- DUCKDB_PATH: 分析用 DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード時の SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時必須）
- PAPER_FILL_MODE: ペーパートレードの fill モード（instant/partial/never/reject）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒。デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

---

## 使い方（主要エントリポイント）

各スクリプトはパッケージモジュールとして実行できます。

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine（発注実行）
  - 実行:
    - python -m kabusys.run_execution
  - ペーパートレードを使う場合:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - この場合、BrokerClientFactory は MockBrokerClient を返し、デフォルトで data/paper_trading.db を使用します。
  - 停止方法:
    - 実行中にプロセスが参照する stop フラグファイルを作ると停止ロジックが動作します。
      - stop フラグパス: project_root/data/stop_requested.flag
      - 例: touch data/stop_requested.flag
    - Kill Switch（リスク条件により自動で data/kill.flag を生成）により停止することもあります。

- Monitoring（監視ループ）
  - 実行:
    - python -m kabusys.run_monitoring
  - ポーリング間隔の変更:
    - 環境変数 MONITOR_POLL_INTERVAL（秒）を設定して起動（例: MONITOR_POLL_INTERVAL=30）
  - 注意:
    - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path（SQLITE_PATH）を使用して監視テーブルを初期化します。

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数より優先）

- AI / Regime / News スコアリング
  - OpenAI API キーが必要（OPENAI_API_KEY）
  - news_nlp.score_news(conn, target_date, api_key=None) を呼び出す（スクリプト例はなし。モジュール経由で利用）
  - regime_detector.score_regime(conn, target_date, api_key=None) でレジーム評価と DB 書き込み

---

## 停止・制御フラグ

- stop_requested.flag
  - run_execution と run_monitoring が監視している「外部からの停止要求」ファイル
  - path:
    - run_monitoring: project_root/data/stop_requested.flag
    - run_execution: project_root/data/stop_requested.flag
  - これを作成すると各ループは安全に終了します。

- kill.flag
  - KillSwitch により作成されるファイル。ExecutionEngine に対して停止を促す（安全装置）。
  - path: Settings.kill_flag_path（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアされます（本番では 0 推奨）。

---

## ロギング

- ログはコンソール出力（stdout）と日次ローテートファイル（logs/<app_name>.log）に出力されます。
- ログ設定は kabusys.utils.logging_setup.setup_logging を通じて統一的に行われます。
- 環境変数 LOG_DIR でログディレクトリを変更できます（デフォルト: logs/）。
- LOG_LEVEL 環境変数でログレベルを指定します（デフォルト: INFO）。

---

## 主要ファイル / ディレクトリ構成

（プロジェクトルートからの相対パスを示します）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の読み込み・検証ロジック
  - config_setup.py
    - .env 対話式ウィザード
  - validate_config.py
    - 起動前の設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py
      - Paper Trading の検証レポート生成
  - execution/
    - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py
    - 発注やリスク管理の実装（詳細は各ファイル参照）
  - monitoring/
    - monitoring_db.py
      - SQLite テーブルの初期化・永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (アラート送信の抽象)
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
  - data/
    - （実行時に生成されるファイル）
      - data/monitoring.db         （デフォルト SQLITE_PATH）
      - data/paper_trading.db     （PAPER_TRADING_SQLITE_PATH）
      - data/kabusys.duckdb       （デフォルト DUCKDB_PATH）
      - data/execution.pid        （PID ファイル）
      - data/stop_requested.flag  （ループ停止フラグ）
      - data/kill.flag            （Kill Switch）
  - logs/
    - 実行時に生成されるログファイル（例: logs/execution.log, logs/monitoring.log）

---

## 注意点 / 運用メモ

- データベースファイルと .env は絶対にバージョン管理へコミットしないでください（.env はシークレットを含みます）。
- 本番環境（KABUSYS_ENV=live）に切り替えると実際に発注が行われます。設定は慎重に。
- monitoring は環境にかかわらず本番 `SQLITE_PATH` を用いて監視DBを初期化します（意図的な挙動）。
- OpenAI を使う処理は API キーが必須。キーが無い場合は ValueError が発生します。
- PyYAML が無い場合、validate_config は YAML のパース検証をスキップします（警告）。

---

## よく使うコマンドまとめ

- 仮想環境作成・アクティベート
  - python -m venv .venv && source .venv/bin/activate

- パッケージインストール
  - pip install duckdb openai psutil PyYAML

- .env 作成ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要に応じて README を追記します（デプロイ手順、CI/CD、テストの実行方法、詳しい設定例、DB スキーマドキュメント等）。補足して欲しい箇所があれば教えてください。