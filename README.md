# KabuSys

日本株向け自動売買システムのコードベース（ライブラリ + 起動スクリプト群）。  
このリポジトリはトレード実行エンジン、監視モジュール、ファクター・リサーチ、ポートフォリオ構築、AI（ニュース NLP / レジーム判定）などを含むフルスタックな自動売買フレームワークです。

バージョン: 0.1.0

---

## 概要

KabuSys は以下のような責務を持つモジュール群で構成されています：

- Execution: 発注・注文管理・リスク管理・再整合（ExecutionEngine）
- Monitoring: システム稼働監視、取引監視、リスク監視、Kill Switch（監視→停止シグナル）
- Research: DuckDB を用いたファクター計算・特徴量解析
- Portfolio: 候補選定・重み付け・ポジションサイジング・セクター制限
- AI: OpenAI を用いたニュースセンチメント（news_nlp）と市場レジーム判定（regime_detector）
- Tools: ペーパートレード検証レポート生成などのユーティリティスクリプト
- Utils: ロギング設定、プロセス優先度設定、環境設定読み込みなど共通ユーティリティ
- Config: 環境変数読み込み・Settings ラッパー、設定ウィザード、検証ツール

設計上、データベースは DuckDB（分析用）と SQLite（監視 / 発注ログ用）で分離して扱います。`KABUSYS_ENV=paper_trading` の場合はペーパートレード向けの専用 SQLite を使用し、本番 DB と分離されます。

---

## 主な機能一覧

- 実行エンジン
  - Broker クライアント抽象化（実口座 / モック切替）
  - Order Manager / Risk Manager / Reconciler / ExecutionEngine
- 監視
  - SystemMonitor: CPU/メモリ/ディスク/プロセス状態、データ鮮度チェック
  - TradeMonitor: 注文滞留・約定異常検出（trade_logs 参照）
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch: 条件に応じた停止フラグ生成（data/kill.flag）
  - MonitoringEngine: 各監視をまとめて定期実行・通知連携
- ポートフォリオ構築
  - 候補選定（スコア・順位）、等配分・スコア加重、ポジション数算出（lot 単位、リスクベース）
  - セクター集中制限、レジーム乗数
- リサーチ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB）
  - 将来リターン計算、IC（Spearman）計算、統計サマリ
- AI（OpenAI と連携）
  - ニュースセンチメント（銘柄ごとに -1.0〜1.0）
  - 市場レジーム判定（ma200 + マクロセンチメントの合成）
  - API 呼び出しは冪等性・リトライ・検証を考慮した安全実装
- ツール
  - Paper Trading 検証レポート生成（orders / system logs を集計して PASS/FAIL 判定）
- 設定・検証
  - 対話式 .env 作成ウィザード（config_setup）
  - 設定検証 CLI（validate_config）

---

## 必要条件 / 依存パッケージ

- Python 3.10+
- 主要依存（最低限）:
  - duckdb
  - psutil
  - openai
- オプション:
  - PyYAML（`validate_config` の YAML 検証時に必要）
- インストール例（仮想環境推奨）:
  - pip install -r requirements.txt
  - （requirements.txt が無い場合）例:
    pip install duckdb psutil openai pyyaml

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone ... && cd <repo>

2. 仮想環境を作成し依存をインストール
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
   - pip install duckdb psutil openai pyyaml

3. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を使う機能を使う場合は:
     - OPENAI_API_KEY を設定

4. 設定の検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります:
     - python -m kabusys.validate_config --strict

5. ディレクトリ（data, logs）を作成（多くは起動スクリプトが自動作成します）
   - mkdir -p data logs

注意:
- デフォルト DB パス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (monitoring): data/monitoring.db
  - Paper trading SQLite: data/paper_trading.db
- KABUSYS_ENV が `paper_trading` の場合は paper_trading 用 SQLite を使用します（設定: PAPER_TRADING_SQLITE_PATH）。

---

## 使い方（起動 / 各種コマンド）

- 実行エンジン起動（デフォルトは Settings に基づく動作）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定するとモックブローカー・専用 DB を使用します。
  - 実行中に停止させるには data/stop_requested.flag を作成するか kill flag を利用。

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書きできます（デフォルト: 60）。
  - 監視は常に本番用 sqlite_path を参照します（環境にかかわらず）。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- ライブラリ関数の利用（例）
  - ポートフォリオ:
    from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes
  - リサーチ:
    from kabusys.research import calc_momentum, calc_volatility, calc_value
  - AI（ニューススコア）:
    from kabusys.ai import score_news
    score_news(conn, target_date, api_key="YOUR_KEY")
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="YOUR_KEY")

- ログ
  - デフォルトでコンソール（stdout）および logs/<app_name>.log（日次ローテーション）に出力されます。
  - 環境変数 LOG_LEVEL / LOG_DIR で挙動を変更可能。

---

## 重要なファイル / フラグ

- data/stop_requested.flag
  - run_execution / run_monitoring のループ停止に使われる一時フラグ
- data/kill.flag
  - KillSwitch が検出をした場合に ExecutionEngine に停止を促すフラグとして書き込まれます
- data/execution.pid / data/*.pid
  - 実行エンジンの PID を保存する場所（Settings で上書き可能）
- .env / .env.local
  - 環境変数（Settings は自動で .env を読み込む。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）

---

## ディレクトリ構成（主要ファイルのみ）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み・Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (参照されるがコードベースにより存在)
  - execution/                — ExecutionEngine 関連（broker_factory, order_manager 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/ (runtime)
    - monitoring.db
    - paper_trading.db
    - kabusys.duckdb
    - kill.flag, stop_requested.flag, execution.pid
  - logs/ (runtime)
    - execution.log
    - monitoring.log
    - その他アプリケーションログ

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

重要（デフォルト値あり／オプション）:
- KABUSYS_ENV (development | paper_trading | live) — default: development
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB)
- LOG_LEVEL (DEBUG/INFO/...)
- LOG_DIR
- OPENAI_API_KEY (AI 機能を使う場合)
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング間隔秒)
- PAPER_FILL_MODE (instant | partial | never | reject)

詳細は `src/kabusys/config.py` を参照してください。

---

## 運用上の注意

- KABUSYS_ENV=live の場合は設定ミスが重大なリアルマネー損失に直結します。`validate_config` や .env の確認を厳重に行ってください。
- KillSwitch・監視はフェイルセーフを重視しており、条件により自動で data/kill.flag を書き込みます。`KILL_FLAG_CLEAR_ON_START` は本番環境で 1 にしないことを推奨します。
- OpenAI を利用するコードは API 利用料が発生します。テスト時は API キーの管理に注意してください。
- DuckDB / SQLite のファイルはバックアップ・権限設定を適切に行ってください。

---

## 開発・拡張のヒント

- DuckDB 接続を渡してリサーチ関数を直接実行できます（ユニットテストが容易）。
- AI 呼び出し部分は `_call_openai_api` をモック化してテスト可能な設計になっています。
- logging_setup を起動スクリプトの最初に呼び出すことでログ出力を統一できます。
- process_priority / set_cpu_affinity は psutil を利用。権限により失敗する場合は警告ログを出して継続します。

---

README は必要に応じてプロジェクト固有の実行手順や追加の運用マニュアルを追記してください。ソースの詳細な仕様は各モジュールの docstring を参照することを推奨します。