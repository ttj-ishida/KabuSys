# KabuSys

日本株自動売買システム（ライブラリ / 実行スクリプト群）のリポジトリ README（日本語）。

この README はプロジェクト概要、主な機能、セットアップ手順、使い方、ディレクトリ構成を説明します。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買／リサーチ基盤です。  
主な要素は以下です。

- 実行エンジン（ExecutionEngine）: 注文発行、リスク管理、オーダー管理を行う。
- 監視（Monitoring）: システム状態、注文状況、リスク指標を定期チェックしアラートや Kill Switch を管理。
- ポートフォリオ構築モジュール: 候補選定・重み付け・リスク調整・株数決定を行う純粋関数群。
- リサーチモジュール: DuckDB 上の株価・財務データからファクター計算や特徴量解析。
- AI モジュール: OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価、レジーム検出。
- ユーティリティ: 設定ウィザード、設定検証、ログ設定、プロセス優先度設定など。
- ツール: ペーパートレード検証レポート生成など。

設計方針として、DB を分離（paper_trading 用 DB は本番 DB と独立）、フェイルセーフ（API 失敗時はフォールバック）、ルックアヘッドバイアス回避（date.today を直接参照しない）などが取られています。

---

## 機能一覧（抜粋）

- 環境設定読み込み・ウィザード（.envの生成）: kabusys.config_setup
- 設定検証 CLI: kabusys.validate_config
- 実行エンジン起動スクリプト: run_execution.py
  - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、data/paper_trading.db に記録
- 監視ポーリング起動スクリプト: run_monitoring.py
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で変更可能
  - 監視は常に本番 sqlite_path を使用（環境に依存しない）
- 監視 DB 永続化（SQLite）ラッパー: monitoring.monitoring_db
- モニタ群: system_monitor, trade_monitor, risk_monitor, monitoring_engine
- Kill Switch: 条件に応じて data/kill.flag を書き込み ExecutionEngine 停止を指令
- ポートフォリオ構築: select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
- リサーチ: calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
- AI 関連: ニュース NLP（score_news）、市場レジーム判定（score_regime）
- ツール: Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
- ユーティリティ: ログ設定（utils.logging_setup）、プロセス優先度（utils.process_priority）

---

## セットアップ手順

前提:
- Python 3.9+（型ヒントでの union ｜ を使うため Python 3.10 以上が望ましいが、コードは 3.9+ でも動作する場合あり）
- SQLite（標準ライブラリで含まれる）
- その他ライブラリ: duckdb, psutil, openai, PyYAML（オプション: 設定検証で YAML の中身をチェックする場合）

1. リポジトリをクローンしてルートへ移動
   - git clone ...
   - cd <project_root>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - requirements.txt がない場合は最低限:
     - pip install duckdb psutil openai
     - 設定検証で YAML を使う場合: pip install PyYAML

4. .env を準備
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - あるいはルートに .env を配置（.env.example を参考にする）
   - 重要な環境変数（概要は下に記載）

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにしたい場合: python -m kabusys.validate_config --strict

6. データディレクトリの確認
   - デフォルト DB/log/flag ファイルの親ディレクトリ（data/、logs/）が存在するか確認。
   - 必要であれば手動で作成するかスクリプトが自動作成します。

---

## 環境変数（主なもの）

（.env に設定する項目の主な一覧。デフォルト値は括弧内に示す）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV ("development" | "paper_trading" | "live") (default: development)
  - paper_trading: MockBroker を使い data/paper_trading.db に記録
  - live: 本番向け（注意喚起あり）
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能を使う場合に必要)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db) — 監視用 SQLite（monitoring は常に sqlite_path を参照）
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- PAPER_FILL_MODE ("instant" | "partial" | "never" | "reject") (default: instant)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL) (default: INFO)
- LINE_CHANNEL_ACCESS_TOKEN (任意、アラート送信用)
- LINE_USER_ID (任意、アラート送信用)
- KILL_FLAG_CLEAR_ON_START (0/1) (default: 0) — Execution 起動時に kill.flag を自動クリアするか
- MONITOR_POLL_INTERVAL (監視ポーリング間隔秒、run_monitoring で参照、default: 60)

注意:
- .env は Git にコミットしないこと（秘密情報を含む）。
- 設定ウィザード（kabusys.config_setup）は .env の生成・更新を対話的に行えます。

---

## 使い方（主要コマンド）

- 環境ウィザード（.env の作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 動作概要:
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し data/paper_trading.db を使用
    - 実行中は data/execution.pid に PID が書かれる（設定で変更可能）
    - data/stop_requested.flag が存在すると起動を停止／実行中は停止要求を検出してエンジンを停止

- 監視モニタ起動（Polling）
  - python -m kabusys.run_monitoring
  - 動作概要:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き（デフォルト 60 秒）
    - 監視は常に 本番 sqlite_path（SQLITE_PATH） を使用する（環境に依存しない）
    - data/stop_requested.flag を検出すると監視ループを終了

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプションで --db パスを指定して別 DB を読むことも可能

- AI / リサーチ関数（ライブラリとして利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - kabusys.research.calc_momentum(conn, target_date) など
  - これらはコードからインポートして利用します（DuckDB 接続等を渡す）

---

## 実行時のフラグ / ファイル

- data/stop_requested.flag
  - 起動スクリプト（run_execution / run_monitoring）はこのファイルの存在を監視し、存在すると安全に停止する
- data/kill.flag
  - Kill Switch が書き込むファイル。ExecutionEngine に停止命令を与えるために使用
- data/execution.pid（デフォルト）
  - 実行エンジンの PID 保持ファイル

---

## ログ

- ログ設定は kabusys.utils.logging_setup.setup_logging によって統一的に行われます。
- デフォルトでは stdout（コンソール）と日次ローテートされるファイル（logs/<app_name>.log）に出力されます。
- ログディレクトリは LOG_DIR 環境変数や引数で変更可能。ファイル出力に失敗した場合はコンソールのみで継続します。

---

## トラブルシューティング（よくある注意点）

- 環境変数未設定による起動失敗:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必須。config_setup で設定、validate_config で確認できます。
- run_monitoring が DB に接続できない:
  - run_monitoring は常に sqlite_path（SQLITE_PATH）を使用します。DB ファイルのパーミッションやパスを確認してください。
- Paper Trading と本番 DB の混同防止:
  - paper_trading 環境では Execution は PAPER_TRADING_SQLITE_PATH を使いますが、Monitoring は常に SQLITE_PATH を参照します（設計仕様のため注意）。
- OpenAI を使う機能:
  - OPENAI_API_KEY が必要。API レート制限や一時エラーに対してはリトライ・フォールバック処理が入っていますが、API キーやネットワークの確認を行ってください。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要ファイル・モジュール一覧（抜粋）。

- src/
  - kabusys/
    - __init__.py
    - config.py                    — 環境変数 / Settings
    - config_setup.py              — .env 対話式ウィザード
    - validate_config.py           — 設定検証 CLI
    - run_execution.py             — ExecutionEngine 起動スクリプト
    - run_monitoring.py            — Monitoring ポーリング起動スクリプト
    - utils/
      - logging_setup.py           — ログ設定ユーティリティ
      - process_priority.py        — プロセス優先度 / CPU affinity
    - monitoring/
      - monitoring_db.py           — SQLite 永続化層
      - system_monitor.py
      - trade_monitor.py           — （trade モニタ、実装ファイルは存在）
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py           — （アラート送信ロジック）
      - monitoring_engine.py
    - execution/
      - execution_engine.py        — ExecutionEngine（主要ロジック）
      - broker_factory.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
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
      - news_nlp.py                 — ニュースセンチメント評価
      - regime_detector.py         — 市場レジーム判定
      - __init__.py
    - tools/
      - paper_verification_report.py
      - __init__.py
    - data/                         — 実行時に使用する DB・PID・flag ファイル（リポジトリには含めない）

（注）一部ファイル（trade_monitor.py、alert_manager.py、execution_engine の詳細等）はここで抜粋していませんが、コードベース内に存在します。

---

## 開発者向けメモ

- DuckDB を用いたリサーチ処理は conn（duckdb.DuckDBPyConnection）を受け取り SQL と Python を組み合わせて処理する設計です。データは prices_daily / raw_financials / raw_news 等のテーブルを想定。
- AI 呼び出しは OpenAI SDK（OpenAI）を想定。テストでは _call_openai_api をモック可能に設計されています。
- クリティカルな DB 書き込み処理（market_regime / ai_scores 等）はトランザクション（BEGIN/COMMIT/ROLLBACK）で保護されています。
- ローカル実行時は KILL_FLAG_CLEAR_ON_START を 0 にしておくこと（本番では特に注意）。

---

必要があれば、以下を追記して README を拡張できます:
- 詳細な環境変数テーブル（例: キー、説明、デフォルト、必須フラグ）
- 実行例（ログ抜粋、シナリオ別手順）
- データベーススキーマのダンプ
- 開発／デバッグ手順（ユニットテスト、モックの方法）

ほかに追加したい情報があれば教えてください。