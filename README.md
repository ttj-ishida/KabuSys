# KabuSys

日本株向け自動売買システムのプロトタイプ。ポートフォリオ構築、発注ロジック、監視、研究用ファクター計算、そして一部 AI を用いたニュースセンチメント評価を含むモジュール群で構成されています。

バージョン: 0.1.0

---

## 概要

KabuSys は次の目的を持つモジュール式のシステムです。

- データ準備・分析（DuckDB を利用）
- ファクター計算 / 研究ユーティリティ（research）
- ポートフォリオ構築（candidate 選定・重み付け・ポジションサイズ決定）
- 発注・ExecutionEngine（本番 / ペーパートレード分離）
- システム監視（プロセス・データ鮮度・リスク監視）と Kill Switch
- ニュース NLP による銘柄／マクロセンチメント評価（OpenAI 利用）
- 各種 CLI ユーティリティ（.env ウィザード / 設定検証 / レポート出力）

設計方針として、
- DB は DuckDB（分析）と SQLite（監視・注文ログ）を併用
- 本番 (live) / 開発 (development) / ペーパートレード (paper_trading) を環境変数で切替
- OpenAI を利用する箇所は API キー必須で、失敗時にフォールバックするフェイルセーフ実装
などが採用されています。

---

## 主な機能一覧

- Execution
  - ExecutionEngine による発注処理（紙トレ or 本番で挙動を切替）
  - RiskManager / OrderManager / Reconciler 等の実装（発注・リスク制御）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、プロセス稼働チェック
  - TradeMonitor: 注文の滞留や約定異常の検出
  - RiskMonitor: ドローダウン / ポジション上限監視とリスクイベント記録
  - KillSwitch: 条件を満たした際に data/kill.flag を書いて Execution を停止
  - MonitoringEngine: 上記監視を束ねて定期実行
- Portfolio
  - 候補選定、等配分・スコア加重配分、セクターキャップ適用、ポジションサイズ計算
- Research
  - ファクター（Momentum / Volatility / Value 等）計算（DuckDB 経由）
  - 将来リターン / IC 計算 / 統計サマリ機能
- AI
  - news_nlp: OpenAI でニュースを銘柄別にスコアリングして ai_scores に格納
  - regime_detector: ETF+マクロセンチメントを合成して market_regime を判定
- ツール
  - .env 設定ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）
- ユーティリティ
  - ロギング設定（logs 日次ローテーション）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 要件（概略）

必須パッケージ（プロジェクト環境に応じてインストールしてください）:

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（設定 YAML 検証を行う場合、無くても実行は可能）
（実際の requirements.txt がある場合はそれを参照してください）

---

## セットアップ手順

1. リポジトリをクローン / 取得し、プロジェクトルートへ移動。

2. 仮想環境を作成して有効化（例）:
   - python -m venv .venv
   - source .venv/bin/activate (Linux/macOS) または .venv\Scripts\activate (Windows)

3. 必要パッケージをインストール:
   - pip install duckdb psutil openai PyYAML
   - （ローカルでテストのみ行う場合は openai は不要）

4. 初期設定ファイル（.env）を作成:
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - もしくは .env.example をコピーして手動編集（リポジトリに例ファイルがある場合）

5. 設定検証:
   - python -m kabusys.validate_config
   - 重要な警告まで含めて失敗にしたい場合は --strict を付与

6. ログディレクトリ等の初期化は起動スクリプトが自動で行います（`logs/`、`data/` 等）。

---

## 環境変数（主なもの）

- KABUSYS_ENV: 実行環境 (development | paper_trading | live) — デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuステーション API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視 DB）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定モード (instant | partial | never | reject) — デフォルト: instant
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ保存ディレクトリ（デフォルト: logs）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時に必要）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒。監視スクリプトで上書き可。デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0。本番では 0 推奨）

---

## 使い方（代表的なコマンド）

- 環境設定ウィザード（.env 作成 / 更新）
  - python -m kabusys.config_setup

- 設定検証（.env / config/*.yaml の検証）
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視ループ起動（SystemMonitor を定期実行、SQLite にログを残す）
  - python -m kabusys.run_monitoring
  - 補足:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）
    - この監視は KABUSYS_ENV に関わらず monitoring 用の sqlite_path（settings.sqlite_path）を使用します
    - 停止はプロジェクトルート/data/stop_requested.flag を作成して行います

- ExecutionEngine 起動（発注エンジン）
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を用いて data/paper_trading.db に記録（本番 DB と完全分離）
    - 実行中の PID は data/execution.pid に書かれます。停止は data/stop_requested.flag で指示
    - 起動時に data/stop_requested.flag が既に存在する場合は起動せず終了します

- Paper Trading 検証レポート（SQLite の paper_trading DB を指定して集計）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で DB パスを明示可能。環境変数 PAPER_TRADING_SQLITE_PATH でも指定可。

- AI 系（ニュース NLP / レジーム判定）
  - OpenAI API キーが必須（OPENAI_API_KEY）
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼んで利用
  - 実行はスクリプト/Engine の一部として組み込めます（詳細は該当モジュール参照）

---

## 停止 / Kill Switch

- 手動停止（Execution 停止のためのフラグ）
  - data/kill.flag: KillSwitch が書き込まれるファイル。存在すると ExecutionEngine 等に停止シグナルとなる設計の場所があります。
  - data/stop_requested.flag: run_monitoring / run_execution 停止を指示するための外部制御ファイル（起動スクリプトで参照）

- 注意:
  - KILL_FLAG_CLEAR_ON_START=1 にすると Execution 起動時に kill.flag が自動クリアされます（開発用）。本番では 0 推奨。

---

## ロギング

- setup_logging ユーティリティにより、
  - コンソール出力 (stdout)
  - 日次ローテーションのファイル出力（logs/<app_name>.log、30日保持）
  が統一的に設定されます。

- ディレクトリ作成に失敗した場合はファイル出力を省略してコンソールのみになります。

---

## ディレクトリ構成（主要ファイル抜粋）

（`src/kabusys` 配下を想定）

- kabusys/
  - __init__.py
  - config.py                — 環境変数/設定管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — SQLite 監視テーブル用永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
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
  - data/                    — 実行時に利用するファイル群（data/*.db, flags, pid 等）
  - logs/                    — ログ保存先（デフォルト）

---

## 注意点 / 運用メモ

- DB 分離:
  - monitoring は settings.sqlite_path（通常 data/monitoring.db）を使用します。Monitoring は環境にかかわらず本番 sqlite_path を用いる設計になっている箇所がありますので運用時は注意してください。
  - Paper trading（KABUSYS_ENV=paper_trading）は専用 DB（PAPER_TRADING_SQLITE_PATH）に記録し、本番 DB と分離されます。

- OpenAI 利用:
  - news_nlp / regime_detector は OpenAI を使用します。API キー未設定時は明示的なエラーまたはフォールバックが行われます（モジュールにより挙動が異なります）。
  - API 呼び出しはレートリミット・ネットワーク障害等を考慮してリトライ実装が入っています。

- 環境自動読み込み:
  - config.py はプロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を自動読み込みします。自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- テスト・開発:
  - 多くの関数は副作用を持たない純粋関数（portfolio / research）として実装されています。ユニットテストが書きやすい設計です。
  - OpenAI 呼び出しや外部依存はモジュール内で注入／差し替え可能な形で実装されており、テスト時はモック可能です。

---

## 参照 / さらなる読み物

- 各モジュール内の docstring やコメントに詳しい設計意図・使用方法が書かれています。特に:
  - portfolio/*.py: PortfolioConstruction に基づく説明
  - research/*.py: StrategyModel / Factor 計算に関する注記
  - ai/*.py: prompt 設計、API リトライ方針など

---

問題や追加したい項目（例: requirements.txt、CI 設定、運用手順書など）があれば教えてください。README に追記して整備します。