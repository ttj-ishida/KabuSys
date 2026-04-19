# KabuSys

日本株自動売買システム「KabuSys」のリポジトリ向け README（日本語）。

この README は提供されたコードベースの要点（目的、機能、セットアップ、使い方、ディレクトリ構成）をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したモジュール群で、以下の主要責務を持ちます。

- 発注実行（ExecutionEngine）：ブローカークライアントを使った注文発行、リスク管理、オーダー調停など
- 監視（Monitoring）：システム状態・注文状態・リスク指標を定期的に監視し、必要に応じて Kill Switch を発動
- ポートフォリオ構築（Portfolio）：候補選定・ウェイト算出・ポジションサイジング・セクター制御などの純粋関数群
- リサーチ（Research）：DuckDB 上の価格・財務データからファクター計算・特徴量探索・IC算出
- AI 補助（AI）：ニュースの NLP によるセンチメント評価や市場レジーム判定（OpenAI API を利用）
- ツール類：ペーパートレード検証レポートなどユーティリティスクリプト
- 設定管理：.env ウィザード、設定検証 CLI、Settings 抽象化

設計方針の一部：
- ペーパートレード（KABUSYS_ENV=paper_trading）は本番 DB と完全分離（別 SQLite）
- DuckDB は分析用 DB（prices_daily 等）として使用
- 監視系は SQLite（monitoring.db）にログ永続化
- OpenAI 等の外部 API は API キーを環境変数で注入し、フェイルセーフ（失敗時はフォールバック）設計

---

## 主な機能一覧

- Execution
  - ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - ブローカー抽象化（実ブローカまたは MockBroker を環境に応じて使用）
  - リスク管理（最大ポジション比率・利用率・ドローダウン監視等）
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor の定期実行（python -m kabusys.run_monitoring）
  - kill.flag による Execution の強制停止（Kill Switch）
  - 監視ログを SQLite に永続化（system_status / trade_logs / risk_logs / dashboard / positions）
- Portfolio
  - 候補選定（スコア順）、等金額・スコア加重、リスクベースのポジションサイズ算出
  - セクターキャップ適用、レジーム乗数計算
- Research
  - モメンタム・ボラティリティ・バリューのファクター計算（DuckDB）
  - 将来リターン・IC（Information Coefficient）・統計サマリー
- AI
  - ニュースを OpenAI に送り銘柄ごとのセンチメントを ai_scores に書き込む（news_nlp）
  - ETF + マクロニュースを組合せた市場レジーム判定（regime_detector）
- ツール
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）

---

## 前提 / 必要条件

- Python 3.10 以上（コードベースでの型注釈に `|` を使用）
- 必要な Python パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証時に任意で使用）
- システムで SQLite ファイルやログディレクトリを書き込めること

（実際の requirements.txt がある場合はそれを参照してください）

---

## セットアップ手順（ローカル開発向け）

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML
     （プロジェクトで requirements.txt があればそれを利用：pip install -r requirements.txt）

3. .env の作成（対話式ウィザード）
   - python -m kabusys.config_setup
     - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
     - 環境: KABUSYS_ENV を development / paper_trading / live のいずれかで設定
     - paper_trading を使う場合、PAPER_FILL_MODE や PAPER_TRADING_SQLITE_PATH を確認

4. 設定の検証
   - python -m kabusys.validate_config
   - 問題があれば .env を修正して再検証
   - --strict を付けると警告もエラー扱い（exit code 1）

5. 必要ディレクトリの作成（通常はスクリプトが自動で作成しますが手動でも可）
   - mkdir -p data logs

---

## 環境変数（主要なもの）

- JQUANTS_REFRESH_TOKEN（必須）: J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD（必須）: kabuステーション API パスワード
- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（monitoring）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant / partial / never / reject）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ出力ディレクトリ（デフォルト: logs）
- KILL_FLAG_CLEAR_ON_START: 本番環境での kill.flag 自動クリア（0 / 1）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

注意:
- run_monitoring は Monitoring 用 DB 接続に常に本番 sqlite_path を使用します（環境に依存せず）。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path を使用して本番 DB と分離します。

---

## 使い方（主要スクリプト）

- .env 作成（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視ループ起動
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（秒、デフォルト 60）
    - 監視が停止すべき場合はプロジェクトルートの data/stop_requested.flag を作成（run_monitoring はこのファイルを検知して終了）
    - ログ: logs/monitoring.log（設定により stdout とファイル両方）

- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading とすると MockBrokerClient を使い、データは data/paper_trading.db に保存されます
    - エンジン実行中に停止させたい場合は data/stop_requested.flag を作成
    - 実行中は data/execution.pid（デフォルト）に PID が書き込まれる

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数より優先）

- AI モジュール（スコア付与 / レジーム）
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime
  - これらは DuckDB 接続と target_date を受け取り、OpenAI API を使用します（OPENAI_API_KEY 必須）

---

## ロギング / PID / Kill Switch

- ログ:
  - 共通の logging_setup があり、stdout と日次ローテーションファイル（logs/<app_name>.log）を設定
  - LOG_DIR 環境変数でディレクトリを上書き可能

- プロセス優先度:
  - run_monitoring / run_execution は起動時に set_process_priority("high") を呼ぶ（psutil を利用）
  - CPU affinity 設定関数も util に用意（必要に応じて呼ぶ）

- Kill Switch / 停止フラグ:
  - KillSwitch は data/kill.flag に理由を書き込み、ExecutionEngine に停止を促す
  - 手動停止や運用上の停止は data/stop_requested.flag を作成すると run_* スクリプトが検知して終了する

---

## データベース / マイグレーション

- 監視用 SQLite（init_monitoring_db による自動作成）
  - テーブル: system_status, trade_logs, positions, risk_logs, dashboard
  - 起動時に不足カラム（例: latency_ms, peak_value）があれば ALTER TABLE で追加入力する簡易マイグレーション処理あり

- DuckDB
  - prices_daily / raw_financials / raw_news / ai_scores / market_regime 等の分析テーブルを想定
  - Research / AI モジュールは DuckDB 接続を受け取って動作

---

## ディレクトリ構成（概観）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動ロード機能含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - execution/               — 発注実行関連（Engine / BrokerFactory / OrderManager 等）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（DB 初期化 + ラッパークラス）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
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
  - utils/
    - logging_setup.py
    - process_priority.py
  - tools/
    - paper_verification_report.py

プロジェクトルートには想定ファイル・ディレクトリ：
- .env, .env.local（環境変数）
- data/ (SQLite DB、PID、flagファイルなど)
- logs/ (ログファイル)
- config/ (yaml テンプレートや設定ファイル：system_config.yaml 等)

---

## 開発メモ / 注意点

- ペーパートレード: 本番データベースと完全に分離するため KABUSYS_ENV=paper_trading を利用してください。
- 外部 API（OpenAI 等）は課金やレート制限に注意。AI モジュールは失敗時にフォールバックする設計だが、運用ポリシーを決めてください。
- .env は機密情報を含むため絶対にリポジトリにコミットしないでください（config_setup のヘッダにも警告あり）。
- ログディレクトリや DB 親ディレクトリが存在しない場合、validate_config は警告を出します（起動時に自動作成される場合あり）。
- システム時計やタイムゾーンに依存する処理は UTC を基準にしている箇所が多く、ローカルタイムとの扱いに注意してください（news window 等は JST と UTC の変換ロジックあり）。

---

必要に応じて README に追加したい内容（例：詳細な API ドキュメント、ExecutionEngine の使い方、OrderManager/Repo のインターフェース仕様、運用 runbook など）があれば教えてください。README をそれに合わせて拡張します。