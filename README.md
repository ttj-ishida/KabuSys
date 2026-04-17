README
=====

概要
----
KabuSys は日本株向けの自動売買システム（研究・ポートフォリオ構築・発注・監視・AI 補助機能を含む）のパッケージです。
主な目的は、DuckDB を使ったリサーチ・ファクター計算、ポートフォリオ構築ロジック、発注エンジン（本番 / ペーパートレード切替）および監視（モニタリング／キルスイッチ）を提供することです。

主な特徴
---------
- ポートフォリオ構築
  - 候補選定（スコア降順）、等配分 / スコア加重配分
  - ポジションサイズ計算（risk_based / equal / score）
  - セクター集中抑制・レジーム乗数
- 発注周り（Execution）
  - ExecutionEngine 組立て（Broker クライアントの抽象化）
  - paper_trading モードでは MockBrokerClient を使用、実 DB と分離
- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/ディスク、プロセス生存確認、株価データ鮮度チェック
  - TradeMonitor: 滞留注文・約定異常の検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード管理
  - KillSwitch: 条件に応じて data/kill.flag を作成して ExecutionEngine を安全停止
  - MonitoringEngine: 上記モニタを束ねポーリング実行
- AI サポート
  - news_nlp: OpenAI（gpt-4o-mini 等）でニュースをスコアリングし ai_scores に書き込み
  - regime_detector: MA200 とマクロニュースを合成して日次の市場レジーム判定
- 研究用モジュール
  - factor_research: Momentum / Volatility / Value 等のファクター計算（DuckDB ベース）
  - feature_exploration: 将来リターン、IC（Spearman）や統計サマリ
- ツール
  - 環境設定ウィザード（.env の生成）: kabusys.config_setup
  - 設定検証 CLI: kabusys.validate_config
  - Paper Trading 検証レポート: kabusys.tools.paper_verification_report

前提・依存
----------
- Python 3.10+
- 必須ライブラリ（少なくとも実行時に必要となるもの）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
- 任意
  - PyYAML（config/*.yaml の中身検証を行うとき）
- sqlite3 は標準ライブラリで提供

インストール例
--------------
仮想環境を作成して依存を入れる例:

1. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate

2. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - （YAML 検証が必要なら）pip install pyyaml

セットアップ手順
---------------
1. プロジェクトルートに移動（.git や pyproject.toml のある場所）
2. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - または手動で .env を作成（.env.example があれば参考に）

3. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになる: python -m kabusys.validate_config --strict

4. DB 初期化:
   - monitoring モジュールは起動時に必要なテーブルを自動作成します（init_monitoring_db）。
   - Paper Trading 用 DB は paper_trading モードで別ファイル（デフォルト: data/paper_trading.db）を使用。

主要な環境変数（一部）
---------------------
（config.Settings による解釈・デフォルト値）
- 必須:
  - JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
  - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- 一般設定:
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
- DB パス:
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — デフォルト: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 DB（デフォルト: data/paper_trading.db）
- AI:
  - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector を使う場合必須）
- Paper Trading:
  - PAPER_FILL_MODE — instant | partial | never | reject （デフォルト: instant）
- 監視 / 制御:
  - PID_FILE_PATH — デフォルト: data/execution.pid
  - KILL_FLAG_PATH — デフォルト: data/kill.flag
  - KILL_FLAG_CLEAR_ON_START — 0|1（デフォルト 0）
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

実行方法（主要コマンド）
-----------------------
- 環境ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- ExecutionEngine を起動（発注エンジン）:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使い data/paper_trading.db に記録され、本番 DB と分離されます。
  - ExecutionEngine は data/execution.pid に PID を書きます。停止させるには監視側が data/kill.flag を書くか、プロセスを停止してください。
- Monitoring を起動（監視ループ）:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（デフォルト 60 秒）
  - 監視は常に本番 sqlite_path を参照（環境にかかわらず）
- Paper Trading 検証レポート生成:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: data/paper_trading.db、環境変数 PAPER_TRADING_SQLITE_PATH でも指定可
- AI モジュール（プログラムから呼び出す形）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - conn: DuckDB 接続オブジェクト
    - api_key: None の場合は環境変数 OPENAI_API_KEY を参照
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

停止・Kill Switch の仕組み
------------------------
- KillSwitch（kabusys.monitoring.kill_switch）は RiskMonitor の結果や各種条件により data/kill.flag を書き込みます。
- ExecutionEngine は起動時・実行中に kill.flag の有無を確認し、存在する場合は停止処理を行います。
- run_monitoring/run_execution にそれぞれ stop_requested.flag / execution.pid 等のフラグファイルパスが利用されています（data/ 以下）。

開発者向けメモ
---------------
- config モジュールはプロジェクトルート（.git か pyproject.toml）を探索して .env を自動読み込みします。自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- .env は決してリポジトリにコミットしないこと（config_setup.py でも注意喚起があります）。
- DuckDB を使ったリサーチ機能は prices_daily / raw_financials / raw_news 等のテーブルを前提にしています。データ投入は別スクリプト（本 README に含まれていない）で行ってください。
- AI 呼び出し部分（OpenAI）はレート制限・ネットワークエラー等を考慮したリトライロジックを持っていますが、API キーと通信環境は十分に用意してください。

ディレクトリ構成（主なファイル）
--------------------------------
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — 市場レジーム判定（OpenAI + MA200）
  - monitoring/
    - monitoring_db.py       — SQLite 監視 DB（テーブル作成 / 永続化 API）
    - system_monitor.py      — CPU/メモリ/ディスク/プロセス/データ鮮度監視
    - trade_monitor.py       — 滞留注文 / 約定異常監視
    - risk_monitor.py        — ドローダウン / ポジション数監視
    - kill_switch.py         — kill.flag の作成/削除
    - monitoring_engine.py   — 各 Monitor を束ねる実行エンジン
    - alert_manager.py       — （アラート送信を扱う想定のマネージャ）
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 株数計算・投下資金スケーリング
    - risk_adjustment.py     — セクター制限・レジーム乗数
  - research/
    - factor_research.py     — Momentum/Volatility/Value 等
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - utils/
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - execution/               — 発注関連（OrderManager, ExecutionEngine, broker_factory 等）※実装ファイル群（省略）
  - data/                    — data ファイル（実行時に生成される DB / pid / flag 等）
  - その他:
    - 各種モジュールに単体関数があり、ライブラリ用途でも利用できます（例: portfolio.calc_position_sizes、research.calc_momentum）。

注意事項 / 運用上のヒント
------------------------
- KABUSYS_ENV を必ず確認してください。live モードは本番発注を行います。初回は development / paper_trading で動作確認することを推奨します。
- paper_trading は本番 DB と分離されます（PAPER_TRADING_SQLITE_PATH を使用）。ペーパートレードで十分な検証を行ってから live を使ってください。
- Kill Switch と監視は本番安全性に直接関係するため、KILL_FLAG_CLEAR_ON_START の値や LINE 通知設定などを本番運用前に必ず確認してください。
- .env に API キーなどを保存する場合は取り扱いに注意し、機密管理を行ってください。

ライセンス・バージョン
----------------------
- パッケージバージョン: src/kabusys/__version__ = 0.1.0
- ライセンス情報はプロジェクトルート（LICENSE 等）を確認してください（このリポジトリのコードブロックには含まれていません）。

以上。必要であれば、セットアップ手順の詳細化（systemd / supervisor でのデプロイ例、Dockerfile、requirements.txt の推奨内容など）も作成します。必要なものを教えてください。