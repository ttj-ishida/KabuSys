# KabuSys

日本株向けの自動売買システム（ライブラリ / 実行スクリプト群）

このリポジトリは、戦略・ポートフォリオ構築、発注実行、監視、リサーチ、ニュースNLP／レジーム判定などのコンポーネントを含む自動売買プラットフォームの一部実装です。  
この README はソースコード（src/kabusys 以下）に基づき、プロジェクト概要、機能、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買を目的としたモジュール群です。主な設計方針は以下のとおりです。

- 戦略・ポートフォリオ構築ロジックは純粋関数で実装（副作用を極力排除）。
- 発注・リスク管理・リコンシリエーション等の Execution 層を別プロセスで稼働。
- 監視（Monitoring）コンポーネントは別プロセスでポーリングし、問題検出時に Execution を停止可能（Kill Switch）。
- Paper Trading モードでは本番 DB / 発注 API と完全に分離された Mock 実装と専用 DB を使用。
- DuckDB を分析用 DB、SQLite を監視・発注ログ用に利用。
- OpenAI を用いたニュースセンチメント（news_nlp）・レジーム判定（regime_detector）をサポート（API キー必須）。

---

## 主な機能一覧

- Execution（実行）
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - Paper Trading: MockBrokerClient と専用 SQLite（data/paper_trading.db）による分離
  - リスク管理、オーダー管理、リコンシリエーション等の統合

- Monitoring（監視）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine（run_monitoring.py）
  - SQLite ベースの監視 DB（監視テーブル・ログ保存）
  - Kill Switch（data/kill.flag）を用いた Execution 停止シグナル

- Portfolio（ポートフォリオ構築）
  - 候補選定、等重／スコア重み、ポジションサイズ計算、セクター上限適用、レジーム乗数

- Research（リサーチ）
  - ファクター算出（モメンタム、ボラティリティ、バリュー）
  - 特徴量探索（将来リターン計算、IC 計算、統計サマリ）

- AI（OpenAI 利用）
  - news_nlp: ニュースを集約して LLM に問合せ、銘柄ごとにセンチメントを算出し ai_scores に書き込み
  - regime_detector: MA とマクロニュースの LLM 評価を組み合わせた市場レジーム判定

- ツール
  - 設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）

---

## セットアップ手順（開発 / 実行環境）

1. Python 環境の準備（推奨: virtualenv / venv）
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリのインストール
   - 必要な主要ライブラリ（プロジェクトにより追加が必要になる場合があります）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config YAML 検証を行う場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （※ requirements.txt はこの配布に含まれていない場合があります。実行時に import エラーが出たライブラリを追加してください。）

3. プロジェクトルートに移動（.git または pyproject.toml を基準に自動検出）
   - config.py は .env / .env.local を自動で読み込みます（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

4. 環境変数の設定（.env を作る）
   - 対話式ウィザード推奨:
     - python -m kabusys.config_setup
   - あるいは .env を直接作成（.env.example を参考にする想定）。
   - 重要な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要なオプション（デフォルト値は括弧内）
     - KABUSYS_ENV: development | paper_trading | live (development)
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_LEVEL: INFO
     - OPENAI_API_KEY: OpenAI を使う場合は設定必須（news_nlp / regime_detector）
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring で参照）

5. 設定検証（起動前推奨）
   - python -m kabusys.validate_config
   - 警告をエラー扱いにする場合は --strict を付与

6. データディレクトリ作成
   - デフォルトで logs/、data/ 等を使用。必要に応じてディレクトリを作成してください。
   - ログ: logs/<app_name>.log（TimedRotatingFileHandler による日次ローテーション）

---

## 使い方（主要スクリプト）

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- ExecutionEngine 起動（本番 / ペーパーいずれも）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）にトランザクションを記録します。
    - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
    - 実行中、停止シグナルは data/stop_requested.flag を作ることで与えられます。

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - 環境にかかわらず monitoring 用には本番 sqlite_path（SQLITE_PATH）を使用します。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、デフォルト 60）。
    - 停止検出: data/stop_requested.flag を見る。停止フラグでループ終了。
    - 監視は SystemMonitor（プロセス稼働・データ鮮度等）、TradeMonitor、RiskMonitor を利用してログ・アラート・kill.flag 生成等を行います。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数より優先）

- AI モジュール（OpenAI 必須）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - raw_news / news_symbols / ai_scores を操作。OpenAI API キーを渡すか環境変数 OPENAI_API_KEY を設定。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

- ログ設定
  - 全スクリプトで共通の logging 設定関数が用意されています:
    - from kabusys.utils.logging_setup import setup_logging
    - デフォルトで stdout と logs/<app_name>.log（日次ローテート）に出力。
    - LOG_LEVEL 環境変数でデフォルトログレベルを変更可能。

---

## ファイル / ディレクトリ構成（概要）

以下は src/kabusys 内の主要モジュールです（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/.env 読み込み・Settings 定義
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 環境・設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - execution/               — Execution 層（BrokerFactory, ExecutionEngine, OrderManager...）
    - (実装ファイル群)
  - monitoring/
    - monitoring_db.py       — SQLite 監視 DB 初期化 + 永続化 API (MonitoringDB)
    - system_monitor.py      — システム監視（プロセス、生存、データ鮮度）
    - trade_monitor.py       — 注文関連監視（滞留注文、約定異常など）
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — kill.flag の書き込み/クリア
    - monitoring_engine.py   — 各モニタを束ねるエンジン
    - alert_manager.py       — アラート送信（LINE 等、実装に依存）
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 発注株数計算（丸め・制限）
    - risk_adjustment.py     — セクター制限・レジーム乗数
  - research/
    - factor_research.py     — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — IC / 将来リターン / 統計サマリ
  - ai/
    - news_nlp.py            — ニュースセンチメント（OpenAI 呼び出し・結果書込）
    - regime_detector.py     — 市場レジーム判定（MA + マクロニュース）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト

補足:
- デフォルトの DB / ログパスは Settings（config.py）で定義されます:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - LOG_DIR: logs/
  - PID / flag ファイル: data/execution.pid, data/kill.flag, data/stop_requested.flag など

---

## 運用上の注意点

- KABUSYS_ENV:
  - development: 開発用（発注なし / テスト）
  - paper_trading: ペーパー（MockBroker を使用、専用 DB に記録。本番 DB と完全に分離）
  - live: 本番（実際に発注）
  - 本番 (live) 設定時は LINE 通知や KILL_FLAG の扱いなどを慎重に確認してください（validate_config のチェックを利用）。

- Kill Switch:
  - RiskMonitor 等が条件を満たすと kill.flag を書き込み、Execution の停止を誘発します。起動時に KILL_FLAG_CLEAR_ON_START を 1 にすると自動クリアされますが、本番では 0 を推奨します。

- OpenAI API:
  - news_nlp / regime_detector は OpenAI（gpt-4o-mini 等）を利用します。API キーを環境に設定してください。API 利用時は呼び出し回数・コストに注意してください。失敗時は安全側のフォールバックを行う設計になっていますが、結果の妥当性は運用で確認してください。

- DB マイグレーション:
  - monitoring_db.init_monitoring_db は既存 DB に対して安全にカラム追加を行うコードを含みます（冪等）。

---

## 参考コマンドまとめ

- 仮想環境作成・有効化
  - python -m venv .venv
  - source .venv/bin/activate

- インストール（例）
  - pip install duckdb psutil openai PyYAML

- .env 作成ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Execution 起動
  - python -m kabusys.run_execution

- Monitoring 起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要に応じて README の補足（依存関係の固定、CI 設定、デプロイ手順、コンフィグ YAML の生成方法、各モジュールの詳細ドキュメント等）を追加できます。特に本番運用を想定する場合は、運用手順（ログローテーション、バックアップ、監視アラートの受信先設定）や安全対策（Kill Switch の取り扱い、API キー管理方針）を文書化することを推奨します。