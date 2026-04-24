README
=====

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした小規模なコードベースです。
主な機能としてシグナル生成やポートフォリオ構築、発注エンジン（ExecutionEngine）、
監視（Monitoring）、Paper Trading 用の検証ツール、ニュース NLP / レジーム判定などを含みます。

特徴
----
- 実行環境分離:
  - KABUSYS_ENV により development / paper_trading / live を切替可能。
  - paper_trading モードでは MockBrokerClient を使い data/paper_trading.db に記録し、本番 DB と分離。
- モジュール構成:
  - execution: 発注エンジン、オーダー管理、リスク管理、リコンシリエーションなど
  - monitoring: システム監視、トレード監視、リスク監視、Kill Switch
  - portfolio: 候補選定・重み計算・ポジションサイズ計算・セクター制限
  - research: ファクター計算・特徴量解析（DuckDB 経由）
  - ai: ニュース NLP（OpenAI）・レジーム検出
  - tools: 検証レポート生成スクリプト等
- ロギング:
  - 統一的な setup_logging ユーティリティを提供（コンソール + 日次ローテートファイル出力）
- 設定管理:
  - .env 自動読み込み（プロジェクトルート検出）と対話式設定ウィザード、起動前検証 CLI を提供
- データベース:
  - DuckDB（分析用、デフォルト: data/kabusys.duckdb）
  - SQLite（監視用: data/monitoring.db、Paper Trading 用: data/paper_trading.db）

主要機能一覧
--------------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番 / ペーパーで DB を分離し、BrokerClientFactory を通じてブローカーと連携
- Monitoring（run_monitoring.py、MonitoringEngine）
  - システム状態・データ鮮度・滞留注文・リスク監視、Kill Switch と通知連携
- 設定ウィザード（config_setup.py）と設定検証 CLI（validate_config.py）
- Paper Trading 検証レポート（tools/paper_verification_report.py）
  - 稼働率・注文成立率・送信率・レイテンシ等の指標算出と PASS/FAIL 判定
- Portfolio モジュール
  - 候補選定、等重・スコア重みによる重み付け、リスクベースのポジションサイズ算出
- Research モジュール
  - モメンタム・ボラティリティ・バリュー等のファクター計算、Forward Returns・IC 計算
- AI モジュール
  - ニュース記事を OpenAI でセンチメント化して ai_scores に書き込む機能
  - 市場レジーム判定（ma200 + マクロセンチメント合成）

セットアップ手順
----------------
1. リポジトリをクローン / 取得
   - この README はパッケージの src/kabusys 以下を前提とします。

2. Python 仮想環境と依存パッケージ
   - python 3.9+ を想定
   - 一例:
     python -m venv .venv
     source .venv/bin/activate
     pip install --upgrade pip
   - 必要ライブラリ（主要なもの）:
     - duckdb
     - psutil
     - openai (ai 機能を使う場合)
     - PyYAML（validate_config の YAML 検証を行う場合に推奨）
   - 例:
     pip install duckdb psutil openai pyyaml

   ※ requirements.txt は本リポジトリに含まれていないため、使用する機能に応じて適宜インストールしてください。

3. 初期設定 (.env)
   - 対話式ウィザードで .env を作成:
     python -m kabusys.config_setup
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 本番で OpenAI を使う場合:
     - OPENAI_API_KEY を設定（.env または環境変数）
   - .env はプロジェクトルートに置く（.git にコミットしないこと）

4. 設定検証
   - 起動前に設定を検証:
     python -m kabusys.validate_config
   - 警告もエラー扱いにする strict モード:
     python -m kabusys.validate_config --strict

5. ディレクトリ / ファイル初期化
   - logs/（ログ用）や data/（pid/flag/DB）などは自動作成されます（権限が必要）。
   - 監視 DB（デフォルト）: data/monitoring.db
   - DuckDB（デフォルト）: data/kabusys.duckdb
   - Paper Trading DB（paper_trading モード）: data/paper_trading.db

使い方（起動・実行例）
---------------------

- ExecutionEngine を起動（本番 / 開発 / ペーパーは KABUSYS_ENV で切替）
  - 環境変数設定例（bash）:
    export KABUSYS_ENV=development
    export JQUANTS_REFRESH_TOKEN=...
    export KABU_API_PASSWORD=...
  - 起動:
    python -m kabusys.run_execution

  - paper_trading モードで起動すると MockBrokerClient を使用し data/paper_trading.db に記録されます:
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution

  - 実行中の停止:
    - プロセスは data/stop_requested.flag や data/kill.flag を監視し、フラグがあれば停止します。
    - Kill Switch はリスク条件を満たした際に data/kill.flag を書いて ExecutionEngine に停止シグナルを送ります。

- Monitoring を起動
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で設定（デフォルト 60 秒）
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring

  - 監視は常に本番 sqlite_path（Settings.sqlite_path）を利用します（環境に依存せず監視 DB を統一）。

- 設定ウィザード / 検証
  - ウィザード:
    python -m kabusys.config_setup
  - 検証:
    python -m kabusys.validate_config

- Paper Trading 検証レポート
  - 例（期間指定）:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI 関連（ニューススコア / レジーム）
  - これらはモジュール関数として提供されています（CLI ではなくスクリプトやスケジューラー経由で呼び出し）。
  - OpenAI API キーが必要:
    export OPENAI_API_KEY=sk-...

運用上の注意 / 重要ポイント
----------------------------
- .env の自動ロード:
  - デフォルトでプロジェクトルートの .env / .env.local を自動読み込みします。
  - 自動ロードを無効にする場合:
    export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- PID / Flag / Stop ファイル:
  - 実行スクリプトは data/execution.pid や data/stop_requested.flag、data/kill.flag を使用します。
  - これらは手動で操作可能ですが、本番での扱いは慎重に行ってください。
- ログ:
  - デフォルト: logs/<app_name>.log（日次ローテーション、30日保持）
  - ログレベルは LOG_LEVEL または setup_logging の引数で制御
- Paper Trading と本番データの分離:
  - paper_trading モードは DB を分離しており、本番データを汚染しない設計です。運用時は KABUSYS_ENV を必ず確認してください。
- OpenAI の呼び出し:
  - ネットワークエラー・429・5xx に対してリトライ実装あり。ただし API 利用料とレート制限には注意してください。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys/ 以下の主要なファイル・ディレクトリです（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / Settings 管理（.env 自動ロード含む）
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 起動前チェック CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - execution/                 — Execution 関連（broker_factory, execution_engine, order_manager 等）
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
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
  - data/                      — データパイプライン / DuckDB 関連（prices_daily 等） ※実装ファイル群
  - utils/
    - logging_setup.py
    - process_priority.py

補足（開発者向け）
------------------
- Settings クラス（config.py）で許容する環境値やデフォルトパスが定義されています。カスタマイズはここか .env で行います。
- ロギングは setup_logging() を各起動スクリプトの最初に呼ぶことで統一されます。
- Monitoring / Execution 両方のプロセスで data/stop_requested.flag を使って安全に停止できます（監視は stop を検知してループを抜ける、実行エンジンは run_session を停止）。

ライセンス・その他
------------------
- 本 README はコードベースに付随する基本的な説明です。実運用前に config/*.yaml（存在する場合）や .env の内容を確認してください。
- このリポジトリのライセンス情報はプロジェクトルートの LICENSE（存在する場合）を参照してください。

問題報告・拡張
----------------
- 新しい機能追加やバグ報告はプロジェクトの issue / PR のフローに従ってください。
- 研究・AI モジュールは外部 API（OpenAI）に依存するため、テスト環境向けにモック化して利用することを推奨します。