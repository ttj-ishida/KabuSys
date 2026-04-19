# KabuSys

バージョン: 0.1.0

KabuSys は日本株の自動売買システム（バックエンドライブラリ）です。市場ファクター計算、ポートフォリオ構築、ポジションサイズ決定、監視/アラート、ペーパートレード検証、LLM を用いたニュース NLP／レジーム判定などのユーティリティを提供します。

---

## 概要

このリポジトリは、取引ロジック・監視・リサーチ・AI連携の主要コンポーネントをモジュール化した Python パッケージです。主要な実行スクリプト（ExecutionEngine 起動、Monitoring 起動）のほか、設定ウィザード・設定検証・ペーパートレード検証レポート生成ツールなどを備えています。

主な設計方針:
- DuckDB / SQLite を用いたデータ永続化（分析用に DuckDB、監視/発注ログに SQLite）
- 環境変数 / .env による設定管理
- 本番 / ペーパー（paper_trading）を分離した DB 設計
- OpenAI（gpt-4o-mini 等）を使ったニュースセンチメント・レジーム判定（任意）

---

## 主な機能一覧

- ExecutionEngine 起動スクリプト（run_execution）
  - KABUSYS_ENV により本番 / ペーパーを切替
  - Broker クライアントのファクトリ経由で実ブローカー or MockBroker を使用
  - リスク管理・注文管理・照合（reconciler）を組み合わせて稼働

- Monitoring（run_monitoring / MonitoringEngine）
  - SystemMonitor: CPU/メモリ/ディスク、プロセス生存チェック、データ鮮度チェック
  - TradeMonitor: 発注履歴/滞留注文/約定異常などの監視（trade_logs 参照）
  - RiskMonitor: ドローダウン/ポジション上限監視、ダッシュボード更新
  - KillSwitch: 条件により data/kill.flag を書き込み ExecutionEngine に停止指示
  - AlertManager（通知: LINE 等）連携（任意）

- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定、等金額/スコア加重、リスクベースサイズ算出、セクターキャップ、レジーム乗数

- リサーチ（kabusys.research）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 特徴量解析（将来リターン、IC、統計サマリー）

- AI モジュール（kabusys.ai）
  - news_nlp: OpenAI を用いたニュースセンチメントスコア算出（ai_scores テーブルへ書込）
  - regime_detector: MA200 とマクロセンチメントを合成して market_regime に書き込み

- 設定関連ツール
  - config_setup: 対話式に .env を生成/更新
  - validate_config: .env と config/*.yaml の検証
  - tools.paper_verification_report: ペーパートレードの検証レポート生成

---

## セットアップ手順

前提:
- Python 3.10 以上（PEP 604 の型記法 (A | B) を使用）
- Git リポジトリルートにプロジェクトがあること（.env 自動読み込み用）

1. 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 代表的な依存:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - pyyaml (validate_config の YAML 検証を使う場合)
   - 例:
     - pip install duckdb psutil openai pyyaml

   （requirements.txt がある場合はそれを使用してください。）

3. ディレクトリ作成（初回）
   - mkdir -p data logs
   - data フォルダはデフォルトで SQLite / PID / フラグファイルを置きます。
   - logs はログファイル（logs/<app_name>.log）用です。

4. 環境変数設定
   - .env をプロジェクトルートに作成するか、環境変数をセットしてください。
   - 必須:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 推奨/例（.env）:
     JQUANTS_REFRESH_TOKEN=your_token_here
     KABU_API_PASSWORD=your_password_here
     KABUSYS_ENV=development           # development | paper_trading | live
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO
     KILL_FLAG_CLEAR_ON_START=0
     # AI 機能を使う場合
     OPENAI_API_KEY=sk-xxxxx

   - 設定ウィザードで .env を生成する:
     - python -m kabusys.config_setup

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにしたい場合は --strict

---

## 使い方（主要スクリプト）

- ExecutionEngine 起動（通常はサービス・systemd 等で運用）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBroker が使われ Paper Trading DB（data/paper_trading.db）に記録されます
  - 実行中の停止: data/stop_requested.flag を作成すると、次のループで停止処理が始まります
  - PID ファイル: data/execution.pid（設定による）

- Monitoring 起動（監視プロセス）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で秒指定（デフォルト 60 秒）
  - 監視は常に本番用 sqlite_path を使用します（KABUSYS_ENV に依存しません）
  - 停止: data/stop_requested.flag を置く

- 設定ウィザード
  - python -m kabusys.config_setup
  - .env を対話式に生成/更新します

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit 1）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定可能（デフォルト data/paper_trading.db）

- AI モジュールの利用例
  - news_nlp.score_news()（DuckDB 接続と target_date を渡して使用）
  - regime_detector.score_regime()（同上）
  - 実行には OPENAI_API_KEY の設定が必要

監視・停止に関する補足:
- KillSwitch は RiskMonitor 等の出力により data/kill.flag を書き込み、ExecutionEngine が検出します。
- KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番は 0 推奨）。

---

## 主要環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要（任意／推奨）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
- OPENAI_API_KEY: OpenAI を利用する場合に必要
- MONITOR_POLL_INTERVAL: 監視ポーリング秒（run_monitoring）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant|partial|never|reject）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START など

設定不足は python -m kabusys.validate_config で検出できます。

---

## ディレクトリ構成

（プロジェクトルートに src/ があるレイアウトを想定）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/.env の読み込み・Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前の設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
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
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py (参照あり)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (参照あり)
  - execution/
    - broker_factory.py (参照あり)
    - execution_engine.py (参照あり)
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py

データ / ログ:
- data/ (デフォルト)
  - monitoring.db (SQLITE_PATH)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - kill.flag
  - stop_requested.flag
  - execution.pid
- logs/
  - execution.log, monitoring.log, ... (app_name ごとに日次ローテーション)

---

## 開発上の注意点 / ヒント

- 本番とペーパートレードの DB は分離されています（paper_trading モード時は paper_sqlite_path を使用）。
- run_monitoring は KABUSYS_ENV に依らず本番 sqlite_path を参照します（監視は本番 DB を見る設計）。
- OpenAI 関連はネットワーク・API の可用性を考慮してフェイルセーフ（失敗時はフォールバック）実装になっていますが、APIキーは必須です。
- DuckDB を用いたリサーチ関数群は SQL を用いて高速に計算します。prices_daily / raw_financials 等のテーブルが前提です。
- ログは setup_logging により stdout と日次ローテートファイルへ出力されます。ログディレクトリの作成に失敗した場合は stdout のみで継続します。
- プロセス優先度設定（set_process_priority）は権限により失敗する場合があります（警告のみ）。

---

## トラブルシューティング

- .env が読み込まれない/期待した設定が反映されない場合:
  - プロジェクトルートが正しく検出されているか（.git または pyproject.toml が存在するか）を確認
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 が設定されていないか確認

- DuckDB/SQLite のパス関連警告:
  - validate_config が parent ディレクトリ存在をチェックします。必要なら手動でディレクトリを作成してください。

- 実行が停止しない / 停止できない:
  - data/stop_requested.flag を作成すると run_* の主ループは次のポーリングで停止します
  - data/kill.flag は KillSwitch が書き込む停止シグナル（ExecutionEngine が検出して停止）

---

README は導入ガイドとしての要点をまとめています。さらに詳細な内部設計（StrategyModel.md / PortfolioConstruction.md 等）や外部インテグレーションは別ドキュメントを参照してください。必要であれば README を拡張して起動スクリプトの systemd ユニット例、Docker 化手順、CI/CD 設定例などを追加します。