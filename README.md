# KabuSys

日本株向け自動売買システム（ライブラリ／実行スクリプト群）

このリポジトリは、戦略・ポートフォリオ構築、発注（ExecutionEngine）、監視（Monitoring）、研究用ユーティリティ、AI を使ったニュース解析などを含む自動売買システムのコア実装です。

---

## プロジェクト概要

KabuSys は以下を目的としたコンポーネント群を提供します。

- 株価・財務データを用いたファクター計算・特徴量作成（research）
- ポートフォリオ構築（候補選定・重み付け・株数決定・セクター制約など）
- 発注エンジン（ExecutionEngine） — 本番／ペーパートレード対応
- システム監視（SystemMonitor / TradeMonitor / RiskMonitor）と Kill Switch
- AI を用いたニュースセンチメント評価（OpenAI 経由）
- 運用支援ツール（.env ウィザード、設定検証、Paper Trading レポート）
- ロギング、プロセス優先度設定、DB マイグレーション等のユーティリティ

主要なデータストアは DuckDB（分析用）と SQLite（監視・発注ログ・ペーパートレード用）です。

---

## 機能一覧

- config/ 環境設定（.env 自動ロード、Settings クラス）
- 対話式 .env 生成ウィザード（kabusys.config_setup）
- 起動前チェック（kabusys.validate_config）
- ExecutionEngine（本番 / paper_trading 切替、MockBroker の利用）
- Monitoring（定期ポーリング、プロセス生存確認、データ鮮度チェック、各種アラート、Kill Switch）
- RiskMonitor（ドローダウン・ポジション上限検出、risk_logs 記録）
- Portfolio: 候補選定・重み付け・ポジションサイズ計算・セクターキャップ、レジーム調整
- Research: モメンタム・バリュー・ボラティリティ等のファクター計算、将来リターン・IC 計算
- AI: ニュースのセンチメント（news_nlp）／市場レジーム判定（regime_detector） — OpenAI API 利用
- 運用ツール: Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）
- ユーティリティ: ログ設定、プロセス優先度、psutil を使ったシステム情報取得、DB 初期化/マイグレーション

---

## セットアップ手順

1. Python 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージのインストール（例）
   - pip install -r requirements.txt
   ※ リポジトリに requirements.txt がない場合、少なくとも以下が必要になります:
     - duckdb
     - psutil
     - openai（AI 機能を使う場合）
     - PyYAML（config YAML 検証を行う場合）
   （環境に合わせて追加してください）

3. .env の作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - もしくは手動でプロジェクトルートに `.env` を作成し、以下の主要変数を設定します（例）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - KABUSYS_ENV=development | paper_trading | live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LOG_LEVEL=INFO
     - OPENAI_API_KEY=...  （AI 機能を使用する場合）
   - 自動ロードはデフォルトで有効。無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにしたい場合は `--strict` を指定

5. データディレクトリとログディレクトリ
   - デフォルトでは `data/` と `logs/` を使用します。必要に応じて作成してください（setup_logging が自動で作成を試みます）。

---

## 環境変数（主なもの）

- KABUSYS_ENV: execution 環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuステーション API のベース URL（デフォルト localhost）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_DIR: ログ出力先ディレクトリ（デフォルト logs/）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY: OpenAI を使う機能の API キー
- MONITOR_POLL_INTERVAL: SystemMonitor のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading 時の約定挙動（instant / partial / never / reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"0" or "1"）

---

## 使い方

主要な実行スクリプトはパッケージモジュールとして起動します。プロジェクトルートで仮想環境を有効にして実行してください。

- 環境設定ウィザード（.env の作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視プロセス起動（SystemMonitor のポーリングループ）
  - MONITOR_POLL_INTERVAL 環境変数で秒数を上書き可能（例: export MONITOR_POLL_INTERVAL=30）
  - python -m kabusys.run_monitoring
  - 監視は常に本番用の sqlite_path を使用して monitoring テーブルを初期化します。

- 実行エンジン起動（ExecutionEngine）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）にデータを記録します。
  - python -m kabusys.run_execution

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは環境変数 `PAPER_TRADING_SQLITE_PATH` または `--db` オプションで指定可能。

- AI 機能
  - OpenAI API キーが必要です（OPENAI_API_KEY）。news_nlp.score_news や regime_detector.score_regime を利用するモジュールはキーがない場合 ValueError を投げます。

停止・運用に関する注意:

- 停止フラグ: 実行スクリプトはプロジェクトルートの `data/stop_requested.flag` を監視しており、存在するとループを終了します。
- Kill Switch: `data/kill.flag` が作成されると ExecutionEngine に停止シグナルが送られます（Settings.kill_flag_path により経路は変更可）。`KILL_FLAG_CLEAR_ON_START=1` を設定することで起動時に自動クリアできますが、本番では推奨されません。
- PID ファイル: `data/execution.pid`（デフォルト）などが使用されます。

ログ:

- 標準出力（stdout）と日次ローテーションファイル（logs/<app_name>.log）へ出力されます。ログディレクトリは `LOG_DIR` 環境変数で変更可。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 & Settings クラス、自動 .env ロード
  - config_setup.py          — 対話式 .env ウィザード（python -m kabusys.config_setup）
  - validate_config.py       — 起動前の設定検証 CLI
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite ベースの監視 DB 初期化 / 永続化 API
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — 注文状態監視（滞留注文・約定異常等）
    - risk_monitor.py        — ドローダウン・ポジション数監視
    - kill_switch.py         — kill.flag 制御
    - monitoring_engine.py   — 複数 Monitor をまとめるエンジン
    - alert_manager.py       —（アラート送信ロジック、LINE 連携等）
  - execution/
    - execution_engine.py    — ExecutionEngine（セッション起動・発注処理）
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み付け
    - position_sizing.py     — 株数計算・上限・単元丸め
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py            — ニュースを OpenAI でセンチメント化して ai_scores に書き込む
    - regime_detector.py     — ETF MA 等とマクロ NLP を組み合わせて市場レジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート（コマンドライン）
- config/
  - *.yaml                   — 各種設定テンプレート（system_config.yaml 等）
- data/
  - （デフォルト SQLite / PID / flag / などがここに置かれます）
- logs/
  - execution.log, monitoring.log, ...（タイムローテーション）

---

## 運用上のメモ / 注意点

- KABUSYS_ENV が `live` の場合は本番動作になります。LINE 通知設定など本番向けのガード・確認を十分に行ってください（validate_config に警告機能あり）。
- paper_trading 環境は本番 DB と分離されます（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI 呼び出しは外部 API に依存するため、レート制限や一時エラーが発生しうる。news_nlp・regime_detector ではリトライとフォールバック実装がありますが、API キーの管理やコストに注意してください。
- DB スキーマ変更は monitoring_db.init_monitoring_db に簡単なマイグレーションコードが含まれます。大幅な変更は慎重に扱ってください。
- ログディレクトリの作成に失敗した場合はファイルハンドラが無効化され、コンソールのみの出力になります（警告表示）。

---

## 開発・拡張のヒント

- research モジュールは DuckDB 接続を受け取り SQL と Python で計算する設計です。prices_daily / raw_financials テーブルに依存します。
- AI モジュールはテスト容易性を考慮して API 呼び出し関数を分離しているため、ユニットテストでは該当関数をモックしてください（例: unittest.mock.patch）。
- ロギングは全体で統一された setup_logging を使ってください（アプリ名別にログファイルが生成されます）。
- モジュール間で副作用（.env の自動ロードや sqlite3.Connection の row_factory 設定等）があるため、単体テスト時は環境変数や DB ファイルパスを分離して利用してください。

---

この README はコードベースから主要な使い方・構成を抜粋したものです。個別モジュールの詳細な仕様（引数・戻り値・動作の微妙な挙動）については該当ソースの docstring を参照してください。質問や補足があればお知らせください。