# KabuSys

日本株向け自動売買システムの一部コンポーネントをまとめた軽量ライブラリ / 実行スクリプト群です。本リポジトリは取引ロジック、モニタリング、リサーチ、AI（ニュース NLP）などのモジュールを含み、ローカル開発・ペーパートレード・本番（live）を想定した設計になっています。

主な目的
- データ取得・ファクター計算（DuckDB 利用）
- ポートフォリオ構築・ポジションサイズ算出（純粋関数群）
- ExecutionEngine（発注エンジン：kabuステーション / MockBroker）
- 監視（System / Trade / Risk）と Kill Switch
- ニュース NLP を使った銘柄ごとのセンチメント評価（OpenAI）

以下に本プロジェクトの概要、機能、セットアップ、使い方、ディレクトリ構成を示します。

## 機能一覧
- 設定管理
  - .env 自動読み込み（プロジェクトルートの .env / .env.local）
  - 対話式設定ウィザード: kabusys.config_setup
  - 設定検証 CLI: kabusys.validate_config
- 実行 / 発注
  - run_execution.py: ExecutionEngine 起動スクリプト
    - KABUSYS_ENV により paper_trading 時は MockBroker を使用し、履歴は data/paper_trading.db に分離
    - PID ファイル管理（data/execution.pid 等）
- 監視
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60s）
    - monitoring DB（SQLite）への永続化（monitoring_db）
    - Kill Switch（データに応じて data/kill.flag を書く）
  - MonitoringEngine: System/Trade/Risk 各 Monitor を束ねる実行ユーティリティ
- モジュール群
  - portfolio: 候補選定、重み計算、ポジションサイズ計算、セクター制限、レジーム乗数
  - research: ファクター（Momentum/Value/Volatility）計算、将来リターン、IC 計算、統計サマリ
  - ai:
    - news_nlp: OpenAI を使った銘柄別センチメント評価（ai_scores テーブルに書き込み）
    - regime_detector: MA + マクロニュースの LLM 評価を合成して市場レジームを判定
  - monitoring: DB 層（monitoring_db）、SystemMonitor / TradeMonitor / RiskMonitor、KillSwitch、AlertManager（通知用）
  - tools: Paper Trading 検証レポート生成スクリプト（paper_verification_report）
- ユーティリティ
  - logging_setup: 一貫したログ設定（コンソール + 日次ローテーションファイル）
  - process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ

## 前提・依存（例）
ソース中で使用されているライブラリの一例です。実際は requirements.txt を用意している想定です。
- Python 3.9+
- duckdb
- psutil
- openai（AI 機能利用時）
- sqlite3（標準ライブラリ）

インストール例（環境に合わせて変更してください）:
- pip install -r requirements.txt
- または個別: pip install duckdb psutil openai

## 環境変数（主要）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading の場合の DB、デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI 機能利用時）
- LOG_LEVEL（例: INFO）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒数を上書き）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか。1 で有効）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env をロードしない

注: .env は絶対にリポジトリにコミットしないでください。

## セットアップ手順（簡易）
1. リポジトリをクローン／配置
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate（Windows は別コマンド）
3. 依存ライブラリをインストール
   - pip install -r requirements.txt
   - もしくは pip install duckdb psutil openai
4. 初期 .env を作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
     - 必須キー（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を入力してください
5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります
6. ディレクトリ確認 / 作成
   - data/ および logs/ は自動作成されますが、パーミッション等に注意してください

## 実行方法（代表例）

- ExecutionEngine（発注エンジン）起動
  - 開発・テスト:
    - KABUSYS_ENV=development python -m kabusys.run_execution
      - development では発注は行われない（想定）
  - ペーパートレード:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
      - MockBroker を利用し data/paper_trading.db に記録（本番 DB とは分離）
  - 本番:
    - KABUSYS_ENV=live python -m kabusys.run_execution

- Monitoring（システム監視）起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で調整（例: MONITOR_POLL_INTERVAL=30）

- Paper Trading 検証レポート出力
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で別 DB を指定可（デフォルトは環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）

- 開発／テスト用ユーティリティ
  - 各モジュールは import してユニットテスト可能です（例: kabusys.portfolio.calc_position_sizes）

## ログ・DB・フラグファイル
- ログ:
  - デフォルト: logs/<app_name>.log（例: logs/execution.log, logs/monitoring.log）
  - 日次ローテーション・30日保持
- SQLite:
  - 監視用: data/monitoring.db（Settings.sqlite_path）
  - ペーパー用: data/paper_trading.db（Settings.paper_sqlite_path）
- DuckDB:
  - 分析用: data/kabusys.duckdb（Settings.duckdb_path）
- PID / 停止フラグ:
  - data/execution.pid: ExecutionEngine の PID 保存（設定により異なるパス）
  - data/stop_requested.flag: 外部からスクリプトを止めたい場合に利用（run_execution/run_monitoring はこのファイルを検知して終了）
  - data/kill.flag: KillSwitch が危険検知時に書き込むフラグ（ExecutionEngine はこのフラグを検知して停止）
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag が自動でクリアされます（本番では注意）

注意:
- stop_requested.flag は運用者が手動で作成してプロセスを停止するための仕組みです。
- kill.flag はシステム側（KillSwitch）から生成される「強制停止」シグナルです。運用時は kill.flag の扱いに注意してください。

## よく使うコマンド例
- .env を作る（対話式）
  - python -m kabusys.config_setup
- 設定を検証
  - python -m kabusys.validate_config
- Execution をデバッグ起動（ペーパートレード）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Monitoring を起動（ポーリング 30 秒）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

## 開発者向けメモ
- 自動 .env ロードを無効化する場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- ロギング設定は kabusys.utils.logging_setup.setup_logging を各スクリプトが呼んで統一しています。テスト時はログディレクトリをモックするか、level を DEBUG に設定してください。
- OpenAI を使う機能（news_nlp, regime_detector）は API キーが必須です（環境変数 OPENAI_API_KEY または引数で渡す）。
- モジュールはできるだけ副作用を避け、純粋関数（portfolio 等）を用いてユニットテストがしやすい設計になっています。

## ディレクトリ構成（主要ファイル）
以下は src/kabusys 下のおおまかな構成（本リポジトリに含まれるファイルに基づく）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（Settings）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 株数計算・スケーリング・丸め
    - risk_adjustment.py      — セクターキャップ・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py      — Momentum/Volatility/Value 計算
    - feature_exploration.py  — 将来リターン / IC / 統計サマリ
    - __init__.py
  - ai/
    - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py      — レジーム判定（MA + LLM）
    - __init__.py
  - monitoring/
    - monitoring_db.py        — SQLite スキーマ / 永続化層
    - system_monitor.py       — システム状態 / データ鮮度監視
    - trade_monitor.py        — （存在する実装に依存）発注ログ監視
    - risk_monitor.py         — ドローダウン / ポジション制限監視
    - kill_switch.py          — Kill Switch（kill.flag 書込み）
    - monitoring_engine.py    — Monitor の統合実行器
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity
    - __init__.py

（補足）trade_monitor.py、ExecutionEngine、OrderManager 等の詳細実装はリポジトリの他ファイルに含まれます。ここでは主要な使用ポイントをまとめました。

---

README の内容はコードの現在の状態に基づいた要約です。実運用前に必ず python -m kabusys.validate_config で設定を検証し、テスト環境（paper_trading）で十分に検証してください。質問や追加で欲しいコマンド例・設定例があれば教えてください。