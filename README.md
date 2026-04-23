# KabuSys

日本株向け自動売買システムのコードベース README（日本語）

---

## プロジェクト概要

KabuSys は日本株の自動売買／研究パイプラインを想定したプロジェクトです。  
主な機能は以下を含みます:

- 発注・約定の実行エンジン（ExecutionEngine）
- 監視・アラート（System / Trade / Risk Monitor、Kill Switch）
- ポートフォリオ構築（銘柄選定、重み付け、ポジションサイズ計算）
- リサーチ機能（ファクター計算、特徴量探索、IC 計算）
- ニュース NLP を用いたセンチメントスコアリング（OpenAI 利用可）
- ペーパートレード用の分離 DB とレポート生成ツール
- 環境設定ウィザードおよび設定検証 CLI
- 共通ユーティリティ（ログ設定、プロセス優先度設定等）

設計方針として、実運用を意識した永続化（SQLite / DuckDB）、フェイルセーフ（API失敗時のフォールバック）、およびルックアヘッドバイアス対策が各モジュールで考慮されています。

---

## 機能一覧（概要）

- Execution
  - ブローカークライアント抽象化（実口座 / モック切替）
  - OrderManager, RiskManager, Reconciler を組み合わせた ExecutionEngine
  - ペーパートレード時は専用 SQLite（data/paper_trading.db）へ記録
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク・プロセス生存・データ鮮度チェック
  - TradeMonitor: 発注/約定ログから滞留や異常検出（trade_logs）
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch: フラグファイル (data/kill.flag) による強制停止シグナル
  - MonitoringEngine: 上記を束ねたポーリングループ
- Portfolio
  - 銘柄選定、等重/スコア加重、リスクベースのポジションサイズ計算
  - セクターキャップ、レジーム乗数
- Research
  - ファクター計算（Momentum / Value / Volatility 等）
  - 将来リターン、IC（Spearman）や統計サマリー
- AI
  - news_nlp: OpenAI を使ったニュースセンチメント（ai_scores テーブルへ書き込み）
  - regime_detector: ETF MA とマクロニュースを組み合わせた市場レジーム判定
- Tools
  - config_setup: .env の対話式作成/更新ウィザード
  - validate_config: .env / config/*.yaml の事前検証 CLI
  - paper_verification_report: ペーパートレード結果の検証レポート生成

---

## 要件（抜粋）

- Python 3.10+
- 必須 Python パッケージ（例）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config ファイルパース・検証時にあると便利）
- SQLite（標準ライブラリで利用）
- 環境によっては追加の依存や OS 権限（プロセス優先度設定など）が必要

（実際の依存はプロジェクトの pyproject.toml / requirements.txt を参照してください）

---

## セットアップ手順

1. リポジトリをクローン / 配布パッケージを展開

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows では .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - あるいは個別に: pip install duckdb psutil openai pyyaml

4. 環境変数設定（.env）
   - 対話式ウィザードを利用:
     - python -m kabusys.config_setup
   - もしくは手動でプロジェクトルートに `.env` を作成
   - 主要な環境変数（抜粋）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — ペーパートレード用 DB（デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY — AI 機能を使う場合に必須
     - LOG_LEVEL — デフォルト: INFO

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 本番環境では --strict を付けて警告もエラー扱いにできます

6. データディレクトリ作成
   - デフォルトでは data/ が使用されます。ログは logs/ に出力されます。

---

## 使い方（実行 / CLI）

- 実行エンジンを起動
  - python -m kabusys.run_execution
  - 備考:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録します（本番 DB と分離）。
    - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
    - 実行中に data/stop_requested.flag を作成するとエンジンを安全に停止します。
    - 実行時に data/execution.pid に PID を書き込みます。

- 監視モジュールを起動
  - python -m kabusys.run_monitoring
  - 備考:
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視データの永続化先）。
    - 停止は data/stop_requested.flag の作成で検知します。

- .env を対話的に作る / 更新
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit 1）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション:
    - --db で PAPER_TRADING_SQLITE_PATH を直接指定可能

- ライブラリとしての利用（簡単な例）
  - ポートフォリオ構築関数:
    - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes
  - 研究用関数:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value
  - AI スコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")

---

## 重要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境（development / paper_trading / live）デフォルト: development
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY — OpenAI を使う機能で必要
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）

---

## ディレクトリ構成（主要ファイルと説明）

（プロジェクト内の `src/kabusys` を想定）

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — .env 自動読み込み・Settings クラス（さまざまな設定プロパティ）
  - config_setup.py — .env 対話式ウィザード CLI
  - validate_config.py — 起動前の設定チェック CLI
  - run_execution.py — ExecutionEngine 起動スクリプト（エントリポイント）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - monitoring/
    - monitoring_db.py — SQLite テーブル作成 / 永続化 API（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py — システム状態・データ鮮度チェック
    - trade_monitor.py — 発注/約定ログ監視（滞留/異常検出）  ※（ファイルは抜粋に含まれている前提）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の書込み・判定
    - monitoring_engine.py — 各モニタを束ねる
    - alert_manager.py — 通知（LINE など）管理（抜粋に含まれる想定）
  - execution/
    - execution_engine.py — ExecutionEngine 本体（EngineConfig 等）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py — 発注関連の実装（抜粋に含まれる想定）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 発注株数計算
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）で ai_scores にスコアを書き込む
    - regime_detector.py — レジーム判定（ETF MA + マクロセンチメント）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成ツール
  - utils/
    - logging_setup.py — 共通ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 運用上の注意・補足

- ペーパートレードと本番 DB は分離されています。KABUSYS_ENV=paper_trading の場合、Execution は PAPER_TRADING_SQLITE_PATH を使いますが、Monitoring は常に本番の sqlite_path を参照する設計です。
- 停止管理:
  - data/stop_requested.flag を run_* スクリプトが監視しており、このファイルが存在すると安全に終了します。
  - KillSwitch は data/kill.flag を作成して ExecutionEngine に停止を指示します（存在確認・クリア機能あり）。
- ロギング:
  - ログは stdout（console）と logs/<app_name>.log（日次ローテーション）に出力されます。ログレベルは LOG_LEVEL または引数で指定可能。
- OpenAI 利用:
  - OPENAI_API_KEY を環境変数か各関数引数で与えてください。
  - API 呼び出しはリトライやフェイルセーフが実装されていますが、利用トークンやコストに注意してください。
- バージョン管理:
  - .env は機密情報を含むため絶対に Git へコミットしないでください（config_setup のヘッダにも明記あり）。

---

README はこのコードベースの導入と日常的な実行に必要な最低限の情報をまとめています。詳細な実装や API（各モジュールの関数引数・返り値等）はソースコード中の docstring を参照してください。追加で「導入手順のステップごとのコマンド例」や「各コンポーネントのシーケンス図」などが必要であれば教えてください。