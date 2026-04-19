# KabuSys

日本株向けの自動売買システム（リサーチ / ポートフォリオ構築 / 発注 / 監視 / AI 支援）のモノリポジトリ。  
この README はソースツリー（src/kabusys 以下）を基にした概要・セットアップ・使い方のまとめです。

注意: 各スクリプト・モジュールは単体での利用やテストを想定しており、実行時には適切な環境変数・APIキー・DBファイルが必要です。

---

## プロジェクト概要

- DuckDB を用いた時系列データ（prices_daily / raw_financials / raw_news 等）の分析・ファクター計算。
- ポートフォリオ構築（銘柄選定・重み付け・ポジションサイズ計算）。
- ExecutionEngine（発注）と Monitoring（監視）コンポーネント。
  - KABUSYS_ENV に応じて paper_trading モード（MockBrokerClient + 分離DB）での検証が可能。
- AI モジュール（OpenAI）を用いたニュースセンチメント（news_nlp）や市場レジーム判定（regime_detector）。
- 監視用の SQLite 永続化層（monitoring_db）とリスク監視 / Kill Switch / アラート連携。
- 運用を支援する CLI: .env ウィザード、設定検証、Paper Trading 検証レポート生成 等。

---

## 主な機能一覧

- 環境管理
  - 自動でプロジェクトルートの .env / .env.local を読み込み（必要に応じて上書き）
  - config_setup による対話式 .env 生成
  - validate_config による起動前チェック（必須環境変数・DBパス・config yaml 等）

- 実行（発注）関連
  - run_execution: ExecutionEngine を起動（KABUSYS_ENV=paper_trading のときは MockBroker を使用し data/paper_trading.db に記録）
  - BrokerClientFactory による本番/モック切替
  - リスク管理（RiskManager, Reconciler, OrderManager など）

- 監視関連
  - run_monitoring: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定可、デフォルト 60 秒）
  - MonitoringEngine: System / Trade / Risk モニタを束ね、KillSwitch や AlertManager と連携
  - MonitoringDB: SQLite に system_status / trade_logs / risk_logs / positions / dashboard 等を保持

- 研究・ファクター
  - research.calc_momentum / calc_volatility / calc_value 等（DuckDB を直接参照）
  - feature_exploration: 将来リターン計算、IC（Information Coefficient）、統計サマリー

- ポートフォリオ構築
  - portfolio.select_candidates / calc_equal_weights / calc_score_weights
  - risk_adjustment.apply_sector_cap / calc_regime_multiplier
  - position_sizing.calc_position_sizes（単元株丸め・aggregate cap のスケーリング）

- AI（OpenAI）関連
  - ai.news_nlp.score_news: ニュース記事を LLM でセンチメント評価して ai_scores に書き込み
  - ai.regime_detector.score_regime: ma200 + マクロニュースの LLM 評価を合成して市場レジーム判定

- 運用ツール
  - tools.paper_verification_report: Paper Trading の挙動（稼働率・成功率・レイテンシ等）を集計してレポート化

---

## セットアップ手順

1. Python 環境を準備（推奨: virtualenv / venv）
   - Python 3.10+ を想定

2. 必要なパッケージをインストール
   - 明示的な requirements.txt はプロジェクトに含まれていないため、主に以下をインストールしてください:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML (validate_config で YAML 検証を有効にする場合)
   - 例:
     - pip install duckdb psutil openai PyYAML

3. 環境変数 (.env) を作成
   - 初期対話的ウィザードを実行:
     - python -m kabusys.config_setup
   - 生成された .env を編集して必要な値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY（AI を使う場合）など）を設定してください。
   - 自動ロード: src/kabusys/config.py はプロジェクトルートの .env / .env.local を自動で読み込みます（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict オプションで警告も失敗扱い（exit code 1）にできます。

5. データディレクトリの作成（必要に応じて）
   - デフォルト DB パス: data/kabusys.duckdb（DuckDB）、data/monitoring.db（SQLite）
   - ログディレクトリ: logs/（setup_logging が自動作成しますが権限に注意）

---

## 環境変数（主要）

- KABUSYS_ENV: execution モード
  - development / paper_trading / live
  - paper_trading のとき run_execution は data/paper_trading.db を使用
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- OPENAI_API_KEY: AI 機能を使う場合必要
- DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視 SQLite ファイルパス（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（default: data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の注文成立挙動）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
- LOG_DIR: ログ出力ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 1 にすると起動時に data/kill.flag を自動クリア（危険、production では 0 推奨）

ファイルベースのフラグ:
- data/kill.flag: Kill Switch（監視モジュールが発動した場合に書き込まれる停止フラグ）
- data/stop_requested.flag: run_execution / run_monitoring のループ停止用（外部から起動停止するためのフラグ）
- data/execution.pid: ExecutionEngine の PID（デフォルトパス）

---

## 使い方（代表的なコマンド）

- .env の対話式作成:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- 実行エンジンを起動（発注を含む）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading のときは MockBroker を使用し PAPER_TRADING_SQLITE_PATH に記録
    - 起動時に data/stop_requested.flag が存在する場合は起動しない
    - 停止は data/stop_requested.flag を作成するか、プロセスに KeyboardInterrupt を送る

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL で polling 間隔を上書き可能（秒、デフォルト 60）
  - 監視は環境に関わらず本番の SQLITE_PATH を使用してログを残します（monitoring 用 DB は共通で使用する設計）
  - 停止は data/stop_requested.flag を作成するか KeyboardInterrupt

- Paper Trading の検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH を使用

- AI モジュール（例）
  - ai.news_nlp.score_news / ai.regime_detector.score_regime は DuckDB 接続を受け取り内部で OpenAI を呼び出します。
  - 実行時には OPENAI_API_KEY を設定してください。

---

## 運用上の注意点

- run_monitoring は Monitoring 用 SQLite（SQLITE_PATH）を使用します。監視ログは本番 DB に記録されるため注意してください。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と完全分離します。
- Kill Switch:
  - RiskMonitor が閾値を超えるなどの条件で KillSwitch が data/kill.flag を書き込むと、手動で flag を削除するまでエンジンが自動再開しない場合があります。KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアしますが、本番では推奨されません。
- ログ:
  - logs/<app_name>.log に日次ローテーションで保存されます（30日保持）。
  - 権限やディスク容量に注意してください。

---

## 主要ディレクトリ構成

（リポジトリルートの src/kabusys を基準）

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動読み込みと Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前チェック CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - utils/
    - logging_setup.py       — 共通ログ設定
    - process_priority.py    — 優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（テーブル定義・操作）
    - system_monitor.py      — システム状態 / データ鮮度監視
    - trade_monitor.py       — 発注ログ監視（滞留注文等） ※実装ファイルあり
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 管理
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - alert_manager.py       — アラート送信（LINE 等） ※実装ファイルあり
  - execution/
    - execution_engine.py    — ExecutionEngine 本体（セッション管理）
    - broker_factory.py      — BrokerClient の生成（実ブローカ / モック切替）
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
    - news_nlp.py            — ニュース NLP スコアリング
    - regime_detector.py     — 市場レジーム判定
  - data/                    — 実行時に使用するデータファイル（logs/, db files, flags を想定）

（上記は主要ファイル一覧です。詳細は各モジュールの docstring を参照してください）

---

## トラブルシューティング

- PyYAML が見つからない:
  - validate_config は YAML のパースチェックをスキップしますが、できれば PyYAML をインストールしてください。
- OpenAI API 関連のエラー:
  - OPENAI_API_KEY が未設定の場合、AI 関連関数はエラーを送出します。キーを設定してください。
  - API の 429 / タイムアウト / 5xx は内部でリトライがありますが、上限に達すると該当処理はスキップされます（安全第一の設計）。
- ログディレクトリ作成失敗:
  - 権限やマウント先を確認してください。ファイルハンドラが作成できない場合コンソールログのみで継続します。
- run_monitoring が想定通り sqlite に書き込まれない:
  - run_monitoring は環境に関わらず Settings.sqlite_path を使用します。期待する DB を参照しているか確認してください。

---

以上。各モジュールの詳細な使い方・引数・戻り値についてはソースコード内の docstring を参照してください。必要であれば README の追加セクション（デプロイ手順、CI、開発フロー等）を作成します。