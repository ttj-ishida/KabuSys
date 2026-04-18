# KabuSys

日本株向け自動売買システムのミニマル実装。バックテスト・リサーチ用の DuckDB ベースのファクター計算、ペーパートレード対応の ExecutionEngine、システム／トレード監視と Kill Switch、LLM を用いたニュースセンチメント・レジーム検出など、取引運用に必要な主要コンポーネントを備えています。

---

## プロジェクト概要

- 名称: KabuSys
- 目的: 日本株の自動売買パイプライン（シグナル生成 → ポートフォリオ構築 → 発注 → 監視）を提供するライブラリ／実行環境。
- 主要機能:
  - ポートフォリオ構築（候補選定、重み付け、株数計算）
  - リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（単元丸め、集約キャップ）
  - リサーチ機能（モメンタム / ボラティリティ / バリュー等のファクター計算、IC 等）
  - AI モジュール（ニュースの NLP スコアリング、レジーム判定 via OpenAI）
  - ExecutionEngine（ペーパートレードと本番の分離、リスク管理、注文管理）
  - Monitoring（SystemMonitor / TradeMonitor / RiskMonitor、kill.flag による停止）
  - ユーティリティ（設定ウィザード、設定検証、ログ設定、プロセス優先度管理）
  - レポートツール（Paper Trading 検証レポート生成）

---

## 機能一覧（抜粋）

- 設定管理
  - .env 自動読み込み（プロジェクトルート検出）
  - 対話式環境設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
- 実行
  - ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - Monitoring 起動スクリプト（python -m kabusys.run_monitoring）
  - 停止/強制停止用フラグ（data/stop_requested.flag, data/kill.flag）
- ポートフォリオ構築
  - select_candidates, calc_equal_weights, calc_score_weights
  - calc_position_sizes（risk_based / equal / score）
  - apply_sector_cap, calc_regime_multiplier
- リサーチ
  - calc_momentum, calc_volatility, calc_value
  - calc_forward_returns, calc_ic, factor_summary, rank
- AI（OpenAI を利用）
  - ニュースセンチメントの取得と ai_scores への書き込み
  - マクロニュースを用いた日次レジーム判定（market_regime テーブル）
- 監視／アラート
  - MonitoringDB（SQLite）を中心とした永続化
  - SystemMonitor（CPU/メモリ/Disk、プロセス・データ鮮度）
  - RiskMonitor（ドローダウン、ポジション上限の検出）
  - KillSwitch（閾値超過時に data/kill.flag を書き込む）
- ツール
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）

---

## 動作要件（想定）

- Python 3.9+
- 必須ライブラリ（代表例）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
- 推奨: PyYAML（config/*.yaml の検証に使用）、SQLite（組み込み）、必要に応じて外部依存を pip で導入してください。

（プロジェクトに requirements.txt がない場合は上記を個別にインストールしてください。）

インストール例:
- 仮想環境作成
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- パッケージインストール例
  - pip install duckdb psutil openai PyYAML

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境を作成して有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows は .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML

4. 環境変数設定
   - 対話式に .env を作成する:
     - python -m kabusys.config_setup
     - ウィザードに従い J-Quants トークン、kabu API パスワード等を入力
   - もしくは .env を手動で作成（.env.example を参照）

5. 設定の検証
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります

6. data / logs ディレクトリの確認
   - デフォルトの DB / PID / flag ファイルは data/ 配下に置かれます。必要に応じて .env でパスを上書きしてください。
   - ログはデフォルト logs/ 配下に出力されます（LOG_DIR または setup_logging の引数で変更可能）。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabuステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- KABUSYS_ENV — 実行環境（development / paper_trading / live）
  - paper_trading 時は MockBroker を利用し、ペーパートレード専用 DB を使用する
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知設定（任意）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）
- PAPER_FILL_MODE — ペーパートレードの約定モード（instant/partial/never/reject）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト 60）

---

## 使い方（主要コマンド）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient が使われ、ペーパートレード DB（PAPER_TRADING_SQLITE_PATH）に記録されます。
  - 実行中に data/stop_requested.flag を作成すると停止シグナルとして検出して終了します。
  - PID ファイル: data/execution.pid（設定で変更可能）

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）
  - 監視は常に本番用 sqlite_path を使用します（環境に依らず監視 DB は共通）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH でも DB パスを指定可能

- AI 機能（プログラム経由）
  - ai.score_news(conn, target_date, api_key=None)
    - conn: duckdb.DuckDBPyConnection
    - target_date: datetime.date
    - api_key が None の場合 OPENAI_API_KEY 環境変数を使用
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)

注意:
- AI 機能を使うには OPENAI_API_KEY が必要です。
- 実運用（KABUSYS_ENV=live）では kill.flag 等の設定を特に注意してください（KILL_FLAG_CLEAR_ON_START は危険性があります）。

---

## ファイル / ディレクトリ構成（主要部分）

（リポジトリの src/kabusys 以下を抜粋した簡易ツリー）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - utils/
      - __init__.py
      - logging_setup.py
      - process_priority.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py      (参照あり)
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py      (参照あり)
    - execution/
      - execution_engine.py   (参照あり)
      - broker_factory.py     (参照あり)
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - data/ (ランタイム生成)
      - monitoring.db (デフォルト)
      - paper_trading.db (paper_trading 用)
      - kill.flag
      - stop_requested.flag
      - execution.pid
    - logs/ (ランタイム生成, ログファイルを保存)

（実際のファイルはリポジトリのルート構成に合わせて確認してください）

---

## 注意事項 / 運用上のポイント

- .env は決して Git にコミットしないでください（機密情報を含みます）。
- KABUSYS_ENV を live に設定する場合は、LINE通知や kill.flag の設定などを十分に確認してください。
- Monitoring は常に sqlite_path（本番 DB）を使用するため、監視先 DB の設定ミスがないよう注意してください。
- ペーパートレードは production DB と分離されるよう paper_trading 用のパスを設定してください（PAPER_TRADING_SQLITE_PATH）。
- プロセス優先度設定は set_process_priority により試みられますが、権限不足や非サポート OS の場合は警告が出てスキップされます。
- AI モジュールは外部 API を使うため、API エラーやレート制限へのリトライロジックが組まれていますが、API キーの漏洩・利用料には注意してください。

---

必要であれば、README にさらに詳しい API 使用例（コードスニペット）、設定のベストプラクティス、データベーススキーマ（monitoring tables の説明）を追記します。どの部分を詳細化したいか教えてください。