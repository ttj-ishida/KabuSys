# KabuSys — 日本株自動売買システム（README）

このリポジトリは日本株の自動売買システム用ユーティリティ群とライブラリ群を含みます。戦略・ポートフォリオ構築、監視、ペーパートレード検証、LLM を使ったニュース/レジーム判定などのコンポーネントが含まれます。

以下は本コードベースの概要、機能、セットアップ手順、使い方、ディレクトリ構成の説明です。

---

目次
- プロジェクト概要
- 機能一覧
- 前提・依存関係
- セットアップ手順
- 使い方（主要スクリプト）
- 環境変数 / 設定
- 停止・Kill スイッチ / フラグファイル
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株向け自動売買に必要なユーティリティとサービス群（ExecutionEngine、Monitoring、Portfolio Construction、Research、AI スコアリング等）をモジュール化したコードベースです。
- DB 永続化は主に DuckDB（分析・リサーチ用）と SQLite（監視・発注ログ用）を使用します。
- OpenAI（LLM）連携によりニュースのセンチメントや市場レジーム判定を行う機能があります（任意）。

機能一覧
- 実行（Execution）起動スクリプト（run_execution.py）
  - 本番/ペーパートレード切替（KABUSYS_ENV）
  - ブローカークライアントのファクトリ、OrderManager / RiskManager / Reconciler 組み立て、ExecutionEngine の起動
  - paper_trading 環境では MockBroker を使用し、data/paper_trading.db に完全分離して記録

- 監視（Monitoring）起動スクリプト（run_monitoring.py）
  - SystemMonitor / TradeMonitor / RiskMonitor をポーリングして監視ログを SQLite に保存
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）

- 設定ウィザード（config_setup.py）
  - .env ファイルの対話式作成・更新

- 設定検証 CLI（validate_config.py）
  - .env と config/*.yaml の基本的な整合性チェック（--strict オプションあり）

- Paper Trading 検証レポート（tools/paper_verification_report.py）
  - ペーパートレード用 SQLite を集計して PASS/FAIL 判定を出力

- Portfolio モジュール（portfolio/）
  - 候補選定、配分計算（等重・スコア重み）、
  - セクター集中制限、レジーム乗数、株数決定（単元丸め・aggregate cap）

- Research モジュール（research/）
  - ファクター計算（モメンタム・ボラティリティ・バリュー）
  - 将来リターン・IC、統計サマリー

- AI モジュール（ai/）
  - news_nlp: ニュースを LLM（OpenAI）でスコアリングして ai_scores テーブルに保存
  - regime_detector: ETF（1321）MA やマクロ記事を LLM で分析して market_regime に書込

- ユーティリティ
  - ログ設定（utils/logging_setup.py）: stdout + 日次ローテーションファイル出力
  - プロセス優先度設定（utils/process_priority.py）
  - 監視 DB 書込ラッパ（monitoring/monitoring_db.py）
  - KillSwitch（監視 → Execution 停止判定）など

前提・依存関係
- Python: 3.10 以上を推奨（型ヒント表記に依存）
- 主な Python パッケージ（例）:
  - duckdb
  - psutil
  - openai (LLM 機能を使う場合)
  - PyYAML（validate_config の YAML 検証を有効にする場合）
- SQLite は標準ライブラリで利用可能
- システム環境により権限が必要な操作（プロセス優先度設定等）が失敗する可能性あり（ログに警告）

推奨インストール（例）
- 仮想環境を作成して有効化後:
  - pip install duckdb psutil openai PyYAML

セットアップ手順（クイックスタート）
1. リポジトリをクローン
   - git clone <this-repo>
   - cd <repo>

2. Python 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows の場合: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML

4. .env の作成
   - python -m kabusys.config_setup
   - 対話ウィザードで J-Quants トークンや KABU_API_PASSWORD、KABUSYS_ENV などを設定
   - あるいは .env をエディタで直接作成（.env.example を参照）

5. 設定検証
   - python -m kabusys.validate_config
   - 問題があればメッセージに従い修正

6. 必要なディレクトリを作成（data, logs 等）
   - mkdir -p data logs

主要スクリプトの使い方
- 実行（Execution Engine）起動
  - python -m kabusys.run_execution
  - 概要:
    - KABUSYS_ENV 環境変数により挙動が変わる（development / paper_trading / live）
    - paper_trading の場合、MockBroker を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録
    - 起動時に data/stop_requested.flag が存在する場合は起動を中止
    - 実行中は data/execution.pid に PID を書く

- 監視（Monitoring）起動
  - python -m kabusys.run_monitoring
  - 概要:
    - Settings.sqlite_path（デフォルト data/monitoring.db）に監視ログを書き込む（Monitoring は常に本番 sqlite_path を使用）
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト 60）
      - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    - 監視スクリプトは data/stop_requested.flag を検知するとループを終了する

- 設定ウィザード
  - python -m kabusys.config_setup
  - .env を対話的に作成・更新する

- 設定検証
  - python -m kabusys.validate_config [--strict]
  - --strict を付けると警告も失敗扱い（exit 1）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 環境変数 PAPER_TRADING_SQLITE_PATH を使うか --db で指定
  - 出力は標準出力（PASS/FAIL と指標）

- ライブラリ API（ライブラリ的に使用する例）
  - ポートフォリオ関数:
    - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes
  - リサーチ関数:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

環境変数 / 設定のポイント
- 自動 .env ロード
  - デフォルトでプロジェクトルート（.git または pyproject.toml の位置）を探し、.env を読み込みます
  - 無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

- 重要な必須環境変数
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）

- 主な設定項目（.env のキー）
  - KABUSYS_ENV: development | paper_trading | live
  - DUCKDB_PATH: デフォルト data/kabusys.duckdb
  - SQLITE_PATH: 監視 DB のパス（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 DB（paper_trading 環境）
  - OPENAI_API_KEY: AI 機能を使う場合に必要
  - LOG_LEVEL, LOG_DIR など

Kill スイッチ / フラグファイル（停止制御）
- stop_requested.flag
  - run_monitoring.py / run_execution.py は data/stop_requested.flag の存在をチェックしてループを終了またはエンジン停止を行う
  - 管理用に外部からこのファイルを作成すると処理を穏やかに停止できる

- kill.flag
  - 監視レイヤ（KillSwitch）が重大リスク（ドローダウン閾値超過・ポジション上限超過等）を検出した場合に data/kill.flag を書き込み、ExecutionEngine に停止シグナルを出します
  - Execution 起動時に KILL_FLAG_CLEAR_ON_START 設定で自動クリア可能（本番では 0 推奨）

ログ
- ログ出力は utils.logging_setup.setup_logging で統一
  - stdout（StreamHandler）と日次ローテートファイル（logs/<app_name>.log）
  - LOG_DIR 環境変数でログディレクトリを上書き可能

注意点 / 運用上のヒント
- 本番（KABUSYS_ENV=live）では設定ミスが致命的になり得るため、validate_config の出力を必ず確認してください
- LLM 機能（ai.news_nlp, ai.regime_detector）は API 失敗時にフェイルセーフ（デフォルト値で続行）する設計ですが、API キーやコールコストを考慮して運用してください
- monitoring は常に Settings.sqlite_path（本番監視 DB）を使用します。ペーパートレード用ロギングは Execution 側で paper_trading モード時に専用 DB に切り替わります

ディレクトリ構成（主要ファイル）
（src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定読み込みロジック（.env 自動ロード等）
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - news_nlp.py             — ニュースの LLM スコアリング
    - regime_detector.py      — 市場レジーム判定（LLM + MA）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - monitoring/
    - monitoring_db.py        — SQLite 監視 DB レイヤ
    - system_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - (trade_monitor, alert_manager 等が別ファイルとして存在)
  - utils/
    - logging_setup.py
    - process_priority.py
  - (その他、execution/* や data/* 等のサブモジュール)

（注）上記は現状の代表的なファイルのみ抜粋しています。実際のリポジトリにはさらに多くのモジュール（execution 関連、data.pipeline 等）が含まれる想定です。

最後に
- まずは .env を作成し（config_setup）、validate_config でチェック、ローカルでは KABUSYS_ENV=development で動作確認し、必要に応じて paper_trading モードで一連のフローを検証してください。
- LLM 連携を行う機能を有効にする場合は OPENAI_API_KEY を用意してください。

必要であれば README をさらに詳細化（例: 各モジュール API ドキュメント、運用ランブック、systemd/cron での稼働方法、ユニットテスト実行方法など）します。どの項目を詳しく追加するか教えてください。