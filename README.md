# KabuSys

日本株向け自動売買システムのコアライブラリ群。ポートフォリオ構築、ポジションサイジング、リスク制御、監視、Paper Trading 用の検証ツール、AI を使ったニュース/レジーム判定などを含みます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
  - 環境設定ウィザード
  - 設定検証
  - ExecutionEngine（発注エンジン）起動
  - Monitoring（監視）起動
  - Paper Trading 検証レポート生成
  - AI 関連（ニュース NLP / レジーム判定）
  - ライブラリ API の利用例（研究・ポートフォリオ）
- 重要な環境変数
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株自動売買を目的としたモジュール群です。  
設計方針の主な特徴：
- 発注ロジックと研究（リサーチ）ロジックを分離
- DuckDB（時系列/財務データ）と SQLite（監視・取引ログ）を併用
- Paper Trading 用の分離 DB をサポート（実口座と完全分離）
- モジュール化された監視（System / Trade / Risk）と Kill Switch による安全停止
- OpenAI を用いたニュースセンチメント / マクロ判定（オプション）

---

## 機能一覧

- 設定管理
  - .env 自動ロード（プロジェクトルート検出）
  - 対話式環境設定ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
- 実行系
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - Paper Trading モード（MockBrokerClient）と専用 SQLite（data/paper_trading.db）
- 監視系
  - SystemMonitor / TradeMonitor / RiskMonitor の統合（monitoring_engine）
  - kill.flag による外部停止シグナル
  - 監視 DB（SQLite）にログ永続化（monitoring_db）
- ポートフォリオ構築
  - 候補選定、重み計算（等金額 / スコア重み）
  - ポジションサイジング（risk-based, equal, score）
  - セクターキャップ、レジーム乗数
- リサーチ
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン、IC（Information Coefficient）計算、統計サマリー
- AI
  - news_nlp: ニュース記事のセンチメントを OpenAI で評価して ai_scores へ格納
  - regime_detector: ETF とマクロ記事を統合して market_regime を作成
- ツール
  - Paper Trading 用検証レポート生成スクリプト（tools.paper_verification_report）

---

## セットアップ手順

1. Python 環境
   - 推奨: Python 3.10+
   - 仮想環境を作成して有効化:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール（例）
   - 必要な主な依存:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（validate_config で YAML 検証を行う場合に必要）
   - 例:
     - pip install duckdb psutil openai pyyaml

   （プロジェクトに requirements.txt がない場合、上記を個別にインストールしてください）

3. プロジェクトルートの確認
   - .git または pyproject.toml を基準にプロジェクトルートを自動検出します。

4. 初期設定 (.env)
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - もしくは .env を手動で作成（下の「重要な環境変数」を参照）。

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

6. データディレクトリ作成（必要に応じて）
   - デフォルトでは data/ ディレクトリを使用します。ログは logs/ 配下に保存されます。

---

## 使い方

以下は主要 CLI / 実行例です。いずれもプロジェクトルートから実行できます。

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動（実運用 / ペーパートレード共通）
  - python -m kabusys.run_execution
  - 実行時挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）にログを記録します。
    - 停止フラグ: data/stop_requested.flag を作成すると起動中のエンジンを停止できます。
    - PID ファイル: data/execution.pid（設定により変更可）

- Monitoring 起動（監視ポーリングループ）
  - python -m kabusys.run_monitoring
  - 動作:
    - 監視ループはデフォルト 60 秒間隔で実行（環境変数 MONITOR_POLL_INTERVAL で秒数を上書き可能）
    - 監視は環境にかかわらず本番用 sqlite_path を使用して監視ログを記録します（デフォルト: data/monitoring.db）
    - 停止フラグ: data/stop_requested.flag を作成するとループを終了します

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH / --db で変更可）

- AI 関連（ニュース NLP / レジーム判定）
  - OpenAI API キーを環境変数 OPENAI_API_KEY に設定するか、関数呼び出し時に api_key を渡します。
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - 注意: API コールは課金対象となります。API キー管理は慎重に。

- ライブラリ API の利用（研究・ポートフォリオ）
  - 研究モジュール（kabusys.research）は DuckDB 接続を受け取り、prices_daily / raw_financials 等のテーブルを参照して計算を行います。
  - ポートフォリオモジュール例:
    - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes
    - candidates = select_candidates(buy_signals, max_positions=10)
    - weights = calc_equal_weights(candidates)
    - sizes = calc_position_sizes(weights, candidates, portfolio_value, available_cash, current_positions, open_prices)

---

## 重要な環境変数

主要なものを抜粋します。詳細は config.py を参照してください。

必須（本番で必要）
- JQUANTS_REFRESH_TOKEN — J-Quants API トークン
- KABU_API_PASSWORD — kabuステーション API パスワード

一般
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/…）
- LOG_DIR — ログ出力ディレクトリ（デフォルト: logs）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレードの約定挙動: instant|partial|never|reject
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動でクリアするか（1 はクリア。production では 0 推奨）
- KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）

停止・制御用ファイル
- data/kill.flag — ExecutionEngine の即時停止（Kill Switch のトリガ）
- data/stop_requested.flag — run_* スクリプトの外側ループ停止用（停止をリクエストするファイル）
- data/execution.pid — 実行エンジンの PID 書き込み先（デフォルト）

※ .env は自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

---

## ディレクトリ構成

主要ファイル・ディレクトリの抜粋:

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数・設定管理
    - config_setup.py          — 対話式 .env ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — Monitoring 起動スクリプト
    - tools/
      - paper_verification_report.py — Paper Trading 検証レポート
    - utils/
      - logging_setup.py       — 統一ロギング設定
      - process_priority.py    — プロセス優先度 / CPU affinity 設定
    - monitoring/
      - monitoring_db.py       — SQLite 永続化層（監視用）
      - system_monitor.py
      - trade_monitor.py       — （コードベースに存在。監視ロジック）
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py       — （アラート送信ロジック）
    - execution/
      - execution_engine.py
      - broker_factory.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
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
    - data/                    — 実行時に使うファイル（logs/, data/ 等）
      - *.db, pid, flag ファイル など

（上記はソース内に含まれる主要モジュールを抜粋したものです）

---

補足: 本リポジトリはモジュール群としての提供を想定しており、個別機能の詳細（BrokerClient 実装や ExecutionEngine の詳細な設定値、監視の閾値など）は該当モジュールの docstring / コメントに記載されています。実運用前には必ず python -m kabusys.validate_config により設定検証を行い、KABUSYS_ENV を適切に設定してください。

必要であれば README に「systemd サービス定義」や「デプロイ手順（Docker / コンテナ）」のテンプレートも追加できます。ご希望があれば教えてください。