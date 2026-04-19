# KabuSys

KabuSys は日本株向けの自動売買・リサーチ基盤（軽量な実行エンジン、監視、ファクター計算、AI 補助モジュール等）です。本 README はコードベース（src/kabusys）の概要、機能、セットアップ手順、使い方、ディレクトリ構成をまとめたものです。

注意: このリポジトリは実際の発注や外部 API（kabuステーション / J-Quants / OpenAI 等）を利用する設計を含みます。本番運用時は環境設定・権限管理・検証を十分に行ってください。

---

## プロジェクト概要

- 自動売買の実行エンジン（ExecutionEngine）と、それを監視する Monitoring コンポーネントを提供します。
- ポートフォリオ構築（候補選定・重み付け・単元丸め）・リスク調整・ポジションサイズ計算の純粋関数群を提供します（DB 参照なしで純粋関数として使用可能）。
- DuckDB を用いたリサーチ（ファクター計算、特徴量解析）モジュールを備えています。
- OpenAI を利用したニュースの NLP スコアリング／市場レジーム判定をサポートします（API キー必要）。
- 監視ログの永続化は SQLite（デフォルト: data/monitoring.db）で行います。
- 実行環境切替（development / paper_trading / live）をサポート。`paper_trading` では MockBroker を用い、paper 専用 DB に記録します。

---

## 主な機能一覧

- 実行エンジン起動スクリプト
  - run_execution.py: ExecutionEngine を起動。`KABUSYS_ENV=paper_trading` の場合は MockBroker を利用して paper_trading DB に記録。
- 監視ループ起動スクリプト
  - run_monitoring.py: SystemMonitor を定期実行し、system_status / risk_logs / trade_logs / dashboard などへ記録。
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を変更可能（デフォルト 60 秒）。
- 設定管理
  - config_setup.py: 対話式ウィザードで `.env` を作成・更新。
  - validate_config.py: `.env` と `config/*.yaml` の検証 CLI。
- 監視・リスク管理
  - monitoring モジュール: SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, MonitoringEngine, MonitoringDB 等。Kill Switch によりフラグファイルで ExecutionEngine を停止可能。
- ポートフォリオ構築
  - portfolio モジュール: 候補選定、等重・スコア重み付け、セクター制限、レジーム乗数、ポジションサイズ計算。
- リサーチ
  - research モジュール: ファクター計算（モメンタム／バリュー／ボラティリティ）、将来リターン、IC 計算、統計サマリ等（DuckDB を利用）。
- AI（OpenAI）連携
  - ai.news_nlp: raw_news を集約し OpenAI でセンチメントを算出して ai_scores テーブルへ書込。
  - ai.regime_detector: ETF の MA200 とマクロニュースを組合せてレジーム判定し market_regime テーブルへ書込。
- ユーティリティ
  - utils: logging 設定、プロセス優先度／CPU affinity 設定等。
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成ツール（稼働率、約定成功率、レイテンシ等の集計・判定）。

---

## 必要な依存（主なもの）

以下のライブラリが使用されています。環境に応じて適切なバージョンをインストールしてください。

- Python 3.10+（| 型注釈などで 3.10 以上を想定）
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（config/*.yaml の検証を行う場合。未インストール時は検証をスキップ）

例（pip）:
pip install duckdb psutil openai pyyaml

（実運用では requirements.txt を用意して pip install -r することを推奨します。)

---

## セットアップ手順（簡易）

1. リポジトリをクローンし、仮想環境を作成／有効化
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

2. 依存をインストール
   - pip install duckdb psutil openai pyyaml

3. 対話式で `.env` を作成
   - python -m kabusys.config_setup
   - このスクリプトはデフォルトでプロジェクトルートの `.env` を生成します。

4. 設定検証（任意）
   - python -m kabusys.validate_config
   - 本番チェックを厳格に行う場合は --strict を付ける。

5. データディレクトリの作成（必要に応じて）
   - デフォルトでは data/ と logs/ が使用されます。.env で上書き可能。

6. OpenAI 等外部 API を使う場合は `.env` にキーを設定（OPENAI_API_KEY など）。

---

## 使い方（起動方法・主要コマンド）

- 環境変数の指定方法（例）：
  - KABUSYS_ENV=development
  - JQUANTS_REFRESH_TOKEN=...
  - KABU_API_PASSWORD=...
  - OPENAI_API_KEY=...
  - MONITOR_POLL_INTERVAL=30
  - SQLITE_PATH=data/monitoring.db
  - DUCKDB_PATH=data/kabusys.duckdb

- 設定ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- 監視ループ起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能。デフォルトは 60 秒。
  - 監視は常に本番的な SQLite パス（Settings.sqlite_path）を使用します（環境に依らず）。

- 実行エンジン起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）に記録します。
  - 実行中の停止は data/stop_requested.flag または data/kill.flag 等でコントロールします（KillSwitch により kill.flag が書かれると Engine に停止シグナルが送られます）。

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可能）

- AI 機能（ニューススコア／レジーム判定）:
  - ai モジュールの関数を呼ぶか、上記の ExecutionEngine 内から利用されます。利用には OPENAI_API_KEY が必要です。
  - AI の呼び出しは外部 API を伴うため、テスト時は該当呼び出し関数をモックすることを推奨します。

---

## 重要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能使用時に必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト: data/paper_trading.db)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- LOG_DIR (ログ保存先、デフォルト: logs/)
- MONITOR_POLL_INTERVAL (監視ポーリング間隔（秒）; run_monitoring.py の場合)

設定は `.env`（.env.local）または実行環境の環境変数で管理します。`config_setup.py` で対話的に生成できます。

---

## 停止・Kill スイッチ

- data/kill.flag: KillSwitch が書き込むフラグファイル。存在すると ExecutionEngine に対して停止シグナルを送る設計です。
- data/stop_requested.flag: run_monitoring/run_execution が監視している停止フラグ。存在時にループを終了します。
- 実行開始時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動クリアする挙動を制御できます（本番では 0 を推奨）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys の主要モジュール（抜粋）です。

- kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数 / .env 自動読み込み・Settings クラス
  - config_setup.py — .env 対話ウィザード
  - validate_config.py — 設定検証 CLI
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト

  - ai/
    - news_nlp.py — ニュースを LLM でスコアリングして ai_scores に保存
    - regime_detector.py — 市場レジーム判定（MA200 + マクロニュース）
  - monitoring/
    - monitoring_db.py — SQLite による監視ログ永続化（schema 作成・アクセス API）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — （発注ログの監視、コード参照）
    - risk_monitor.py — ドローダウン & ポジション数監視
    - kill_switch.py — フラグファイルでの停止制御
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py — （LINE 等への通知管理）
  - execution/
    - execution_engine.py — 実行エンジン本体（EngineConfig 等）
    - broker_factory.py — BrokerClient の生成（Mock / 実ブローカ切替）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 実行に関する各コンポーネント
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数決定・単元丸め・集約キャップ処理
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - data/
    - pipeline.py, stats.py, ...（DuckDB 用パイプライン / 統計ユーティリティ）
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポートスクリプト
  - utils/
    - logging_setup.py — ログ設定ユーティリティ（Stream + TimedRotatingFile）
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

（上記に挙がっていないファイルや細かい実装はソースツリーを参照してください）

---

## 開発・運用上の注意

- KABUSYS_ENV の値によって実挙動が変わります（特に発注部分）。paper_trading と live を混同しないでください。
- .env は機密情報（API トークン等）を含むため決してリポジトリにコミットしないでください。
- OpenAI 等の外部 API 呼び出しは課金対象であり、レート制限やエラーに対するリトライ処理が組み込まれていますが、想定外の挙動が発生する可能性があります。テスト環境で十分に検証してください。
- ログは logs/<app_name>.log に日次ローテーションで保存されます。ログディレクトリ作成に失敗した場合は標準出力のみになります。
- SQLite/ DuckDB のパスは .env で調整可能です。運用時は適切なバックアップおよびディスク容量の監視を行ってください。

---

## よく使うコマンドまとめ

- 仮想環境作成・有効化:
  - python -m venv .venv
  - source .venv/bin/activate

- 依存インストール:
  - pip install duckdb psutil openai pyyaml

- .env 作成:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジン起動:
  - python -m kabusys.run_execution

- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

この README はコードから抽出した主要機能と利用方法の要約です。細かい API やクラスの挙動については該当モジュールの docstring を参照してください（例: ai/news_nlp.py、portfolio/position_sizing.py、monitoring/monitoring_db.py 等）。必要であれば、実行例や環境設定のテンプレート（.env.example）を別途作成します。