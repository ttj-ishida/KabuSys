# KabuSys

日本株向けの自動売買・研究用ライブラリ群です。ポートフォリオ構築、発注エンジン、監視、研究（ファクター計算）、
およびニュースNLPを用いたAI支援モジュールなどを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の観点をカバーするモジュール群で構成されています。

- 発注（ExecutionEngine）: ブローカークライアント経由で注文を管理・送信する実行エンジン
- 監視（Monitoring）: システム状態、注文ログ、リスク（ドローダウン・ポジション数）を定期監視し、Kill Switch を発動可能
- ポートフォリオ構築（Portfolio）: 候補選定、重み計算、ポジションサイズ決定、セクターキャップ等の純粋関数
- 研究（Research）: DuckDB 上でファクター計算・特徴量解析、将来リターン計算・IC 等
- AI（AI）: OpenAI を用いたニュースセンチメント解析（銘柄毎スコア）および市場レジーム判定
- ユーティリティ: 設定読み込み、ログ設定、プロセス優先度設定など

設計方針の一部:
- DB は DuckDB（分析用）・SQLite（監視／発注ログ）を使用
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と分離して paper_trading.db に記録
- 外部 API（OpenAI など）は環境変数経由でキーを与える
- ルックアヘッドバイアス対策やフェイルセーフ設計（API失敗時のフォールバック）を重視

---

## 主な機能一覧

- Execution
  - ExecutionEngine の起動スクリプト: run_execution.py
  - BrokerClientFactory による本番 / モックブローカー切替（KABUSYS_ENV に依存）
  - 注文履歴・trade_logs の永続化、リスク管理（RiskManager）や Reconciler 等

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク・データ鮮度・プロセス稼働検知
  - TradeMonitor: 注文の滞留 / 約定異常検出（trade_logs 参照）
  - RiskMonitor: ドローダウン / ポジション数監視と dashboard 更新
  - KillSwitch: 条件に応じて data/kill.flag を書き込み ExecutionEngine の停止をトリガ
  - run_monitoring.py によるポーリングループ実行（ポーリング間隔は MONITOR_POLL_INTERVAL で上書き可）

- Portfolio
  - 候補選定、等重／スコア加重、リスクベース配分、セクター制約、レジーム乗数、単元丸めなど

- Research
  - calc_momentum / calc_volatility / calc_value：DuckDB 上の prices_daily / raw_financials を用いたファクター計算
  - calc_forward_returns / calc_ic / factor_summary：特徴量探索用関数群

- AI
  - news_nlp.score_news：OpenAI を使ってニュースを銘柄別にセンチメントスコア化し ai_scores テーブルへ書込
  - regime_detector.score_regime：ETF（1321）MA とマクロニュースの LLM スコアを合成して市場レジーム判定

- ツール
  - config_setup.py: .env の対話式初期作成ウィザード
  - validate_config.py: 環境変数・config/*.yaml の事前検証 CLI
  - tools.paper_verification_report: Paper Trading の稼働・注文成功率等の検証レポート生成

---

## セットアップ手順

以下は一般的なセットアップ手順の例です。プロジェクト特有の依存は requirements.txt 等に記載されている前提です。

1. Python 環境
   - 推奨: Python 3.10+（duckdb, psutil, openai 等が必要）

2. リポジトリをクローン / 配置
   - git clone ... またはパッケージとして配置

3. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux / macOS)
   - .venv\Scripts\activate     (Windows)

4. 依存関係インストール
   - pip install -r requirements.txt
   - または最低限: pip install duckdb psutil openai

5. .env の作成（推奨）
   - 対話式ウィザードを利用:
     - python -m kabusys.config_setup
   - ウィザードで生成された .env は決して Git にコミットしないでください。

6. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL になります

7. データディレクトリ等（必要に応じて作成）
   - data/ （デフォルトの SQLite / pid / flag 保存先）
   - logs/ （ログ出力先）
   - これらは起動時に自動作成されますが、権限等で失敗する場合は手動作成してください

---

## 必要な環境変数（主なもの）

※ .env で管理するのが便利です。config_setup ウィザードで主要項目が生成できます。

- 認証関連
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - OPENAI_API_KEY (AI 機能を使う場合、score_news / score_regime 等)

- 実行環境指定
  - KABUSYS_ENV: development | paper_trading | live
    - paper_trading: MockBroker を使用し data/paper_trading.db に分離
    - live: 本番（実際に発注）

- ロギング・パス
  - LOG_LEVEL (DEBUG|INFO|...)
  - LOG_DIR (ログ保存ディレクトリ)
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト: data/paper_trading.db)

- その他（監視 / Kill Switch）
  - PID_FILE_PATH (デフォルト: data/execution.pid)
  - KILL_FLAG_PATH (デフォルト: data/kill.flag)
  - KILL_FLAG_CLEAR_ON_START (起動時に kill.flag を自動クリアするか: 0/1)

- Paper Trading の挙動
  - PAPER_FILL_MODE: instant | partial | never | reject

- モニター制御
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）

詳細は kabusys.config.Settings クラスのプロパティを参照してください。

---

## 使い方（主要スクリプト）

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し PAPER_TRADING_SQLITE_PATH を使う（本番 DB と分離）
    - 起動前に data/stop_requested.flag が存在する場合は起動せず終了
    - 終了させたいときは data/stop_requested.flag を作成する（または kill.flag を書き込ませる）

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で指定可能（デフォルト: 60）
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（監視 DB は共通で運用）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH (PAPER_TRADING_SQLITE_PATH より優先)

- AI 関連
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key=None)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=None)

注意点:
- run_execution / run_monitoring はロギング設定（logs/<app>.log）を作成します。ログディレクトリ作成に失敗した場合はコンソールのみ出力になります。
- 停止フラグ: run_execution/run_monitoring それぞれがプロジェクト内の data/stop_requested.flag を監視してループを抜けます。
- Kill Switch: RiskMonitor 等が条件を満たすと data/kill.flag を書き、ExecutionEngine に停止シグナルを送ります（Execution 側は起動時の KILL_FLAG_CLEAR_ON_START に応じて振る舞います）。

---

## 主要ファイル・ディレクトリ構成

（src/kabusys 以下を中心に抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                 — 設定/.env ロードと Settings クラス
    - config_setup.py           — .env 対話式ウィザード
    - validate_config.py        — 設定検証 CLI
    - run_execution.py          — ExecutionEngine 起動スクリプト
    - run_monitoring.py         — Monitoring ポーリング起動スクリプト

    - ai/
      - __init__.py
      - news_nlp.py             — ニュース NLP（OpenAI）による銘柄スコア
      - regime_detector.py      — 市場レジーム判定（MA + マクロ NLP）

    - monitoring/
      - monitoring_db.py        — SQLite モデル/永続化層
      - system_monitor.py       — システム状態・データ鮮度監視
      - trade_monitor.py        — （注文監視ロジック: 省略 / 参照）
      - risk_monitor.py         — ドローダウン / ポジション上限監視
      - kill_switch.py          — kill.flag 管理
      - monitoring_engine.py    — 各 Monitor を束ねるランナー
      - alert_manager.py        — （LINE 等通知の抽象化: 省略 / 参照）

    - execution/
      - execution_engine.py     — ExecutionEngine 本体
      - order_manager.py
      - order_repository.py
      - broker_factory.py
      - reconciler.py
      - risk_manager.py

    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py

    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py

    - tools/
      - __init__.py
      - paper_verification_report.py

    - utils/
      - logging_setup.py         — 共通ログ設定
      - process_priority.py      — プロセス優先度/CPU affinity 設定
      - __init__.py

- data/                         — デフォルトの DB / pid / flag 等（アプリ実行時に作成）
  - monitoring.db (SQLITE_PATH)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - kabusys.duckdb (DUCKDB_PATH)
  - execution.pid
  - kill.flag
  - stop_requested.flag

- logs/                         — ログファイル出力先（logs/execution.log, logs/monitoring.log 等）

---

## 運用上の注意・推奨事項

- .env は絶対にバージョン管理にコミットしないでください（API キー・パスワードなどの機密情報を含む）。
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=0 を推奨します（自動クリアは危険）。
- Monitoring は監視用 DB を用いるため、run_monitoring は監視用 SQLite のパス（SQLITE_PATH）に書き込みます。monitoring は常に本番 sqlite_path を参照する実装です。
- OpenAI を利用するモジュールは API 呼び出し失敗時にフォールバック動作を持ちますが、API キーとレート制限に注意してください。
- ログや DB の保存先に対するディスク容量と権限を事前に確認してください（ディスク満杯は運用上のリスクになります）。

---

README はここまでです。必要であれば以下を追記できます:
- 具体的なコマンド例（systemd / Supervisor / Docker 起動ユニットのサンプル）
- requirements.txt の推奨内容
- API の詳細ドキュメント（関数ごとの入出力仕様）
どの情報を追加したいか教えてください。