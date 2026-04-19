# KabuSys

日本株向けの自動売買システムのコアライブラリ群です。ポートフォリオ構築、ポジションサイジング、発注管理、監視、Paper Trading 向け検証、ニュースの NLP スコアリング等の機能を含みます。

---

## プロジェクト概要

KabuSys は日本株の自動売買運用を想定したモジュール群です。設計方針として以下を重視しています：

- 本番 / ペーパートレードの分離（DB も分離）
- 監視（System / Trade / Risk）と Kill Switch による安全停止
- DuckDB を使ったリサーチ・ファクター計算（独立した分析基盤）
- OpenAI を利用したニュース NLP と市場レジーム判定（オプション）
- 設定ウィザード・検証ツールを備え、運用前チェックを容易にする

---

## 主な機能一覧

- 起動スクリプト
  - run_execution: ExecutionEngine（発注エンジン）起動
  - run_monitoring: SystemMonitor のポーリングループ起動
- 設定関連
  - config_setup: 対話式で .env を作成/更新するウィザード
  - validate_config: .env / config/*.yaml の事前検証 CLI
- 監視・安全機構
  - SystemMonitor / TradeMonitor / RiskMonitor（監視ロジック）
  - MonitoringEngine（各 Monitor を束ねるポーリングエンジン）
  - KillSwitch（条件に応じて data/kill.flag を書き込み ExecutionEngine を停止）
- データ永続化
  - monitoring_db: SQLite による監視ログ・ダッシュボード保存（自動マイグレーション含む）
  - DuckDB: 研究用途（prices_daily / raw_financials 等）
- ポートフォリオ構築
  - 候補選定、重み付け（等額 / スコア加重）、ポジションサイズ計算、セクターキャップ、レジーム乗数
- リサーチ
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン・IC・統計サマリ
- AI（オプション）
  - news_nlp: OpenAI を使ったニュースセンチメントの銘柄別スコア化
  - regime_detector: MA200 とマクロニュースで日次レジーム判定
- ユーティリティ
  - ロギング設定（コンソール + 日次ローテーションファイル）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
  - tools.paper_verification_report: Paper Trading の成績・健全性レポート生成

---

## 動作要件

- Python 3.10+
- 必須（機能に応じて）
  - duckdb
  - psutil
- AI 機能を使う場合
  - openai（OpenAI API クライアント）
- YAML 検証を使う場合（validate_config）
  - PyYAML

インストール例（venv 推奨）:
- 仮想環境作成
  - python -m venv .venv
  - source .venv/bin/activate  # Windows: .venv\Scripts\activate
- 必要パッケージをインストール（例）
  - pip install duckdb psutil openai pyyaml

※ requirements.txt は本リポジトリに含まれていないため、利用する機能に応じて上記パッケージを追加してください。

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作る
   - git clone <repo-url>
   - cd <repo-root>
   - python -m venv .venv
   - source .venv/bin/activate

2. 必要パッケージをインストール
   - pip install duckdb psutil
   - OpenAI を使う場合: pip install openai
   - validate_config で YAML 検証を使う場合: pip install pyyaml

3. 初期設定（.env）
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成（プロジェクトルート）
     - 例（最低限必要な環境変数）:
       - JQUANTS_REFRESH_TOKEN=your_token_here
       - KABU_API_PASSWORD=your_password_here
       - KABUSYS_ENV=development
       - DUCKDB_PATH=data/kabusys.duckdb
       - SQLITE_PATH=data/monitoring.db
       - LOG_LEVEL=INFO

4. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 警告も厳格に扱う場合: python -m kabusys.validate_config --strict

5. 必要なディレクトリ（data, logs 等）は自動作成されますが、権限に注意してください。

---

## 環境変数（主なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境
  - KABUSYS_ENV: development | paper_trading | live
    - paper_trading の場合、ExecutionEngine は MockBrokerClient を使用し paper_trading 用 DB に書き込みます
- データベース / ファイルパス
  - DUCKDB_PATH: 分析用 DuckDB のパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH: Execution PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH: Kill Flag のパス（デフォルト: data/kill.flag）
- その他
  - LOG_LEVEL: ログレベル（DEBUG/INFO/...）
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（1/0）
  - PAPER_FILL_MODE: ペーパートレード時の約定挙動（instant | partial | never | reject）
  - OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）

---

## 起動・使い方

主要な実行コマンドはモジュール形式で提供されています。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が利用され、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します（本番 DB と分離）。
    - data/stop_requested.flag が存在すると起動を中止したりループ停止のトリガーになります。
    - ExecutionEngine 側の停止は data/kill.flag を書き込む（KillSwitch が作成）ことで行います。

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使って監視ログを記録します。
  - 停止は data/stop_requested.flag を作成するか、Ctrl+C（KeyboardInterrupt）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

- AI 機能（プログラムから呼び出す）
  - ニュース NLP スコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key=...)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=...)

- ログ
  - デフォルトは logs/<app_name>.log（日次ローテーション、30日分保持）
  - setup_logging() を各スクリプトが呼び出します
  - コンソールは stdout に出力されます

- 停止 / Kill Switch
  - KillSwitch は条件（ドローダウン超過、ポジション上限等）に応じて data/kill.flag を作成します。
  - ExecutionEngine は kill.flag を検出すると安全に停止するよう設計されています。
  - 手動で停止したい場合:
    - 停止指示（monitoring 側）: echo "reason" > data/kill.flag
    - 監視ループを止めたい場合: touch data/stop_requested.flag

---

## 注意事項 / 運用上のポイント

- Paper Trading と Live の DB は分離されています。KABUSYS_ENV を適切に設定してください。
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=1 を避けることを推奨します（自動で Kill Flag をクリアしてしまうと安全機構が無効化される可能性があります）。
- OpenAI を使う機能は API コスト・レイテンシやエラーを考慮しています。API キーの管理に注意してください。
- ログディレクトリや data ディレクトリの作成に失敗した場合、ファイル出力は無効化されコンソール出力のみとなることがあります。
- run_monitoring はデフォルトで monitoring DB（SQLITE_PATH）を使用します。監視データは永続化され自動マイグレーションを行います。

---

## ディレクトリ構成（抜粋）

以下は主要モジュールの構成と役割の抜粋です（src/kabusys 配下）。

- src/kabusys/
  - __init__.py — パッケージ定義（__version__ 等）
  - config.py — 環境変数読み込み・Settings
  - config_setup.py — .env 対話ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py — 統一的なログ設定
    - process_priority.py — プロセス優先度・CPU affinity 設定
  - monitoring/
    - monitoring_db.py — SQLite 用永続化層（テーブル作成・API）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 発注ログ監視（滞留注文等） ※実装ファイルあり
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — Kill Switch（flag ファイル操作）
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py — 通知管理（LINE 等）（実装ファイルあり）
  - execution/  — 発注関連のコンポーネント群（BrokerFactory, ExecutionEngine, OrderManager 等）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数算出
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — ファクター計算（momentum, volatility, value）
    - feature_exploration.py — 将来リターン・IC・統計
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py — 市場レジーム判定（OpenAI）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成

（上記は抜粋です。詳細なファイルは src/kabusys 以下を参照してください。）

---

## よく使うコマンドまとめ

- 環境ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- Execution 起動: python -m kabusys.run_execution
- Monitoring 起動: python -m kabusys.run_monitoring
- Paper 検証レポート: python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

---

README はプロジェクトの概要と基本的な使い方をまとめたものです。細かな設定や実装の詳細は各モジュール（src/kabusys 以下の .py ファイル）に記載された docstring を参照してください。必要であれば、README に追加したい具体的な内容（デプロイ手順、systemd サービス設定例、運用チェックリスト等）を教えてください。