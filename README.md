README — KabuSys（日本語）
======================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を行うための小型フレームワークです。本リポジトリには以下の主要機能を含みます。

- 実行エンジン（ExecutionEngine）: 発注・リスク管理・再整合を行う実行系（本番 / ペーパートレード対応）
- 監視（Monitoring）: システム状態・注文ログ・リスク監視と Kill Switch（停止フラグ）機能
- ポートフォリオ構築: 候補選定、重み付け、ポジションサイズ計算、セクター制限
- 研究（Research）: ファクター計算（モメンタム、ボラティリティ、バリュー等）、特徴量解析、IC 計算
- AI 統合: ニュース NLP（OpenAI）を用いた銘柄センチメント集計および市場レジーム判定
- ユーティリティ: 環境設定ウィザード、設定検証、ログ設定、プロセス優先度制御、レポート生成ツール

主な設計方針
- 本番とペーパートレードの DB を分離可能（KABUSYS_ENV により制御）
- ルックアヘッド（将来情報参照）を避ける実装方針
- OpenAI 呼び出しは外部 API として明確に分離、失敗時はフェイルセーフで継続

機能一覧
--------
- 環境設定ウィザード: python -m kabusys.config_setup で .env を対話的に作成/更新
- 設定検証: python -m kabusys.validate_config で .env および config/*.yaml のチェック
- 実行エンジン起動: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは MockBroker を使用し data/paper_trading.db に記録
- 監視ループ起動: python -m kabusys.run_monitoring
  - 環境に関係なく production sqlite_path を使用して監視ログを保持
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を調整（デフォルト 60 秒）
- Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report
- AI 機能:
  - kabusys.ai.score_news(...) : ニュースを LLM でスコアリングし ai_scores に書き込む
  - kabusys.ai.regime_detector.score_regime(...) : 市場レジーム判定と market_regime 書き込み
- 研究用 API:
  - kabusys.research.calc_momentum / calc_volatility / calc_value
  - kabusys.research.calc_forward_returns / calc_ic / factor_summary

動作要件
--------
- Python 3.10 以上（型注釈で union 型演算子 `|` を使用）
- システムパッケージ（一般的なもの）:
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（設定ファイル検証を行う場合、任意）
- SQLite は標準ライブラリで利用
- ネットワーク接続（本番ブローカー・OpenAI API 等を利用する場合）

セットアップ手順
----------------
1. リポジトリ取得
   - git clone <repository-url>
   - cd <repository-root>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージインストール
   - pip install --upgrade pip
   - pip install duckdb psutil openai
   - （任意）pip install pyyaml

   ※ プロジェクトに requirements.txt がない場合は必要に応じて追加してください。

4. 環境変数設定
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
     - これによりプロジェクトルートに .env を作成できます（.env は絶対に Git にコミットしないでください）。
   - もしくは手動で .env を作成し、下記の主要な環境変数を設定してください。

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — default: development
- OPENAI_API_KEY (AI 機能利用時に必要)
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
- PAPER_FILL_MODE — paper_trading 時の約定モード（instant|partial|never|reject）
- LOG_LEVEL — default: INFO
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — （任意）アラート通知用
- KILL_FLAG_CLEAR_ON_START — 起動時 kill flag を自動クリアする場合は 1（本番では 0 推奨）

5. 設定検証
   - python -m kabusys.validate_config
   - 必要に応じて --strict フラグで警告も FAIL 扱いにできます

使い方（実行）
--------------
- 実行エンジン（ExecutionEngine）起動:
  - python -m kabusys.run_execution
  - 注意: data/execution.pid や data/stop_requested.flag、data/kill.flag を使って制御します
  - KABUSYS_ENV=paper_trading の場合は paper_trading DB（PAPER_TRADING_SQLITE_PATH）が使われます

- 監視ループ起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数で秒単位のポーリング間隔を変更できます（デフォルト 60 秒）
  - 監視は設定に関係なく settings.sqlite_path（監視用の本番 DB）を使用します

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

ライブラリ / API の使用例
-----------------------
- 研究用ファクター計算（DuckDB 接続を渡す）:
  from kabusys.research import calc_momentum
  result = calc_momentum(duckdb_conn, target_date)

- ニュース NLP スコアリング（OpenAI API キーを環境変数または引数で指定）:
  from kabusys.ai import score_news
  count = score_news(duckdb_conn, target_date, api_key="sk-...")

注意点
- .env は必ず機密情報を含むので Git にコミットしないでください
- 本番環境 (KABUSYS_ENV=live) では kill flag の自動クリア (KILL_FLAG_CLEAR_ON_START=1) を避けてください
- OpenAI を使用する場合は API 呼び出しのコストとレート制限に注意してください
- 監視は production の sqlite_path を参照します（監視データは実行環境に依存せず production path に保存されます）

ディレクトリ構成
----------------
（src/kabusys 配下を中心に抜粋）

- src/kabusys/
  - __init__.py                 — パッケージ定義、バージョン
  - config.py                   — 環境変数 / Settings 管理、自動 .env ロード
  - config_setup.py             — 対話式 .env ウィザード（CLI）
  - validate_config.py          — 起動前設定検証（CLI）
  - run_execution.py            — ExecutionEngine 起動スクリプト（CLI）
  - run_monitoring.py           — SystemMonitor ポーリング起動スクリプト（CLI）

  - ai/
    - news_nlp.py               — ニュースの LLM スコアリング
    - regime_detector.py        — 市場レジーム判定（LLM + MA 合成）
    - __init__.py

  - execution/                  — 実行エンジン関連（broker, order_manager 等）
    - (複数ファイル: ExecutionEngine, OrderManager, RiskManager, Reconciler, BrokerFactory 等)

  - monitoring/
    - monitoring_db.py          — SQLite による監視ログ永続化
    - system_monitor.py         — システム状態・データ鮮度監視
    - trade_monitor.py          — 注文滞留・約定異常検出（概念）
    - risk_monitor.py           — ドローダウン / ポジション上限監視
    - kill_switch.py            — kill.flag 管理
    - monitoring_engine.py      — 各 Monitor をまとめるエンジン
    - alert_manager.py          — （アラート通知の実装ポイント）

  - portfolio/
    - portfolio_builder.py      — 候補選定・重み計算
    - position_sizing.py        — 株数決定・投下金額・丸め処理
    - risk_adjustment.py        — セクターキャップ・レジーム乗数
    - __init__.py

  - research/
    - factor_research.py        — momentum / volatility / value ファクター計算
    - feature_exploration.py    — 将来リターン・IC・統計サマリー
    - __init__.py

  - data/                       — （実行時に生成される想定）
    - monitoring.db (デフォルト: data/monitoring.db)
    - kabusys.duckdb (デフォルト: data/kabusys.duckdb)
    - paper_trading.db (ペーパートレード用)
    - kill.flag, stop_requested.flag, execution.pid などフラグ/制御ファイル

  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト

  - utils/
    - logging_setup.py          — 統一ログ設定ユーティリティ
    - process_priority.py       — プロセス優先度 / CPU affinity 設定ユーティリティ
    - __init__.py

運用上のヒント
--------------
- ログはデフォルトで logs/<app_name>.log に日次ローテートで保存されます。LOG_DIR で変更可能です。
- 停止指示は data/stop_requested.flag を作成すると起動中のスクリプトがそれを検出して安全に停止します。
- Kill Switch（data/kill.flag）はリスクトリガー発生時に ExecutionEngine 側を強制停止させる仕組みです。起動時にクリアするかは設定で制御してください。
- Paper Trading の検証は tools/paper_verification_report.py を使うと主要指標（稼働率、成功率、レイテンシ等）をまとめて出力できます。

ライセンス / 貢献
-----------------
（ここにプロジェクトのライセンスと貢献方法を追記してください）

お問い合わせ / 参考
------------------
- 実装の詳細はソース内の docstring やコメントに記載されています。必要な箇所を参照してください。