# KabuSys

KabuSys は日本株向けの自動売買／リサーチ基盤です。本リポジトリはシグナル生成、ポートフォリオ構築、発注（Execution）、監視（Monitoring）、AI を使ったニュース解析などのコンポーネントを含むモジュール群を提供します。

以下はコードベースを基にした README（日本語）です。利用開始手順、主要機能、使い方、ディレクトリ構成などをまとめています。

## プロジェクト概要
- 日本株自動売買システムのプロトタイプ／基盤実装。
- 主な機能:
  - シグナル生成・ファクター計算（research）
  - ポートフォリオ構築（portfolio）
  - 注文管理・ExecutionEngine（execution）
  - 監視（Monitoring）と Kill Switch（自動停止）
  - ニュースの NLP によるセンチメントスコアリング（AI）
  - Paper Trading 用の分離された DB と検証レポート機能（tools）
- 設定は `.env` ファイル / 環境変数で管理。`config_setup` ウィザードを用意。

## 主な機能一覧（抜粋）
- execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - Paper Trading（KABUSYS_ENV=paper_trading）時は MockBrokerClient を使用し、データは `data/paper_trading.db` に記録（本番 DB と分離）
- monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - SQLite ベースの監視ログ（monitoring_db）
  - Kill Switch（条件を満たすと `data/kill.flag` を作成して発注エンジンを停止）
  - run_monitoring.py によりポーリング監視を実行（環境変数でポーリング間隔を指定可能）
- portfolio
  - 銘柄選定、重み計算（等金額・スコア重み）、セクターキャップ、レジーム乗数、ポジションサイズ計算
- research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC 計算、統計サマリ
- ai
  - news_nlp: OpenAI を使ったニュースセンチメントスコアリング（ai_scores テーブルへ書き込み）
  - regime_detector: ETF とマクロニュースを組み合わせて市場レジーム判定し DB に書き込み
- tools
  - paper_verification_report: ペーパートレード実行結果を解析して検証レポートを出力

## 前提条件 / 必要環境
- Python 3.10 以上（構文で `|` 型ヒント等を使用しているため）
- 推奨パッケージ（最低限）:
  - duckdb
  - psutil
  - openai
  - pyyaml（設定ファイル検証時に任意）
- 例（pip）:
  - pip install duckdb psutil openai pyyaml

※ 実際の要件はプロジェクトの requirements.txt がある場合はそちらで確認してください。

## セットアップ手順

1. リポジトリをクローン／チェックアウト
   - git clone ... など

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml

4. `.env` の作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
     - ウィザードは J-Quants トークン、kabu API パスワード、DB パス、ログレベル等を設定します。
   - 手動で作る場合は `.env.example` を参考に `JQUANTS_REFRESH_TOKEN` と `KABU_API_PASSWORD` は必須で設定してください。

5. 設定の検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告も含めて厳密に fail にしたい場合:
     - python -m kabusys.validate_config --strict

6. ディレクトリ／初期 DB の準備
   - デフォルトでは `data/` 以下に DB/log/pid/flag ファイルを配置します。プロセス実行前に `data/` ディレクトリを作成しておくと安全です。
   - 自動的に作成される箇所もありますが、権限や配置先の確認を推奨します。

## 主要な環境変数（主に .env に設定）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 任意や重要:
  - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
    - paper_trading: Execution は MockBrokerClient を使用し `data/paper_trading.db` に記録
  - DUCKDB_PATH: デフォルト `data/kabusys.duckdb`
  - SQLITE_PATH: 監視 DB のデフォルト `data/monitoring.db`
  - PAPER_TRADING_SQLITE_PATH: paper trading 用 SQLite（デフォルト `data/paper_trading.db`）
  - LOG_LEVEL: DEBUG/INFO/…（デフォルト: INFO）
  - OPENAI_API_KEY: OpenAI を使う AI モジュールで必要
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0。本番では 0 推奨）
- 自動読み込み:
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）から `.env` と `.env.local` を自動読み込みします。自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。

## 使い方（よく使うコマンド例）

- 環境作成（ウィザード）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- モニタ（監視）起動
  - python -m kabusys.run_monitoring
  - 説明:
    - デフォルトのポーリング間隔は 60 秒（環境変数 MONITOR_POLL_INTERVAL で上書き可）。
    - 監視は monitoring DB（`SQLITE_PATH`）に記録します（環境にかかわらず本番 sqlite_path を使用する実装上の挙動）。
    - 停止方法:
      - プロジェクトルートの `data/stop_requested.flag` を作成するとスクリプトが検知して終了します。

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 説明:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して paper_trading 用 DB (`PAPER_TRADING_SQLITE_PATH` / `data/paper_trading.db`) に記録します。本番と分離されます。
    - 起動時に `data/stop_requested.flag` が既に存在すると起動を行わず終了します。
    - 実行中に停止するには `data/stop_requested.flag` を作成するか、`data/kill.flag` による Kill Switch を監視している場合は監視からのキルにより停止されます。

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - オプション `--db PATH` で DB ファイルを指定可能（環境変数 `PAPER_TRADING_SQLITE_PATH` より優先）。

- AI 関連（プログラム的に利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - OpenAI API キーは引数か環境変数 `OPENAI_API_KEY` で指定
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

## ログ設定
- 共通ユーティリティ `kabusys.utils.logging_setup.setup_logging` を使っているため、各スクリプト（monitoring / execution 等）は統一されたログ出力を行います。
- 出力先:
  - コンソール (stdout)
  - ローテーティングファイル (デフォルト: logs/<app_name>.log、日次ローテーション、30 日保持)
- ログディレクトリは環境変数 `LOG_DIR` または引数で変更可能。

## 停止フラグ / PID / Kill Switch
- stop flag:
  - `data/stop_requested.flag` — 実行中の run_monitoring / run_execution がこれを検知して安全に終了します（手動で作成）。
- kill flag:
  - `data/kill.flag` — KillSwitch がレジームやドローダウン条件によりこのファイルを書き込むと ExecutionEngine に停止シグナルを送ります（Execution 側は起動時に設定等を参照して対処）。
- PID ファイル:
  - `data/execution.pid` 等（Settings.pid_file_path で指定）に PID を書く仕組みを ExecutionEngine が利用しています。

## 主要モジュールの概要
- kabusys.config
  - .env ロード / Settings クラス（アプリケーション設定）
- kabusys.config_setup
  - .env を対話式に作成するウィザード
- kabusys.validate_config
  - 起動前の設定検証ツール（必須環境変数、ファイル存在、YAML パース等）
- kabusys.run_monitoring
  - SystemMonitor ポーリングループ起動スクリプト
- kabusys.run_execution
  - ExecutionEngine 起動スクリプト（paper_trading モードでの分離をサポート）
- kabusys.monitoring
  - monitoring_db: SQLite スキーマ / 永続化層
  - system_monitor / trade_monitor / risk_monitor / monitoring_engine / kill_switch / alert_manager 等
- kabusys.portfolio
  - portfolio_builder, position_sizing, risk_adjustment（純関数群で配分・サイズ計算）
- kabusys.research
  - factor_research, feature_exploration（DuckDB を使ったファクター計算、IC 等）
- kabusys.ai
  - news_nlp, regime_detector（OpenAI を利用したスコアリング）
- kabusys.tools
  - paper_verification_report（ペーパートレードの検証レポート）

## ディレクトリ構成（抜粋）
リポジトリの主要ファイル・ディレクトリは以下の通り（実際のファイル数はこれより多い場合があります）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_monitoring.py
    - run_execution.py
    - utils/
      - logging_setup.py
      - process_priority.py
      - __init__.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - risk_monitor.py
      - trade_monitor.py (参照あり)
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py (参照あり)
    - execution/
      - execution_engine.py (参照あり)
      - order_manager.py (参照あり)
      - broker_factory.py (参照あり)
      - order_repository.py (参照あり)
      - reconciler.py (参照あり)
      - risk_manager.py (参照あり)
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
      - __init__.py
    - data/      (実行時に使用する DB / flag / pid / ログ等)
    - logs/      (ログファイルの保存先、デフォルト)

## 運用上の注意 / ベストプラクティス
- 本番環境 (KABUSYS_ENV=live) では Kill Switch 設定、LINE 通知などアラート経路を必ず設定してください。
- `.env` は機密情報を含むため、絶対に Git にコミットしないでください（config_setup のヘッダーにも注意書きあり）。
- Paper Trading モードを使用することで本番 DB と完全分離された検証が可能です（PAPER_TRADING_SQLITE_PATH を利用）。
- OpenAI の利用は API キーの管理とリクエスト頻度に注意してください（コスト・レート制限）。
- monitoring と execution を別プロセス／別ホストで動かす設計が可能です。監視は本番 sqlite_path を参照するため、監視用 DB の配置と権限を検討してください。

## トラブルシューティング
- DB/ログディレクトリが作成できない場合:
  - ログや DB ファイルの書き込み権限を確認してください。`logs/` や `data/` の所有者/パーミッションが正しいことを確認します。
- モジュール ImportError（例: PyYAML がない）:
  - validate_config は PyYAML がない場合 YAML の検証をスキップしますが、必要に応じて `pip install pyyaml` を行ってください。
- OpenAI API 関係のエラー:
  - `OPENAI_API_KEY` が設定されているか、API レスポンスのレート制限やネットワーク状態を確認してください。AI モジュールは一部リトライロジックを備えていますが、致命的な失敗時はフォールバック（スコアを 0 にする等）が入ります。

---

この README はリポジトリ内のソースコードから抽出・要約したもので、詳細な仕様や利用方法は個々のモジュール（特に execution / broker 関連）を参照してください。必要であれば各コマンドの具体的なオプションや、設定ファイルのサンプル（.env.example / config/*.yaml）のテンプレートを追加できます。