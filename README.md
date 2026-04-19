# KabuSys

日本株自動売買システムの一部モジュール群（設定管理、監視、実行エンジン起動スクリプト、ポートフォリオ構築・ポジション決定ロジック、リサーチ、AI 補助など）。

このリポジトリはモジュール単位で構成されており、スクリプトとして起動可能なエントリポイント（run_execution/run_monitoring など）や対話式の .env ウィザード・設定検証ツールを含みます。

---

## プロジェクト概要

- 目的: 日本株向けの自動売買システムの基盤となる共通ユーティリティ群と複数の実行 / 監視スクリプト群を提供する。
- 主な機能:
  - 実行エンジン (ExecutionEngine) 起動スクリプト（run_execution）
  - 監視プロセス起動スクリプト（run_monitoring）
  - 環境設定ウィザード（.env 生成 / 更新支援）
  - 設定検証ツール（環境変数・設定ファイルの整合性チェック）
  - Paper Trading 検証レポート生成ツール
  - ポートフォリオ構築 / リスク調整 / ポジションサイジングなどの純粋関数群
  - DuckDB / SQLite を用いたリサーチ・ログ永続化および監視ログ管理
  - OpenAI を用いたニュース NLP（センチメント評価）や市場レジーム判定（AI 補助）

---

## 機能一覧（抜粋）

- 設定関連
  - .env 自動読み込み（プロジェクトルートの .env / .env.local、環境変数が優先）
  - 対話式ウィザード: `python -m kabusys.config_setup`
  - 設定検証 CLI: `python -m kabusys.validate_config [--strict]`

- 実行 / 監視
  - 実行エンジン起動: `python -m kabusys.run_execution`
    - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使用し、paper_trading 用 DB（data/paper_trading.db）に記録
    - PID ファイル (data/execution.pid) の扱い、停止フラグ (data/stop_requested.flag) 対応
  - 監視プロセス起動: `python -m kabusys.run_monitoring`
    - ポーリングループで SystemMonitor を定期実行（デフォルト 60 秒）
    - 環境変数 `MONITOR_POLL_INTERVAL` で間隔上書き可能
    - 監視ログは SQLite（monitoring.db）に保存（Monitoring は環境にかかわらず本番 sqlite_path を使用）

- 監視モジュール
  - SystemMonitor: CPU/メモリ/ディスク・プロセス PID チェック・データ鮮度監視
  - TradeMonitor: 発注履歴の滞留・約定等をチェック（実装参照）
  - RiskMonitor: ドローダウン、ポジション数上限監視（risk_logs / dashboard 更新）
  - KillSwitch: 条件に応じて data/kill.flag を書き込み、ExecutionEngine 停止シグナル発行
  - MonitoringEngine: 上記を束ねてポーリング・アラート送出（AlertManager 経由）

- ポートフォリオ関連（純粋関数群）
  - 候補選定: select_candidates
  - 重み計算: calc_equal_weights, calc_score_weights
  - セクター上限適用: apply_sector_cap
  - レジーム乗数: calc_regime_multiplier
  - ポジションサイズ決定: calc_position_sizes

- リサーチ / AI
  - ファクター計算 (momentum/value/volatility)
  - 将来リターン・IC 計算・特徴量サマリ
  - News NLP: OpenAI でニュースをセンチメントスコア化（ai.news_nlp）
  - Regime Detector: MA200 とマクロセンチメントを合成して市場レジーム判定（ai.regime_detector）

- ユーティリティ
  - ログ設定ユーティリティ（日次ローテーション + stdout）
  - プロセス優先度 / CPU affinity 設定（psutil 経由）

---

## セットアップ手順

前提:
- Python 3.10+ を推奨（型注釈の表記や使用ライブラリの互換考慮）
- システムに sqlite3 は標準で同梱、外部パッケージを以下でインストール

推奨パッケージ（最低限）:
- duckdb
- psutil
- openai
- pyyaml（設定検証で YAML 内容をチェックしたい場合）
- （必要に応じて）他の実装済みモジュールに依存するパッケージ

例:
- pip でインストール:
  - pip install duckdb psutil openai pyyaml

初期ファイル/ディレクトリの作成:
- プロジェクトルートで次を実行しておくと良い:
  - mkdir -p data logs

.env の作成:
- 対話式ウィザードで作成:
  - python -m kabusys.config_setup
- 生成後は設定を検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いになる

設定自動読み込みの補足:
- 起動時 .env の自動ロードはデフォルトで有効（プロジェクトルートの .env / .env.local を読み込み）
- 自動ロードを無効化するには環境変数を設定:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須環境変数（代表例）:
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- OPENAI_API_KEY（AI 機能を使う場合）
- KABUSYS_ENV（development / paper_trading / live、デフォルト: development）

主要な環境変数（概要）:
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログディレクトリ（デフォルト logs/）
- PID_FILE_PATH: Execution PID ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH: Kill Switch フラグパス（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするフラグ（0/1）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60）

---

## 使い方（実行例）

1. .env を作成・編集
   - python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config
   - 問題があれば表示されるエラー・警告を修正

3. 実行エンジン起動（本番 / ペーパー共通）
   - python -m kabusys.run_execution
   - 挙動:
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し paper_trading 用 DB を参照
     - 起動前に data/stop_requested.flag が存在すると起動せず終了
     - 実行中に data/stop_requested.flag が作成されると安全に停止する

4. 監視プロセス起動
   - python -m kabusys.run_monitoring
   - ポーリング間隔を変更するには:
     - export MONITOR_POLL_INTERVAL=30
     - python -m kabusys.run_monitoring

5. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - デフォルトの DB: data/paper_trading.db。別 DB を使う場合:
     - python -m kabusys.tools.paper_verification_report --db /path/to/db

6. AI 系機能
   - News NLP（プログラムから呼ぶ例）:
     - from kabusys.ai.news_nlp import score_news
     - score_news(conn, target_date, api_key="...")  # conn は DuckDB 接続
   - Regime スコア付与:
     - from kabusys.ai.regime_detector import score_regime
     - score_regime(conn, target_date, api_key="...")

7. 停止 / Kill
   - 手動でシステム停止をリクエストするにはプロジェクトの data ディレクトリにフラグを置く:
     - data/stop_requested.flag — run_monitoring / run_execution が検知して停止
     - data/kill.flag — KillSwitch による安全停止フラグ。起動時に KILL_FLAG_CLEAR_ON_START=1 なら自動クリアされる（本番では注意）

ログ:
- logs/<app_name>.log に日次ローテーションで出力（デフォルト logs/、設定可）
- 標準出力にもログが出る（stdout）

注意:
- Monitoring の初期化は run_monitoring/run_execution 内で SQLite テーブルを作成する（init_monitoring_db）
- Monitoring は sqlite_path を本番設定で使用する（環境にかかわらず）

---

## 主要なディレクトリ構成（src/kabusys/ の主なファイル）

- __init__.py
- config.py
  - 環境変数の読み込み / Settings クラス
- config_setup.py
  - 対話式 .env ウィザード
- validate_config.py
  - 設定検証 CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト
- utils/
  - logging_setup.py — ログ設定
  - process_priority.py — プロセス優先度 / CPU affinity
- monitoring/
  - monitoring_db.py — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py — システムヘルス・データ鮮度監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — フラグ書き込みによる停止
  - monitoring_engine.py — 全 Monitor を束ねる（AlertManager 連携）
  - trade_monitor.py — （発注ログのチェック: 滞留・約定異常検出など）
  - alert_manager.py — （通知を送る抽象レイヤ。実装により LINE 等へ通知）
- execution/
  - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py
  - （注文実行 / ブローカ連携 / リスク管理の実装群）
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
- research/
  - factor_research.py, feature_exploration.py
- ai/
  - news_nlp.py — ニュースから銘柄別センチメントを取得して ai_scores に書き込む
  - regime_detector.py — MA200 とマクロセンチメント合成によるレジーム判定
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成

（実際のファイル・ディレクトリの詳細はリポジトリの tree を参照してください）

---

## 運用上の注意・ベストプラクティス

- 本番環境（KABUSYS_ENV=live）は取り扱いに注意:
  - validate_config は live を検出すると警告を出す（LINE 通知等が未設定だとアラートが届かない）
  - KILL_FLAG_CLEAR_ON_START=1 は本番では危険（Kill Switch を誤ってクリアしてしまう）
- Paper Trading は本番 DB と完全分離:
  - KABUSYS_ENV=paper_trading の場合、paper_sqlite_path（PAPER_TRADING_SQLITE_PATH）を使用
- ログディレクトリに書き込み権限がない場合、ファイル出力は無効化され stdout のみになる
- OpenAI を使う機能は API コスト・レート制限に注意。リトライやバッチ化が施されていますが実運用では制限を設計に反映してください
- DuckDB / SQLite のファイルパスは .env 経由で設定可能。バックアップ / 保守計画を用意してください

---

## 参考コマンドまとめ

- 環境設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視プロセス起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- AI スコア付与（スクリプト内呼び出し）:
  - from kabusys.ai.news_nlp import score_news

---

もし README に追加したい具体的な実行例、.env のサンプル（機密情報を省いた雛形）、あるいは開発用の docker-compose / systemd ユニット例などがあれば、目的に合わせて追記します。どの情報を優先して拡充しますか？