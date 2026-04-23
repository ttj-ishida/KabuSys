# KabuSys

日本株自動売買システムのコアライブラリ群と起動スクリプト群。  
戦略・ポートフォリオ構築、発注実行、監視、リサーチ、AI（ニュース NLP / レジーム判定）などの機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株を対象とした自動売買システム用のコンポーネント群です。  
主要な責務は次の通りです。

- シグナル → ポートフォリオ構築 → 発注数量計算 → 注文発行（ExecutionEngine）
- 実行状況・システム健全性の監視（Monitoring）
- Paper Trading（検証用の発注モック & 専用 DB）
- ファクター計算・リサーチ用ユーティリティ（DuckDB を想定）
- ニュースを LLM（OpenAI）で評価して AI スコアを生成
- 設定ウィザード/検証スクリプト、レポート生成ツール

設計方針の例:
- Paper Trading は本番 DB と完全分離（デフォルト: data/paper_trading.db）
- 監視は環境にかかわらず本番の sqlite_path を参照してログを残す
- LLM 呼び出しはフェイルセーフ設計（失敗時は安全側にフォールバック）

---

## 主な機能一覧

- Execution
  - ExecutionEngine（発注フロー、リスク管理、リコンシリエーション）
  - BrokerClientFactory（本番 or モックの切替）
  - Paper Trading モード（PAPER_FILL_MODE で約定挙動を制御）

- Monitoring
  - SystemMonitor（CPU/Memory/Disk、データ鮮度、プロセス生存確認）
  - TradeMonitor / RiskMonitor（滞留注文、ドローダウン、ポジション上限）
  - KillSwitch（条件発動で data/kill.flag を書き込み Execution を停止）
  - monitoring DB（SQLite）永続化層

- Portfolio Construction
  - 候補選定、等ウェイト／スコア加重、リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（単元株丸め、aggregate cap）

- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 特徴量探索（Forward Returns、IC、統計サマリ）

- AI（LLM）
  - news_nlp: ニュース記事を集約して OpenAI でセンチメントスコアを算出・保存
  - regime_detector: ETF の MA とマクロニュースで市場レジーム判定

- ツール
  - 環境設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
  - Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report

---

## 必要条件（概要）

- Python 3.9+（推奨: 3.10/3.11）
- 主要依存ライブラリ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config の詳細検証を行う場合）
- OS: Linux / macOS / Windows（プロセス優先度設定はプラットフォーム差分あり）

インストール例（仮）:
pip install duckdb psutil openai pyyaml

※ 実際の requirements.txt / lockfile がある場合はそちらを使ってください。

---

## セットアップ手順

1. リポジトリをクローン、プロジェクトルートへ移動。

2. 依存パッケージをインストール:
   - pip install -r requirements.txt
   - または必要なパッケージを個別にインストール（上記参照）

3. .env の作成（対話式ウィザード推奨）:
   - python -m kabusys.config_setup
   - 重要な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI 機能を使う場合:
     - OPENAI_API_KEY を環境変数または .env に設定

4. 設定の検証:
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

5. データディレクトリ作成:
   - デフォルトで使用されるディレクトリ: data/ logs/
   - .env の DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH 等を確認

6. （任意）Paper Trading DB 初期化やサンプルデータ投入を行ってください。

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）
  - paper_trading: Broker はモックを使用し data/paper_trading.db に記録
  - live: 本番
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- OPENAI_API_KEY（AI 機能で必要）
- DUCKDB_PATH（default: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB, default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB, default: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/...）
- LOG_DIR（ログ保存先）
- MONITOR_POLL_INTERVAL（監視ループのポーリング間隔、秒、default: 60）
- PAPER_FILL_MODE（paper_trading の約定挙動: instant / partial / never / reject）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか: 0/1）

---

## 使い方（起動・ツール）

- 環境ウィザード
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine（発注実行）
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使われ、発注ログは PAPER_TRADING_SQLITE_PATH に書き込まれます
    - 実行中は data/execution.pid に PID が書かれます
    - 停止は data/stop_requested.flag を作成するか、Kill Switch により data/kill.flag が書かれた場合に検出して停止します

- Monitoring（システム監視ループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書きできます
  - 監視は monitoring 用の sqlite (SQLITE_PATH) にログを残します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH

- AI / Research モジュール（ライブラリ API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - research モジュールは DuckDB 接続を受け取り計算を行います（例: calc_momentum）

---

## モードとデータ分離

- paper_trading モードは発注処理をモック化し、専用の SQLite ファイル（PAPER_TRADING_SQLITE_PATH）へ記録します。本番の監視 DB（SQLITE_PATH）とは別に保たれるためデータが混ざりません。
- 監視（Monitoring）は KABUSYS_ENV に関係なくデフォルトの sqlite_path（SQLITE_PATH）を使用して監視ログを記録します。

---

## 停止 / キルスイッチ動作

- 停止フラグ（run_execution / run_monitoring 停止）
  - data/stop_requested.flag を作成するとループを検出して優雅に停止します
- Kill Switch（リスク超過等で ExecutionEngine を止める）
  - KillSwitch は条件に応じて data/kill.flag を書き込みます
  - ExecutionEngine 起動時に kill.flag が存在すると起動を拒否します（安全機構）
  - KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動クリアします（本番では 0 推奨）

---

## ログ設定

- 共通ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="execution" 等)
- 出力:
  - コンソール（stdout）
  - 日次ローテートのログファイル: <LOG_DIR>/<app_name>.log（デフォルト logs/）
- LOG_LEVEL は環境変数または引数で指定可能

---

## 開発向け注意点

- DuckDB を使ったリサーチ/AI 部分はローカルに DuckDB ファイル（DUCKDB_PATH）を置いて利用します
- OpenAI API を使う機能は API キーが必要。失敗時はフォールバック（例: スコアを 0 にする等）する設計ですが、正しく動作させるにはキーを用意してください
- .env は絶対にリポジトリにコミットしないでください（config_setup にもその旨が記載されています）

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数／設定読み込みユーティリティ（自動 .env ロード）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（テーブル定義・CRUD）
    - system_monitor.py      — システム状態監視
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - monitoring_engine.py   — 各モニタの統合ポーリング
    - kill_switch.py         — kill.flag 管理
    - ...                    — alert_manager 等（詳細は各ファイル参照）
  - execution/
    - execution_engine.py    — エンジン本体（起動・セッション管理）
    - broker_factory.py      — Broker クライアント生成（本番 / モック）
    - order_manager.py       — 注文管理
    - order_repository.py    — 注文リポジトリ
    - reconciler.py          — 注文照合
    - risk_manager.py        — 発注時リスク制御
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 株数計算
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — ファクター計算（momentum, value, volatility）
    - feature_exploration.py — IC 等の分析ユーティリティ
  - ai/
    - news_nlp.py            — ニュースを LLM でスコア化して ai_scores に書き込む
    - regime_detector.py     — 市場レジーム判定（MA + マクロニュース）
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート生成
  - utils/
    - logging_setup.py       — ログ初期化ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定ユーティリティ
    - ...

その他、config/*.yaml（生成スクリプトあり）や data/、logs/ などの運用ディレクトリを使用します。

---

## よくある質問 / 備考

- Q: Paper Trading と本番 DB は混ざりますか？  
  A: 混ざりません。paper_trading モードでは paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使います。

- Q: LLM（OpenAI）を試すには？  
  A: OPENAI_API_KEY を設定し、ai.score_news / ai.regime_detector を呼んでください。API 呼び出しはリトライやフォールバック設計が施されています。

- Q: 監視ループの間隔は？  
  A: MONITOR_POLL_INTERVAL（秒）で設定可能。デフォルト 60 秒。

---

必要があれば README に手順のスクリーンショットや .env.example の雛形、より詳しい起動例（systemd / supervisor 用のユニットファイル例）を追加します。どの情報を優先して追記しますか？