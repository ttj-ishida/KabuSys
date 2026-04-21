# KabuSys

日本株向け自動売買システムのライブラリ／起動スクリプト群（開発中）。
本リポジトリは注文実行エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ用ファクター計算、
および OpenAI を利用したニュース NLP / レジーム判定などの補助モジュールを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要なコンポーネント群を提供します。主な設計方針は次の通りです。

- 実行エンジン（ExecutionEngine）とモニタリングを分離して堅牢化
- Paper Trading（ペーパートレード）を本番 DB と完全分離して検証可能
- DuckDB を分析用データベース、SQLite を監視・履歴保存用に利用
- OpenAI（GPT 系）を用いたニュースセンチメントやレジーム判定を実装
- ロギング・プロセス優先度設定など運用に配慮したユーティリティを提供

---

## 機能一覧

- 起動スクリプト
  - run_execution: ExecutionEngine を起動（KABUSYS_ENV に応じて Paper/Live/Dev を切替）
  - run_monitoring: SystemMonitor をポーリングで実行
- 設定管理・CLI
  - config_setup: 対話式 .env 作成ウィザード
  - validate_config: 環境変数 / config/*.yaml の静的検証ツール
- 監視（monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor: システム・注文・リスクの監視
  - MonitoringDB: SQLite に監視ログを保存する永続化層（system_status, trade_logs, positions, risk_logs, dashboard 等）
  - KillSwitch: 条件により data/kill.flag を出力して ExecutionEngine を停止
  - MonitoringEngine: 各 Monitor を束ねるポーリングエンジン
- 実行（execution）
  - BrokerClientFactory（環境により MockBroker を選択）
  - OrderManager / OrderRepository / Reconciler / RiskManager / ExecutionEngine（発注制御、リスク制御、再整合）
- ポートフォリオ構築（portfolio）
  - 候補選定、重み計算、ポジションサイジング、セクター制限、レジーム乗数などの純粋関数群
- リサーチ（research）
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリーなど
- AI（ai）
  - news_nlp: raw_news を集約して OpenAI へ送信し銘柄単位のセンチメントスコアを ai_scores に書き込み
  - regime_detector: マクロニュース + ETF MA 乖離を合成して日次で市場レジーム判定
- ツール
  - paper_verification_report: ペーパートレード DB を解析して検証レポートを生成

ユーティリティ
- logging_setup: 統一的なログ設定（stdout + 日次ローテーションファイル）
- process_priority: プロセス優先度・CPU affinity 設定ユーティリティ
- config.Settings: 環境変数ラッパ（自動 .env ロード機能あり）

---

## セットアップ手順

前提:
- Python 3.10+ を想定
- システムに合わせて必要パッケージをインストール

推奨手順（例）:

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 必須（プロジェクトで使う主要ライブラリの例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config の検証に任意）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （requirements.txt があればそれを利用してください）

3. .env の初期作成（対話式）
   - python -m kabusys.config_setup
   - 各種キー（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を入力
   - .env は Git にコミットしないでください

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります: python -m kabusys.validate_config --strict

5. データディレクトリの確認
   - デフォルトのパス:
     - DuckDB: data/kabusys.duckdb（環境変数 DUCKDB_PATH で変更可）
     - Monitoring SQLite: data/monitoring.db（環境変数 SQLITE_PATH）
     - Paper Trading SQLite: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）
   - ログディレクトリ: logs/（環境変数 LOG_DIR で変更可）
   - 起動スクリプトは data ディレクトリ下の flag/pid ファイルを利用します（data/stop_requested.flag, data/kill.flag, data/execution.pid）

6. OpenAI を利用する場合
   - 環境変数 OPENAI_API_KEY を設定するか、ai モジュール呼び出し時に api_key 引数を渡してください

注意:
- KABUSYS_ENV は `development` / `paper_trading` / `live` のいずれか
- paper_trading モードでは MockBrokerClient を使用し、paper_trading.db に記録され本番 DB と分離されます

---

## 使い方（実行例）

基本的なコマンド例（プロジェクトルートで実行）:

- 実行エンジンを起動
  - python -m kabusys.run_execution
  - 実行中に data/stop_requested.flag を作成すると安全に停止します
  - 実行時に data/execution.pid が作成されます

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト 60）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

ライブラリ関数の利用例（Python REPL / スクリプト内）:

- ポートフォリオ関数
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes
  - candidates = select_candidates(buy_signals, max_positions=10)
  - weights = calc_score_weights(candidates)
  - shares = calc_position_sizes(weights, candidates, portfolio_value=100_000_000, available_cash=10_000_000, ...)

- リサーチ関数（DuckDB 接続が必要）
  - import duckdb
  - conn = duckdb.connect("data/kabusys.duckdb")
  - from kabusys.research import calc_momentum
  - records = calc_momentum(conn, target_date=date(2026,4,1))

- AI スコアリング（OpenAI API キーが必要）
  - from kabusys.ai import score_news
  - score_news(conn, target_date=date(2026,4,1), api_key="sk-...")

注意点（運用）:
- run_monitoring は Settings に依らず本番の sqlite_path（data/monitoring.db）を使用します
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path を使用して本番 DB と隔離します
- 停止方法:
  - run_* スクリプトは data/stop_requested.flag の存在を検知して停止します
  - KillSwitch は特定のリスク条件で data/kill.flag を書き込み ExecutionEngine を止める仕組みです
- ログ:
  - デフォルトで stdout と logs/<app_name>.log（日次ローテーション）に出力
  - 環境変数 LOG_DIR / LOG_LEVEL で変更可能

---

## 重要な環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN — 必須（J-Quants API）
- KABU_API_PASSWORD — 必須（kabuステーション API）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY — OpenAI を利用する場合に必要
- DUCKDB_PATH — デフォルト data/kabusys.duckdb
- SQLITE_PATH — 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 DB（デフォルト data/paper_trading.db）
- LOG_LEVEL — ログレベル（デフォルト INFO）
- LOG_DIR — ログ保存ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE — ペーパートレード時の約定挙動（instant|partial|never|reject）

---

## ディレクトリ構成（主要ファイル）

想定プロジェクトルート構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                    — Settings / .env 自動読み込みロジック
    - config_setup.py              — .env 作成ウィザード（対話式）
    - validate_config.py           — 設定検証 CLI
    - run_execution.py             — ExecutionEngine 起動スクリプト
    - run_monitoring.py            — SystemMonitor ポーリング起動
    - utils/
      - logging_setup.py           — ログ設定ユーティリティ
      - process_priority.py        — プロセス優先度 / CPU affinity
    - execution/
      - broker_factory.py
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
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
    - tools/
      - paper_verification_report.py
- data/
  - monitoring.db (SQLite)        — デフォルトの監視 DB
  - paper_trading.db (SQLite)     — Paper Trading 用 DB（paper_trading モード）
  - kabusys.duckdb                — デフォルトの DuckDB ファイル
  - stop_requested.flag           — 手動停止用フラグ（存在するとループが終了）
  - kill.flag                     — KillSwitch が書き込む停止フラグ
  - execution.pid                 — 実行エンジンの PID ファイル
- logs/
  - execution.log
  - monitoring.log
  - ... 日次ローテーションで保管

---

## 運用上の注意

- 本番（KABUSYS_ENV=live）では設定を慎重に確認してください。validate_config は live 向けの追加警告を出します。
- .env は絶対にコミットしないでください。config_setup のヘッダにも注意書きがあります。
- OpenAI API 呼び出しを行うモジュールはネットワーク障害や 5xx 等でリトライを行いますが、API_KEY 未設定時はエラーになります。テスト時は API 呼び出し部分をモックすることを推奨します。
- run_monitoring は監視 DB を直接使います。監視処理は本番の sqlite_path を参照する点に注意してください。
- process priority の設定やファイル書き込み権限など OS レベルの制約により機能が制限される場合があります（警告ログが出ます）。

---

## 追加情報 / 貢献

- 設計やドキュメント改善・テスト追加・実装のバグ修正など歓迎します。
- 新しい依存を追加する場合は requirements.txt / pyproject.toml を更新してください。
- API キーや機密情報は環境変数で管理してください。

---

以上が本コードベースの README.md の概要です。必要であれば「開発者向けセットアップ（デバッグ、テスト、モックの作り方）」や「各モジュールの API リファレンス」を追記します。どの章を優先して詳しくしますか？