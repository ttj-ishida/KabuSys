# KabuSys

日本株向け自動売買システムのリポジトリ（パッケージ名: `kabusys`）。戦略・発注エンジン、監視・リスク管理、リサーチ/ファクター計算、ニュース NLP 等のコンポーネントを含みます。

---

## プロジェクト概要

KabuSys は以下の主要コンポーネントを備えた、プロダクション志向の自動売買フレームワークです。

- Execution Engine（発注・リスク管理・オーダー管理）
- Monitoring（システム稼働・注文・リスクの監視、Kill Switch）
- Portfolio Construction（候補選定・重み付け・ポジションサイズ決定）
- Research（ファクター計算・IC 計算・特徴量探索）
- AI モジュール（ニュース NLP によるセンチメント評価、レジーム判定）
- ユーティリティ（ログ設定・プロセス優先度設定・設定ウィザード・設定検証）
- 開発用ツール（Paper Trading 検証レポート生成）

設計方針の一部：
- 本番用 DB と Paper Trading DB を分離（`KABUSYS_ENV=paper_trading` で切替）
- .env による設定管理（`config_setup` ウィザードで作成）
- DuckDB を分析用途に利用、SQLite を監視/履歴保存に利用
- OpenAI API を用いる NLP 処理は API キー必須でフォールバックやリトライを実装

---

## 機能一覧

主な機能（抜粋）：

- Execution
  - ブローカークライアント抽象化（本番/モック切替）
  - OrderManager / Reconciler / RiskManager / ExecutionEngine
  - Paper Trading 向けの専用 DB（`data/paper_trading.db`）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスクの監視、データ鮮度、実行プロセス存在チェック
  - TradeMonitor: 注文滞留・約定異常検出（コード中に実装あり）
  - RiskMonitor: ドローダウン・ポジション上限チェック、ダッシュボード更新
  - KillSwitch: しきい値超過で `data/kill.flag` を書き込み Execution を停止
  - MonitoringEngine / run_monitoring スクリプト（ポーリング）
- Portfolio
  - 候補選定（スコア順、上位 N）
  - 重み計算（等金額・スコア加重）
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ決定（risk-based / equal / score）
- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB ベース）
  - 将来リターン、IC（Spearman）計算、ファクター統計
- AI
  - news_nlp.score_news: OpenAI でニュースをスコアリングして ai_scores に書込
  - regime_detector.score_regime: ETF MA とマクロニュースで市場レジーム判定
- ユーティリティ
  - 設定ウィザード: `config_setup.py`（.env の対話的作成）
  - 設定検証: `validate_config.py`（必須環境変数・YAML ファイル等のチェック）
  - ログ設定ユーティリティ（コンソール + 日次ローテート）
  - プロセス優先度 / CPU affinity 設定
- ツール
  - Paper Trading 検証レポート生成スクリプト（`kabusys.tools.paper_verification_report`）

---

## 前提 / 要件

必須（代表）パッケージ（プロジェクトにより変動するため、必要に応じて追加してください）：

- Python 3.10+
- duckdb
- psutil
- openai
- PyYAML（config YAML のパースが必要なら）
- その他: 標準ライブラリ（sqlite3 など）

例（pip）:
pip install duckdb psutil openai PyYAML

注意:
- 実際の requirements.txt がない場合はプロジェクトに合わせて依存を追加してください。
- OpenAI API を使う機能を利用する場合は環境変数 `OPENAI_API_KEY` を設定してください。

---

## セットアップ手順

1. リポジトリをクローンしてパッケージを配置（例: 開発環境）
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
4. .env を作成
   - 対話式ウィザードを使う（推奨）
     - python -m kabusys.config_setup
   - あるいは手動で `.env` をプロジェクトルートに作成
     - 主要なキー:
       - JQUANTS_REFRESH_TOKEN（必須）
       - KABU_API_PASSWORD（必須）
       - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
       - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
       - SQLITE_PATH（デフォルト: data/monitoring.db）
       - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
       - OPENAI_API_KEY（AI 機能を使う場合）
       - LOG_LEVEL（例: INFO）
       - KILL_FLAG_CLEAR_ON_START（本番では 0 推奨）
5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 警告を許容しない場合は --strict を付ける（警告で exit 1）

---

## 使い方（主要スクリプト / CLI）

各モジュールはパッケージとして直接起動できます。プロジェクトルート（`.git` や `pyproject.toml` があるディレクトリ）で実行してください。

- Execution Engine（実行/ペーパートレード）
  - python -m kabusys.run_execution
  - 挙動:
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、`data/paper_trading.db` に記録（本番 DB と分離）
    - 起動時に `data/stop_requested.flag` があれば起動しない
    - 実行中に `data/stop_requested.flag` が作成されると停止する
    - 起動時に PID を `data/execution.pid` に書き込む

- Monitoring（監視ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き（デフォルト: 60）
  - 監視は本番 sqlite_path を使用（環境にかかわらず）
  - 停止フラグ: `data/stop_requested.flag`

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - オプション: --strict（警告も FAIL 扱い）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 `PAPER_TRADING_SQLITE_PATH` または `data/paper_trading.db`

- AI / プログラム API（サンプル）
  - ニュース NLP:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key="...")
  - レジーム検出:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key="...")

備考:
- ログ: `kabusys.utils.logging_setup.setup_logging` が `logs/<app_name>.log` を出力（デフォルト daily rotate、30 日保持）。ログディレクトリは環境変数 `LOG_DIR` で変更可能。
- Kill Switch:
  - 監視コンポーネントの結果に基づき `data/kill.flag` を書き込むと Execution 側で停止シグナルとして利用されます。
  - `KILL_FLAG_CLEAR_ON_START=1` により起動時に自動クリアする設定が有りますが、本番では危険（デフォルト 0 推奨）。

---

## 環境変数一覧（主なもの）

必須（起動前に設定が必要）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要な任意 / デフォルト付き:
- KABUSYS_ENV (development / paper_trading / live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
- OPENAI_API_KEY — AI 機能利用時に必須
- LOG_LEVEL — デフォルト: INFO
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリア（0/1。production は 0 推奨）

設定ファイルは `.env` をプロジェクトルートに置くか、OS 環境変数を利用してください。自動ロードはデフォルトで有効ですが、テストなどで無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ配下の主要なファイル一覧（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / Settings 管理
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py (実装あり)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (実装あり)
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
  - data/
    - pipeline.py (価格データ取得等)
    - stats.py (zscore 等)
  - utils/
    - logging_setup.py
    - process_priority.py

補足:
- DB の実体ファイルはデフォルトで `data/` 配下（`data/kabusys.duckdb`, `data/monitoring.db`, `data/paper_trading.db`）。
- ログは `logs/` に格納されます（`LOG_DIR` で変更可）。
- stop/kill フラグ用ファイル:
  - data/stop_requested.flag — 起動/実行ループの停止フラグ（run_monitoring/run_execution がチェック）
  - data/kill.flag — Kill Switch が Execution を停止するために書き込むフラグ
  - data/execution.pid — Execution 起動時に書き込まれる PID

---

## 運用上の注意 / トラブルシューティング

- 本番運用時は `KABUSYS_ENV=live` を設定し、`validate_config.py` で警告を確認してください。特に LINE 通知設定や KILL_FLAG_CLEAR_ON_START の値は注意が必要です。
- OpenAI API を利用する機能は API レート制限・エラーに対してリトライを行いますが、キーが未設定だと例外を投げる箇所があります（`score_news`, `score_regime` 等）。
- DuckDB / SQLite に関するパス設定は `.env` で明示してください。親ディレクトリが存在しない場合は起動時に自動作成されることもありますが、権限等で失敗する場合があります。
- ログディレクトリ作成に失敗した場合はコンソール出力のみになる旨の警告が出ます。ディスク権限を確認してください。
- 停止や強制停止の操作は `data/stop_requested.flag` や `data/kill.flag` の状態を用いて行います。これらのファイル操作による操作は冪等性を考慮して設計されていますが、運用上は手順を統一してください。

---

README はここまでです。より詳細な API ドキュメントやモジュールごとの仕様書（例えば PortfolioConstruction.md, StrategyModel.md 等）が別途ある想定です。必要であれば、個別モジュールの使い方（関数シグネチャ、返り値、例）や依存関係をさらに展開した README を作成します。どの部分を詳しく書きたいか教えてください。