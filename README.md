KabuSys — 日本株自動売買システム
===============================

以下はこのコードベース（src/kabusys/*）の README です。起動スクリプト、監視・実行コンポーネント、研究用モジュール、AI連携などを含む自動売買フレームワークの概要・セットアップ・使い方を日本語でまとめています。

プロジェクト概要
----------------
KabuSys は日本株の自動売買システム向けライブラリ兼起動スクリプト群です。主な目的は
- 発注エンジン（ExecutionEngine）の実行（実口座 / ペーパートレード切替）
- システム稼働・注文状況・リスク監視（Monitoring）
- ポートフォリオ構築・ポジションサイズ計算等の純関数群（研究・戦略部）
- DuckDB を使った調査/ファクター計算（research）
- OpenAI を使ったニュース NLP（AI モジュール）
- 開発用の設定ウィザード・設定検証ツール・レポート生成ツール

特徴（機能一覧）
----------------
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により paper_trading と live を切替）
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔変更可）
- 設定管理
  - config.py: 環境変数／.env の自動読み込みと Settings クラス
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: 起動前の設定チェック CLI
- 監視（monitoring）
  - system_monitor, trade_monitor, risk_monitor, monitoring_engine, kill_switch, monitoring_db
  - kill.flag による安全停止（Kill Switch）
- 実行（execution）
  - BrokerClientFactory（本番/モック切替）、ExecutionEngine、OrderManager、RiskManager、Reconciler、OrderRepository
  - paper_trading 時は MockBrokerClient を使い data/paper_trading.db に分離保存
- ポートフォリオ構築（純粋関数）
  - portfolio_builder: 候補選定 / 重み計算（等分・スコア加重）
  - position_sizing: 株数算出・lot 単位丸め・aggregate cap 調整
  - risk_adjustment: セクターキャップ・レジーム乗数
- 研究（research）
  - factor_research: モメンタム/ボラティリティ/バリューファクター算出（DuckDB）
  - feature_exploration: 将来リターン計算・IC（スピアマン）・統計サマリ
- AI（ai）
  - news_nlp.score_news: raw_news を集約して OpenAI へ投げ、ai_scores テーブルに保存
  - regime_detector.score_regime: マクロニュース＋ETF MA を合成して市場レジーム判定
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成

前提・依存パッケージ
-------------------
主な依存（開発時にインストールが必要）:
- Python 3.9+
- duckdb
- psutil
- openai (AI 機能使用時)
- PyYAML（validate_config の YAML 検証を行いたい場合）

セットアップ手順
----------------
1. リポジトリを取得し、仮想環境を作成・有効化する:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール:
   - pip install duckdb psutil openai pyyaml
   - ※AI 機能を使わない場合は openai を必須にする必要はありません。
   - requirements.txt があればそれを利用してください（本リポジトリに含まれていない場合は手動で）。

3. .env の準備:
   - 対話式ウィザードを使う（推奨）:
       python -m kabusys.config_setup
     これで .env を生成できます（ファイルはプロジェクトルートに作成される想定）。
   - サンプル項目:
       JQUANTS_REFRESH_TOKEN=your_token_here
       KABU_API_PASSWORD=your_kabu_password
       KABUSYS_ENV=development  # development | paper_trading | live
       DUCKDB_PATH=data/kabusys.duckdb
       SQLITE_PATH=data/monitoring.db
       LOG_LEVEL=INFO
       OPENAI_API_KEY=sk-...  # AI 機能を使う場合

4. 設定検証（任意だが推奨）:
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります。

5. データディレクトリを作成（任意。スクリプトは自前で作ることもある）:
   - mkdir -p data logs

使い方（起動例）
----------------

- ExecutionEngine を起動する（本番 or paper_trading 切替に注意）:
  - 環境変数で切替: KABUSYS_ENV=paper_trading / live / development
  - 実行:
      python -m kabusys.run_execution
    - paper_trading の場合は settings.is_paper に応じて data/paper_trading.db を使用します。
    - 起動時に data/stop_requested.flag があれば起動せず終了します。
    - ExecutionEngine は内部で execution.pid を書きます（デフォルト: data/execution.pid）。

- Monitoring を起動する（ポーリングで各モニタを定期実行）:
    python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で秒指定（デフォルト 60 秒）。
  - run_monitoring は常に本番 sqlite_path（data/monitoring.db 等）を使用して監視テーブルを初期化します。
  - 停止: data/stop_requested.flag を作成するか KeyboardInterrupt。

- Paper Trading 検証レポート生成:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db オプション、または環境変数 PAPER_TRADING_SQLITE_PATH を指定可能。

- AI モジュール（例）:
  - news_nlp.score_news(conn, target_date, api_key=None)
    - api_key が None の場合は環境変数 OPENAI_API_KEY を参照。
  - regime_detector.score_regime(conn, target_date, api_key=None)
    - OpenAI API キーが必要（AI 機能は API 呼び出しのため有料 API を使用）。

重要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — default: development
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB（default: data/paper_trading.db）
- OPENAI_API_KEY — AI 機能利用時
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）
- PAPER_FILL_MODE — paper_trading 時の注文約定挙動（instant | partial | never | reject）
- LOG_LEVEL — ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- KILL_FLAG_CLEAR_ON_START — ExecutionEngine 起動時に kill.flag を自動削除するか（0/1）

ログ
----
- ログ出力は kabusys.utils.logging_setup.setup_logging によって統一管理されます。
- デフォルトのログディレクトリは logs/、ファイル名は <app_name>.log（例: execution.log, monitoring.log）。
- ローテーション: 日次、30 日分保持。

停止・Kill Switch
----------------
- KillSwitch は data/kill.flag を書き込むことで ExecutionEngine に停止信号を送ります。監視側（MonitoringEngine）が条件を満たすと kill.flag を書き込みます。
- ExecutionEngine は起動時に KILL_FLAG_CLEAR_ON_START 設定を参照して kill.flag を自動クリアするかどうか判断します（本番では自動クリアは危険なのでデフォルトで無効推奨）。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                — .env 自動読み込みと Settings
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト

- ai/
  - news_nlp.py            — ニュースの LLM スコアリング（ai_scores への書込）
  - regime_detector.py     — 市場レジーム判定（ma200 + マクロセンチメント）
- monitoring/
  - monitoring_db.py       — SQLite テーブル定義・CRUD（system_status 等）
  - system_monitor.py      — システム稼働・データ鮮度チェック
  - trade_monitor.py       — （注文ログ監視: ファイル内にある）
  - risk_monitor.py        — ドローダウン・ポジション上限監視
  - kill_switch.py         — kill.flag 書込みユーティリティ
  - monitoring_engine.py   — 各モニタを束ねるポーリングエンジン
  - alert_manager.py       — （アラート送信用管理: ファイル内にある）
- execution/
  - execution_engine.py    — 実行エンジン
  - broker_factory.py      — Broker クライアント生成（本番/Mock 切替）
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
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py
  - process_priority.py

補足・トラブルシューティング
---------------------------
- .env は絶対にリポジトリにコミットしないでください（config_setup でも警告があります）。
- validate_config.py は起動前の必須環境変数や config/*.yaml の存在をチェックできます。PyYAML が無い場合は YAML チェックをスキップします。
- run_monitoring は常に sqlite_path（本番 DB 想定）を使うため、開発環境で monitoring を走らせる場合は SQLITE_PATH を別ファイルに設定することを推奨します。
- AI 呼び出しはネットワークエラーや API レート制限に対してリトライロジックがありますが、API キー・課金設定が正しいか事前に確認してください。
- psutil の一部機能は権限が必要な場合があります（プロセス優先度設定など）。権限不足時は警告を出してスキップします。

ライブラリ API（簡易）
---------------------
- kabusys.portfolio.select_candidates / calc_equal_weights / calc_score_weights
- kabusys.portfolio.calc_position_sizes
- kabusys.research.calc_momentum / calc_volatility / calc_value
- kabusys.research.calc_forward_returns / calc_ic / factor_summary / rank
- kabusys.ai.score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

最後に
------
この README はコードコメントと実装から必要な情報を抜粋してまとめています。実際の導入時は .env や config/*.yaml を適切に設定し、validate_config で問題ないことを確認してから run_execution/run_monitoring を起動してください。必要であれば各モジュールの docstring を参照して挙動を確認してください。質問や追加のドキュメント化が必要であれば教えてください。